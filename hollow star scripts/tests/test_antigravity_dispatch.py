from __future__ import annotations

import json
import unittest

from tools.antigravity_dispatch import build_command, prompt_for_mode, response_from_output


class AntigravityDispatchTests(unittest.TestCase):
    def test_plan_mode_is_read_only_and_machine_readable(self) -> None:
        command = build_command("agy", "inspect the project")
        self.assertEqual(command[0:2], ["agy", "-p"])
        self.assertIn("READ-ONLY TASK", command[2])
        self.assertIn("--mode=plan", command)
        self.assertEqual(command[command.index("--output-format") + 1], "json")

    def test_write_mode_uses_accept_edits(self) -> None:
        command = build_command("agy", "repair the test", write=True, timeout=42)
        self.assertNotIn("READ-ONLY TASK", command[2])
        self.assertIn("--mode=accept-edits", command)
        self.assertIn("42s", command)

    def test_optional_flags_are_forwarded(self) -> None:
        command = build_command(
            "agy",
            "review",
            model="gemini-3-pro",
            agent="reviewer",
            effort="high",
        )
        self.assertEqual(command[command.index("--model") + 1], "gemini-3-pro")
        self.assertEqual(command[command.index("--agent") + 1], "reviewer")
        self.assertEqual(command[command.index("--effort") + 1], "high")

    def test_json_response_is_unwrapped(self) -> None:
        stdout = json.dumps({"status": "SUCCESS", "response": "done", "usage": {}})
        response, metadata = response_from_output(stdout)
        self.assertEqual(response, "done")
        self.assertEqual(metadata["status"], "SUCCESS")

    def test_non_json_output_is_preserved(self) -> None:
        self.assertEqual(response_from_output("plain response\n"), ("plain response", None))

    def test_prompt_guard_preserves_write_task(self) -> None:
        self.assertEqual(prompt_for_mode("make the change", True), "make the change")


if __name__ == "__main__":
    unittest.main()
