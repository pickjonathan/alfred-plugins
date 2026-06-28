#!/bin/bash
#
# Sync this workflow's source files into the installed Alfred workflow, and
# (re)build the distributable .alfredworkflow bundle.
#
# Usage:
#   ./install.sh           sync source -> installed workflow (+ rebuild bundle)
#   ./install.sh --package  only rebuild the .alfredworkflow bundle
#   ./install.sh --open     import via Alfred (double-click equivalent)
#
# Finds the installed workflow by its bundle id, so it keeps working even if
# Alfred assigned a different user.workflow.<UUID> folder.

set -euo pipefail

BUNDLE_ID="com.pickjonathan.claude-session-search"
BUNDLE_NAME="Claude Session Search.alfredworkflow"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE" || exit 1

# Files that make up the workflow (everything the bundle ships).
FILES=(info.plist search.py resume.sh action.sh quicklook.sh transcript.py README.md icon.png)

package() {
  rm -f "$BUNDLE_NAME"
  zip -j -X "$BUNDLE_NAME" "${FILES[@]}" >/dev/null
  echo "Built $BUNDLE_NAME"
}

find_workflows_root() {
  # Resolve Alfred's current preferences folder, then its workflows dir.
  local prefs
  prefs="$(defaults read com.runningwithcrayons.Alfred-Preferences syncfolder 2>/dev/null || true)"
  prefs="${prefs/#\~/$HOME}"
  if [ -z "$prefs" ] || [ ! -d "$prefs" ]; then
    prefs="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences"
  fi
  printf '%s/workflows' "$prefs"
}

find_installed_dir() {
  local root="$1" match
  [ -d "$root" ] || return 1
  match="$(grep -rl "$BUNDLE_ID" "$root"/*/info.plist 2>/dev/null | head -1)"
  [ -n "$match" ] && dirname "$match"
}

case "${1:-}" in
  --package)
    package
    exit 0
    ;;
  --open)
    package
    open "$HERE/$BUNDLE_NAME"
    echo "Opened in Alfred — confirm the Import dialog."
    exit 0
    ;;
esac

package

ROOT="$(find_workflows_root)"
DEST="$(find_installed_dir "$ROOT" || true)"

if [ -z "${DEST:-}" ] || [ ! -d "$DEST" ]; then
  echo "Workflow not installed yet — opening the bundle for Alfred to import."
  open "$HERE/$BUNDLE_NAME"
  echo "Confirm the Import dialog, then re-run ./install.sh to enable in-place sync."
  exit 0
fi

cp "${FILES[@]}" "$DEST/"
chmod +x "$DEST"/*.sh "$DEST"/*.py 2>/dev/null || true
echo "Synced ${#FILES[@]} files -> $DEST"
