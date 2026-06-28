#!/bin/bash
#
# Alfred secondary actions for a Claude session.
#
# Usage: action.sh <verb> "<session-id>|||<cwd>|||<jsonl-path>"
#   verbs:
#     edit-cwd  open the session's working directory in your editor
#     reveal    reveal the .jsonl transcript in Finder
#     copy-cmd  copy the resume command to the clipboard
#
# Workflow env var:
#   EDITOR_APP : cursor | code | finder | <App name>   (default: cursor)

set -euo pipefail

ARG_SEP="|||"
verb="${1:-}"
arg="${2:-}"

if [ -z "$verb" ] || [ -z "$arg" ]; then
  echo "action.sh: usage: action.sh <verb> <arg>" >&2
  exit 1
fi

session_id="${arg%%"${ARG_SEP}"*}"
rest="${arg#*"${ARG_SEP}"}"
cwd="${rest%%"${ARG_SEP}"*}"
jsonl="${rest#*"${ARG_SEP}"}"

EDITOR_APP="${EDITOR_APP:-cursor}"

open_in_editor() {
  local target="$1"
  case "$(echo "$EDITOR_APP" | tr '[:upper:]' '[:lower:]')" in
    finder) open "$target" ;;
    code | vscode)
      if command -v code >/dev/null 2>&1; then code -n "$target"; else open -a "Visual Studio Code" "$target"; fi ;;
    cursor)
      if command -v cursor >/dev/null 2>&1; then cursor -n "$target"; else open -a "Cursor" "$target"; fi ;;
    *) open -a "$EDITOR_APP" "$target" || open "$target" ;;
  esac
}

case "$verb" in
  edit-cwd)
    [ -d "$cwd" ] || cwd="$HOME"
    open_in_editor "$cwd"
    echo "Opened $cwd"
    ;;
  reveal)
    if [ -f "$jsonl" ]; then open -R "$jsonl"; else open "$(dirname "$jsonl")"; fi
    echo "Revealed $jsonl"
    ;;
  copy-cmd)
    cmd="cd \"$cwd\" && claude --resume \"$session_id\" --dangerously-skip-permissions"
    printf '%s' "$cmd" | pbcopy
    echo "Copied resume command"
    ;;
  *)
    echo "action.sh: unknown verb '$verb'" >&2
    exit 1
    ;;
esac
