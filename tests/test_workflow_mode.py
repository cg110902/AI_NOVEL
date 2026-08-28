# -*- coding: utf-8 -*-
"""
Workflow mode (manual / automatic) contract tests.

Two layers:
  * config layer — default resolution, workspace override, legacy aliases,
    and hard failure on garbage values;
  * CLI layer — `studio.py mode` view/set/persist and mode visibility in
    `status` / `hello --json`, run through the public CLI in a throwaway
    workspace (same style as test_cli_e2e).
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))

from config_core import load_effective_config, clear_cache  # noqa: E402

_STUDIO = _ROOT / "studio.py"


class WorkflowModeConfigTests(unittest.TestCase):
    def setUp(self):
        clear_cache()
        self.home = Path(tempfile.mkdtemp(prefix="mode_cfg_"))

    def tearDown(self):
        clear_cache()
        shutil.rmtree(self.home, ignore_errors=True)

    def _ws_profile(self, mode=None):
        ws = self.home / f"ws_{len(list(self.home.iterdir()))}"
        meta = ws / "00_meta"
        meta.mkdir(parents=True, exist_ok=True)
        payload = {}
        if mode is not None:
            payload = {"workflow": {"mode": mode}}
        (meta / "genre_profile.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ws

    def test_default_mode_is_automatic(self):
        self.assertEqual(
            load_effective_config(None).get("workflow", {}).get("mode"),
            "automatic",
        )

    def test_workspace_override_to_manual(self):
        ws = self._ws_profile("manual")
        self.assertEqual(
            load_effective_config(str(ws)).get("workflow", {}).get("mode"),
            "manual",
        )

    def test_legacy_aliases_are_normalized(self):
        for legacy, expected in (("autonomous_creation", "automatic"),
                                 ("director_review", "manual"),
                                 ("auto", "automatic")):
            clear_cache()
            ws = self._ws_profile(legacy)
            self.assertEqual(
                load_effective_config(str(ws)).get("workflow", {}).get("mode"),
                expected,
                msg=f"legacy value {legacy!r} must map to {expected}",
            )

    def test_invalid_mode_is_config_error(self):
        ws = self._ws_profile("yolo")
        with self.assertRaises(ValueError):
            load_effective_config(str(ws))

    def test_builtin_defaults_keep_healing_fields(self):
        wf = load_effective_config(None).get("workflow", {})
        self.assertTrue(wf.get("self_healing_pipeline"))
        self.assertEqual(wf.get("max_auto_retry_attempts"), 3)
        for gate in ("initialization_alignment", "final_review",
                     "critical_failure", "retry_exhausted", "state_conflict"):
            self.assertTrue(wf.get("manual_gates", {}).get(gate), msg=gate)


class WorkflowModeCliTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="mode_cli_"))
        self.ws = self.home / "ws"

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(_STUDIO), *args, "--workspace", str(self.ws)],
            cwd=str(_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=120,
        )

    def test_mode_view_set_and_persist(self):
        r = self.run_cli("init", "-t", "模式书", "-g", "悬疑", "-p", "林默")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

        r = self.run_cli("mode", "--json")
        self.assertEqual(r.returncode, 0)
        view = json.loads(r.stdout)
        self.assertEqual(view["mode"], "automatic")

        r = self.run_cli("mode", "--set", "manual", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["mode"], "manual")
        mode_file = self.ws / "00_meta" / "workflow_mode.json"
        self.assertTrue(mode_file.is_file())
        self.assertEqual(json.loads(mode_file.read_text(encoding="utf-8"))["mode"],
                         "manual")

        # A fresh CLI invocation must see the persisted book-level override.
        r = self.run_cli("mode", "--json")
        self.assertEqual(json.loads(r.stdout)["mode"], "manual")

        # status surfaces the mode too.
        r = self.run_cli("status")
        self.assertEqual(r.returncode, 0)
        self.assertIn("manual", r.stdout)

        # Switching back keeps the book-level file in sync.
        r = self.run_cli("mode", "--set", "automatic", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["mode"], "automatic")

    def test_mode_rejects_garbage_value(self):
        r = self.run_cli("init", "-t", "模式书", "-g", "悬疑", "-p", "林默")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        r = self.run_cli("mode", "--set", "yolo")
        self.assertEqual(r.returncode, 2)

    def test_hello_json_reports_workflow_mode(self):
        r = self.run_cli("init", "-t", "模式书", "-g", "悬疑", "-p", "林默")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        r = self.run_cli("hello", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["project"]["workflow_mode"],
                         "automatic")


if __name__ == "__main__":
    unittest.main()
