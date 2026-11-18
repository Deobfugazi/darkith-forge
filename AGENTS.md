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
  loopholes. The registry (tools/delivery_gate.sh) names all 16: L-01 manifest-version,
  L-02 apk-version, L-03 self-report, L-04 artifact-built, L-05 artifact-signed,
  L-06 artifact-aligned, L-07 fork-singularity (§19), L-08 bridge-contract, L-09 asset-parity,
  L-10 currency, L-11 registry-nonempty, L-12 one-surface, L-13 no-doc-dup, L-14 family-whole,
  L-15 signer-identity, L-16 arsc-stored, L-17 native-tools. `--source-only` records the
  APK-dependent checks as named SKIPs on a box with no APK, never a silent pass.

## Version truth (never guess again)
- Truth is AndroidManifest.xml: versionCode=3, versionName=1.2.0-omega. Bridge VERSION=hk-bridge-52.
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
  at once (`tree`=50 .kt, `tree.orig`=50, `tree_omega`=55) with 11 common files divergent.
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
    registry 11 -> 16 loopholes.
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
    is generated by `tools/pack_delivery.py`, whose inputs (`tree_omega/`, `dist/`,
    `delivery/c7_patched_sources.zip`) are not in the repo; the legacy `make-bundle-zip.py`
    path is unreconstructable without them. That is the next surface, not this one.

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
- GIT HYGIENE (cost two CI cycles): NEVER `git add -A` here. `tree_omega/`, `dist/`,
  `.agent_tmp/` and `app-signed.apk` are deliberately untracked; `add -A` commits them and
  then kb_index ("misfiled (no register)"), fork-singularity ("divergent copies") and the
  convergence tree hash all FAIL. Stage surgically: `git add -u` for tracked edits, plus
  explicit paths for new files.
- DEPLOY ORDER for a release that the live app can actually see: `inject_updater.py` ->
  `build-forge.py` -> `kb_index.py --write` -> one-shot/sync/bundle/repo/delivery to fixed
  point -> commit -> PUSH (board_pulse needs HEAD==origin) -> CI -> GitHub Release with
  `darkith-one-shot.sh` + `VERSION.json` as assets. The runtime host (port 12000) is a
  moving sandbox: point the PRIMARY mirror at GitHub once the repo is public.
