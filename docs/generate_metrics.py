# -*- coding: utf-8 -*-
"""
Project metrics generator (零第三方依赖，标准库实现).

从单一真值源收集项目实时指标，供文档以「行内数字 + HTML 注释标记」引用，
避免 README / AGENTS / tool-contracts 中的命令数、工具数、测试数、雷达子工具数与源码失步。

指标来源（单一真值源）：
    - command count   : `python studio.py help --json`（机器可读 CLI 命令地图）
    - test count      : `unittest.TestLoader().discover(tests/)` 的 countTestCases()
                        （与 `python studio.py test` 即 unittest discover 完全一致）
    - tool count      : `tools/*.py` 目录中可运行的确定性工具模块数
    - radar subtools  : `tools/studio_radar.py` 中注册的雷达子工具名列表

文档引用约定：在包含数字的文档行末尾追加一行内注释标记，例如
    python studio.py test   # 运行 105 项自动化测试 <!-- {{generated}} tests -->
生成器扫描这些标记，用正则提取行内数字并与实测值比对。

用法：
    python docs/generate_metrics.py            # 打印实测摘要 + 与文档标记的比对结果
    python docs/generate_metrics.py --json     # 输出机器可读实测指标 dict
    python docs/generate_metrics.py --check    # 校验（退出码 0=一致，1=失步；供 CI 门禁用）
"""

import sys
import re
import json
import subprocess
import argparse
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TOOLS = _ROOT / "tools"
_TESTS = _ROOT / "tests"

ENVELOPE_SCHEMA = "novel-studio.envelope/v1"

# 与 `python studio.py test`（unittest discover，cwd=项目根）保持一致的可导入路径。
# 从 docs/ 以 `python docs/generate_metrics.py` 运行时需把项目根放入 sys.path，
# 否则 test_*.py 里 `from init_new_novel import ...` 会导入失败导致计数偏低。
for _p in (_ROOT, _TOOLS, _TESTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# 文档标记：`<!-- {{generated}} <key> -->`
MARKER_RE = re.compile(r"<!--\s*\{\{\s*generated\s*\}\}\s*([A-Za-z_]+)\s*-->")
# 行内数字提取（允许“xx 项 / xx 个 / xx 命令 / xx 子工具”等中文量词）
_NUM_RE = re.compile(r"(\d+)\s*(?:项|个|命令|子工具)?")


def _command_count():
    proc = subprocess.run(
        [sys.executable, str(_ROOT / "studio.py"), "help", "--json"],
        cwd=str(_ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return None
    cmds = data.get("commands") if isinstance(data, dict) else None
    return len(cmds) if isinstance(cmds, list) else None


def _test_count():
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(str(_TESTS), pattern="test_*.py")
    return suite.countTestCases()


def _tool_count():
    if not _TOOLS.exists():
        return 0
    return len([p for p in _TOOLS.glob("*.py")
                if not p.name.startswith("__") and p.name != "_version.py"])


def _radar_subtools():
    """从 tools/studio_radar.py 提取注册的雷达子工具名（不执行/不导入该模块）。"""
    path = _TOOLS / "studio_radar.py"
    if not path.exists():
        return []
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('("'):
            continue
        if '", [' not in s and "', [" not in s:
            continue
        first = s.lstrip("(").split(",", 1)[0].strip().strip('"').strip("'")
        if first and not first.endswith(".py") and "=" not in first:
            names.append(first)
    seen = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def collect():
    return {
        "schema": ENVELOPE_SCHEMA,
        "commands": _command_count(),
        "tests": _test_count(),
        "tools": _tool_count(),
        "radar_subtools": _radar_subtools(),
        "generated_by": "docs/generate_metrics.py",
    }


def _scan_doc_markers(root, texts):
    """扫描 root 下所有 md 文件，返回 {key: [(file, 行内数字, 整行)]}。"""
    hits = {k: [] for k in texts}
    for md in root.rglob("*.md"):
        if "node_modules" in str(md):
            continue
        for ln in md.read_text(encoding="utf-8").splitlines():
            m = MARKER_RE.search(ln)
            if not m:
                continue
            key = m.group(1)
            if key not in hits:
                continue
            nm = _NUM_RE.search(ln)
            hits[key].append((md.relative_to(root), int(nm.group(1)) if nm else None, ln.strip()))
    return hits


def _diff_docs(m, hits):
    """比对文档标记数字与实测，返回失步消息列表。"""
    stale = []
    # radar 用子工具数量
    expected = {
        "commands": m["commands"],
        "tests": m["tests"],
        "tools": m["tools"],
        "radar": len(m["radar_subtools"]),
    }
    for key, rows in hits.items():
        exp = expected.get(key)
        if exp is None:
            continue
        for fname, claimed, _line in rows:
            if claimed != exp:
                stale.append(f"{fname}:{key} 文档={claimed} 实测={exp}")
    return stale


def main():
    ap = argparse.ArgumentParser(description="Project metrics collector")
    ap.add_argument("--json", action="store_true", help="输出机器可读实测指标 dict")
    ap.add_argument("--check", action="store_true",
                    help="校验文档 {{generated}} 标记数字 == 实测（退出码 0/1，供 CI 用）")
    args = ap.parse_args()

    m = collect()

    if args.json:
        print(json.dumps(m, ensure_ascii=False, indent=2))
        return 0

    texts = {"commands", "tests", "tools", "radar"}
    hits = _scan_doc_markers(_ROOT, texts)
    stale = _diff_docs(m, hits)

    if not args.check:
        print(f"命令数 {m['commands']} | 测试数 {m['tests']} | 工具数 {m['tools']} "
              f"| 雷达子工具 {len(m['radar_subtools'])}")
        if stale:
            print("⚠️  文档 {{generated}} 标记与实测不符：")
            for msg in stale:
                print("  - " + msg)
        return 0

    if stale:
        for msg in stale:
            print("STALE: " + msg)
        return 1
    print("OK: {{generated}} 标记与实测一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
