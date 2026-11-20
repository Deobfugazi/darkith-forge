# co-ordinasync — the portable invariant toolkit (MUST #40)

One file. Carry it anywhere. `kit/coordinasync.py`, ~46 KB, python3.10+, stdlib only.
No install, no venv, no package index, no network, no directory layout to rebuild.

## Why one file

The toolchain began as four modules wired by absolute path into one repo on one account.
Carrying it to another account meant re-deriving it, and every re-derivation reintroduced
the same defects. An apparatus that must be rebuilt at each hop is not an apparatus.

## Carry it

```sh
# on the machine you are leaving
scp kit/coordinasync.py you@other-host:/path/to/that/project/

# there
cd /path/to/that/project
python3 coordinasync.py install     # writes tools/ + build/gen/ into THIS project
python3 coordinasync.py selftest    # 12 checks, nothing outside a temp dir touched
```

`install` is optional. The bundle runs standalone; `install` just materialises the module
files so you can edit them as ordinary sources.

## Commands

| command | does |
|---|---|
| `install [dir]` | seed a project: modules, `TASKS.md`, `proof/`, `.coordinasync.json` |
| `selftest` | 12 checks over a throwaway project; exit 0 = the whole chain works |
| `ingest` | read the session log, put the Operator's orders on the board, ping boards |
| `check` | verify the board carries the order in force and every law names a real gate |
| `propagate` | mirror the order in force to every board this project carries |
| `pulse` | record boot instant + last activity, classify the circadian phase |
| `status` | one screen: phase, watermark, laws, board agreement |

## Where it looks for things

Nothing is assumed about a platform. The project states its own facts:

```json
// .coordinasync.json, at the project root
{ "event_roots": ["/where/this/host/keeps/conversation/logs"] }
```

Resolution order for conversation logs: `COORDINASYNC_EVENT_ROOTS`, then
`.coordinasync.json`, then `conversations/` beside the tool, then `../conversations`.
A project that declares nothing gets nothing — never somebody else's orders.

Environment:

| var | meaning |
|---|---|
| `COORDINASYNC_ROOT` | the project to operate on (default: the bundle's own directory) |
| `COORDINASYNC_EVENT_ROOTS` | `os.pathsep`-separated log roots; beats the declaration |
| `COORDINASYNC_TZ_OFFSET_MIN` | Operator's UTC offset in minutes (default `480`, +08:00) |

## What it refuses to do

- Write a board it did not read (SPI-2).
- Report success on a run that failed.
- Fail closed on a fresh account that has no law corpus yet — there is nothing to check
  against, so it carries the order and says so. Fail-closed applies where a corpus exists
  and contradicts the order.
- Ingest one project's session into another. Each project declares its own log root.

## The build

`kit/coordinasync.py` is generated, not hand-edited:

```sh
python3 build/make-coordinasync.py     # reads tools/ + build/gen/, writes kit/coordinasync.py
```

Sources stay single. The bundle is an artifact of `tools/`, so there is exactly one copy
of each module and no fork for the NEVER #11 gate to catch.

CI runs `coordinasync selftest` on every build, so a kit that stops being portable fails
here rather than on the Operator's next account.
