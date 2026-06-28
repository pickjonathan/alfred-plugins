# Claude Session Search — Alfred Workflow

Search through your Claude Code sessions by description (or full text) and
resume the one you pick in your terminal — by default in **Warp** with
permission checks bypassed (`--dangerously-skip-permissions`).

## What it does

1. Scans `~/.claude/projects/*/*.jsonl` (every Claude Code session on this Mac).
2. Builds a human-readable description per session: Claude's conversation
   **summary** if present, otherwise your **first real prompt** (command/meta
   entries skipped).
3. Shows results newest-first with working directory, git branch and short id.
4. Two-tier matching: query tokens are matched against the description / path /
   branch / id; anything that doesn't match there is then searched against the
   **full conversation body** (shown with a 🔍 and a snippet).
5. On action, opens your terminal in the session's original directory and runs
   `claude --resume <id> [--dangerously-skip-permissions] [extra flags]`.

## Usage

```
cs                → list all sessions (most recent first)
cs eks deploy     → filter (all words must match; falls back to full-text)
```

### Actions on the highlighted result

| Key      | Action                                                        |
| -------- | ------------------------------------------------------------- |
| `↵`      | Resume in terminal **with** `--dangerously-skip-permissions`  |
| `⌥ ↵`    | Resume **without** the bypass flag                            |
| `⌘ ↵`    | Open the session's working directory in your editor           |
| `⌃ ↵`    | Reveal the session `.jsonl` transcript in Finder              |
| `⇧ ↵`    | Quick Look the conversation (rendered transcript)             |
| `fn ↵`   | Copy the resume command to the clipboard                      |

## Configuration

Set these in Alfred → **Configure Workflow** (or edit the workflow variables):

| Variable       | Default  | Purpose                                                       |
| -------------- | -------- | ------------------------------------------------------------- |
| `TERMINAL_APP` | `warp`   | `warp` / `iterm` / `terminal` / `ghostty`                     |
| `OPEN_MODE`    | `tab`    | `tab` or `window` (iTerm; Warp always opens a window)         |
| `EDITOR_APP`   | `cursor` | `cursor` / `code` / `finder` / any app name (used by `⌘`)     |
| `CLAUDE_FLAGS` | *(none)* | Extra flags appended to the resume command, e.g. `--model opus` |
| `FULLTEXT`     | on       | Also search full conversation text when metadata doesn't match |

## Requirements

- **Alfred 5** with the Powerpack.
- **Claude Code CLI** on `PATH` (or at `~/.local/bin/claude`).
- The chosen terminal:
  - **Warp** — uses Launch Configurations via the `warp://` URL scheme. No
    Accessibility permission required.
  - **iTerm / Apple Terminal** — driven via AppleScript (`osascript`).
  - **Ghostty** — best-effort via System Events keystrokes; needs macOS
    **Accessibility** permission for Alfred.
- System Python 3 at `/usr/bin/python3` (ships with macOS; no extra packages).

## Install

Double-click `Claude Session Search.alfredworkflow` and confirm the import.

### Developing / re-syncing edits

After editing any source file, run `./install.sh` to rebuild the bundle **and**
copy the files into the installed workflow in place (it locates the workflow by
its bundle id, so it survives Alfred reassigning the folder):

```sh
./install.sh            # sync source -> installed workflow + rebuild bundle
./install.sh --package  # only rebuild the .alfredworkflow
./install.sh --open     # rebuild and open in Alfred to (re)import
```

## Files

| File            | Purpose                                                       |
| --------------- | ------------------------------------------------------------- |
| `info.plist`    | Workflow definition (Script Filter → modifier-gated actions). |
| `search.py`     | Scans sessions, full-text search, emits Alfred JSON.          |
| `resume.sh`     | Opens the configured terminal and resumes the session.        |
| `action.sh`     | `⌘`/`⌃`/`fn` actions (open dir, reveal, copy command).        |
| `quicklook.sh`  | Renders + Quick Looks the transcript (`⇧`).                   |
| `transcript.py` | Renders a session `.jsonl` to a readable HTML transcript.     |
| `make_icon.py`  | Regenerates `icon.png` (the Claude-style sunburst mark).      |
| `install.sh`    | Rebuilds the bundle and syncs source into the live workflow.   |

## How Warp resume works

`resume.sh` writes `~/.warp/launch_configurations/claude-resume.yaml` with the
session's `cwd` and an `exec` command, then runs `open "warp://launch/claude-resume"`.

## Notes / limitations

- Description quality depends on the session; empty ones show `(no prompt yet)`.
- Only the first ~400 lines per file are scanned for the first prompt / cwd;
  full-text scans up to 2 MB per file.
- Results are capped at 200 sessions.
- The icon evokes Claude's mark for personal use — swap in the official asset
  before redistributing.
