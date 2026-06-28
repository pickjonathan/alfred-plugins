#!/bin/bash
#
# Alfred action (⇧): render a session transcript to HTML and Quick Look it.
#
# Argument: "<session-id>|||<cwd>|||<jsonl-path>"

set -euo pipefail

ARG_SEP="|||"
arg="${1:-}"
if [ -z "$arg" ]; then
  echo "quicklook.sh: no argument given" >&2
  exit 1
fi

session_id="${arg%%"${ARG_SEP}"*}"
rest="${arg#*"${ARG_SEP}"}"
jsonl="${rest#*"${ARG_SEP}"}"

if [ ! -f "$jsonl" ]; then
  echo "quicklook.sh: transcript not found: $jsonl" >&2
  exit 1
fi

here="$(cd "$(dirname "$0")" && pwd)"
cache="${alfred_workflow_cache:-${TMPDIR:-/tmp}}"
mkdir -p "$cache"
out="$cache/transcript-${session_id:0:8}.html"

/usr/bin/python3 "$here/transcript.py" "$jsonl" "$out"

# Quick Look the rendered transcript (panel closes on Esc / loses focus).
qlmanage -p "$out" >/dev/null 2>&1 &
