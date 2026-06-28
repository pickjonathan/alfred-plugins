#!/usr/bin/env python3
"""
Render a Claude Code session .jsonl into a readable HTML transcript.

Usage: transcript.py <jsonl-path> <out-html-path>

Keeps user/assistant turns and tool calls/results in a compact, scannable form.
No third-party dependencies (system Python 3).
"""
import html
import json
import os
import sys


def coerce_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for p in content:
            if not isinstance(p, dict):
                continue
            t = p.get("type")
            if t == "text" and p.get("text"):
                out.append(p["text"])
            elif t == "tool_use":
                name = p.get("name", "tool")
                out.append("⚙️  [tool: %s]" % name)
            elif t == "tool_result":
                out.append("↩︎  [tool result]")
            elif t == "thinking":
                out.append("💭 [thinking]")
        return "\n".join(out)
    return ""


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: transcript.py <jsonl> <out.html>\n")
        return 1
    path, out = sys.argv[1], sys.argv[2]

    rows = []
    title = os.path.basename(path)
    summary = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
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
                if otype not in ("user", "assistant"):
                    continue
                if obj.get("isMeta") or obj.get("isSidechain"):
                    continue
                text = coerce_text(obj.get("message", {}).get("content")).strip()
                if not text:
                    continue
                ts = obj.get("timestamp", "")
                rows.append((otype, ts, text))
    except OSError as e:
        sys.stderr.write("transcript.py: %s\n" % e)
        return 1

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<style>",
        "body{font:14px/1.5 -apple-system,Helvetica,Arial,sans-serif;",
        "max-width:820px;margin:24px auto;padding:0 16px;color:#1f1f1f;}",
        ".sum{background:#f6efe9;border-left:4px solid #d97757;padding:10px 14px;",
        "border-radius:8px;margin-bottom:20px;}",
        ".turn{margin:14px 0;padding:10px 14px;border-radius:10px;}",
        ".user{background:#eef4fb;}",
        ".assistant{background:#f7f3ef;}",
        ".role{font-weight:700;font-size:11px;text-transform:uppercase;",
        "letter-spacing:.5px;color:#8a6a58;margin-bottom:4px;}",
        ".user .role{color:#3a6ea5;}",
        "pre{white-space:pre-wrap;word-wrap:break-word;margin:0;font:inherit;}",
        "h1{font-size:18px;}", "</style></head><body>",
        "<h1>%s</h1>" % html.escape(title),
    ]
    if summary:
        parts.append("<div class='sum'><b>Summary:</b> %s</div>" % html.escape(summary))
    if not rows:
        parts.append("<p><i>No conversation content found.</i></p>")
    for role, ts, text in rows:
        label = "You" if role == "user" else "Claude"
        parts.append(
            "<div class='turn %s'><div class='role'>%s</div><pre>%s</pre></div>"
            % (role, html.escape(label), html.escape(text))
        )
    parts.append("</body></html>")

    with open(out, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
