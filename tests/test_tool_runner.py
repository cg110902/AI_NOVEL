import json
import tempfile
import unittest
from pathlib import Path

from tool_runner import ToolResult, run


class ToolRunnerTests(unittest.TestCase):
    def test_result_json_and_ok(self):
        result = ToolResult(("demo",), 0, '{"ok": true}', "")
        self.assertTrue(result.ok)
        self.assertEqual(result.json(), {"ok": True})

    def test_cli_help_json_e2e(self):
        result = run(("help", "--json"), timeout=30)
        self.assertTrue(result.ok, result.stderr)
        payload = result.json()
        self.assertIn("commands", payload)
        self.assertTrue(any(item["name"] == "hello" for item in payload["commands"]))

    def test_workspace_is_forwarded(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run(("hello", "--json"), workspace=Path(directory), timeout=30)
            self.assertTrue(result.ok, result.stderr)
            self.assertEqual(result.json()["workspace"], str(Path(directory).name))

    def test_rejects_empty_args(self):
        with self.assertRaises(ValueError):
            run(())


if __name__ == "__main__":
    unittest.main()
