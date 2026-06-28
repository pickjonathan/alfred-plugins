"""Tests for transcript.py."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures", "projects")
sys.path.insert(0, ROOT)

import transcript  # noqa: E402

S1 = os.path.join(FIXTURES, "-Users-me-app", "11111111-1111-1111-1111-111111111111.jsonl")
S3 = os.path.join(FIXTURES, "-Users-me-empty", "33333333-3333-3333-3333-333333333333.jsonl")


class Coerce(unittest.TestCase):
    def test_text_and_tool_markers(self):
        content = [
            {"type": "text", "text": "hi"},
            {"type": "tool_use", "name": "Bash"},
            {"type": "tool_result"},
            {"type": "thinking"},
        ]
        out = transcript.coerce_text(content)
        self.assertIn("hi", out)
        self.assertIn("tool: Bash", out)
        self.assertIn("tool result", out)
        self.assertIn("thinking", out)


class Render(unittest.TestCase):
    def _render(self, src):
        out = os.path.join(tempfile.mkdtemp(), "t.html")
        rc = subprocess.call([sys.executable, os.path.join(ROOT, "transcript.py"), src, out])
        self.assertEqual(rc, 0)
        with open(out, encoding="utf-8") as fh:
            return fh.read()

    def test_renders_turns_and_summary(self):
        html = self._render(S1)
        self.assertIn("Fix the authentication bug in auth.py", html)  # summary banner
        self.assertIn("Help me fix the authentication bug", html)     # user turn
        self.assertIn("Let me inspect the login flow", html)          # assistant turn
        self.assertIn("Claude", html)

    def test_html_escaping(self):
        # The assistant text contains '&' which must be escaped.
        html = self._render(S1)
        self.assertIn("tokens.", html)
        self.assertIn("&amp;", html)
        self.assertNotIn("flow & tokens", html)  # raw ampersand should not survive

    def test_empty_session(self):
        html = self._render(S3)
        self.assertIn("No conversation content", html)


if __name__ == "__main__":
    unittest.main()
