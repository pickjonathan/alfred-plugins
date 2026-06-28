#!/bin/bash
#
# Alfred action: resume a Claude Code session in the configured terminal.
#
# Argument: "<session-id>|||<cwd>|||<jsonl-path>"  (from search.py)
# Optional first arg: --no-bypass  (omit --dangerously-skip-permissions)
#
# Workflow environment variables (set in Alfred → Configure Workflow):
#   TERMINAL_APP : warp | iterm | terminal | ghostty   (default: warp)
#   OPEN_MODE    : tab | window                         (default: tab)
#   CLAUDE_FLAGS : extra flags appended to the claude command (default: empty)

set -euo pipefail

ARG_SEP="|||"
BYPASS=1
if [ "${1:-}" = "--no-bypass" ]; then
  BYPASS=0
  shift
fi

arg="${1:-}"
if [ -z "$arg" ]; then
  echo "resume.sh: no argument given" >&2
  exit 1
fi

# Split the 3-field argument.
session_id="${arg%%${ARG_SEP}*}"
rest="${arg#*${ARG_SEP}}"
cwd="${rest%%${ARG_SEP}*}"

if [ -z "$cwd" ] || [ ! -d "$cwd" ]; then
  cwd="$HOME"
fi

TERMINAL_APP="$(echo "${TERMINAL_APP:-warp}" | tr '[:upper:]' '[:lower:]')"
OPEN_MODE="$(echo "${OPEN_MODE:-tab}" | tr '[:upper:]' '[:lower:]')"
CLAUDE_FLAGS="${CLAUDE_FLAGS:-}"

# Resolve the claude binary so the launched shell finds it regardless of its
# login PATH.
claude_bin="claude"
for cand in "$HOME/.local/bin/claude" "$(command -v claude 2>/dev/null || true)"; do
  if [ -n "$cand" ] && [ -x "$cand" ]; then
    claude_bin="$cand"
    break
  fi
done

flags=""
[ "$BYPASS" = "1" ] && flags=" --dangerously-skip-permissions"
[ -n "$CLAUDE_FLAGS" ] && flags="$flags $CLAUDE_FLAGS"

# The command run inside the new terminal. ~/.local/bin is prepended as a safety
# net in case the login shell's PATH lacks it.
resume_cmd="export PATH=\"\$HOME/.local/bin:\$PATH\"; cd \"$cwd\" && \"$claude_bin\" --resume \"$session_id\"$flags"

# AppleScript string-literal escaper (\\ and ").
osa_esc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

launch_warp() {
  local config_name="claude-resume"
  local config_dir="$HOME/.warp/launch_configurations"
  local config_file="$config_dir/$config_name.yaml"
  mkdir -p "$config_dir"
  yaml_esc() { printf '%s' "$1" | sed 's/"/\\"/g'; }
  cat > "$config_file" <<EOF
---
name: "$config_name"
windows:
  - tabs:
      - title: "claude · ${session_id:0:8}"
        layout:
          cwd: "$(yaml_esc "$cwd")"
          commands:
            - exec: "$(yaml_esc "$resume_cmd")"
EOF
  open "warp://launch/$config_name"
}

launch_iterm() {
  # iTerm2's scripting application name is "iTerm".
  if [ "$OPEN_MODE" = "window" ]; then
    /usr/bin/osascript <<EOF
tell application "iTerm"
  activate
  create window with default profile
  tell current session of current window to write text "$(osa_esc "$resume_cmd")"
end tell
EOF
  else
    /usr/bin/osascript <<EOF
tell application "iTerm"
  activate
  if (count of windows) = 0 then
    create window with default profile
  else
    tell current window to create tab with default profile
  end if
  tell current session of current window to write text "$(osa_esc "$resume_cmd")"
end tell
EOF
  fi
}

launch_terminal() {
  # Apple Terminal: do script opens a new window; reuse front window for a tab.
  /usr/bin/osascript <<EOF
tell application "Terminal"
  activate
  do script "$(osa_esc "$resume_cmd")"
end tell
EOF
}

launch_ghostty() {
  # Ghostty has limited scripting; drive it via System Events keystrokes.
  # Requires Accessibility permission for Alfred/osascript.
  open -a Ghostty || open -na Ghostty
  /usr/bin/osascript <<EOF
tell application "Ghostty" to activate
delay 0.5
tell application "System Events"
  keystroke "$(osa_esc "$resume_cmd")"
  key code 36
end tell
EOF
}

case "$TERMINAL_APP" in
  warp) launch_warp ;;
  iterm | iterm2) launch_iterm ;;
  terminal | apple) launch_terminal ;;
  ghostty) launch_ghostty ;;
  *)
    echo "resume.sh: unknown TERMINAL_APP '$TERMINAL_APP', falling back to warp" >&2
    launch_warp
    ;;
esac
