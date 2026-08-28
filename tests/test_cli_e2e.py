# -*- coding: utf-8 -*-
"""
End-to-end tests for the public `studio.py` CLI run through `subprocess`
inside throwaway temporary workspaces.

Rationale: these cover cross-command, cross-version contract that a unit-level
tool test cannot reach — real exit codes, JSON stdout purity (stderr
isolation), failed-proposal fallout, snapshot semantics, and audit-preserving
cleanup. They must stay green on both Windows and POSIX, so we never rely on
path separators or shell quoting, and we always pass the temp workspace
through the public ``--workspace`` option.

Covered here (per task):
  * init creates a usable workspace and refuses a non-forced re-init;
  * an illegal/garbage chapter name is rejected by `lint`;
  * `lint --json` emits *pure* JSON on stdout with an empty stderr;
  * `sync` refuses empty syncs (missing draft / missing proposal) with a
    non-zero exit, and shows a failure banner + `failed/` move when the
    proposal fails validation;
  * `snapshot` rejects an empty name and tolerates duplicate names;
  * `clean` keeps the audit directories (`state_inbox/processed/` and
    `snapshots/`) intact.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_STUDIO = _ROOT / "studio.py"


# A proposal that passes the state-mutation schema but trips the field-type
# validators, so the merge engine moves it to `failed/` and prints the banner.
_BAD_TYPES_PROPOSAL = {
    "schema": "novel-studio.state-mutation/v1",
    "chapter": "ch_001",
    "chapter_title": "测试章节",
    "guns": {},                     # must be a list
    "misunderstandings": [],
    "growth_arcs": [],
    "timeline": [],
    "transactions": [],
    "synopsis": "梗概",
}

_VALID_PROPOSAL = {
    "schema": "novel-studio.state-mutation/v1",
    "chapter": "ch_001",
    "chapter_title": "测试章节",
    "guns": [],
    "misunderstandings": [],
    "growth_arcs": [],
    "timeline": [],
    "transactions": [],
    "synopsis": "梗概",
}

_DRAFT_BODY = textwrap.dedent(
    """\
    第一章 测试
    　　林澈在宗门后山修行了一夜，体内的灵气终于圆满。
    　　他抬手将一块温润的灵玉收进怀中，转身下山。
    """
).strip() + "\n"


class CliE2EBase(unittest.TestCase):
    """subprocess helpers + a per-test throwaway home directory."""

    def setUp(self):
        # mkdtemp gives us a random *absolute* path that subprocess can pass
        # literally on both Windows and POSIX.
        self.home = Path(tempfile.mkdtemp(prefix="cli_e2e_"))
        self.ws = self.home / "ws"

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def run_cli(self, *args, workspace=None, cwd=None):
        """Run `python studio.py <args>` and capture stdout/stderr as text."""
        return subprocess.run(
            [sys.executable, str(_STUDIO), *args, "--workspace", str(workspace or self.ws)],
            cwd=str(cwd) if cwd else str(_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )

    def init_ws(self, title="E2E测试书", genre="玄幻", protagonist="林澈", ws=None):
        r = self.run_cli("init", "-t", title, "-g", genre, "-p", protagonist,
                         workspace=ws or self.ws)
        self.assertEqual(r.returncode, 0, msg=f"init failed: {r.stdout}\n{r.stderr}")
        return r

    @staticmethod
    def write_text(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def write_proposal(path: Path, proposal) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
        return path


class InitCommandTests(CliE2EBase):
    def test_init_creates_usable_workspace(self):
        ws = self.ws
        self.init_ws()
        # Core SSOT tree exists.
        self.assertTrue((ws / "04_timeline_and_state" / "current_state.json").is_file())
        self.assertTrue((ws / "00_meta" / "genre_profile.json").is_file())
        self.assertTrue((ws / "00_meta" / "project_bible.md").is_file())
        # Re-initing the same book without --force is refused (non-zero, no wipe).
        before = (ws / "04_timeline_and_state" / "current_state.json").read_text(encoding="utf-8")
        r = self.run_cli("init", "-t", "E2E测试书", "-g", "玄幻", "-p", "林澈")
        self.assertEqual(r.returncode, 1)
        after = (ws / "04_timeline_and_state" / "current_state.json").read_text(encoding="utf-8")
        self.assertEqual(after, before, "non-forced re-init must not touch SSOT")

    def test_init_creates_nested_workspace(self):
        nested = self.home / "deep" / "nested" / "book"
        self.init_ws(ws=nested)
        self.assertTrue((nested / "04_timeline_and_state" / "current_state.json").is_file())


class IllegalChapterTests(CliE2EBase):
    def test_lint_rejects_garbage_chapter_name(self):
        self.init_ws()
        r = self.run_cli("lint", "not a real chapter")
        self.assertNotEqual(r.returncode, 0, msg=r.stdout)
        self.assertIn("无法解析", r.stdout)
        # A nonexistent but *validly-shaped* chapter also exits non-zero.
        r2 = self.run_cli("lint", "ch_999")
        self.assertEqual(r2.returncode, 1, msg=r2.stdout)


class LintJsonPurityTests(CliE2EBase):
    def test_lint_json_stdout_is_pure_and_stderr_empty(self):
        self.init_ws()
        r = self.run_cli("lint", "ch_999", "--json")
        self.assertEqual(r.returncode, 1)          # no draft → gate fails
        self.assertEqual(r.stderr.strip(), "")     # JSON mode: stderr isolated
        data = json.loads(r.stdout)                # whole stdout parses as JSON
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["command"], "lint")
        self.assertEqual(data["target"], "ch_999")

    def test_sync_jsonlike_not_expected_but_real_commands_parse(self):
        # Guard: the JSON contract is stable enough for programmatic callers.
        self.init_ws()
        r = self.run_cli("lint", "ch_999", "--json")
        payload = json.loads(r.stdout)
        self.assertIn("confusion", payload)


class SyncCommandTests(CliE2EBase):
    def test_sync_refuses_missing_draft(self):
        self.init_ws()
        # No draft and no proposal → non-zero, explicit refusal.
        r = self.run_cli("sync", "ch_002")
        self.assertEqual(r.returncode, 1, msg=r.stdout)
        self.assertIn("拒绝空同步", r.stdout)

    def test_sync_refuses_draft_without_proposal(self):
        self.init_ws()
        self.write_text(self.ws / "05_manuscript" / "vol_01" / "finalized" / "ch_001.md",
                        _DRAFT_BODY)
        r = self.run_cli("sync", "ch_001")
        self.assertEqual(r.returncode, 1, msg=r.stdout)
        self.assertIn("未找到正式状态提案", r.stdout)

    def test_sync_failed_proposal_banner_and_failed_move(self):
        self.init_ws()
        self.write_text(self.ws / "05_manuscript" / "vol_01" / "finalized" / "ch_001.md",
                        _DRAFT_BODY)
        inbox = self.ws / "04_timeline_and_state" / "state_inbox"
        self.write_proposal(inbox / "ch_001.json", _BAD_TYPES_PROPOSAL)
        r = self.run_cli("sync", "ch_001")
        self.assertEqual(r.returncode, 1, msg=r.stdout)
        # The failure banner is user-visible (this is the failure *signal*).
        self.assertIn("未通过校验", r.stdout)
        self.assertIn("failed/", r.stdout)
        # The offending proposal is quarantined into failed/.
        self.assertTrue((inbox / "failed" / "ch_001.json").is_file(),
                        msg="proposal must move to state_inbox/failed/")

    def test_sync_success_path(self):
        self.init_ws()
        self.write_text(self.ws / "05_manuscript" / "vol_01" / "finalized" / "ch_001.md",
                        _DRAFT_BODY)
        inbox = self.ws / "04_timeline_and_state" / "state_inbox"
        self.write_proposal(inbox / "ch_001.json", _VALID_PROPOSAL)
        r = self.run_cli("sync", "ch_001")
        self.assertEqual(r.returncode, 0, msg=r.stdout)
        self.assertIn("同步完成", r.stdout)
        snapshots = (self.ws / "04_timeline_and_state" / "snapshots").glob("*ch_001_done*")
        self.assertTrue(list(snapshots), "sync must create an end-of-sync snapshot")


class SnapshotCommandTests(CliE2EBase):
    def test_snapshot_rejects_empty_name(self):
        self.init_ws()
        r = self.run_cli("snapshot", "")
        self.assertEqual(r.returncode, 1, msg=r.stdout)
        self.assertIn("不能为空", r.stdout)

    def test_snapshot_duplicate_name_coexists(self):
        self.init_ws()
        r1 = self.run_cli("snapshot", "checkpoint_x")
        self.assertEqual(r1.returncode, 0, msg=r1.stdout)
        r2 = self.run_cli("snapshot", "checkpoint_x")
        self.assertEqual(r2.returncode, 0, msg=r2.stdout)
        snaps = list((self.ws / "04_timeline_and_state" / "snapshots").glob("*checkpoint_x*"))
        self.assertEqual(len(snaps), 2, msg="duplicate name must create a second, time-stamped snapshot")


class CleanCommandTests(CliE2EBase):
    def test_clean_preserves_audit_dirs(self):
        self.init_ws()
        ws = self.ws
        # Plant sensible real content in the audit dirs before cleaning.
        inbox = ws / "04_timeline_and_state" / "state_inbox"
        self.write_text(inbox / "processed" / "ch_000_done.json", "{}")
        self.write_text(ws / "05_manuscript" / "vol_01" / "raw_drafts" / "ch_001_v1.md",
                        "初稿占位")
        snap_dir = ws / "04_timeline_and_state" / "snapshots"
        self.run_cli("snapshot", "pre_clean")   # real snapshot
        self.assertTrue(list(snap_dir.glob("*pre_clean*")))

        r = self.run_cli("clean")
        self.assertEqual(r.returncode, 0, msg=r.stdout)
        self.assertIn("清空", r.stdout)
        # Manuscript is wiped…
        self.assertTrue((inbox / "processed" / "ch_000_done.json").is_file(),
                        msg="clean must keep state_inbox/processed/ (audit trail)")
        # …but audit directories and their contents survive untouched.
        self.assertTrue((inbox / "processed").is_dir())
        self.assertTrue(snap_dir.is_dir())
        self.assertTrue(list(snap_dir.glob("*pre_clean*")),
                        msg="clean must keep snapshots/ for rollback")
        self.assertEqual(list((ws / "05_manuscript" / "vol_01" / "raw_drafts").glob("*.md")),
                         [], msg="clean must empty the manuscript")


if __name__ == "__main__":
    unittest.main()