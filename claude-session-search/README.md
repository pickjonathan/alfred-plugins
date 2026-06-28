# Claude Session Search — Alfred Workflow

[![CI](https://github.com/pickjonathan/alfred-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/pickjonathan/alfred-plugins/actions/workflows/ci.yml)

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
| `run-tests.sh`  | Runs the Python + bash test suites.                            |
| `tests/`        | `unittest` tests + bash script tests + JSONL fixtures.         |

## Architecture

```
Alfred keyword "cs {query}"
        │
        ▼
  search.py  ──reads──▶  ~/.claude/projects/*/*.jsonl
        │  (emits Alfred Script Filter JSON; arg = "id|||cwd|||jsonl-path")
        ▼
  ┌─────────────── modifier-gated connections ───────────────┐
  │  ↵   resume.sh "$arg"             → open terminal, resume │
  │  ⌥   resume.sh --no-bypass "$arg" → resume, no bypass     │
  │  ⌘   action.sh edit-cwd "$arg"    → open cwd in editor    │
  │  ⌃   action.sh reveal "$arg"      → reveal .jsonl         │
  │  ⇧   quicklook.sh "$arg"          → transcript.py → QL    │
  │  fn  action.sh copy-cmd "$arg"    → pbcopy resume command │
  └───────────────────────────────────────────────────────────┘
```

The `arg` passed to every action is `"<session-id>|||<cwd>|||<jsonl-path>"`.
Configuration is read from workflow environment variables (see above).

### How Warp resume works

`resume.sh` writes `~/.warp/launch_configurations/claude-resume.yaml` with the
session's `cwd` and an `exec` command, then runs `open "warp://launch/claude-resume"`.
iTerm and Apple Terminal are driven via AppleScript; Ghostty via keystrokes.

## Testing

```sh
./run-tests.sh             # Python unittest + bash script tests
PYTHON=/usr/bin/python3 ./run-tests.sh   # pick a specific interpreter
python3 -m unittest discover -s tests -v # Python tests only
```

- **Python tests** (`tests/test_search.py`, `tests/test_transcript.py`) cover the
  description/cwd/branch extraction, full-text matching, Alfred-item shape, and
  the HTML transcript renderer. They run against the JSONL fixtures in
  `tests/fixtures/` and exercise `search.py` end-to-end by pointing
  `CLAUDE_PROJECTS_DIR` at the fixtures.
- **Bash tests** (`tests/test_scripts.sh`) mock `open` / `pbcopy` / `osascript`
  on `PATH` and assert that `resume.sh` and `action.sh` produce the right Warp
  launch config, AppleScript, clipboard contents, and `open` calls — so they run
  on both macOS and Linux CI.

CI (`.github/workflows/ci.yml`) runs ShellCheck, validates `info.plist`, runs the
suite, and verifies the `.alfredworkflow` bundle contents on every push/PR.

### Testing hooks

`search.py` and `resume.sh` accept env overrides purely to enable testing:

| Variable             | Used by      | Purpose                                          |
| -------------------- | ------------ | ------------------------------------------------ |
| `CLAUDE_PROJECTS_DIR`| `search.py`  | Point the scan at a different projects directory |
| `OSASCRIPT`          | `resume.sh`  | Substitute the `osascript` binary (mockable)     |

## Troubleshooting

- **Nothing happens on Enter / `claude: command not found`** — `resume.sh`
  resolves `~/.local/bin/claude` then `command -v claude`, and prepends
  `~/.local/bin` to `PATH`. If Claude Code lives elsewhere, add its directory to
  your login shell `PATH`.
- **Warp opens but doesn't run the command** — ensure your Warp is recent enough
  to support Launch Configurations (`warp://launch/…`). As a fallback, switch
  `TERMINAL_APP` to `iterm` or `terminal`.
- **Ghostty doesn't type the command** — the Ghostty path uses System Events
  keystrokes; grant Alfred **Accessibility** access in System Settings →
  Privacy & Security.
- **Icon didn't update** — reopen Alfred Preferences; macOS caches workflow icons.
- **Edits aren't reflected** — run `./install.sh` to sync source into the
  installed workflow.

## Notes / limitations

- Description quality depends on the session; empty ones show `(no prompt yet)`.
- Only the first ~400 lines per file are scanned for the first prompt / cwd;
  full-text scans up to 2 MB per file.
- Results are capped at 200 sessions.
- The icon evokes Claude's mark for personal use — swap in the official asset
  before redistributing.
