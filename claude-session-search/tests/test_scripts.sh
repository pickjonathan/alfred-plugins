#!/bin/bash
#
# Tests for resume.sh and action.sh using mocked external commands
# (open / pbcopy / osascript). Runnable on macOS and Linux CI.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "  ok   - $1"; }
nok()  { FAIL=$((FAIL + 1)); echo "  FAIL - $1"; }
check() { if eval "$2"; then ok "$1"; else nok "$1 ($2)"; fi; }

# Per-test sandbox: fake HOME, mock bin, a real cwd, a fake transcript.
setup() {
  SANDBOX="$(mktemp -d)"
  export HOME="$SANDBOX/home"
  mkdir -p "$HOME"
  MOCKBIN="$SANDBOX/bin"
  mkdir -p "$MOCKBIN"
  LOG="$SANDBOX/calls.log"
  : > "$LOG"

  # open: log args.
  cat > "$MOCKBIN/open" <<EOF
#!/bin/bash
echo "open \$*" >> "$LOG"
EOF
  # pbcopy: log stdin.
  cat > "$MOCKBIN/pbcopy" <<EOF
#!/bin/bash
echo "pbcopy: \$(cat)" >> "$LOG"
EOF
  # osascript stand-in (also referenced via OSASCRIPT): log stdin.
  cat > "$MOCKBIN/osascript" <<EOF
#!/bin/bash
echo "osascript:" >> "$LOG"
cat >> "$LOG"
EOF
  chmod +x "$MOCKBIN"/*
  export OSASCRIPT="$MOCKBIN/osascript"

  CWD="$SANDBOX/proj"
  mkdir -p "$CWD"
  JSONL="$CWD/session.jsonl"
  echo '{"type":"user","message":{"content":"hi"}}' > "$JSONL"
  ARG="abc123|||$CWD|||$JSONL"
  OLDPATH="$PATH"
  export PATH="$MOCKBIN:$PATH"
}

teardown() {
  export PATH="$OLDPATH"
  unset OSASCRIPT
  rm -rf "$SANDBOX"
}

echo "resume.sh — warp (bypass)"
setup
TERMINAL_APP=warp bash "$SCRIPT_DIR/resume.sh" "$ARG" >/dev/null 2>&1
YAML="$HOME/.warp/launch_configurations/claude-resume.yaml"
check "writes launch config" "[ -f '$YAML' ]"
check "config has cwd"        "grep -q 'cwd: \"$CWD\"' '$YAML'"
check "config has bypass flag" "grep -q -- '--dangerously-skip-permissions' '$YAML'"
check "opens warp url"        "grep -q 'warp://launch/claude-resume' '$LOG'"
teardown

echo "resume.sh — warp (--no-bypass)"
setup
TERMINAL_APP=warp bash "$SCRIPT_DIR/resume.sh" --no-bypass "$ARG" >/dev/null 2>&1
YAML="$HOME/.warp/launch_configurations/claude-resume.yaml"
check "no bypass flag in config" "! grep -q -- '--dangerously-skip-permissions' '$YAML'"
check "still resumes session"    "grep -q 'resume.*abc123' '$YAML'"
teardown

echo "resume.sh — extra CLAUDE_FLAGS"
setup
TERMINAL_APP=warp CLAUDE_FLAGS="--model opus" bash "$SCRIPT_DIR/resume.sh" "$ARG" >/dev/null 2>&1
YAML="$HOME/.warp/launch_configurations/claude-resume.yaml"
check "appends extra flags" "grep -q -- '--model opus' '$YAML'"
teardown

echo "resume.sh — iterm via osascript"
setup
TERMINAL_APP=iterm bash "$SCRIPT_DIR/resume.sh" "$ARG" >/dev/null 2>&1
check "invokes osascript"       "grep -q '^osascript:' '$LOG'"
check "targets iTerm"           "grep -q 'tell application \"iTerm\"' '$LOG'"
check "writes resume command"   "grep -q -- '--resume' '$LOG'"
teardown

echo "resume.sh — apple terminal via osascript"
setup
TERMINAL_APP=terminal bash "$SCRIPT_DIR/resume.sh" "$ARG" >/dev/null 2>&1
check "targets Terminal" "grep -q 'tell application \"Terminal\"' '$LOG'"
teardown

echo "resume.sh — falls back to HOME when cwd missing"
setup
TERMINAL_APP=warp bash "$SCRIPT_DIR/resume.sh" "abc|||/no/such/dir|||/x" >/dev/null 2>&1
YAML="$HOME/.warp/launch_configurations/claude-resume.yaml"
check "uses HOME as cwd" "grep -q \"cwd: \\\"$HOME\\\"\" '$YAML'"
teardown

echo "action.sh — copy-cmd"
setup
bash "$SCRIPT_DIR/action.sh" copy-cmd "$ARG" >/dev/null 2>&1
check "copies a resume command" "grep -q 'pbcopy:.*--resume \"abc123\"' '$LOG'"
check "copy includes bypass"    "grep -q 'pbcopy:.*--dangerously-skip-permissions' '$LOG'"
teardown

echo "action.sh — reveal"
setup
bash "$SCRIPT_DIR/action.sh" reveal "$ARG" >/dev/null 2>&1
check "reveals jsonl in finder" "grep -q 'open -R $JSONL' '$LOG'"
teardown

echo "action.sh — edit-cwd (finder)"
setup
EDITOR_APP=finder bash "$SCRIPT_DIR/action.sh" edit-cwd "$ARG" >/dev/null 2>&1
check "opens cwd" "grep -q 'open $CWD' '$LOG'"
teardown

echo
echo "Passed: $PASS  Failed: $FAIL"
[ "$FAIL" -eq 0 ]
