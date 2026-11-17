# RESUME — read this first in any new session

The agent VM is **ephemeral**. Its filesystem is wiped between sessions. The only
bytes that survive are the ones pushed to the private repo. This file is the
recovery protocol; follow it before doing anything else.

## 1. Where the project lives

- **Canonical host (private):** `Deobfugazi/darkith-forge`, branch `main`.
- Auth: the `GITHUB_TOKEN` secret (owner `Deobfugazi`). No credentials are stored
  in the repo, ever.

## 2. Restore (do this FIRST in a fresh VM)

```bash
# in the workspace, with GITHUB_TOKEN present:
bash tools/restore.sh
```

That clones or fast-forwards the workspace to the last checkpoint.

## 3. Save (do this BEFORE the session ends)

```bash
bash tools/continuity.sh "what I just did"
```

It commits everything and pushes to `main`. It **refuses to push** if signing key
material ever becomes tracked.

## 4. The rules that keep this survivable

- **One canonical tree.** Never keep two divergent live copies of a file; the
  loser is deleted or frozen with a dated note. (AGENTS.md §19 NEVER #11.)
- **Compile is the proof.** A tree is current only after a clean compile of that
  tree, not after a grep. (MUST #11.)
- **Every input is versioned.** Manifest, `res/`, `assets/`, `build.sh` live in
  the tree, not only inside an APK. (MUST #12.)
- **Secrets never enter git.** The APK signing key (`release_key`/`release_cert`)
  lives only inside the built APK and in your offline backup. `.gitignore` blocks
  it; `tools/continuity.sh` re-checks before every push.
- **Regenerable output stays out.** `delivery/`, `dl/`, `*.zip`, screenshots are
  rebuilt by the `build/*.py` packagers — they are not committed.

## 5. If a session is lost mid-work

1. `bash tools/restore.sh` to get the last checkpoint.
2. Read `DARKITH.md` (single source of truth) and `AGENTS.md` (repo knowledge).
3. Re-run the gates (`build/verify.py`, and the Android build once the toolchain
   is present) to see what actually holds — do not trust a stale claim.
