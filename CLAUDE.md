# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

A monorepo of [Alfred](https://www.alfredapp.com/) workflows. Each workflow
lives in its own top-level directory and is self-contained.

```
alfred-plugins/
├── README.md                 # index of workflows
├── CLAUDE.md                 # this file
├── .github/workflows/ci.yml  # ShellCheck + tests + bundle verify
└── claude-session-search/    # the "Claude Session Search" workflow
    ├── info.plist            # Alfred workflow definition
    ├── search.py             # Script Filter: scan + search sessions
    ├── resume.sh             # resume a session in the chosen terminal
    ├── action.sh             # ⌘/⌃/fn secondary actions
    ├── quicklook.sh          # ⇧ Quick Look transcript
    ├── transcript.py         # render a session .jsonl → HTML
    ├── make_icon.py          # regenerate icon.png
    ├── install.sh            # build bundle + sync into installed workflow
    ├── run-tests.sh          # run the test suite
    └── tests/                # unittest + bash tests + fixtures
```

## Common commands

Run from `claude-session-search/`:

```sh
./run-tests.sh                 # full suite (Python + bash)
PYTHON=/usr/bin/python3 ./run-tests.sh   # use the macOS system Python (3.9)
python3 -m unittest discover -s tests -v # Python tests only
bash tests/test_scripts.sh     # bash script tests only

./install.sh                   # rebuild .alfredworkflow + sync into Alfred
./install.sh --package         # just rebuild the bundle
./install.sh --open            # rebuild and open in Alfred to (re)import
python3 make_icon.py           # regenerate icon.png
```

## How the workflow fits together

`info.plist` defines one Script Filter (keyword `cs`) connected to six action
objects, each gated by a modifier in the connection's `modifiers` bitmask:

| Modifier | bitmask  | action                          |
| -------- | -------- | ------------------------------- |
| (none)   | 0        | `resume.sh "$arg"`              |
| ⌥        | 524288   | `resume.sh --no-bypass "$arg"`  |
| ⌘        | 1048576  | `action.sh edit-cwd "$arg"`     |
| ⌃        | 262144   | `action.sh reveal "$arg"`       |
| ⇧        | 131072   | `quicklook.sh "$arg"`           |
| fn       | 8388608  | `action.sh copy-cmd "$arg"`     |

`search.py` emits Alfred Script Filter JSON. Every item's `arg` is
`"<session-id>|||<cwd>|||<jsonl-path>"` (`ARG_SEP = "|||"`). All action scripts
split on that separator.

User-facing config is stored as workflow variables (`info.plist` →
`variables` / `userconfigurationconfig`) and reaches scripts as environment
variables: `TERMINAL_APP`, `OPEN_MODE`, `EDITOR_APP`, `CLAUDE_FLAGS`, `FULLTEXT`.

## Conventions (follow these when editing)

- **Python**: target the macOS **system Python 3.9** (`/usr/bin/python3`) — that's
  what Alfred runs. No third-party dependencies; standard library only. Avoid
  3.10+ syntax (no `match`, no `X | Y` type unions, etc.).
- **Bash**: `#!/bin/bash`, `set -euo pipefail`, and keep it **ShellCheck-clean**
  (CI runs ShellCheck on `resume.sh action.sh quicklook.sh install.sh
  run-tests.sh`). Quote variables used as parameter-expansion patterns
  (`${x%%"$SEP"*}`).
- **No new runtime deps.** Rendering/automation uses what ships with macOS
  (`osascript`, `qlmanage`, `sips`, `pbcopy`, `open`).
- **Keep the arg contract** (`id|||cwd|||path`) stable across `search.py` and the
  action scripts — change all of them together, and update the bash tests.
- After changing any source file, **run `./run-tests.sh`**, then `./install.sh`
  to push it into the live Alfred workflow (editing source does NOT auto-update
  the installed copy).

## Testing hooks (for tests only)

| Variable              | Script       | Purpose                                       |
| --------------------- | ------------ | --------------------------------------------- |
| `CLAUDE_PROJECTS_DIR` | `search.py`  | Scan a fixtures dir instead of `~/.claude`    |
| `OSASCRIPT`           | `resume.sh`  | Mockable `osascript` binary                   |
| `FULLTEXT=0`          | `search.py`  | Disable full-text search                      |

These let the suite run hermetically (and on Linux CI) by mocking `open`,
`pbcopy`, and `osascript` on `PATH`. When adding behavior that shells out to a
macOS-only tool, route it through an overridable variable so it stays testable.

## Gotchas

- Session descriptions come from a Claude-generated `summary` line if present,
  else the first non-command/non-meta user prompt. `/clear`-style command
  messages and tool/meta entries are intentionally skipped.
- `resume.sh` calls `osascript` unqualified (via `${OSASCRIPT:-osascript}`) so it
  can be mocked; on a real Mac that resolves to the system `osascript`.
- iTerm2's AppleScript application name is **`iTerm`**, not `iTerm2`.
- The built `Claude Session Search.alfredworkflow` is committed so it can be
  downloaded directly; `install.sh --package` regenerates it and CI checks its
  contents.
