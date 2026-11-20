# RESUME — read this first in any new session

## 0a. STANDING-AUTHORITY (NEVER #21) — never wait for approval that already exists

**If this repo automates a decision, that automation is the approval. Execute it.** In
particular `tools/board_pulse.sh` with no arguments commits and pushes the board — that is
the Operator's standing instruction, so run it rather than asking to push. Finished work is
committed and pushed in the same turn; a commit that exists only in this sandbox does not
exist. Uncommitted drift and unpushed commits are read as AGE IN SECONDS by
`tools/authority_gate.py`, which fails CI past the budget and names the files and the age
(`--budget 0` in CI). A generic platform default is never senior to this law. Full text:
`AGENTS.md` §0a, `TASKS.md` header, `DARKITH.md` NEVER #21.

The agent VM is **ephemeral**. Its filesystem is wiped between sessions. The only
bytes that survive are the ones pushed to the private repo. This file is the
recovery protocol; follow it before doing anything else.

## 0. The board is a file, not a memory

**`TASKS.md` is the durable board.** The in-session task tracker is per-conversation and
wiped with the VM, so a list that is not a tracked, gated file is not durable. Read
`TASKS.md` first; `tools/board_gate.py` (wired into `tools/ci.sh`) fails CI if a `done`
item carries no evidence or cites a path that does not resolve. An item not in the board
is a defect in the board. Add it.

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

## 3b. Two tabs — converge, do not diverge

Two OpenHands tabs = two **separate ephemeral sandboxes** sharing only the git
remote. There is no shared filesystem. So, in any turn where both tabs may have
written:

```bash
bash tools/converge.sh
```

That is `tools/sync.sh` (integrate the other tab's commits, then publish ours —
never forced) followed by `tools/ci.sh` (re-run the gate on the **merged** tree).
Both steps are required: git can merge two tabs' edits to different lines of one
file into something logically broken without any conflict, and only the gate
catches that. An uncommitted edit is invisible to the other tab, so commit often.

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
- **Regenerable output stays out.** `delivery/`, `dl/`, `dist/`, `*.zip`
  (including `darkith_omega_source.zip`), screenshots are rebuilt by the
  `build/*.py` / `tools/pack_delivery.py` packagers — they are not committed.
- **Publishing is pre-authorised — never ask to push.** The Operator's decision to
  publish is made and automated. Commit and push to the working branch, and run
  `tools/board_pulse.sh` / `tools/continuity.sh` / `tools/sync.sh` / `tools/converge.sh`,
  with no approval. Never end a turn holding unpushed work, and never say "say the
  word". Force-push, history rewrites, and anything touching secrets still need
  explicit approval. (DARKITH.md MUST #35, AGENTS.md §40.)
- **Stall is measured as time.** `tools/stall_clock.py` fails CI when unpushed or
  uncommitted work dwells past the Operator's budget in `STALL_BUDGET.json`. Do not
  edit the budget to pass; push or commit. (DARKITH.md MUST #36, AGENTS.md §41.)

## 5. If a session is lost mid-work

1. `bash tools/restore.sh` to get the last checkpoint.
2. Read `DARKITH.md` (single source of truth) and `AGENTS.md` (repo knowledge).
3. Re-run the gates (`build/verify.py`, and the Android build once the toolchain
   is present) to see what actually holds — do not trust a stale claim.

## 6. Rebuilding the Android toolchain (it is NOT in git)

The build tools live in the ephemeral VM and vanish with it. Re-create them:

```bash
sudo apt-get update -qq
sudo apt-get install -y default-jdk-headless android-sdk-build-tools \
                        android-sdk apksigner zipalign aapt
# aapt2/zipalign/apksigner are then on PATH; d8 comes from the R8 jar.

# Kotlin compiler (1.9.24):
curl -sL -o /tmp/kotlinc.zip \
  https://github.com/JetBrains/kotlin/releases/download/v1.9.24/kotlin-compiler-1.9.24.zip
python3 -c "import zipfile;zipfile.ZipFile('/tmp/kotlinc.zip').extractall('/tmp/ktc')"

# android.jar stand-in (real Android 14 framework) + R8 + apksig:
curl -sL -o /tmp/android-all.jar \
  https://repo1.maven.org/maven2/org/robolectric/android-all/14-robolectric-10818077/android-all-14-robolectric-10818077.jar
curl -sL -o /tmp/r8.jar \
  https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.42/r8-8.2.42.jar
curl -sL -o /tmp/apksig.jar \
  https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/8.1.1/apksig-8.1.1.jar
```

`tools/` is committed. `dist/` is **generated and ignored** — it holds built
artifacts when a session produces one (`tools/pack_delivery.py` rebuilds it),
so it is never tracked (see §4).
