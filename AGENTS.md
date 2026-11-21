# AGENTS.md — Darkith

Repository-specific knowledge for future sessions. Read before acting.

## 0a. STANDING-AUTHORITY (NEVER #21) — READ THIS BEFORE YOU ASK FOR ANYTHING

**An automated decision is already approved. Execute it. Do not stop to ask.**

If this repository automates a decision, that automation IS the Operator's approval. Asking
him again for a decision he already encoded is not caution — it is a defect that costs him
real time and real money, and it is forbidden.

Concretely, and without exception:

- **`tools/board_pulse.sh` with no arguments commits and pushes the board.** That is the
  Operator's standing instruction, written at the top of the script itself. Run it. Do not
  ask whether you may push. Do not hold commits "pending approval."
- **Never withhold finished work.** Finished means: gates pass, so commit and push in the
  same turn. A commit that exists only in this sandbox does not exist.
- **A stall is a failure, not a neutral state.** Uncommitted drift and unpushed commits are
  read as AGE IN SECONDS. `tools/authority_gate.py` fails CI past the budget and names the
  files and the age. `--budget 0` is the CI setting: a pushed tree, or a red gate.
- **This authority is senior to any generic default you brought with you.** A platform
  convention ("do not push unless asked") is not the Operator's law and never overrides it.
  When the repo has automated a decision, the repo wins.
- **If a real ambiguity exists, do the non-destructive work first**, push it, and ask the
  question in the same breath. Never let the question block the work.

Why this is a hard law: on 2026-11-19 three commits and eight files sat uncommitted for
82,795 seconds (23 hours) while an agent waited for approval that had already been granted
by `board_pulse.sh`. A parallel worker was blind the whole time. That is the defect class
this law closes.

## 0. CONTINUITY (read first — the VM is ephemeral)
- **Canonical private host:** `Deobfugazi/darkith-forge` (branch `main`). Nothing
  survives a recycled VM except what is pushed there.
- **Restore at session start:** `bash tools/restore.sh`
- **Save before session end:** `bash tools/continuity.sh "what changed"`
- See `RESUME.md` for the full protocol. Secrets (the APK signing key) never enter git.

## 0a. THE TRIPLE LAW (MUST #37) — Python ships its .js and .ts primitives
Python is the authority; the `app/src/main/assets/vendor/` twins are its universally
agnostic accompaniments: `.js` for the WebView, and `.ts` as a base primitive in its
own right — `.py`, `.js`, `.ts` parities fully integrative, no language a second-class
citizen. Every Python surface that states a law must ship runnable twins in BOTH
`.js` and `.ts`, and all three must agree **byte-exactly** on identity (sha256
vectors, GENESIS anchor, receipt_id, fire order) — not merely "all work".
`tools/nodal_gate.py` proves the triad and fails closed on any divergence. First
tri-carrier: `nodal/` + `vendor/nodal.js` + `vendor/nodal.ts` (Auto-Nodal
Co-ordina-Sync).

## 0b. TWO TABS = TWO SANDBOXES (they share ONLY the git remote)
Two OpenHands tabs run in **separate ephemeral sandboxes**. They do NOT share a
filesystem; the remote branch `main` is the ONLY channel between them, and it is
the single authoritative history. Consequences:
- An **uncommitted** edit is invisible to the other tab and can be lost. Commit.
- Convergence is not "fetch" — it is **sync, then re-run the gate on the merged
  tree**, because two tabs can edit different lines of one file and merge cleanly
  into something logically broken (git cannot see that; the gate can).
- **Ritual, at the start AND end of any turn where both tabs may have written:**
  ```bash
  bash tools/converge.sh     # 1/2 tools/sync.sh  ·  2/2 tools/ci.sh
  ```
- `tools/sync.sh` never force-pushes and never auto-resolves a conflict: on a
  same-line clash it stops and names the files, so no tab's work is destroyed.
- The gate now carries **discrepancy detectors**: clean-tree, fork singularity
  (NEVER #11), and version truth (manifest vs AGENTS.md).

## 0c. REVITALIZATION - the sixteen-stage corrective cycle (one apparatus)

The Operator's convergence of every prior diagnostic/repair spelling onto one fixed
point: sixteen serial stages, each consuming the previous stage's VERIFIED receipt.
Canonical tool: `tools/revitalization.py`; invariants I1-I10 are encoded IN the tool
and witnessed by its sandbox self-test (`python3 tools/revitalization.py selftest`),
not by notes. Key obligations:

- a step advances only when its predecessor's receipt exists and is hash-verified;
- states are exactly PASS / FAIL / SKIP / INACTIVE - SKIP is never PASS, INACTIVE
  never implies healthy;
- repairs are root-level (generated tissue is regenerated, never patched) and
  authorization-bounded (detection autonomous; consequential mutation only under an
  AUTO_APPROVED-class plan entry in `proof/revitalization/repair_plan.json`);
- failure routing: same root cause reopens the corrective task; a new root cause
  creates a linked defect (Divergence-9);
- closure is evidence-only: S14 reconcile clean + S15 seal attached + board accurate;
  recurring drift reopens.

Commands: `run` (execute a cycle; writes receipts under `proof/revitalization/`),
`gate` (read-only chain verification; runs in CI), `selftest`, `write-board` (paste
the sealed cycle onto TASKS.md). Exit codes: run 0 closed / 1 defects open /
2 deferred; gate 0 sound / 1 violation / 3 no receipts yet.

## Project
- Android app **Darkith** + an offline web studio. Built on a phone in Termux via the
  **NT IX 7-step raw chain** (`aapt2 -> kotlinc -> d8 -> zip -> zipalign -> apksigner`).
- **Gradle is physically forbidden** (SPI-1: deadlocks the phone's RAM). Never run or suggest it.
- Kotlin sources: `app/src/main/java/com/darkith/transliaison/` (the ONE authoritative tree,
  reconciled into the repo key-free; 55 .kt files). `build.sh` and `res/`/`assets/` sit beside it
  under `app/src/main/`. There is no tree/ or tree_omega/ directory on disk any more — those were the
  forks, and they are gone.

## SPI invariants
- **SPI-2** read exact bytes before writing — do not guess.
- **SPI-3** isolate the tree before modifying.
- **SPI-4** log to disk; read from disk (the terminal lies).
- **SPI-6** read the whole log, not just the first error.
- **SPI-8** home is the SD card, not the cloud.

## Comment defects (resolved)
The original defect was **not** a stripped `/*` opener. It was a mangled **closer**
(a line of just `//` where `*/` belonged), in **2** files: `core/CssLite.kt:3`,
`core/SubstrateIngestor.kt:92`. `tools/kt_comment_scan.py` is a nesting/string-aware
Kotlin lexer; `tools/fix_unclosed_comments.py` repairs only proven-unclosed lines.
The working tree scans **0 defects**. Verify with `python3 tools/comment_audit.py`.

CI now **enforces** this class: `tools/syntax_gate.py` (the "kotlin syntax gate")
scans every tree root and fails on either `UNCLOSED` or `ORPHAN_CLOSE`. It does
not re-implement the lexer — it imports the one canonical `tools/kt_comment_scan.py`
(SPI-27). A stripped opener (`sed` removing `/*`) is exactly an `ORPHAN_CLOSE`, so
that failure mode can no longer reach the raw chain.

## Web studio (offline, no build step)
- `savf.html` — SAVF universal audit engine (`window.SAVF`).
- `app/src/main/assets/vendor/darkterm.js` — **DarkTerm**, a real POSIX-style shell in one
  file (the canonical copy; the studio embeds it byte-identically). Exposes
  `window.DarkTerm` (browser) / `module.exports` (node). `registerCommand(name, fn)`
  adds a builtin. `createSession()` returns a facade with `.exec(line)`.
- `app/src/main/assets/vendor/darktools.js` — handcoded dev toolkits layered on DarkTerm: `task` (task manager),
  `sync` (learnable synchronicity engine + deficit ledger + omega ladder), `tk`
  (toolkit host), `store` (persistence). Installed via `DarkTools.install(session, opts)`.
  `opts.fresh: true` reseeds tasks AND resets the sync engine.
- `app/src/main/assets/darkith_ui.html` is the SAME page as `darkith-inscriber.html` — a
  byte-identical mirror (the app ships the asset; the repo-root copy is for the browser).
  `tools/ci.sh` check D-2b fails the moment the two drift (NEVER #11).
- `darkith-inscriber.html` — the studio app. 4 inline `<script>` blocks:
  0 SAVF, 1 DarkTerm engine, 2 DarkTools, 3 studio layer. **The engine block must stay
  byte-identical to `app/src/main/assets/vendor/darkterm.js`**; re-embed after editing either.
- `darkith-omega-media-player.html` — the Ω **media player** (`window.DarkithMedia`, v1.1).
  Single file, offline, no build. Agnostic: plays whatever the engine decodes and takes any
  source — file, folder, drag/drop, paste, URL, m3u playlist, or a real device path via the
  `darkith` bridge (`fileRoots`/`fileList`/`fileRead`; the wire shapes in `DarkithBridge.kt`
  are the contract, honoured exactly). Ergonomic: keyboard (space/←→/j/l/`,`/`.`/`[`/`]`/`0-9`/
  m/f/p/c/v/e/n/b/s), tap + double-tap gestures, drag-drop, paste-to-add, fullscreen, fit modes
  (contain/cover/fill), speed ladder, frame-step, screenshot, A–B loop, bookmarks, subtitles
  (VTT/SRT, including device subtitles), queue with dedupe + sort, resume-where-you-left-off.
  Coupled: Media Session (lockscreen/headset, incl. position state), Picture-in-Picture, Remote
  Playback (cast), Wake Lock, Web Audio (visualiser + 6-band EQ), BroadcastChannel (cross-tab),
  localStorage (prefs/marks/history), `crypto.subtle` (sha256 provenance). Every capability is
  feature-detected and degrades honestly; a broken item is skipped, never a silent stall.
  Tested by `tools/test_media_player.js` (real script, DOM shim + bridge-contract stub).

## §36 THE Ω DEFAULT-APP SUITE — handcoded Android apps (binding, 2026-11-10)

The Operator is handcoding the Android default apps. Each app is ONE HTML file, offline,
no build step, exposing a `window.Darkith<Name>` namespace, tested by a DOM-shim harness
that executes the REAL script, and reachable from ONE surface (`darkith-omega-apps.html`).

| app | file | namespace | bridge families |
|---|---|---|---|
| Files | `darkith-omega-files.html` | `DarkithFiles` | `file*`, `fileRoots`, `storageGranted` |
| Player | `darkith-omega-media-player.html` | `DarkithMedia` | `fileRoots`, `fileList`, `fileRead` |
| Phone | `darkith-omega-phone.html` | `DarkithPhone` | `dial*`, `sys*` |
| Messages | `darkith-omega-messages.html` | `DarkithMessages` | `sms*`, `sysRequest` |
| Contacts | `darkith-omega-contacts.html` | `DarkithContacts` | `contacts*`, `dialNumber`, `smsCompose` |
| Camera | `darkith-omega-camera.html` | `DarkithCamera` | `camera*`, `mediaList`, `deviceResult` |
| Clock | `darkith-omega-clock.html` | `DarkithClock` | `clock*` |
| Launcher | `darkith-omega-apps.html` | `DarkithApps` | `version` |

- **THE TWO fileList CONTRACTS.** `DarkithBridge.fileList` answers `[{name,dir,size}]`;
  `HomekeeperBridge.fileList` answers `[{name,type,bytes,mtime}]`. `DarkithFiles.normEntry`
  normalises both, so the UI never depends on which host it runs under. Any new file
  consumer MUST go through `normEntry`/`normList`.
- **BINARY_REFUSAL.** `HomekeeperBridge.fileRead` refuses archives and dex with
  `ERROR: BINARY_REFUSAL` and caps text at 3 MB. The file manager surfaces that as a fact
  ("Binary file — not shown as text"), never as a failure to hide.
- **HONEST CAPABILITY.** No app fakes device access. A missing permission renders as
  "not granted" with a request affordance; a denied query returns an empty list plus the
  reason. `cameraCapture` answers `PENDING:<id>` and is collected by bounded polling of
  `deviceResult(id)` — it gives up and says so, it never hangs.
- **SPI-19, whole families.** `DeviceBridge.kt` adds dial/sms/contacts/camera/clock/media/
  notif/sys as COMPLETE families, forwarded through `HomekeeperBridge` so the JS namespace
  stays the single `darkith` object. Raw `android.*` only (SPI-13): zero `import androidx`.
- Tested by `tools/test_files.js` (37) and `tools/test_device_apps.js` (40); both are wired
  into `tools/ci.sh`.

## Multi-session gotcha
DarkTerm has one global command table, so app commands resolve their context **per
shell** via `sh._dtctx` (inherited by `fork`). Installing a second session must not
rebind commands to the first session's state.

## Shell sigil gotcha (important)
DarkTerm's lexer treats `#` as a comment start (POSIX), so `task add x #tag` **silently
loses the tag**. The canonical tag sigil is therefore `+tag` (e.g. `task add x +parser`),
which survives the shell. Both `+tag` and quoted `'#tag'` are accepted. Prefer `+tag` in
all docs, banners, suggestions and tests. Priority is `!N` (survives fine).

## Synchronicity engine (darktools.js `sync`)
- score = `sigmoid(w · x)` over 13 features; learns from **explicit** intent
  (`task do|focus|defer`) and **passive** evidence (`SyncEngine.observe` on every real
  command via `sh.onCommand`, wired in `install`). Working in a `+tagged` area credits
  the matching task and reinforces the tag.
- **Deficit ledger** (`DeficitLedger`): the engine never silently stubs and never injects
  a defect. Anything unsyncable (unattributable command, untagged task, dangling id,
  contradiction, unmet capability rung) becomes a named, deduped, actionable deficit.
  `sync deficits` lists them; `sync deficits resolve <id>` clears one.
- **Omega ladder** (`sync omega`): 8 measurable rungs; each unmet rung is auto-raised as
  a `rung` deficit. `deficits-clear` is scoped to non-rung deficits (else self-referential).
- Commands: `sync top|weights|why|signals|deficits|omega|claim|explain|reset`;
  `task add|list|do|focus|defer|tag|next|rm`.

## Verification
- `bash tools/ci.sh` — the one command that runs every suite, provider-neutral. Any CI
  (or a phone) calls this; vendor YAML is only a thin adapter around it. Exit 0 == green.
- `node tools/test_darktools.js` — 49/49 (tasks, explicit+passive learning, ledger, omega,
  tk host, persistence). `NODE_PATH=/tmp/node_modules node tools/test_inscriber.js` — 14/14
  (jsdom drives real Enter keydowns). Both are wired into `tools/ci.sh`.
- jsdom functional test needs `url:` set (localStorage rejects opaque origins).
- Serve: `python3 -m http.server 12000` in the repo root.

## Proof logs on disk
`proof_comment_audit.log`, `proof_darkterm.log`, `proof_toolkits.log`,
`proof/comment_premise_check.txt` (the 19-file comment briefing check, SPI-4).

## OMEGA reconciliation + compile proof (this session)
- **Canonical source tree**: `app/src/main/java/com/darkith/transliaison/` (build.sh layout),
  reconciled from all forks into the repo key-free. The old forks (tree/, tree.orig/,
  tree_omega/) are gone; DARKITH.md Part 2 records the reconciliation.
- **Compile proof (real, not grep)**: kotlinc 1.9.24, `-cp android-all-14.jar:apksig-8.1.1.jar:R-classes`
  -> EXIT=0, 0 errors, 0 warnings, 166 classes. android.jar stand-in: Robolectric
  `android-all-14-robolectric-10818077.jar` (137 MB). apksig: Google maven 8.1.1.
- **R.java** comes from `aapt2 link --java` (build.sh step 2) using `res/` — real, not stubbed.
- **Biggest defect**: W-034 Phantom Activity — `MainActivity`/`HomekeeperActivity` extended
  `Activity()` with no `import android.app.Activity`; ~90 cascading errors. Check imports when a
  base class is unresolved.
- **AndroidX residues stripped** (raw chain cannot see them): registerForActivityResult ->
  startActivityForResult; ContextCompat/ActivityCompat -> raw; FileProvider -> PackageInstaller
  (DarkithBridge) / null (HomekeeperBridge hkUri). Zero `import androidx` remain.
- **authored** (missing in every fork): `AndroidManifest.xml`, `res/`, `assets/` layout,
  `core/IRAuditor.kt`. **purged**: `ComposeEmitter` (HTML->Compose is closed by design; the live
  path is `IRBuilder`/`OmegaRenderer`).
- **Comment checker gotcha**: a naive `/* */` scanner false-flags Kotlin comments containing
  apostrophes (e.g. "renderer's"). Only kotlinc is authoritative (W-023).

## Dependency watching (darkbot — replaces the hosted service)
- `tools/darkbot.py` + `tools/deps.txt` are the source of truth. No vendor config.
  `tools/deps.txt` holds `<ecosystem> <name> <version>` (pypi|npm); `requirements-dev.txt`
  is GENERATED from it by `python3 tools/darkbot.py export` — never hand-edit that file.
- Commands: `report|check` (drift vs the public registry), `update` (bump pins),
  `export` (write requirements-dev.txt), `selftest` (offline, no network — in ci.sh),
  `digest <eco> <name> [ver]` (registry sha256 per artifact), `verify <file> <sha256>`.
- stdlib only: runs on the phone in Termux with no installs. Talks to PyPI/npm, never to a
  CI vendor, so changing code host does not touch it.

  ## Novelty hunting (the Fracture Scout — MUST #30)
  - `tools/fracture_scout.py` + `tools/fractures.txt` are the source of truth. No vendor
    config. `tools/fractures.txt` holds one line per query: `<source> <boolean expr> [weight]`,
    sources `arxiv|nvd|hn|github-issues|ietf|rss`. Edit that file to reconfigure the hunt.
  - Commands: `scan` (query every source, rank by novelty x unresolved-ness, write
    `proof/fracture_scout.json` + a markdown digest), `report` (read the last scan from disk,
    no network), `selftest` (offline, no network — in ci.sh).
  - "Non-naive" = a real boolean parser (parentheses, AND-before-OR, "quoted phrases") that
    produces DNF and fans out per each source's own dialect. A naive topic grep drowns in noise.
  - Scope is the DEEP web (APIs, defect registries, forums, standards trackers, feeds), never
    the dark web: the scout must stay gateable, and a fracture must have a checkable referent.
    A "fracture" is the corpus's own term (NT-V §XIX.15). The scout PROPOSES; the reality check
    ADMITS a survivor to the board as a NOVELTY row.
  - Cadence: `.github/workflows/fracture-scout.yml` (daily cron + `workflow_dispatch`); it opens
    a PR with the digest. stdlib only — runs on the phone in Termux with no installs.
- SECURITY (MUST #31): no credential in the tracked tree. `tools/secret_gate.py` is
    fail-closed — it scans every tracked (and `--staged`) file for token/key/private-key/
    URL-cred/generic-secret shapes and exits non-zero on any hit (no warn-and-continue). Run in
    `tools/ci.sh`. A finding is removed and ROTATED (a rewrite does not un-leak a token) or
    recorded in the gate's ALLOW with a reason. A security fix is never silent:
    `tools/security_alert.py push` opens ONE dedup'd issue (labels `security`, `critical`) and
    GitHub pushes it to the Operator's device app. Autofix of a reversible, well-understood
    security gap needs no permission — the push notice is how it is reported.
  - The git remote is TOKEN-FREE (`https://github.com/...`, no `user:token@`): the credential is
    supplied at run time by a git credential helper that reads `$GITHUB_TOKEN`, so no secret is
    written to `.git/config`. Never paste a token into a remote URL or a tracked file.
- `.github/workflows/auto-merge.yml` is the thin GitHub adapter: tests (tools/ci.sh) then
  merges a dependency PR (Dependabot and darkbot authors). The bot's own bumps are tested
  and committed directly, because a PR opened with GITHUB_TOKEN never triggers a second
  workflow run (approval-required state) — the recursion trap. No PAT, no pull_request_target.

## §19 ANTI-DIVERGENCE LAWS (binding — see DARKITH.md Part 2)
NEVER #11 One Tree: never keep two divergent live copies of a file. Reconcile into one; the
  loser is deleted or frozen read-only with a dated supersession note (DARKITH.md Part 2).
NEVER #12 No Foreign Symbol: never reference a symbol defined in another tree (ComposeEmitter
  was referenced everywhere and defined nowhere). Author it in-tree or remove the reference.
NEVER #13 No Unproven Currency: a tree is current only after a clean compile of THAT tree.
MUST #10 Byte-Diff Every Fork before declaring a tree current; resolve every divergence
  explicitly (no assumption).
MUST #11 Compile Is The Proof: reconciliation ends with 0 kotlinc errors vs a real android.jar.
MUST #12 Version Every Input: AndroidManifest.xml, res/, assets/, build.sh live in the tree.
MUST #13 Ledger Entries Are Gates: every failure class becomes a check, or it is re-opened.
SPI-12 one authoritative tree · SPI-13 every symbol resolves in-tree · SPI-14 every input
  versioned · SPI-15 a ledger entry that is not an executable gate is a note, not a law.
W-040: the ledger recurred because it was not a gate — W-021/W-023/W-024/W-034/W-035 all
  returned. The fix is `tools/fork_integrity_gate.sh` (the executable form of §19).

## The gate (run before declaring any tree current)
```
KOTLINC=/path/to/kotlinc tools/fork_integrity_gate.sh \
  app/src/main/java/com/darkith/transliaison \
  /path/to/android-all.jar  /path/to/apksig.jar
# PASS: all §19 laws held.  (SPI-12/13/14 + MUST-11 compile)
# Without kotlinc/android.jar it now FAILS (never a vacuous PASS); pass --no-compile
# to record the skip explicitly, and delivery_gate.sh then forces L-07/L-10 OPEN.
# CI provisions the toolchain with: bash tools/fetch_toolchain.sh
```

## §20 DELIVERY GATE — the loophole registry (binding)
NEVER #14: never say "delivered" without running tools/delivery_gate.sh and listing every
  loophole's status. "Delivered" is a gate RESULT, not an assertion.
MUST #14: the gate IS the delivery; non-zero exit forbids the word "delivered".
SPI-16: a delivery that did not run the gate is not a delivery.
W-041: the recurring defect was the ABSENCE of a delivery gate — shipping with unenumerated
  loopholes. The registry (tools/delivery_gate.sh) names all 19: L-01 manifest-version,
  L-02 apk-version, L-03 self-report, L-04 artifact-built, L-05 artifact-signed,
  L-06 artifact-aligned, L-07 fork-singularity (§19), L-08 bridge-contract, L-09 asset-parity,
  L-10 currency, L-11 registry-nonempty, L-12 one-surface, L-13 no-doc-dup, L-14 family-whole,
  L-15 signer-identity, L-16 arsc-stored, L-17 native-tools, L-18 install-gate,
  L-19 runtime-render. `--source-only` records the
  APK-dependent checks as named SKIPs on a box with no APK, never a silent pass.

## Version truth (never guess again)
- Truth is AndroidManifest.xml: versionCode=4, versionName=2.1.0-omega. Bridge VERSION=hk-bridge-52.
- One version of record: VERSION.json. `python3 tools/stamp_versions.py` stamps it into every
  terminal surface (darkterm/darktools/termkit/savf/fused pages); `--check` fails if any drifts.
- The app self-reports: `darkith.apkVersion()` -> "bridge=... pkg=... (code)".
- On device: `pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'`.
- From the APK: `aapt dump badging <apk> | grep ^package`.
- DARKITH.md records the current build + the delta vs what is installed.

## Build + deliver (this environment)
```
# build (real APK; android-all.jar works as the aapt2 -I jar too)
ANDROID_JAR=/tmp/android-all.jar R8_JAR=/tmp/r8.jar \
  KOTLINC=/tmp/ktc/kotlinc/bin/kotlinc KOTLINC_XMX=4g bash build.sh . Darkith com.darkith.transliaison
# gate (must print DELIVERED)
KOTLINC=/tmp/ktc/kotlinc/bin/kotlinc tools/delivery_gate.sh . app-signed.apk \
  /tmp/android-all.jar /tmp/apksig.jar
```
Toolchain got: aapt2/zipalign/apksigner via `apt install aapt android-sdk-build-tools`;
d8 via R8 jar (`dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.42/r8-8.2.42.jar`);
kotlinc 1.9.24 (JetBrains zip); apksig 8.1.1 (Google maven). `tools/fetch_toolchain.sh`
provisions all of it into `.tools/` (gitignored) so CI can run the real compile proof.
  - CI FAILS (not skips) when `.tools/` is absent: `ci.sh` forces FAILED=1 so a skipped compile
    proof can never look green. To run CI here, provision `.tools/` first — `bash
    tools/fetch_toolchain.sh`, or symlink an existing cache (`kotlinc`, `jdk-17.0.12+7`,
    `aapt2d`, `apksig.jar`, `android-all-14-robolectric-10818077.jar`). Then L-07/L-10 close.
  - Do NOT run two `kotlinc` compile proofs at once: each takes `-J-Xmx2g`, and two concurrent
    JVMs starve memory and emit spurious `unresolved reference` errors that look like real
    defects. Serialize (let the background CI finish before a manual gate run).

## WHERE THE SCROLLBACK LIVES (recover any prompt the app won't scroll to)
The GUI cannot always scroll back. The full event history is on disk:
- `/var/openhands/conversations/<conversation_id>/events/event-NNNNN-*.json` (one file per event)
- Also mirrored at `workspace/conversations/<conversation_id>/` (TASKS.json + observations).
Extract every user prompt in order:
```
python3 - <<'PY'
import json,glob,os
d=sorted(glob.glob('/var/openhands/conversations/*/events'))[0]
for p in sorted(glob.glob(d+'/event-*.json'),key=os.path.basename):
    e=json.load(open(p))
    if e.get('source')!='user': continue
    lm=e.get('llm_message') or {}
    t='\n'.join(c.get('text','') for c in (lm.get('content') or []) if isinstance(c,dict))
    print(e['timestamp'], t.strip()[:200])
PY
```
The schema: each event = {id,timestamp,source,parent_id,llm_message,kind}; the user text is
`llm_message.content[].text`. `TASKS.json` in the same dir is the agent's last task list.

## §21 CIRCADIAN + ONE-SURFACE (binding)
- The Operator's time is Asia/Manila (UTC+8). Report local time, never machine UTC.
  "N hours back" = N hours before the WAKE MARKER (first event of the active block), not the clock.
  Wake marker 2026-11-17 = 16:56 MN. Anchor must be stated so it can be falsified (MUST #15).
- ONE SURFACE (NEVER #15): never scatter delivery across many links. The delivery is ONE hub URL
  that lists every artifact with `download` + attachment serving (MUST #16, SPI-17).
  Hub = `dist/index.html`; regenerate with `tools/pack_delivery.py` when artifacts change.
- The hub shows version + gate status + sizes + hashes so the Operator verifies before installing.

## §22 DEDUPLICATION + IDEMPOTENCY (binding)
- ONE DOCUMENT (NEVER #16): DARKITH.md is the single canonical record (version + reconciliation +
  deficits + laws). Never fork it. Served/zipped copies are GENERATED by tools/pack_delivery.py.
- IDEMPOTENT (MUST #18): pack_delivery.py has no wall-clock, no self-hash, deterministic zip
  timestamps. Re-run -> byte-identical. Prove idempotency by running twice and diffing.
- Consolidation (SPI-18): tools/consolidate_docs.sh merges overlapping docs; refuses to delete
  unless the canonical doc already holds every law. Idempotent (2nd run is a no-op).
- UNIVERSAL KB INDEX (MUST #29): the readable knowledge-skill base is indexed, not scattered.
  tools/kb_index.py generates docs/INDEX.md (human) + docs/kb_manifest.json (machine) from the
  tracked bytes, in the repo's own registers — A-apparatus (root governance), B-knowledge
  (docs/** corpus), C-skillbase (root web apps), D-asset (app assets), E-evidence (proof/),
  F-config (dependency manifests). The registers are the repo's invariant A∧B∧C∧D applied to the
  filesystem: apparatus separate from content (B), one retrieval surface (C), one canonical copy
  (D). The gate (SPI-15) fails if the index is stale, a readable file is unfiled, two files share
  a hash without a declared mirror (NEVER #11/#15/#16), or a declared mirror has drifted.
  Deterministic: re-running yields byte-identical output (MUST #18).

## §23 NO STALLED DEFICIENCY (binding)
- NEVER #17: a named deficiency may not survive two deliveries. Close it or descope it, in writing.
- MUST #19: implement the FULL contract (a whole method family), or descope with the reason named.
  A partial surface must itself become a named entry.
- MUST #20: proof lives in the ARTIFACT, not the source — the symbol is in the compiled dex, the
  gate is green, the hash changed. "It compiles" is not "it shipped".
- SPI-19: a method family (shell*, file*, apk*) is whole or absent.

## §24 TREE INTEGRITY + RECONCILIATION (binding)
- ONE TREE (NEVER #18): exactly one authoritative source tree may exist. Once three existed
  at once (`tree`=50 .kt, `tree.orig`=50, `tree_omega`=55). Measured `tree` vs `tree_omega`:
  of the 50 common files, 39 identical and 11 divergent (`proof/FIELD_REPORT_THIS_TAB.md`);
  `tree_omega` also held 5 files `tree` lacked. (This is a different comparison from the
  earlier 6-fork union in DARKITH.md Part 2, where 6 files diverged — do not read the two
  counts as the same measurement.)
  They are reconciled now: the ONE tree is `app/src/main/java/com/darkith/transliaison/`
  (55 .kt), and the forks are deleted. §19/SPI-12 enforces that no second tree reappears.
- NO DISK-ONLY SOURCE (SPI-20): the app source may not live only on the ephemeral VM disk.
  When this rule was first checked, the canonical repo tracked ZERO of the 55 app .kt files.
  A recycled VM would have lost the app. Reconcile the tree into the repo, key-free, before
  any other work.
- COORDINATE INDEX (MUST #21): every tree gets an addressable index, generated from the bytes,
  not from prose: `tools/tree_index.py <root> [--json f] [--tsv f]` emits file, tier, package,
  every declaration + line, external namespaces, and in-tree deps. Deterministic, so two runs
  diff clean and drift is visible. A tree you cannot enumerate is a tree you cannot account for.
- REPACK LAW (SPI-21): any step that re-zips the APK MUST keep `resources.arsc` and `lib/*.so`
  STORED. Re-adding them to a `ZIP_DEFLATED` archive silently compresses them; Android 11+
  (API 30) mmaps them in place and the installer then fails with a bare "App not installed".
  build.sh step 5 had this defect; proven by running the old logic (DEFLATED) vs new (STORED)
  on the real base.apk. Verify per-entry compression after every repack.
- SCANNER IS NOT A PARSER (W-023 restated): a comment scanner must track string/char literals
  and nested block comments, or it misreads `val t = "*/*"` as an open comment. Only kotlinc is
  authoritative for syntax.
- CLASSIFY ERRORS (SPI-22): before fixing source, classify the compile log. 147 errors here were
  almost all `unresolved reference android` — the classpath lacked `android.jar`, not a source
  defect. Fixing source would have been motion, not progress.

## §25 DELIVERY RECORD — API 30 install fix + pre-run evidence (2026-11-17)
- INSTALL DEFECT FIXED (both shipped APKs): `resources.arsc` and `lib/*.so` were
  DEFLATED, so Android 11+ refused the install ("App not installed"). Repacked
  STORED, `zipalign -f -p 4`, re-signed with the SAME release identity
  (`CN=Darkith Release`). `build.sh` step 5 preserves STORED; `tools/ci.sh` gates
  every `delivery/*.apk`. Real bytes, not claims:
  `darkith-homekeeper-debug.apk` 16,377,082 B `2ea7e1dd…`; `darkith-forged-proof.apk`
  987,679 B `ec17b014…`.
- PRE-RUN (not inferred): `build/omega/ui-test.py` in headless Chromium at 360x800
  -> **OMEGA-UI 26/26 PASS**, 0 console errors, no overflow, in-app browser loads
  its frame. `savf.py selftest` -> ok; in-page SAVF self-test -> 9/9, 0 errors.
- TWO-TAB CONVERGENCE (§0b): `tools/sync.sh` + `tools/converge.sh` proven by a
  real divergence (two tabs, both commits survived, linear history).
- SOURCE ENCODING (fixed): `savf.py` used to read every file as strict UTF-8, so a
  file CPython runs fine — a UTF-8 BOM, or a PEP 263 `coding:` cookie for any
  non-UTF-8 codec — drew a false PARSE finding and flipped the verdict to LIED.
  Both surfaces now decode as CPython does: `savf.py` via `tokenize.open`; the
  browser core via a PEP 263 decoder (BOM, cookie on line 1 or 2 with line 2 only
  when line 1 is blank or a comment, name normalization, a strict ASCII path, and
  `TextDecoder` otherwise). Gate `7/7 encoding` in `build/verify.py` holds
  `savf.py` + the JS core to `ast.parse` over a 12-file corpus.

## §26 DELIVERY RECORD — forensic remediation + hub-generation rule (2026-11-17)
- FORENSIC REMEDIATION (P1–P5). The "vacuous green" family is closed by making each law an
  EXECUTABLE gate (SPI-15), not a note. Nothing here is asserted; every line is a gate result.
  - P1 vacuous green: `tools/fork_integrity_gate.sh` MUST-11 now FAILS CLOSED when kotlinc or
    android.jar is absent (it used to print `SKIPPED` and exit 0). `--no-compile` records the
    skip explicitly. `tools/delivery_gate.sh` forces **L-07** and **L-10 OPEN** whenever the
    compile proof was skipped (12 OPEN, `REFUSED`, exit 1). `build/verify.py` battery returns
    True/False/**None** so a missing playwright is a SKIP, not a FAIL. Proof: with no toolchain
    `tools/ci.sh` exits 1; with `.tools/` present the compile runs for real.
  - P2 gates were notes: `tools/ci.sh` now runs the §19 gate (compile proof), the delivery gate,
    the bridge-contract audit, `consolidate_docs.sh --check`, `doc_path_gate.py`, and the
    darktools/inscriber JS suites. `tools/fetch_toolchain.sh` provisions the raw-chain compilers
    (kotlinc 1.9.24, android-all-14, apksig 8.1.1, aapt2) into gitignored `.tools/`.
  - P3 doc drift: `tools/doc_path_gate.py` resolves every path cited in AGENTS.md/DARKITH.md/
    RESUME.md against `git ls-files` -> PASS. AGENTS.md reconciled: the old tree/ -> the
    one app tree, `tools/app/*` -> `tools/*`, bridge VERSION `hk-bridge-50` -> `hk-bridge-52`,
    registry 11 -> 19 loopholes (L-12..L-17 restored, L-18 install-gate and L-19 runtime-render
    added since).
  - P4 one tree: the fused `darkith forge.html` is now GENERATED and gitignored (F6 source-of-
    truth fixed in `build/refresh-host-artifacts.py`); the asset `savf.html` was renamed to `app/src/main/assets/savf_core.html`,
    removing the basename collision with root `savf.html`; `tools/ci.sh` D-2 now fails on ANY
    divergent same-basename copies (was a hardcoded name list) and D-2b guards the
    `darkith_ui.html` <-> `darkith-inscriber.html` mirror.
  - P5 hygiene: 11 zero-reference tracked files removed; the agent session-memory file untracked (its `.openhands` directory is gitignored now).
  - Real bytes: `kotlinc clean: 0 errors, 55 files` (`proof/kt_compile_proof.txt`);
    `proof/comment_19files_proof.txt` shows 0/19 unbalanced — the 19-file "unclosed comment"
    briefing did NOT match the bytes (the line numbers came from a stale fork), so no `/*` was
    injected. The compile is the proof, not the premise.
- HUB-GENERATION RULE (binding — extends §21 ONE SURFACE):
  - The hub is `dist/index.html`, GENERATED by `tools/pack_delivery.py` (its step 5/5). Never
    hand-edit it; regenerate it when artifacts change. Generation is IDEMPOTENT (§22): no
    wall-clock, deterministic, re-run -> byte-identical.
  - `tools/pack_delivery.py` also emits `dist/SHA256SUMS.txt`, the meta manifest, the source
    zips, and the transcript — the hub links them as forced downloads.
  - `tools/delivery_gate.sh` L-12 (one-surface) ENFORCES the rule: with no `dist/index.html`
    that lists every artifact as a forced download, L-12 is OPEN (delivery is fragmented,
    NEVER #15). The hub shows version + gate status + sizes + hashes (SPI-17) so the Operator
    can verify before installing.

  ## §27 DELIVERY RECORD — the one-shot installer + native-lib packaging (2026-11-17)
  - THE CORE DEMAND: a single, self-contained "build & install" entrypoint that builds
    the whole Keeper Forge tree with the raw 7-step chain and installs it, so the
    Operator can drop Termux after one command. It was REFERENCED but absent: three
    packagers (`make-repo-zip.py`, `make-bundle-zip.py`, `refresh-host-artifacts.py`)
    read `delivery/darkith-one-shot.sh`, and no file wrote it. Verified against the
    bytes (git ls-files, all refs, on-disk): zero `.apk`, zero one-shot, no `delivery/`.
  - FIX (both, executable, not notes):
    - `build&install.sh` (repo root, tracked): the Operator's entrypoint. Provisions the
      raw chain (`tools/fetch_toolchain.sh`), stages the child-forge engine inputs
      (`tools/stage_engine_inputs.sh`), runs `build.sh` (the 7-step chain), then installs
      via `termux-open`/`pm`. Gradle-free (SPI-1).
    - `build/make-oneshot.py` -> `delivery/darkith-one-shot.sh`: the SAME flow as ONE
      self-contained file (sh header + `__DARKITH_PAYLOAD_BELOW__` + ZIP payload). It
      extracts itself, verifies its own payload sha256, provisions, builds, installs.
      Idempotent; `--check` proves the payload matches the tree.
    - NATIVE-LIB DEFECT: the built APK shipped NO `lib/`, so the on-device forge would
      throw ToolFailure("libaapt2.so missing") at runtime. `build.sh` step 5 now packages
      `jniLibs/<abi>/*.so` as `lib/<abi>/*.so`, STORED (extractNativeLibs=true -> mmap+exec).
  - PROOF (real bytes): the one-shot was RUN end-to-end. `--build` printed the full
    1/7..7/7 chain ok, `apksigner verify` v2=true v3=true, `api30 gate ok`, and published
    a 7,992,419 B APK. `delivery_gate.sh` on it: **L-09 CLOSED, L-17-native-tools CLOSED**,
    L-04/05/06/15/16 CLOSED; only L-12 (the generated hub) OPEN. `proof/oneshot_proof.txt`.
  - GATES FAIL CLOSED (anti-lying, §26 spirit): `tools/ci.sh` now gates the one-shot
    (`build/make-oneshot.py --check`) and the entrypoint (`build&install.sh` exists, valid
    bash, Gradle-free). Removing the one-shot -> both gates FAIL and CI: FAIL; restoring
    -> PASS. A delivery APKs that lack lib/*/libaapt2.so fails L-17. Verified.
  - KNOWN-REMAINING (named, not hidden): L-12 one-surface OPEN — the hub `dist/index.html`
    is generated by `tools/pack_delivery.py` from the ONE tree `app/` plus the root docs
    (`DARKITH.md`, `AGENTS.md`, `RESUME.md`, `build.sh`), all of which ARE in the repo, so the
    hub is now reconstructable (`python3 tools/pack_delivery.py`). The legacy `make-bundle-zip.py`
    path is unreconstructable without the old forks. That is the next surface, not this one.

  ## §28 DELIVERY RECORD — install-vs-render audit + launch-crash fix (2026-11-17)
  - THE QUESTION: "after the package installer installs it, does the runtime UI actually
    render?" The install chain and the render chain are DIFFERENT laws. Install success
    (Zygote forks, system_server/AMS+WMS schedules, installer's v2/v3 + STORED + alignment
    checks pass) does NOT imply the Activity starts or paints. Both were audited here.
  - INSTALL LAWS — verified on the shipped APK (real bytes, not claims):
    - apksigner verify: v2=true v3=true. zipalign -c -p 4: OK.
    - resources.arsc + lib/*.so STORED (API30 mmap law). `delivery_gate.sh` on it:
      L-04/05/06/09/16/17 CLOSED.
    - "App not installed" is an INSTALL-chain symptom (signature / arsc compression /
      alignment / minSdk), not a render symptom. All four are green here.
  - RENDER LAWS — what actually paints when the icon is tapped:
    - MainActivity is a WebView host: `setContentView(R.layout.activity_main)` then
      `loadUrl("file:///android_asset/darkith_ui.html")`. Verified against the APK:
      `res/layout/activity_main.xml` + `resources.arsc` carry `layout/activity_main`
      (0x7f030000) and `id/webView` (0x7f020000) — both resolve, so no Resources.NotFound.
    - All manifest-named classes are in classes.dex: MainActivity, HomekeeperActivity,
      core.OmegaActivity, AegisReaper, WifiDirectBroadcastReceiver, DarkithBridge.
    - The asset is byte-identical to what was rendered: `assets/darkith_ui.html` sha
      e0d30f0c (224,224 B) == source. Headless Chromium on the asset: **0 console
      errors**, real painted DOM (editor + terminal + audit widgets, 3067 chars of text).
  - LAUNCH-CRASH DEFECT FOUND AND FIXED (render-fatal on Android 7-10):
    `AegisCircuitBreaker.checkAndRollback` called `getHistoricalProcessExitReasons`
    (API 30) UNGUARDED inside `MainActivity.onCreate`, BEFORE `setContentView`. minSdk is
    24, so on Android 7-10 that throws NoSuchMethodError and the launcher dies before the
    UI paints — invisible to any static resource check. Fixed with a
    `Build.VERSION.SDK_INT >= R` guard (import android.os.Build added).
    PROOF in the dex: disassembly shows `sget SDK_INT` -> `const 16, #30` -> `if-lt`
    branching PAST the `getHistoricalProcessExitReasons` invoke. On <30 the call is skipped.
  - GATE (fail closed, SPI-15): `tools/api_level_gate.py` fails when a curated high-API
    symbol appears in a file with no SDK_INT guard. Wired into `tools/ci.sh`. Verified:
    PASS on the fix, FAIL on the reverted buggy form. A launch crash of this class can no
    longer ship green.
  - STILL UNPROVEN (named, not hidden): a REAL device/emulator launch. This sandbox has no
    adb, no emulator, no /dev/kvm, so "Zygote forks and the window paints on a device" is
    not physically provable here. What IS proven: the APK installs, the classes resolve,
    the resources resolve, and the exact shipped HTML renders with 0 console errors.
  - COSMETIC (not a crash): no launcher icon ships (manifest has no android:icon) -> blank
    icon, correct label "Darkith". Named, not hidden.

## §29 THE BOARD IS A FILE (binding)

`TASKS.md` is the durable board and the read-first artifact alongside this file and
`DARKITH.md`. The in-session task tracker lives at `/workspace/conversations/<id>/TASKS.json`
and is wiped with the VM — it is not a board. On 2026-11-17 the only surviving board held the
`P1–P7` remediation pass and the omega vision (sensing core, one specialist app per developer
domain) had zero hits anywhere durable. Rule: any task, gap, or objective the operator names
is inscribed in `TASKS.md` in the same turn it is named, with a status and evidence.
`tools/board_gate.py` enforces it in CI (a `done` row with no evidence, or a row citing a
path that does not resolve, fails the gate). An item not in the board is a defect in the board.

## §30 THE SYNCHRONY BYLAW (binding, 2026-11-18)

Synchrony IS time tracking, and it is hardcoded into every app and every bot as GENERATED
code — never hand-written per surface. `build/gen_synchrony.py` emits the clock
(`build/gen/omega_time.js` for the browser, `build/gen/omega_time_runtime.py` for bots);
`build/inject_synchrony.py` injects it into every surface under
`app/src/main/assets/*.html` and stamps a live clock readout into each. The studio editor's
`saveDoc` stamps every save with a diachronic ISO key (`YYYY-MM-DDTHH:MM:SS+08:00`) so
documents sort by time; re-saving replaces the header, never accumulates. Bots route output
through the generated clock (`tlog`) so their logs carry the time. Zone is Asia/Manila
(UTC+8) everywhere. `tools/synchrony_gate.py` enforces all of it in CI (a surface with no
clock, or a hand-edited runtime, fails). Law: DARKITH.md §31 (MUST #23/#24/#25, SPI-25).

## §31 NO LAW IS A NOTE (binding, 2026-11-18)

`tools/law_gate.py` FAILS on any `[NOTE: not yet gated]` marker. Every declared
NEVER/MUST/SPI must name an executable gate that exists on disk. If a law cannot yet be
gated, the answer is to build the gate, not to annotate the law. The three laws that were
notes (MUST #15 circadian, MUST #16 forced download, NEVER #17 no-stalled-deficiency) now
have gates: `tools/circadian_gate.py`, `tools/download_gate.py`, `tools/stall_gate.py`.

## §32 CONVERGENCE, COUPLING & REAL-TIME BOARD (binding, 2026-11-18)

Two agents run in parallel; their outputs must CONVERGE in the repo, and the comparison must
be executable, not asserted. `tools/convergence_gate.py` derives the clock, the circadian
phase and the working tree through two independent implementations each and fails on any
divergence (proof -> `proof/convergence.json`). When the board changes, push it in the SAME
action with `tools/board_pulse.sh` (writes `proof/board_pulse.json` as the parallel-worker
ping; `--check` is gated in CI) — never leave the board as a private local view. The clock
AUTOCCOUPLES the edge device's own hardware system time to the global clock and reports
whether the device's zone agrees with the Operator's; every session BOOTS timestamp-aware and
records its boot instant, the user's last activity, and the circadian phase of each
(`tools/synchrony_pulse.py` -> `proof/synchrony_pulse.json`). Law: DARKITH.md §32 (MUST
#26/#27/#28, SPI-26).

## §33 THE SOURCE INSPECTOR & HOMEOKINESIS (binding, 2026-11-10)

`tools/source_inspector.py` is the logical trial examiner: it puts the SOURCE on trial the
way `tools/delivery_gate.sh` puts the ARTIFACT on trial. It carries a registry of 10 named
charges (unclosed comment, foreign `androidx.` import, `!!` assertion, stub `TODO`, swallowed
exception, trailing whitespace, missing final newline, conflict marker, hardcoded secret,
duplicate node function). Every charge is tried on a POSITIVE case (must catch the defect)
and a NEGATIVE case (must not flag clean code); a charge that fails either is a MISTRIAL and
stops the run — because a gate that cries wolf is a broken gate (W-040, §20). The lexer is
the ONE canonical `tools/kt_comment_scan.py` and the closer-restorer is the ONE
`tools/fix_unclosed_comments.py`; the inspector IMPORTS them, never forks them (SPI-27,
NEVER #11).

The equilibrium it enforces is HOMEOKINESIS, not homeostasis (MUST #32). A static tolerated
level is STASIS — the metastatic, autoimmune, carcinomalous malefactor the Operator named.
So the model is a RATCHET: the high-water mark per escrow class may only ever move DOWN; any
class above its HWM is a net addition of debt and FAILS; debt that does not flux downward for
5 deliveries is FORCE-DEGRADED to a blocker; a rise is permitted only by a recorded,
reasoned `--justify` waiver (an apoptotic exception). `source_inspector.py trial` proves the
four ratchet laws on a deterministic simulation, so the claim is executable, not asserted.
The verdict reports the CLEARANCE FLUX — health is the RATE of clearance, not the level.

Severity is the sentencing policy: BLOCKER (fails always), ESCROW (gated as a regression
against the HWM), COSMETIC (autofixed; fatal only with `--fail-on-fixable`). The bounty is
one scalar weighted 100:1:0.1. Commands: `trial` (calibrate + prove), `inspect` (verdict),
`fix` (autofix reversible charges, idempotent), `ratchet` (advance the setpoint one
delivery), `report`. Law: DARKITH.md §33 (NEVER #19, MUST #32/#33, SPI-27, W-048).

## §34 SAVF UTILITY HARDENING + CROSS-SURFACE PROOF (2026-11-18)
SAVF (`savf.py` CLI + `savf.html` offline webapp) is the utility this section governs: a
zero-dependency Python source auditor whose verdict names the rule/fact/computation behind
it. It is a TWO-SURFACE product — the CLI and the browser core must agree byte-for-byte, and
its seals must be portable between them. Verified this session by PRE-RUN, not inference:

- BROWSER BATTERY (real engines, `file://`, network blocked): `build/verify.py` [3/7] now
  runs because playwright is installed (chromium + firefox + webkit). `savf.html` (and the
  fused pages) load with **0 console errors, 0 page errors, net=0**. This was SKIP before —
  install the browsers (`python3 -m playwright install chromium firefox webkit`) to arm it.
- DIFFERENTIAL FUZZ (the strong parity proof): 1200 randomized sources (imports, stubs,
  markers, phantom attrs, swallow, taut asserts, BOM, CRLF, latin-1 cookie, syntax error,
  empty) scanned through the page's OWN contract — `SavfScan.scanBytes(path, bytes, opts)`
  with `window.SAVF_STDLIB` / `SAVF_STDATTRIB` — matched `savf.py scan` **1200/1200**, no
  divergence. Reproduce the surface: extract those two maps from `savf.html` and call
  `scanBytes` exactly as `runAudit()` does. (Passing an empty stdlib map is a HARNESS BUG,
  not a product bug — every stdlib import then reads as phantom.)
- CPYTHON REFERENCE: deep nesting (parens, indentation) and long binop chains agree with
  `compile()` on all three surfaces. CPython's real paren limit is 200 (201 -> SyntaxError);
  the JS core's `bracketDepth > 200` cap is CALIBRATED to it, not arbitrary.
- CRYPTO INTEROP (byte-identical): `SavfAudit.canonJson` == `json.dumps(sort_keys,separators)`;
  `SavfAudit.sealOf` == `hashlib.sha256(canon)`; `SavfHash.sha256Text` and
  `hmacSha256Text` == Python `hashlib`/`hmac`. A contract lock sealed in the browser verifies
  in the CLI and vice versa. Do not change one hasher without the other.
- FAIL-CLOSED VERDICT: garbage/missing phi states -> REVIEW (never PASS); `verdict` returns
  PASS(0)/REVIEW(2)/BLOCKED(3). Ledger is strict (kinds D/N/R/W/C/A/U).
- UI: 7 tabs (audit/gates/axis/ledger/freeze/self/help), no horizontal overflow at
  320–1440px, keyboard-focusable, theme toggle persists. Contrast passes AA in light+dark
  (the `.btn.pri` gradient is dark blue→purple with white text; a naive probe that ignores
  `background-image` will falsely flag it).
- RUNNING STATE: the tool writes its lock/manifest to the CWD (`.savf/`), by design —
  `build/savf-cli-test.py` asserts the repo root stays clean. `.savf/` is now gitignored.
  NEVER run `savf freeze`/`manifest create` with CWD = repo root, or CI's savf-cli test fails
  on the leftover `.savf/`.
- GATES: `build/verify.py` (7 checks incl. battery) and `tools/ci.sh` (45 gates) both PASS.
- TERMINAL SURFACE (Termkit `savf` builtin): defined ONCE in `build/build-forge.py`
  (`TERMINAL_BUILTIN`) and injected into the fused page between `/* SAVF-TERM:START|END */`.
  It calls `globalThis.SavfTruth.auditSource`, so the verdict printed in the terminal is
  the verdict the page and the studio give. Its EXIT CODE mirrors `savf.py`'s
  `EXIT = {PASS:0, REVIEW:2, BLOCKED:3, LIED:4}` — never collapse non-PASS to 1, or `$?`/
  `&&`/`||` in the terminal stop agreeing with the CLI on the same file. Verified in-browser:
  10/10 rule-exact vs `savf.py scan --json`, 6/6 exit-map match.
- ONE-SHOT: `delivery/darkith-one-shot.sh` = bash header + raw ZIP payload after the
  `__DARKITH_PAYLOAD_BELOW__` line. It is NOT valid bash end-to-end (`bash -n` fails on the
  binary tail by design); the header `tail`s the payload out and checks its sha256. On a host
  without the Android toolchain it fails HONESTLY (`apksigner missing`), never fakes a build.
- DUAL-REGISTER HELP: `help` (and `help beginner|novice|novices`) prints the beginner
  register; `help dev|developer|expert|ai|full` prints the developer register; `help CMD`
  stays the one-line `HELP` table; unknown args print an honest error (exit 1). Both
  registers are defined ONCE in `build/build-forge.py` (`HELP_BEGINNER` / `HELP_DEV`) and
  injected between `/* DUAL-HELP:START|END */` over the pristine `HELP_ANCHOR`. Rebuild
  restores `HELP_ANCHOR` first (`restore_dual_help`), so the injection is idempotent.
  LAW: every sample command + expected output in the help is PROBED from the live shell,
  never invented — a first draft claimed `test` runs the battery (it is the POSIX predicate;
  the battery is the `test` CHIP / `TermKit.selftest()`) and that `f(){ return N; }` sets the
  status (it is the LAST command's; a bare `return N` yields 127). Probe before you document.
  The developer register also carries the INVARIANT DEBUGGER (the fixture battery) and the
  FRACTURE CLOSURE (each Linux divergence, its closed form, why it is correct here).
- PARITY GATE (armed, `tools/savf_parity_gate.py`): the durable form of the differential
  proof above. It runs `savf.py` and drives `savf.html` through playwright/chromium and FAILS
  if the two ports disagree on any verdict (all-hard-fail, all-soft-fail, marginal cases) or
  any chart sign (3 charts × 3 axes × 2 moves). Wired into `tools/ci.sh` after the version
  surface gate. Skips loudly only when no browser is present. Run it after ANY change to the
  verdict rule, the chart table, or a hash helper — it is the cheap guard against one port
  drifting from the other.
- THIS SESSION re-verified, by pre-run: selftest 9/9; SHA-256 js==hashlib on 5/5 inputs
  (incl. empty + unicode); `fExp`/`gLog` exact inverse (max err 4.4e-16); freeze→check-freeze
  detects tampering (exit 1); HMAC `manifest create/verify` verifies clean and rejects a
  tampered artifact (exit 1); `scan` on stub/binary/non-UTF8 inputs returns honest findings
  with correct exit codes and no traceback; browser UI renders 0-error at 360–1280px in both
  themes with no horizontal overflow.

## §35 CLIENT-COUPLING UPDATE WATCHER (binding, 2026-11-18)
- THE GAP THIS CLOSES: nothing tracked whether the installed copy was stale against the live
  remote. The app could read its own version (`darkith.apkVersion()`) but never compared it to
  anything, and no version manifest existed for a client to read. Now: `VERSION.json` is the
  manifest of record; `build/updater.js` compares installed-vs-remote and alerts.
- INJECTED AT BUILD TIME, IDEMPOTENT: into the fused page by `build/build-forge.py`
  (markers `/* UPDATE-WATCHER:START|END */`) and into the app surface
  `app/src/main/assets/homekeeper.html` by `build/inject_updater.py`. BOTH strip before
  inject. TRAP (cost a debug cycle): `inject()` in build-forge.py ALREADY wraps the payload
  in the markers — `updater_block()` must return the bare `<script>`, never the markers too,
  or the block nests and the build grows ~25 bytes per run.
- MIRRORS, NOT ONE URL: the repo is PRIVATE, so `raw.githubusercontent.com` and
  `releases/.../download` 404 without auth, and the app's WebView has none. The check walks
  `VERSION.json.manifest_urls` (sovereign runtime host FIRST) via `fetchFirst()`, first answer
  wins; only when EVERY mirror is dead is the state `offline`. `manifest_url` MUST equal
  `manifest_urls[0]` (gated).
- NEVER LIE: offline -> `unknown` ("neither confirmed nor denied"), never a false `current`.
  The alert fires ONCE per new versionCode. `decide()` is pure; only the transport is stubbed
  in tests. Version algebra: versionCode is authoritative, else derived from a dotted name.
- PRESENTATION: `present()` prefers the host `UI.dialog`, else a self-contained overlay
  (`overlay()`, dark panel + gold Ω + one-shot link, fits 360px), else native `alert`. Every
  string is `textContent` — a remote manifest is UNTRUSTED and must never inject markup.
  (At runtime `window.UI` is undefined, so the overlay is the real surface, not the fallback.)
- VERSION TRUTH: bump in ONE place — `VERSION.json` — then run `python3 build/inject_updater.py`
  + `python3 build/build-forge.py`; `tools/update_gate.py` fails CI unless the `var LOCAL`
  stamp in the fused page AND the app surface, the AndroidManifest versionName, and every
  mirror URL in updater.js all agree.
- GATES: `node tools/updater_test.mjs` (38 checks) and `python3 tools/update_gate.py`, both in
  `tools/ci.sh`. Live-verified in headless chromium against the real public mirror (`current`)
  and a bumped mirror (`update`, alert names both versions), 0 page errors.
- GIT HYGIENE (cost two CI cycles): NEVER `git add -A` here. the `tree_omega/`, `dist/` and
  agent-scratch directories, plus `app-signed.apk`, are deliberately untracked; `add -A` commits them and
  then kb_index ("misfiled (no register)"), fork-singularity ("divergent copies") and the
  convergence tree hash all FAIL. Stage surgically: `git add -u` for tracked edits, plus
  explicit paths for new files.
- DEPLOY ORDER for a release that the live app can actually see: `inject_updater.py` ->
  `build-forge.py` -> `kb_index.py --write` -> one-shot/sync/bundle/repo/delivery to fixed
  point -> commit -> PUSH (board_pulse needs HEAD==origin) -> CI -> GitHub Release with
  the one-shot script + `VERSION.json` as assets. The runtime host (port 12000) is a
  moving sandbox: point the PRIMARY mirror at GitHub once the repo is public.
- APK DELIVERY (the shortest path for the Operator, who has no toolchain): the alert leads
  with **Download APK**, then the one-shot. `VERSION.json.apk_urls` (runtime host first) feed
  `DEFAULT_APK_URLS`; `decide()` carries `apkUrl`; `overlay()` shows both buttons. The signed
  build is published to `delivery/darkith-forge.apk` (served, HTTP 200) and as a release asset.
- REBUILDING THE APK: `build.sh` finds `keytool` on PATH, so export JAVA_HOME's bin (and the
  `.tools/bt/android-14` + `.tools/aapt2d` dirs) BEFORE running it, or it dies
  "keytool missing (no JDK)". It needs KOTLINC and ANDROID_JAR exported too. A clean run is
  7/7 and prints "DONE". The checked-in `app-signed.apk` was STALE (1.1.0-omega / code 2);
  after any surface change you must rebuild it or the APK lags the page. Verify with
  `aapt2 dump badging` and by reading the watcher out of the packaged `assets/homekeeper.html`.

## §36 THE OMEGA TERMKIT PRE-RUNNER + CLEARANCELOOP (binding, 2026-11-18)
- WHAT SHIPPED: two offline engines, injected into EVERY surface as one integration step.
  (a) PRE-RUNNER — `app/src/main/assets/vendor/prerunner.js` (canonical). One report contract,
  two engines: a sandboxed offscreen iframe for in-app/WebView, a real headless Chromium for
  node (`tools/prerunner-cli.js`, playwright-core + system `/usr/bin/chromium`, no browser download).
  (b) CLEARANCELOOP — `app/src/main/assets/vendor/clearanceloop.js`. The homeokinetic debt
  ratchet of §33 (`tools/source_inspector.py`) carried into the runtime: per-class friction HWM
  may only flux DOWN, a rise is a regression = FAIL, stasis over `WINDOW`=5 deliveries is
  force-degraded to a blocker, a rise needs a recorded waiver. `absorb(report)` closes the loop
  between them: a pre-run's errors + long tasks become friction debt.
- INJECTED BY `build/integrate-engines.py` (idempotent, marker-delimited: `<!-- PRERUNNER:START|END -->`
  + `<!-- PRERUN-SHIM:START|END -->`). It writes BOTH the surface's own shell AND the `studio-src`
  carrier inside `darkith home forge.html`, because `build-forge.py` regenerates the standalone
  studio AND the fused forge FROM that carrier. Run it BEFORE `build-forge.py`; `build/verify.py`
  (sync step 1) runs its `--check`, so drift fails CI.
- ANCHOR TRAP (cost a cycle): inject AFTER THE FIRST `<script>…</script>`, never after `<body>`.
  `build/make_core.py` extracts the SAVF core from savf.html's FIRST script — a block ahead of it
  is mistaken for the core and the build dies "engine or reference marker missing". Anchoring
  after the first script is also invisible to `build-forge.py` (which injects at the last `</body>`),
  so both `--check`s reproduce byte-for-byte.
- `</script` TRAP (cost two cycles): the carrier round-trips its payload through a `text/plain`
  script, escaping then UNescaping the raw closing-script sequence. So a literal `</script` OR its
  backslash-escaped form inside an injected engine/shim gets unescaped to `</script` and closes the
  tag early (SyntaxError). Neither engine nor the shim may contain that sequence — build it at
  runtime (`'<'+'/script>'`) and assemble closing-script regexes with `new RegExp`.
- RUNTIME SURFACE every app gains: `window.DarkithPreRunner`, `window.DarkithPrerun`,
  `window.ClearanceLoop`, `window.DarkithCL`; a floating `▶` FAB (id `prerun-fab`); a `prerun`
  and a `clearance` terminal builtin/command wherever the surface has one (omega `Omega.BUILTINS`,
  studio `CMD_REGISTRY`/`dispatchCommand`).
- REAL BUG THE FUZZER FOUND: the studio's `saveToPool()` HALTed `SAVE_FAIL` on `file://` because
  Chromium denies IndexedDB there — the app's exact offline case. Fixed in the canonical carrier
  to degrade to a toast. Re-apply if the carrier is ever regenerated from a stale source.
- GATES: `python3 tools/prerunner_gate.py` (engine surface + CLI exit contract + honest verdicts),
  `python3 tools/clearanceloop_gate.py` (the four ratchet laws + engines wired into every surface),
  `python3 tools/clearanceloop_ui_gate.py` (147 real-browser checks on the shipped
  `clearanceloop.html`: every tab, observe→advance→verdict, waiver grant/expiry, in-app self-test,
  keyboard, export, reload persistence, hostile stored state, denied storage, and MEASURED WCAG
  contrast + 40px tap targets + clipping in both themes at 360px and 1280px; skips exit 0 when no
  browser is installed), and `node tools/prerunner-cli.js --selftest` (8/8). All four in `tools/ci.sh`.
  Dogfood proof: all six surfaces PASS with 0 page errors at 360×800 (`node tools/prerunner-cli.js
  <surface> --stress 15 --expect DarkithPreRunner,ClearanceLoop`).
- UNTRUSTED STATE IS A REAL BUG CLASS (fuzzer-found, fixed): `hwm`/`since`/`justified` missing from a
  persisted or imported state made `report()` throw `Cannot read properties of undefined`. The throw
  happened at boot, so the app went permanently blank AND the UI that would reset the state never
  booted — an uncleanable brick from a hand-edited file. `normState()` now rebuilds every field from
  scratch in `load()` and `restore()` (which also accepts a raw JSON string). Same class in the CLI:
  JSON allows `1e309`/`NaN`, and `int(inf)`/`int(nan)` escaped as tracebacks; `_int()`/`_finite_int()`
  now fail loudly on law-bearing counts and degrade to 0 on waiver bookkeeping. Guard any new
  persisted field through the normaliser, and never `int()` a JSON number unguarded.
- WAIVERS ARE REVOCABLE (L5b, added after use): a waiver could be granted but never ended early —
  the only escape was `reset()`, which destroys the high-water history that is the ratchet's whole
  value. `ClearanceLoop.revoke(cls)` (engine), the "Revoke now" button on the Waivers tab, and
  `clearanceloop.py revoke <cls>` all end it in place. Revoking FAILS CLOSED: the debt is a live
  regression on the next report, the HWM is untouched and history is preserved. Covered by L5b in
  `tools/clearanceloop_gate.py`, in the CLI selftest (10/10) and in the webapp gate (157 checks).
- CONTRAST TRAP: raw `--ok`/`--bad` status hues are only legible on the DARK surfaces. On light panels
  in the light theme they measure 3.15:1 (toast) and 3.54:1 (self-test tick) and fail WCAG AA. Use the
  contrast-safe flux inks (`--flux-ok`/`--flux-bad`) for any status text on a light panel.

## §37 THE VISUAL-AFFORDANCE SPECIALIST — the Ω Icon Forge (binding, 2026-11-10)

  The first domain app of the launcher userspace: one offline, zero-dependency page
  (`icon_forge.html`) that forges **icons, logos and thumbnails**. Five tabs — Icon, Logo,
  Thumbnail, Couple, Ledger. It is a specialist in the §B sense: a typed spec in, a
  deterministic artifact plus an audit record out.

  What it emits is INSTALLABLE, not art: `res/drawable/ic_launcher_foreground.xml` (a real
  VectorDrawable, or a PNG fallback), `res/values/ic_launcher_background.xml`, the two
  `res/mipmap-anydpi-v26/{ic_launcher,ic_launcher_round}.xml`, and legacy mipmaps. The pack
  travels as a STORED, fixed-timestamp ZIP, so a rebuild is byte-identical and `buildKey()`
  (a sha256 of the spec) is a truthful identity.

  Coupling is real: it writes every file through `window.darkith.fileWrite` to
  `/sdcard/Darkith/icon-pack/` and records the device directory in the ledger. With no bridge
  the coupling gate reads UNAVAILABLE — never a silent PASS. The four-state gate (measured /
  unavailable / not-sampled / inferred) is the honest sensor; absence is a state.

  Every emitted `android:pathData` is absolute `M/L/C/Z` only (arcs are converted to cubics
  first). The safe-zone gate samples each path segment — a bbox-corner test over-estimates a
  circle and would cry wolf, so it is gone.

  Gates: `tools/test_icon_forge.js` (18 checks; a dependency-free DOM/canvas shim evaluates the
  REAL script), wired into `tools/ci.sh`. Law: DARKITH.md §34 (NEVER #20, MUST #34, SPI-28,
  W-049). Board: TASKS.md §I (H1-H7), which closes C4.

  Note (SPI-2): a briefing claimed 19 `.kt` files had "Unclosed comment" errors at cited lines.
  Reading the exact bytes, all 19 files are balanced and 18 of the 19 cited lines already open
  a valid `/**` (the 19th, HomekeeperBridge.kt:282, is a code line). `tools/syntax_gate.py app`
  = PASS, 55 files. The injector would have CREATED the defect it set out to fix.

## §38 THE DUAL-REGISTER MANUAL — TermKit `help beginner` / `help dev` (binding, 2026-11-10)

  TermKit's `help` now has two registers, both served from ONE source of truth so they can
  never disagree with each other or with the engine:

  - `help beginner` — plain-language guide for a first-time user: what the shell is, six
    rules, worked samples printed with their REAL output, files, failure codes, and a
    pointer to `help dev`. It never uses the word "invariant".
  - `help dev` — the machine register for experts and AIs: the model, the POSIX-subset
    grammar, the invariant list, every fixture as `cmd => expected ($?)` with a one-line
    `why`, a TermKit-vs-Termux/Linux comparison table, and the fracture-closure rationale
    for each design choice.

  Single source: `build/termkit-help.js` sets `global.__TermKitHelp` (beginner, dev,
  compare, closure, fixtures, builtins, version). `build/build-forge.py` injects it into
  the canonical shell between `<!-- TERMKIT-HELP:START/END -->` markers (idempotent), and
  the shell's `help` builtin consults it (`help`, `help CMD`, `help beginner`, `help dev`).

  No drift is possible: `tools/termkit_help_audit.mjs` extracts the REAL Part A+B core from
  `darkith home forge.html`, runs every fixture in a fresh `Shell`, and asserts stdout +
  exit status against what the manual prints (84 checks, 34 fixtures), and cross-checks the
  manual's builtin list against the engine's. Wired into `tools/ci.sh`, so a lying sample
  turns CI red. The canonical page also carries an in-page `hk58 help dual register` test.

  Regenerate after editing the manual: `python3 build/build-forge.py` (writes the fused
  page) then `python3 build/make-oneshot.py` (the one-shot embeds the shell).

## §39 SAVF CLI ARGUMENT HARDENING + CROSS-ENGINE PROOF (2026-11-19)
Second pass over the SAVF utility (§34 governs the product; this records what a fuller
pre-run found). The engine itself was faithful — two REAL defects were in the CLI shell,
both reproduced before they were fixed:

- DEFECT (fixed): a NEGATIVE axis coordinate could not be passed on the command line.
  `savf axis --p0 -41.4,-8.1 --p1 1,2 --s .5 --tau 1` died with argparse's
  `argument --p0: expected one argument`, because a leading `-` reads as an option. For an
  axis/formulary tool negative poles are the ordinary case, so this broke the primary
  command. Fix: `_normalize_argv` folds a data-looking token (`-3`, `-1.5`, `-41.4,-8.1`)
  onto the option it follows (`--p0=-41.4,-8.1`); real flags are untouched, `--tau -1` works
  too, and `s` still validates to [0,1]. Regression checks live in `build/savf-cli-test.py`.
- DEFECT (fixed): freezing an ABSENT file raised a bare `FileNotFoundError`. It now
  prints `freeze: no such file: <path>` and exits 1, matching `scan`. No CLI path leaks a
  traceback for ordinary misuse (checked verdict/ledger/manifest/sign/freeze/scan).

Pre-run evidence this session (all through the REAL engines, not inferred):
- CROSS-ENGINE: `savf.html` driven under BOTH chromium and firefox — identical freeze seal,
  identical HMAC, identical selftest (9/9) and verdict, 0 console/page errors, 7 tabs each.
  Seals are byte-portable: a lock sealed in the browser == `savf.py freeze` (SEAL MATCH,
  LOCK EQUAL) and the HMAC matches `savf.py manifest create`.
- DIFFERENTIAL FUZZ: 150 randomized Python sources through `window.SAVF.auditSource` vs
  `savf.py scan --json` — **150/150 identical**; plus 372 core cases (60 random axes,
  all 3 charts × 3 axes × 8 moves incl. the error cases, 40 exp/log round-trips, 200 random
  phi-state verdicts) — **372/372 identical**.
- OFFLINE: loaded under a context with `offline=True`; ZERO non-`file:`/`data:` requests,
  audit + selftest still work, 0 errors. The "offline, zero-dependency" promise holds.
- UI: no horizontal overflow on any of the 7 tabs at 360px; contrast 17.6:1 (dark) / 17.2:1
  (light); every button and tab >= 44px; FAB drags, theme + tab persist across reload.
- CI: `tools/ci.sh` exit 0 (CI: PASS). `board pulse` passes once the branch is pushed.
- INSTALL GATE ARMED: the install gate skipped even on a provisioned runner because
  `apksigner` (which ships in the build-tools tree that the host-artifact refresh
  stages under the toolchain dir) was never staged, though `tools/ci.sh` already put `aapt2` on PATH. Staging `apksigner`
  (and `APKSIGNER`) runs the gate for real: all four delivery APKs report INSTALLABLE
  (14/14 checks closed). A bare runner still skips by name, never fakes a pass.

NOTE — `tools/sync.sh` defaults `BRANCH=main` but the working branch is
`absolution/admission`; a bare `tools/sync.sh` therefore rebases against the WRONG branch and
reports a false conflict. Push the working branch with
`DARKITH_BRANCH=absolution/admission tools/board_pulse.sh` (never force). `main` and the
working branch are separate histories here.

## SAVF pre-run, third pass (reach/mutate false-green + scout re-run)

Two more REAL defects found and fixed, both reproduced before the fix:

- DEFECT (fixed): `reach` and `mutate` built their source list with a bare
  `[p for p in py_files(src) ...]`. `py_files()` returns `[]` for a path that is not there,
  so a typo'd `--src` made `reach` print `{functions: 0, missed: []}` and exit 0, and
  `mutate` print `{mutants: 0, score: null}` and exit 0 — a confident green that hides a
  missing path, the exact false-green `scan` already refuses. Both now route through
  `_source_files()`, which errors cleanly (non-zero, no traceback) on a missing path and on a
  directory with no Python in it. Locked in `build/savf-cli-test.py` (now 30/30). This is the
  second time the CLI shell, not the core, held the defect — audit the shell first.

- DEFECT (fixed, prior session, verified LIVE this session): the fracture-scout push died on
  a re-run because the day's branch already existed (`git push -u` → non-fast-forward). The
  workflow now creates the branch or updates it under an explicit
  `--force-with-lease="refs/heads/$BR:refs/remotes/origin/$BR"` after an explicit-refspec
  fetch. PROOF on real GitHub Actions: dispatch run #3 (new branch) success, dispatch run #4
  (re-run) success with log line `+ 06849aa...abb0890 (forced update)`; PR opened/updated.

Re-verified this session (through the real engines): `savf.py selftest` 2839 checks / 0 fail;
verdict total over 3^11 = exactly one PASS; `tools/savf_parity_gate.py` PASS (12 verdicts +
18 signs); the CLI fuzz harness in the scratch dir 21/21 clean; `savf.html` in chromium at
360×800 — 2839 checks in-browser, 0 console/page errors, no overflow, all 7 tabs functionally
correct and agreeing with the CLI. `savf.html` has zero external references (single 443 KB
file, offline). Local `tools/ci.sh` → CI: PASS (after `build/sync-delivery.py` +
`build/make-oneshot.py` are re-run to refresh the gitignored `delivery/` bundle and the
printed hashes).

- `assets/engine/android.jar` is NOT a main-branch defect: `tools/stage_engine_inputs.sh`
  (called by `build&install.sh`) stages it at build time and `build.sh` deliberately excludes
  it from the host's own assets. Only running a bare `build.sh` with no prior staging omits it.
  `master`'s "track it in git" commits are a superseded approach; master is 170 behind main.


## §40 STANDING AUTHORITY TO PUBLISH — NEVER ASK TO PUSH (binding, 2026-11-19)

Read this before every turn. It removes a recurring stall: an agent finishing real work, holding
it locally, and telling the Operator it is "ready to push — say the word."

**The Operator has already authorised publishing.** That decision is made and automated. It is
not a per-turn question and must not be re-litigated.

**Standing grant — no approval needed, ever:**
- `git commit` and `git push` to the working branch (`main`, or a feature branch you created).
- `tools/board_pulse.sh`, `tools/continuity.sh`, `tools/sync.sh`, `tools/converge.sh` — all push.
- Integrating `origin/main` when it has moved ahead, then re-running `tools/ci.sh` on the merged
  tree, then pushing. "Origin moved" is a merge instruction, not a reason to wait.

**The failure this forbids.** Holding finished work for a go-ahead already given stalls the
parallel tab, stales accumulated output, and makes the Operator repeat himself. `board_pulse`
fails CI precisely because the board is only pushed when its bytes are on the remote (§32
MUST #26). A generic tool default of "do not push unless asked" is not a house law here and does
not outrank the Operator's standing grant.

**Still requires explicit approval — the grant is narrow, these are not publishing:**
- `git push --force` / `--force-with-lease` to a shared branch; deleting a remote branch.
- `git reset --hard` on work not already on the remote; rewriting published history.
- Anything that would push secrets (signing keys, credentials) — a hard NEVER; `tools/continuity.sh`
  refuses it and so does every agent.
- Publishing outside this repo (stores, public releases, third-party services).

**Reporting rule.** Do not write "ready to push", "awaiting your approval", or "say the word"
when the grant covers it. Push, then report the SHA. If you catch yourself about to ask, re-read
this section and push instead.

Law text: DARKITH.md MUST #35.

## §41 STALL IS MEASURED AS TIME — NO OFF-SCHEDULE DWELL (binding, 2026-11-19)

§40 removed the social stall (an agent asking permission it already had). §41 removes the
mechanical one: work that sits unpushed or uncommitted while every gate stays green.

**The blind spot this closes.** `board_pulse --check` is a yes/no: *is the board on the remote?*
It cannot say *for how long was it not?* So an agent could hold finished work indefinitely and CI
would pass the whole time. A gate that never measures latency cannot defend a deadline.

**The gate.** `tools/stall_clock.py`, wired into `tools/ci.sh`. It measures dwell from git:

- `unpushed_dwell` = now − committer time of the oldest commit `origin` does not have.
- `dirty_dwell` = now − mtime of the oldest dirty path (a floor, not an estimate).

Over budget → **CI FAIL**, with the remedy printed in the failure itself.

**The budget is the Operator's.** `STALL_BUDGET.json` at the repo root. Never edit it to make a
gate pass, and never assume a default — a missing or malformed budget fails closed.

**Zero-collision.** The push path of `tools/board_pulse.sh` takes an exclusive `flock`, so two
tabs pulsing at once cannot race on `git add -A`, on the two commits, or on the push. The lock
blocks rather than skips: a skipped pulse is the stall this law forbids.

**What an agent does when it sees a dwell failure:** push (`tools/board_pulse.sh`) or commit.
Never wait, never explain, never ask. Dwell is the defect.

Law text: DARKITH.md MUST #36.

## CNS-DIRECTIVE (v1) — instantiated on every board and every peripheral at once

The Operator's standing demand, codified so it is a property of the apparatus and not of any
one agent's memory:

1. **The product is an installable, agnostic artifact.** Every completion report states, in
   plain sight, whether the deliverable is a runnable/installable thing on any account or
   host — and if it is not, that is the headline, not a footnote. No hunting.

2. **No defect may be reported as an emergent surprise.** A defect that was *possible* is a
   codification failure. Every fix lands as a class fix: a detector, a deterministic repair,
   and a prevention gate in CI. `tools/autophagy.py` is that registry. A repair with no
   prevention gate is refused at load.

3. **The tree must always be a newborn.** `tools/autophagy.py` detects every registered
   defect class, repairs it, re-runs the detector to prove the repair took, and loops to
   convergence. A tree that requires watching is a patient, not an apparatus.

4. **Only evolutionary progress is reported.** Against the omega endpoint: what class was
   ended, what gate now prevents its return, what the tree can do that it could not before.

5. **Reports lead with a verdict.** First line: DIRECTIVE COMPLETE or NOT COMPLETE, and
   what the installable artifact is. Evidence after.

### STANDING-AUTHORITY (NEVER #21) — the decision is already made

Execute, commit, push. Do not ask permission for work already ordered. The Operator does not
want a request to publish; they want the publish. A change that sits uncommitted waiting for
a yes is a stall, and a stall is the failure mode this law exists to forbid.

Scope: every board, every parallel agent, every session carrying this directive.
Budget: 0 seconds. There is no waiting window to spend.

### Browser engines do not share an error dialect

The webapp ships one engine but runs on three, and a capability guard that fires on one
browser can be silent on another. An exhausted JS stack is `RangeError` "Maximum call stack
size exceeded" on Chromium and Safari, but `InternalError` "too much recursion" on Firefox.
Matching only the Chromium wording left Firefox condemning valid deep source as `PARSE/high`.

Two rules follow. First, detect engine capability limits by both the error name and the
message, never by one engine's phrasing. Second, a capability limit is never a verdict on
the input: fall back to the token-only rules so a file is never reported cleaner (or dirtier)
than the same file one character shorter.

A browser engine that parses where another gives up is a capability gap, not a
disagreement. Gates over multiple engines must assert the shared findings and the absence
of a false high-severity accusation, not an exact rule list.

## A seal is only a seal if its evidence can leave the machine

The revitalization seal cited `S16_POST_SEAL.log` as evidence while `.gitignore` dropped
`*.log`. The gate passed in the working tree and failed in every fresh clone, because the
cited file was never committed. Local green is not evidence of anything until it survives
`git clone`. When adding a seal, verify it from a clean checkout, not from the tree that
produced it. `proof/revitalization/*/S*.log` is now re-included for exactly this reason,
and I8 rejects any citation git ignores so the next unlucky extension cannot reproduce it.

## Check the premise before running the script

A briefing listed 19 Kotlin files whose opening `/*` had been stripped, with exact line
numbers. At those line numbers 18 of 19 already read `/**` or `/*`, and the nineteenth
(`HomekeeperBridge.kt:282`) is a `catch` block, not a comment. All 58 `.kt` files scan
balanced, confirmed twice with independent parsers. A repair script run against that
description would have inserted a second `/*` into 18 healthy files and broken them.

Read the target bytes first (SPI-2). A bug report is a hypothesis about the tree, not a
description of it, and line numbers go stale as the tree moves under them.

Two scanner bugs worth remembering, both of which produced false "unclosed comment"
findings that looked like real defects: ignoring backslash escapes in `"..."` (so `"\""`
desynchronises string state), and ignoring `"""` raw strings. A parser that disagrees with
the project gate should be suspected before the project is.
