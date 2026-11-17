# AGENTS.md — Darkith

Repository-specific knowledge for future sessions. Read before acting.

## 0. CONTINUITY (read first — the VM is ephemeral)
- **Canonical private host:** `Deobfugazi/darkith-forge` (branch `main`). Nothing
  survives a recycled VM except what is pushed there.
- **Restore at session start:** `bash tools/restore.sh`
- **Save before session end:** `bash tools/continuity.sh "what changed"`
- See `RESUME.md` for the full protocol. Secrets (the APK signing key) never enter git.

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

## Project
- Android app **Darkith** + an offline web studio. Built on a phone in Termux via the
  **NT IX 7-step raw chain** (`aapt2 -> kotlinc -> d8 -> zip -> zipalign -> apksigner`).
- **Gradle is physically forbidden** (SPI-1: deadlocks the phone's RAM). Never run or suggest it.
- Kotlin sources: `tree/app/src/main/java/com/darkith/transliaison/`.
  `tree.orig/` is the pristine pre-fix snapshot (kept for diffing; not built).

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
The working `tree/` scans **0 defects**. Verify with `python3 tools/comment_audit.py`.

## Web studio (offline, no build step)
- `savf.html` — SAVF universal audit engine (`window.SAVF`).
- `darkterm.js` — **DarkTerm**, a real POSIX-style shell in one file. Exposes
  `window.DarkTerm` (browser) / `module.exports` (node). `registerCommand(name, fn)`
  adds a builtin. `createSession()` returns a facade with `.exec(line)`.
- `darktools.js` — handcoded dev toolkits layered on DarkTerm: `task` (task manager),
  `sync` (learnable synchronicity engine + deficit ledger + omega ladder), `tk`
  (toolkit host), `store` (persistence). Installed via `DarkTools.install(session, opts)`.
  `opts.fresh: true` reseeds tasks AND resets the sync engine.
- `darkith-inscriber.html` — the studio app. 4 inline `<script>` blocks:
  0 SAVF, 1 DarkTerm engine, 2 DarkTools, 3 studio layer. **The engine block must stay
  byte-identical to `darkterm.js` on disk**; re-embed after editing either.

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
- `node tools/test_darktools.js` — 46/46 (tasks, explicit+passive learning, ledger, omega,
  tk host, persistence). `NODE_PATH=/tmp/node_modules node tools/test_inscriber.js` — 14/14
  (jsdom drives real Enter keydowns). `node /tmp/difftest3.js` — shell parity vs bash
  (known gaps: `sed -n p`, `{a..e}`, `awk length()`, `xargs -I{}`, awk ternary).
- jsdom functional test needs `url:` set (localStorage rejects opaque origins).
- Serve: `python3 -m http.server 12000` in the repo root.

## Proof logs on disk
`proof_comment_audit.log`, `proof_darkterm.log`, `proof_toolkits.log`.

## OMEGA reconciliation + compile proof (this session)
- **Canonical source tree**: `tree_omega/` (build.sh layout) and its archive `darkith_omega_source.zip`.
  Reconciled from all 6 forks; delivery is the superset. See `RECONCILIATION.md`.
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
- `.github/workflows/auto-merge.yml` is the thin GitHub adapter: tests (tools/ci.sh) then
  merges a dependency PR (Dependabot and darkbot authors). The bot's own bumps are tested
  and committed directly, because a PR opened with GITHUB_TOKEN never triggers a second
  workflow run (approval-required state) — the recursion trap. No PAT, no pull_request_target.

## §19 ANTI-DIVERGENCE LAWS (binding — see singularity_progressive_continuum.md §19)
NEVER #11 One Tree: never keep two divergent live copies of a file. Reconcile into one; the
  loser is deleted or frozen read-only with a dated supersession note (RECONCILIATION.md).
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
  tree_omega/app/src/main/java/com/darkith/transliaison \
  /path/to/android-all.jar  /path/to/apksig.jar:/path/to/rclasses
# PASS: all §19 laws held.  (SPI-12/13/14 + MUST-11 compile)
```

## §20 DELIVERY GATE — the loophole registry (binding)
NEVER #14: never say "delivered" without running tools/delivery_gate.sh and listing every
  loophole's status. "Delivered" is a gate RESULT, not an assertion.
MUST #14: the gate IS the delivery; non-zero exit forbids the word "delivered".
SPI-16: a delivery that did not run the gate is not a delivery.
W-041: the recurring defect was the ABSENCE of a delivery gate — shipping with unenumerated
  loopholes. The registry (tools/delivery_gate.sh) names all 11: L-01 manifest-version,
  L-02 apk-version, L-03 self-report, L-04 artifact-built, L-05 artifact-signed,
  L-06 artifact-aligned, L-07 fork-singularity (§19), L-08 bridge-contract, L-09 asset-parity,
  L-10 currency, L-11 registry-nonempty.

## Version truth (never guess again)
- Truth is AndroidManifest.xml: versionCode=2, versionName=1.1.0-omega. Bridge VERSION=hk-bridge-50.
- The app self-reports: `darkith.apkVersion()` -> "bridge=... pkg=... (code)".
- On device: `pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'`.
- From the APK: `aapt dump badging <apk> | grep ^package`.
- VERSION.md records the current build + the delta vs what is installed.

## Build + deliver (this environment)
```
# build (real APK; android-all.jar works as the aapt2 -I jar too)
cd tree_omega && ANDROID_JAR=/tmp/android-all.jar R8_JAR=/tmp/r8.jar \
  KOTLINC=/tmp/ktc/kotlinc/bin/kotlinc KOTLINC_XMX=4g bash build.sh . Darkith com.darkith.transliaison
# gate (must print DELIVERED)
KOTLINC=/tmp/ktc/kotlinc/bin/kotlinc tools/delivery_gate.sh . tree_omega/app-signed.apk \
  /tmp/android-all.jar /tmp/apksig.jar
```
Toolchain got: aapt2/zipalign/apksigner via `apt install aapt android-sdk-build-tools`;
d8 via R8 jar (`dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.42/r8-8.2.42.jar`);
kotlinc 1.9.24 (JetBrains zip); apksig in tree_omega/libs/apksig.jar.

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
  Hub = `dist/index.html`; regenerate with the snippet in DEFICIT_LEDGER/tools when artifacts change.
- The hub shows version + gate status + sizes + hashes so the Operator verifies before installing.

## §22 DEDUPLICATION + IDEMPOTENCY (binding)
- ONE DOCUMENT (NEVER #16): DARKITH.md is the single canonical record (version + reconciliation +
  deficits + laws). Never fork it. Served/zipped copies are GENERATED by tools/pack_delivery.py.
- IDEMPOTENT (MUST #18): pack_delivery.py has no wall-clock, no self-hash, deterministic zip
  timestamps. Re-run -> byte-identical. Prove idempotency by running twice and diffing.
- Consolidation (SPI-18): tools/consolidate_docs.sh merges overlapping docs; refuses to delete
  unless the canonical doc already holds every law. Idempotent (2nd run is a no-op).

## §23 NO STALLED DEFICIENCY (binding)
- NEVER #17: a named deficiency may not survive two deliveries. Close it or descope it, in writing.
- MUST #19: implement the FULL contract (a whole method family), or descope with the reason named.
  A partial surface must itself become a named entry.
- MUST #20: proof lives in the ARTIFACT, not the source — the symbol is in the compiled dex, the
  gate is green, the hash changed. "It compiles" is not "it shipped".
- SPI-19: a method family (shell*, file*, apk*) is whole or absent.

## §24 TREE INTEGRITY + RECONCILIATION (binding)
- ONE TREE (NEVER #18): exactly one authoritative source tree may exist. On this box three
  existed at once (`tree`=50 .kt, `tree.orig`=50, `tree_omega`=55) with 11 common files
  divergent. That is the fragmentation engine, measured — not asserted. The authoritative
  tree is the NEWEST whose content matches the built APK; here that is `tree_omega`.
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
