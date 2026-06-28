"""Unit and integration tests for search.py."""
import json
import os
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures", "projects")
sys.path.insert(0, ROOT)

import search  # noqa: E402

S1 = os.path.join(FIXTURES, "-Users-me-app", "11111111-1111-1111-1111-111111111111.jsonl")
S2 = os.path.join(FIXTURES, "-Users-me-web", "22222222-2222-2222-2222-222222222222.jsonl")
S3 = os.path.join(FIXTURES, "-Users-me-empty", "33333333-3333-3333-3333-333333333333.jsonl")


class TextHelpers(unittest.TestCase):
    def test_coerce_text_str(self):
        self.assertEqual(search._coerce_text("hello"), "hello")

    def test_coerce_text_list(self):
        content = [
            {"type": "text", "text": "first"},
            {"type": "tool_use", "name": "Read"},
            {"type": "text", "text": "second"},
        ]
        self.assertEqual(search._coerce_text(content), "first\nsecond")

    def test_coerce_text_other(self):
        self.assertEqual(search._coerce_text(None), "")
        self.assertEqual(search._coerce_text(42), "")

    def test_is_real_prompt(self):
        self.assertTrue(search._is_real_prompt("Fix the bug"))
        self.assertFalse(search._is_real_prompt(""))
        self.assertFalse(search._is_real_prompt("   "))
        self.assertFalse(search._is_real_prompt("<command-name>/clear</command-name>"))
        self.assertFalse(search._is_real_prompt("<local-command-stdout>x</local-command-stdout>"))
        self.assertFalse(search._is_real_prompt("Caveat: blah"))
        self.assertFalse(search._is_real_prompt("[Request interrupted by user]"))

    def test_clean_truncates(self):
        out = search._clean("a" * 200, limit=10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("…"))

    def test_clean_collapses_whitespace(self):
        self.assertEqual(search._clean("a\n\n  b\tc"), "a b c")

    def test_pretty_cwd(self):
        home = os.path.expanduser("~")
        self.assertEqual(search._pretty_cwd(home + "/x"), "~/x")
        self.assertEqual(search._pretty_cwd("/opt/y"), "/opt/y")


class RelTime(unittest.TestCase):
    def test_buckets(self):
        now = time.time()
        self.assertEqual(search._rel_time(now), "just now")
        self.assertEqual(search._rel_time(now - 120), "2m ago")
        self.assertEqual(search._rel_time(now - 3 * 3600), "3h ago")
        self.assertEqual(search._rel_time(now - 2 * 86400), "2d ago")
        self.assertEqual(search._rel_time(now - 14 * 86400), "2w ago")


class ParseSession(unittest.TestCase):
    def test_summary_wins(self):
        s = search.parse_session(S1)
        self.assertEqual(s["id"], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(s["title"], "Fix the authentication bug in auth.py")
        self.assertEqual(s["cwd"], "/Users/me/app")
        self.assertEqual(s["git_branch"], "feature/login")

    def test_first_prompt_when_no_summary(self):
        s = search.parse_session(S2)
        self.assertEqual(s["title"], "Add dark mode to the settings page")
        self.assertEqual(s["git_branch"], "main")

    def test_empty_session(self):
        s = search.parse_session(S3)
        self.assertEqual(s["title"], "(no prompt yet)")
        self.assertEqual(s["cwd"], "/Users/me/empty")

    def test_missing_file(self):
        self.assertIsNone(search.parse_session(os.path.join(FIXTURES, "nope.jsonl")))


class FullText(unittest.TestCase):
    def test_match_in_body(self):
        # "flow" only appears in the assistant message body, not metadata.
        snippet = search.fulltext_snippet(S1, ["flow"])
        self.assertIsNotNone(snippet)
        self.assertIn("flow", snippet.lower())

    def test_no_match(self):
        self.assertIsNone(search.fulltext_snippet(S1, ["zzznotpresent"]))

    def test_requires_all_tokens(self):
        self.assertIsNotNone(search.fulltext_snippet(S1, ["login", "tokens"]))
        self.assertIsNone(search.fulltext_snippet(S1, ["login", "zzznotpresent"]))


class BuildItem(unittest.TestCase):
    def test_arg_and_mods(self):
        s = search.parse_session(S1)
        item = search.build_item(s)
        self.assertEqual(
            item["arg"], search.ARG_SEP.join([s["id"], s["cwd"], s["path"]])
        )
        self.assertEqual(
            set(item["mods"].keys()), {"alt", "cmd", "ctrl", "shift", "fn"}
        )
        self.assertEqual(item["quicklookurl"], s["path"])

    def test_branch_suppressed_for_main(self):
        s = search.parse_session(S2)
        item = search.build_item(s)
        self.assertNotIn("⎇", item["subtitle"])

    def test_branch_shown_for_feature(self):
        s = search.parse_session(S1)
        item = search.build_item(s)
        self.assertIn("feature/login", item["subtitle"])

    def test_snippet_subtitle(self):
        s = search.parse_session(S1)
        item = search.build_item(s, snippet="hello world")
        self.assertTrue(item["subtitle"].startswith("🔍"))


def _run(query, extra_env=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECTS_DIR"] = FIXTURES
    if extra_env:
        env.update(extra_env)
    out = subprocess.check_output(
        [sys.executable, os.path.join(ROOT, "search.py"), query], env=env
    )
    return json.loads(out)["items"]


class Integration(unittest.TestCase):
    def setUp(self):
        # Deterministic ordering: S1 newest, S2 middle, S3 oldest.
        now = time.time()
        os.utime(S1, (now, now))
        os.utime(S2, (now - 100, now - 100))
        os.utime(S3, (now - 200, now - 200))

    def test_list_all_sorted(self):
        items = _run("")
        ids = [i["uid"] for i in items]
        self.assertEqual(
            ids,
            [
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222",
                "33333333-3333-3333-3333-333333333333",
            ],
        )

    def test_metadata_filter(self):
        items = _run("dark")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["uid"], "22222222-2222-2222-2222-222222222222")

    def test_fulltext_filter(self):
        # "flow" is only in S1's conversation body.
        items = _run("flow")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["uid"], "11111111-1111-1111-1111-111111111111")
        self.assertTrue(items[0]["subtitle"].startswith("🔍"))

    def test_fulltext_disabled(self):
        items = _run("flow", extra_env={"FULLTEXT": "0"})
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].get("valid", True))

    def test_no_match(self):
        items = _run("zzznotpresentanywhere")
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].get("valid", True))


if __name__ == "__main__":
    unittest.main()
