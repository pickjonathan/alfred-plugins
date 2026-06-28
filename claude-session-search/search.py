#!/usr/bin/env python3
"""
Alfred Script Filter: search through Claude Code sessions.

Scans ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl, builds a human
readable description for each session, filters by the Alfred query and emits
Alfred Script Filter JSON.

Matching is two-tier:
  1. metadata match  — query tokens vs description / path / branch / id
  2. full-text match — query tokens vs the whole conversation body (enabled
     when every query token is >= MIN_FULLTEXT_LEN and FULLTEXT != "0")

The `arg` carried to actions is "<session-id>|||<cwd>|||<jsonl-path>", consumed
by resume.sh / action.sh / quicklook.sh.

Targets the system Python 3 (/usr/bin/python3, 3.9) so it runs reliably inside
Alfred's environment with no third-party dependencies.
"""

import glob
import json
import os
import re
import sys
import time

PROJECTS_DIR = os.path.expanduser(
    os.environ.get("CLAUDE_PROJECTS_DIR", "~/.claude/projects")
)
ARG_SEP = "|||"
MAX_RESULTS = 200
# How many lines to scan per file when hunting for the first real prompt / cwd.
HEAD_LINES = 400
# Full-text: only kick in for reasonably specific tokens, and cap bytes read.
MIN_FULLTEXT_LEN = 3
FULLTEXT_MAX_BYTES = 2 * 1024 * 1024
FULLTEXT = os.environ.get("FULLTEXT", "1") != "0"

_COMMAND_TAG_RE = re.compile(r"</?command-(name|message|args)>", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def _coerce_text(content):
    """Return plain text from a message `content` (str or list of parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text" and p.get("text"):
                parts.append(p["text"])
        return "\n".join(parts)
    return ""


def _is_real_prompt(text):
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    if _COMMAND_TAG_RE.search(t):
        return False
    if t.startswith("<"):  # local-command-stdout / caveat / tool wrappers
        return False
    if t.lower().startswith("caveat:"):
        return False
    if t.startswith("[Request interrupted"):
        return False
    return True


def _clean(text, limit=120):
    t = _WS_RE.sub(" ", text).strip()
    if len(t) > limit:
        t = t[: limit - 1].rstrip() + "…"
    return t


def _rel_time(epoch):
    delta = max(0, int(time.time() - epoch))
    mins = delta // 60
    if mins < 1:
        return "just now"
    if mins < 60:
        return "%dm ago" % mins
    hours = mins // 60
    if hours < 24:
        return "%dh ago" % hours
    days = hours // 24
    if days < 7:
        return "%dd ago" % days
    weeks = days // 7
    if weeks < 5:
        return "%dw ago" % weeks
    months = days // 30
    if months < 12:
        return "%dmo ago" % months
    return "%dy ago" % (days // 365)


def _pretty_cwd(cwd):
    home = os.path.expanduser("~")
    if cwd and cwd.startswith(home):
        return "~" + cwd[len(home):]
    return cwd or "?"


def _decode_project_dir(name):
    if not name:
        return None
    return name.replace("-", "/")


def parse_session(path):
    """Extract metadata from one session jsonl file. Returns dict or None."""
    session_id = os.path.splitext(os.path.basename(path))[0]
    project_dir = os.path.basename(os.path.dirname(path))

    cwd = None
    summary = None
    first_prompt = None
    git_branch = None

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= HEAD_LINES and first_prompt is not None and cwd is not None:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue

                otype = obj.get("type")
                if otype == "summary" and obj.get("summary"):
                    summary = obj["summary"]
                if cwd is None and obj.get("cwd"):
                    cwd = obj["cwd"]
                if git_branch is None and obj.get("gitBranch"):
                    git_branch = obj["gitBranch"]
                if (
                    first_prompt is None
                    and otype == "user"
                    and not obj.get("isMeta")
                    and not obj.get("isSidechain")
                ):
                    msg = obj.get("message", {})
                    text = _coerce_text(msg.get("content"))
                    if _is_real_prompt(text):
                        first_prompt = text.strip()
    except OSError:
        return None

    if cwd is None:
        cwd = _decode_project_dir(project_dir)

    if summary:
        title = _clean(summary)
    elif first_prompt:
        title = _clean(first_prompt)
    else:
        title = "(no prompt yet)"

    return {
        "id": session_id,
        "path": path,
        "cwd": cwd or os.path.expanduser("~"),
        "title": title,
        "mtime": mtime,
        "git_branch": git_branch,
    }


def _matches(query_tokens, haystack):
    hay = haystack.lower()
    return all(tok in hay for tok in query_tokens)


def fulltext_snippet(path, tokens):
    """If every token appears in the conversation body, return a short snippet
    around the first token hit; otherwise return None."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            blob = fh.read(FULLTEXT_MAX_BYTES)
    except OSError:
        return None

    texts = []
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        if obj.get("type") in ("user", "assistant"):
            t = _coerce_text(obj.get("message", {}).get("content"))
            if t:
                texts.append(t)
    body = "\n".join(texts)
    low = body.lower()
    if not all(tok in low for tok in tokens):
        return None

    idx = low.find(tokens[0])
    start = max(0, idx - 40)
    end = min(len(body), idx + 80)
    snippet = body[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(body):
        snippet = snippet + "…"
    return _clean(snippet, 110)


def _mods(arg, pretty):
    """Per-modifier subtitles (all reuse the same arg; the action differs)."""
    return {
        "alt": {"subtitle": "Resume WITHOUT --dangerously-skip-permissions", "arg": arg},
        "cmd": {"subtitle": "Open %s in your editor" % pretty, "arg": arg},
        "ctrl": {"subtitle": "Reveal the session .jsonl transcript", "arg": arg},
        "shift": {"subtitle": "Quick Look the conversation", "arg": arg},
        "fn": {"subtitle": "Copy the resume command to the clipboard", "arg": arg},
    }


def build_item(s, snippet=None):
    pretty = _pretty_cwd(s["cwd"])
    gb = s["git_branch"]
    branch = (" ⎇ %s" % gb) if gb and gb not in ("HEAD", "main", "master") else ""
    if snippet:
        subtitle = "🔍 %s  •  %s" % (snippet, s["id"][:8])
    else:
        subtitle = "%s%s  •  %s  •  %s" % (
            pretty, branch, _rel_time(s["mtime"]), s["id"][:8],
        )
    arg = ARG_SEP.join([s["id"], s["cwd"], s["path"]])
    haystack = " ".join([s["title"], pretty, s["id"], s["git_branch"] or ""])
    return {
        "uid": s["id"],
        "title": s["title"],
        "subtitle": subtitle,
        "arg": arg,
        "match": haystack,
        "mods": _mods(arg, pretty),
        "text": {"copy": s["id"], "largetype": s["title"]},
        "quicklookurl": s["path"],
    }


def main():
    query = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    tokens = [t for t in query.split() if t]

    paths = glob.glob(os.path.join(PROJECTS_DIR, "*", "*.jsonl"))
    sessions = [s for s in (parse_session(p) for p in paths) if s]
    sessions.sort(key=lambda s: s["mtime"], reverse=True)

    items = []
    matched_meta = set()
    for s in sessions:
        haystack = " ".join(
            [s["title"], _pretty_cwd(s["cwd"]), s["id"], s["git_branch"] or ""]
        )
        if tokens and not _matches(tokens, haystack):
            continue
        matched_meta.add(s["id"])
        items.append(build_item(s))
        if len(items) >= MAX_RESULTS:
            break

    # Full-text pass: append sessions whose body (not metadata) matches.
    do_fulltext = (
        FULLTEXT
        and tokens
        and len(items) < MAX_RESULTS
        and all(len(t) >= MIN_FULLTEXT_LEN for t in tokens)
    )
    if do_fulltext:
        for s in sessions:
            if s["id"] in matched_meta:
                continue
            snippet = fulltext_snippet(s["path"], tokens)
            if snippet:
                items.append(build_item(s, snippet=snippet))
                if len(items) >= MAX_RESULTS:
                    break

    if not items:
        items.append(
            {
                "uid": "none",
                "title": "No matching Claude sessions",
                "subtitle": "Try a different search term"
                if tokens
                else "No sessions found in ~/.claude/projects",
                "valid": False,
            }
        )

    sys.stdout.write(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
