# DARKITH — README

> The one file that assumes you know **nothing** and leaves you asking **nothing**.
> If you finish this file and still have a question, that is a defect in this file,
> not a defect in you. The question belongs in the "Questions this file pre-answers"
> section at the bottom, and that section is a gate: it must stay empty of live
> questions.

This README is written in a reusable shape called **the Tri-Tongue README** (also
called the *invariant README format*). The shape is defined in full in
[§12](#12-the-invariant-format-the-reusable-spec). Read [§0](#0-read-this-first)
first; it teaches you how to read the rest.

---

## 0. Read this first

### 0.1 Who this file is for

This file is for three readers **at the same time**:

1. **The complete beginner.** You have never built an Android app, never used a
   terminal, and do not know what "compile" means. You are not expected to know
   anything before you start. Nothing in this file is your fault.
2. **The working engineer.** You know Android, Kotlin, and the command line. You
   want the exact command, the exact file, the exact version — no hand-holding.
3. **The machine.** A program or an AI agent that will read this file to learn how
   to build, verify, and change this project without breaking it.

A normal README serves reader 2 and ignores readers 1 and 3. That is why beginners
get stuck and ask five more questions. This file serves all three in the same
paragraph, using three "tongues" (see [§0.3](#03-the-three-tongues-plain-precise-machine)).

### 0.2 The six laws of this format

Every section of this README obeys six rules. They exist so you never have to ask a
follow-up question.

| Law | Name | What it means in practice |
|---|---|---|
| 1 | **No bare term** | No piece of jargon is ever used before it is defined, in the same file. The first time a term appears, it is explained in parentheses and listed in the [glossary](#4-glossary). |
| 2 | **Three tongues** | Every load-bearing idea is stated three ways: **Plain** (for a beginner), **Precise** (for an engineer), **Machine** (the literal symbol, file, or command a computer reads). |
| 3 | **POV correction** | Where a beginner's natural assumption is wrong, the file names the wrong assumption and corrects it out loud, before you build on it. |
| 4 | **Terminal answer** | No answer ends by pointing you somewhere else. Every answer ends with you either able to act, or knowing the single exact next action. |
| 5 | **Loop breaker** | The file ends with an enumerated list of the questions you would otherwise ask, each already answered in the body. |
| 6 | **Declared audience** | The file states who it is for and what (ideally: nothing) you must already know. |

### 0.3 The three tongues (Plain, Precise, Machine)

Every concept block below looks like this:

> **Plain** — explained as if to a smart person who has never seen this field.
> **Precise** — the correct technical statement, using the real terms.
> **Machine** — the literal artifact: a filename, an identifier, or a command.

You may read only the **Plain** lines and understand the whole project. You may read
only the **Machine** lines and act. Reading all three is how you go from "I followed
the steps" to "I understand why the steps are these steps."

### 0.4 The words you must know before line one

Only four. Each is expanded here; all four reappear in the [glossary](#4-glossary).

- **Repo** (short for *repository*): a folder that remembers every change ever made
  to it. This project is one repo.
- **Terminal**: a text window where you type commands instead of clicking. On
  Android you get one by installing the app **Termux** (see [§3.2](#32-termux)).
- **Build**: the process of turning human-written source code into an app file a
  phone can install. This project's build is done by a script named `build.sh`.
- **App** (short for *application*): the installable file. On Android the file ends
  in `.apk`, which stands for **Android Package Kit**.

That is the entire prerequisite. If those four sentences made sense, you can read
this whole file.

### 0.5 Legend for the code blocks

- Lines beginning with `#` are comments: they explain, they are not run.
- `$` at the start of a line means "type the rest into a terminal."
- Anything in `backticks` is a literal name: a file, a command, or an identifier.
  The `backticks` are not typed.

---

## 1. What is Darkith? (the 60-second answer)

> **Plain.** Darkith is an Android app that you build **on the phone itself** — no
> computer, no internet needed. It is also a small suite of offline web pages (a
> "studio") that runs in a browser. The whole point is *sovereignty*: you own the
> build, the tools, and the data, and they work on a cheap phone in a room with no
> signal.
>
> **Precise.** Darkith is an Android application (`com.darkith.transliaison`) plus
> an offline web studio. It is compiled from Kotlin source with a **Gradle-free**
> seven-step toolchain (the "raw chain") that runs inside Termux on an arm64
> Android device, targeting `minSdk 24` / `targetSdk 34`. It ships an in-app forge
> (a build engine) and a local-assistant design, and it is governed by an
> executable rule set ("gates") that runs in one command: `bash tools/ci.sh`.
>
> **Machine.** Package `com.darkith.transliaison`; version `1.1.0-omega`
> (`versionCode 2`); source in `app/src/main/java/com/darkith/transliaison/`;
> entry points `MainActivity`, `HomekeeperActivity`; build with
> `bash build&install.sh`; verify with `bash tools/ci.sh`.

### 1.1 POV correction (read this before anything else)

> **You probably think:** "Building an app needs Android Studio on a laptop."
>
> **Correct:** Normally, yes. This project deliberately does not do that. It uses
> the same underlying tools Android Studio uses, but calls them directly, one after
> another, from a script. That is harder to set up and easier to understand. The
> reason is explained in [§3.4](#34-gradle-and-why-it-is-forbidden).

> **You probably think:** "No internet means no build tools."
>
> **Correct:** The tools are downloaded **once**, then cached in a folder named
> `.tools/` (see [§3.6](#36-androidjar-the-reference-framework)). After that the
> build runs offline. The one-time download is automated by
> `bash tools/fetch_toolchain.sh`.

---

## 2. The chronicle (the story of this project, in order)

This section is a **chronicle** — a story told in order. It is the literary device
this README is built on: the same set of facts, narrated as a journey from nothing
to a working app, so that each idea arrives only after the idea it depends on.

**Chapter 1 — A phone, not a computer.** The project began with a constraint, not a
feature: it must be built entirely on a 4 GB Android phone using Termux, with no PC.
Every design decision in this repo is downstream of that constraint.

**Chapter 2 — The forbidden tool.** The obvious tool for building Android apps is
**Gradle**. On this phone, Gradle runs out of memory and the phone freezes. So
Gradle is *banned* — not discouraged, banned — and this is written into the rules as
**SPI-1** (see [§3.9](#39-spi-never-must-the-rule-vocabulary)). This ban is the
reason the rest of the project looks unusual.

**Chapter 3 — The raw chain.** With Gradle gone, the build was re-expressed as seven
explicit steps run in order: `aapt2 → kotlinc → d8 → zip → zipalign → apksigner`
(explained in [§3.5](#35-the-raw-chain-aapt2-kotlinc-d8-zip-zipalign-apksigner)).
Each step is a small, single-purpose program. Together they turn Kotlin source into
a signed `.apk`.

**Chapter 4 — The fork disease.** Early on, the source code existed in **six**
divergent copies ("forks"). Files drifted; some referenced code that existed in no
copy at all. The compiler could not build any single copy. The cure was a law:
**one authoritative tree** (NEVER #11), enforced by a gate.

**Chapter 5 — The compiler as the only judge.** A script that "checked" the code
with text search reported success while the real compiler reported an error. The
lesson became a law: only the compiler decides whether code is valid (**W-023**).

**Chapter 6 — The gate.** Every failure the project ever hit was converted into an
automatic check — a **gate**. One command, `bash tools/ci.sh`, runs them all. If any
gate fails, the build is not "done," no matter how finished it looks. A rule that is
not a gate is not a rule; it is a note (SPI-15).

**Chapter 7 — The corpus.** Alongside the code, the project keeps a written body of
reasoning called the **noveltreatise corpus** (`docs/nt/`). Its claims are checked by
a gate (`tools/nt_gate.py`) that resolves every contradiction to a status backed by a
re-runnable command. See [§3.12](#312-the-nt-corpus-and-savf).

**Chapter 8 — The studio.** Around the app sits an offline web studio: pages that run
in any browser from `file://`, with no server and no internet. These are the
`*.html` files at the repo root (see [§5](#5-the-repository-map)).

**Chapter 9 — This file.** This README is the entry point that ties the chapters
together. It exists because the project's own rules demand that a newcomer not have
to ask.

---

## 3. The concepts, each in three tongues

Read the concepts in order; each one uses only concepts already defined above it.

### 3.1 Android

> **Plain.** Android is the operating system on most phones that are not iPhones.
> It runs "apps." The apps you install from the Play Store are Android apps.
> **Precise.** Android is a Linux-based mobile OS; its application framework is
> exposed to app code through the Java/Kotlin class library shipped in `android.jar`.
> **Machine.** The reference API is pinned here to `targetSdk 34` (Android 14) with
> `minSdk 24` (Android 7.0).

### 3.2 Termux

> **Plain.** Termux is a free Android app that gives you a **terminal** (a text
> command window) on your phone, plus a small Linux toolbox. It is how you run the
> build without a computer.
> **Precise.** Termux is a terminal emulator plus a package-managed Linux userland
> (`$PREFIX/bin`) that runs unrooted; its packages target a legacy SDK, which is why
> binaries it installs are executable where app-private storage is not.
> **Machine.** Install Termux, then run the build with `bash build&install.sh` from
> the repo root. The project's durable home is `/sdcard/Darkith/` (SPI-8).

### 3.3 APK (Android Package Kit)

> **Plain.** An `.apk` file is the installable form of an Android app — the thing you
> tap to install.
> **Precise.** An APK is a ZIP archive with a fixed internal layout: a compiled
> manifest, a resource table, `classes.dex` (compiled code), native libraries, and
> assets, plus a cryptographic signature.
> **Machine.** This project's build writes `app-signed.apk` at the repo root. Its
> version is declared in `app/src/main/AndroidManifest.xml`.

### 3.4 Gradle, and why it is forbidden

> **Plain.** Gradle is the tool most Android projects use to build. It is powerful
> and it uses a lot of memory. On this 4 GB phone it runs the phone out of memory,
> and the phone freezes. So this project does not use it, at all.
> **Precise.** Gradle's build daemon allocates a JVM heap that exceeds physical RAM
> on the target device; the kernel swaps to compressed RAM (ZRAM), the CPU saturates
> on compression, and the build hangs at zero progress (failure **W-020**).
> **Machine.** There is no `build.gradle` in this repo and there never will be. The
> ban is **SPI-1**. A gate enforces the absence of Gradle invocation in `build.sh`.

### 3.5 The raw chain: aapt2, kotlinc, d8, zip, zipalign, apksigner

This is the heart of the project. Seven small programs, run in order. Each name is
expanded, then explained.

> **Plain.** Imagine building a house. First you lay out the furniture and paint
> (resources), then you pour the concrete walls (compile the code), then you flatten
> the floor so nothing wobbles (align), then you sign the deed (sign). The raw chain
> is that, for an app.
> **Precise.** The seven steps transform Kotlin source and resources into a signed,
> aligned APK, in this fixed order, because each step consumes the previous step's
> output.
> **Machine.** `bash build.sh . Darkith com.darkith.transliaison` runs the chain and
> prints `1/7 … 7/7`.

| Step | Program | Plain meaning | Machine action |
|---|---|---|---|
| 1 | **aapt2 compile** | Turn each image/layout into a packed form. | compiles `res/` into `.flat` files |
| 2 | **aapt2 link** | Assemble resources + manifest into a base package, and generate the `R` class. | produces `base.apk` and `R.java` |
| 3 | **kotlinc** | Translate the human-written Kotlin into machine code for the Java virtual machine. | compiles `.kt` to `.class` |
| 4 | **d8** | Convert those class files into the single format Android runs. | produces `classes.dex` |
| 5 | **zip / package** | Put code, resources, and assets into one archive. | writes `base.apk` |
| 6 | **zipalign** | Pad the archive so every part starts on a tidy boundary; Android loads it faster and it is required before signing. | writes `aligned.apk` |
| 7 | **apksigner** | Attach a cryptographic signature so the phone trusts the app. | writes `app-signed.apk` |

**Why this exact order?** Alignment (step 6) must happen **before** signing (step 7),
because signing covers the bytes, and aligning changes the bytes. Signing first would
invalidate the alignment. This ordering is a rule (**NT IX §9**), not a preference.

> **POV correction.** You might think "more tools = more fragile." Here the opposite
> is true: each tool does one thing and can be checked in isolation. Gradle hides all
> seven behind one command, which is convenient until it fails, and then you cannot
> see which step broke. The raw chain shows you `1/7 … 7/7` so you always know where
> you are.

### 3.6 android.jar (the reference framework)

> **Plain.** When you write an app, your code calls Android's built-in features
> (buttons, screens, storage). Those features are described in one big reference file
> called `android.jar`. The build tools read it to know what exists.
> **Precise.** `android.jar` is the compiled API surface of the Android framework
> against which app code is compiled. This project stands in a full framework jar
> (the Robolectric `android-all-14-robolectric-10818077.jar`, ~137 MB) for it.
> **Machine.** The toolchain provisions it into `.tools/` via
> `bash tools/fetch_toolchain.sh`; the build reads it from the `ANDROID_JAR`
> environment variable.

> **POV correction (important).** `android.jar` contains **only** the base Android
> framework. It does **not** contain **AndroidX** or **Compose** (defined next). Code
> that imports those will fail to compile against `android.jar` alone. This exact
> mistake has a name here — **W-024, classpath hallucination** — and a gate that
> catches it.

### 3.7 Kotlin

> **Plain.** Kotlin is the programming language this app is written in. It is a
> modern language that runs on Android's engine. The files end in `.kt`.
> **Precise.** Kotlin is a statically typed JVM language; Android's toolchain
> compiles it with `kotlinc` to JVM bytecode, then `d8` to Dalvik bytecode.
> **Machine.** 55 `.kt` files live in `app/src/main/java/com/darkith/transliaison/`.

### 3.8 AndroidX (and Compose)

> **Plain.** AndroidX is a large, separate library of extra Android features that is
> **not** part of the phone's built-in framework. Compose is a modern way to draw
> screens inside AndroidX. They are popular — and this project cannot use them,
> because the raw chain does not load them by default.
> **Precise.** AndroidX and Compose are support libraries distributed as AAR/JAR
> artifacts outside the platform `android.jar`. Using them requires putting those
> JARs on the compile classpath; the Gradle-free chain does not fetch them.
> **Machine.** The repo law is **zero `import androidx`** in the Kotlin tree
> (SPI-13). A gate enforces it: `tools/fork_integrity_gate.sh` fails on any match.

> **POV correction.** You may have read that "AndroidX is the standard." It is, for
> Gradle projects. Here the standard is the opposite, by necessity. Where AndroidX
> would be used, this project uses raw `android.*` equivalents (for example
> `android.widget.Button` instead of `androidx.compose.material3.Button`).

### 3.9 SPI, NEVER, MUST (the rule vocabulary)

The project's rules have three prefixes. Each is an acronym for a rule *family*.

> **Plain.** Think of traffic rules. **NEVER** = a red line you must not cross.
> **MUST** = a thing you must do. **SPI** = the deeper principle underneath many of
> the other two.
> **Precise.** NEVER and MUST are concrete, numbered rules; SPI ("Sovereign Sandbox
> Protocol"/"invariant") entries are the physical laws distilled from real failures.
> **Machine.** The canonical list is in `DARKITH.md` (Part 4). Every rule must name
> an executable gate, or carry the marker `[NOTE: not yet gated]`; `tools/law_gate.py`
> enforces this in CI (SPI-15).

Key examples you will see cited throughout:

- **SPI-1** — Gradle is forbidden on this device; it deadlocks. ([§3.4](#34-gradle-and-why-it-is-forbidden))
- **SPI-2** — read the exact bytes before writing; do not guess.
- **SPI-13** — every referenced symbol must resolve inside the tree; zero `import androidx`.
- **SPI-15** — a rule that is not an executable gate is a note, not a rule.
- **NEVER #11** — never keep two divergent live copies of one file.
- **MUST #11** — compile is the proof; a tree is "current" only after it compiles.

### 3.10 The gates

> **Plain.** A gate is an automatic check that answers "is this still true?" Gates
> run together with one command. If a gate fails, the project is not finished.
> **Precise.** Each gate is a small program in `tools/` (a `.py` or `.sh` file) that
> inspects the tree or the artifact and exits non-zero on a violation. They are
> orchestrated, provider-neutrally, by `tools/ci.sh`.
> **Machine.** `bash tools/ci.sh` runs them all and exits `0` only if every one
> passes. There are 17 gate programs; see [§8](#8-the-gates-what-runs-and-why).

### 3.11 SAVF

> **Plain.** SAVF is the project's own auditing "formulary" — a set of checks that
> decide whether a body of code tells the truth about itself. It runs offline.
> **Precise.** SAVF (**S**igned **A**xis **V**erification **F**ormulary, version
> "SAVF-1") is a zero-dependency Python utility (`savf.py`) with an axis core and a
> set of gates (`scan`, `reach`, `mutate`, `freeze`, `manifest`, `ledger`, `verdict`).
> It grades each claim by kind and can re-run recorded evidence commands.
> **Machine.** `python3 savf.py ledger proof/nt_claims.json --run`. The web build is
> `savf.html`.

### 3.12 The NT corpus, and SAVF

> **Plain.** The project also keeps a written body of reasoning called the
> "noveltreatise" corpus — long documents that argue *why* the project is built the
> way it is. Every claim in them is graded, and any contradiction must be resolved.
> **Precise.** The NT corpus (`docs/nt/`) is the project's *law layer*; `DARKITH.md`
> is the *state layer* and cites the corpus rather than duplicating it. Each claim is
> graded by kind — `D` declared, `N` noted, `R` derived (from other claims), `W`
> witness (re-runs a recorded command and checks its output), `C` contradiction, `A`
> analysis, `U` unknown. `tools/nt_gate.py` fails CI if a claim is cited but not
> carried, if a witness fails, or if a contradiction is unresolved.
> **Machine.** Corpus files `docs/nt/NT-*.txt` and `docs/nt/NT-I-IV-protocol.md`;
> ledger `proof/nt_claims.json`; resolutions `proof/nt_reconciliation.json`; report
> `proof/NT_RECONCILIATION.md`. Index: `docs/nt/NT-INDEX.md`.

The word **noveltreatise** is a coinage of the project's author. In this README it
means, precisely: *a long-form document that states claims, each graded and gated.*

### 3.13 Omega (Ω), the board, and the deficit ledger

> **Plain.** "Omega" is the project's word for *done in the largest sense*: not just
> working, but sovereign, offline, and self-checking. The "board" is the project's
> to-do list, kept in a real file so it survives. A "deficit" is any named gap; the
> project refuses to silently ignore one.
> **Precise.** The board is `TASKS.md` (durable, gated by `tools/board_gate.py`). The
> deficit ledger is `DEFICITS.json`; `tools/stall_gate.py` fails CI if a named deficit
> stays open across two deliveries. The progress indicator is the retention law
> `W_in − E = S ≠ 0` computed by `tools/omega_deficit.py`.
> **Machine.** `python3 tools/board_gate.py`, `python3 tools/stall_gate.py`,
> `python3 tools/omega_deficit.py`.

### 3.14 Homekeeper, the forge, and the studio

> **Plain.** "Homekeeper" is the app's dashboard screen. "The forge" is a build engine
> that lets the app build things from inside itself. "The studio" is the set of
> offline web pages that accompany the app.
> **Precise.** `HomekeeperActivity` hosts a `WebView` dashboard bridged to Kotlin via
> `HomekeeperBridge` (`VERSION = hk-bridge-52`). The in-app forge path is
> `BuildEngine` / `ChimeraBuilder`. The studio pages run from `file://` with no build
> step.
> **Machine.** Studio pages at the repo root: `darkith home forge.html`,
> `darkith code studio.html`, `savf.html`, `omega.html`; the app asset copy
> `app/src/main/assets/homekeeper.html`.

---

## 4. Glossary

Every abbreviation and specialist term used above, alphabetized. Nothing here is
used before it appears in the body; this list is the single place to look them up.

| Term | Expansion | One-line meaning |
|---|---|---|
| **AAR** | Android ARchive | A packaged Android library (like a JAR, with resources). Not used here. |
| **ADB** | Android Debug Bridge | A tool to talk to a phone from a computer. Not required here. |
| **AI** | Artificial Intelligence | A program that performs tasks that normally need a human. |
| **AndroidX** | (Android eXtensions) | A support library outside the platform framework. Banned in this tree. |
| **API** | Application Programming Interface | The set of features a program may call. |
| **APK** | Android Package Kit | The installable Android app file. |
| **aapt2** | Android Asset Packaging Tool 2 | Compiles and links resources; steps 1–2 of the chain. |
| **arm64-v8a** | ARM 64-bit, v8-A | The CPU architecture of the target phone. |
| **CI** | Continuous Integration | Automated checks run on every change. Here: `tools/ci.sh`. |
| **Compose** | Jetpack Compose | AndroidX's UI toolkit. Banned here (needs AndroidX). |
| **CPU** | Central Processing Unit | The chip that executes the program. |
| **d8** | D8 dexer | Converts JVM `.class` files to Android `.dex`; step 4. |
| **dex** | Dalvik EXecutable | Android's compiled-code format. |
| **FAQ** | Frequently Asked Questions | A list of common questions with answers. |
| **GB / MB** | GigaByte / MegaByte | Units of data size (~1000 and ~1 million kilobytes). |
| **GGUF** | GPT-Generated Unified Format | A file format for local AI models. Design-stage here. |
| **Gradle** | (build tool) | The conventional Android build system. Banned (SPI-1). |
| **JAR** | Java ARchive | A packaged bundle of compiled Java/Kotlin code. |
| **JDK** | Java Development Kit | The Java toolset that `kotlinc` and `d8` need. |
| **JVM** | Java Virtual Machine | The runtime Kotlin compiles to first. |
| **kotlinc** | Kotlin compiler | Translates Kotlin to JVM bytecode; step 3. |
| **minSdk / targetSdk** | minimum / target SDK | Oldest supported Android (24) / the API compiled against (34). |
| **NT** | Noveltreatise | A long-form reasoning document; see [§3.12](#312-the-nt-corpus-and-savf). |
| **OS** | Operating System | The base software that runs apps (here: Android). |
| **Ω (Omega)** | — | The project's term for the fully-sovereign goal state. |
| **PC** | Personal Computer | A desktop or laptop computer (this project avoids needing one). |
| **POV** | Point Of View | The reader's assumed frame of reference. |
| **RAM** | Random Access Memory | Working memory; limited on a phone. |
| **SAVF** | Signed Axis Verification Formulary | The offline auditing engine; see [§3.11](#311-savf). |
| **SDK** | Software Development Kit | A versioned set of Android APIs (see `minSdk`/`targetSdk`). |
| **SPI** | Sovereign Sandbox Protocol | The rule family distilled from real failures. |
| **Termux** | — | The Android app that provides a terminal. |
| **WebView** | — | An Android component that renders web pages inside an app. |
| **ZIP** | (archive format) | A single file that packs many files; an APK is a ZIP. |
| **ZRAM** | (compressed RAM) | Compressed memory swap; the mechanism behind the Gradle freeze. |
| **zipalign** | — | Aligns the APK before signing; step 6. |
| **apksigner** | — | Signs the APK; step 7. |

---

## 5. The repository map

Every top-level item, and what it is. (A *top-level item* is a file or folder you see
when you open the repo root.)

| Item | What it is |
|---|---|
| `app/` | The Android app: Kotlin source, resources, assets, manifest. |
| `app/src/main/java/com/darkith/transliaison/` | The one authoritative Kotlin tree (55 `.kt` files). |
| `app/src/main/AndroidManifest.xml` | Declares the app's identity, version, permissions, screens. |
| `build.sh` | The seven-step raw chain, in one script. |
| `build&install.sh` | The one-shot entry point: provision, build, install. |
| `savf.py` | The SAVF auditing engine (Python). |
| `zipalign.py` | A pure-Python fallback for step 6. |
| `tools/` | The gates and helper scripts (see [§8](#8-the-gates-what-runs-and-why)). |
| `docs/` | The knowledge corpus: `docs/nt/` (NT corpus), `docs/INDEX.md`, architecture docs. |
| `proof/` | Machine-generated evidence: ledgers, proofs, reconciliation reports. |
| `build/` | Build tooling and generators (`build/verify.py`, `build/gen_synchrony.py`, …). |
| `libs/` | Jars placed on the compile classpath (for example `apksig.jar`). |
| `delivery/` | Regenerable delivery output (git-ignored; rebuilt on demand). |
| `DARKITH.md` | The single canonical record: version, reconciliation, deficits, laws. |
| `AGENTS.md` | Repository knowledge for an AI agent or a returning human. |
| `RESUME.md` | The recovery protocol: how to restore a lost session. |
| `TASKS.md` | The durable board (the to-do list). |
| `DEFICITS.json` | The deficit ledger (named gaps and their status). |
| `docs/nt/NT-INDEX.md` | The index of the NT corpus and its gate map. |
| `darkith home forge.html` | The main offline web studio. |
| `darkith code studio.html` | The offline code-audit studio. |
| `savf.html` | The browser build of the SAVF engine. |
| `omega.html` | The browser build of the Omega terminal/assistant design. |
| `darkith-inscriber.html` | The studio app; a byte-identical mirror of the shipped asset. |

---

## 6. "What do you want to do?"

Find your goal; run exactly the command shown. Each command is complete.

| I want to… | Do this | What you'll see |
|---|---|---|
| Build and install the app on this phone | `bash build&install.sh` | `1/7 … 7/7`, then the installer prompt |
| Build only, no install | `bash build&install.sh --build` | `app-signed.apk` at the repo root |
| Check that everything still works | `bash tools/ci.sh` | a list of checks, ending `CI: PASS` |
| Download the build tools once (offline after) | `bash tools/fetch_toolchain.sh` | tools cached in `.tools/` |
| See the app's version | open the app dashboard | the engine version string |
| Read the rules | open `DARKITH.md` | the canonical record |
| Read the reasoning corpus | open `docs/nt/NT-INDEX.md` | the corpus index |
| Recover a lost session | `bash tools/restore.sh` | the workspace fast-forwarded |
| Save my work | `bash tools/continuity.sh "what I did"` | committed and pushed |

---

## 7. Build and install (exact, step by step)

> **Plain.** Install Termux, put this repo on the phone, run one command, tap
> "Install."
> **Precise.** `build&install.sh` provisions the toolchain into `.tools/`, stages the
> forge's engine inputs, runs the seven-step chain, then hands the APK to the
> package installer.
> **Machine.**

```bash
# 1. In Termux, from the repo root:
bash build&install.sh

# 2. The script prints:
#      toolchain: provisioning (cached under .tools/)
#      1/7 aapt2 compile  ok
#      2/7 aapt2 link     ok -> base.apk
#      3/7 kotlinc        ok -> classes/
#      4/7 d8             ok -> classes.dex
#      5/7 package        ok -> base.apk
#      6/7 zipalign       ok -> aligned.apk
#      7/7 apksigner      ok -> app-signed.apk
#    then it opens the Android installer. Tap "Install."
```

**If step 3 (`kotlinc`) fails with "unresolved reference":** the toolchain may be
missing, or two compiles ran at once. Re-run
`bash tools/fetch_toolchain.sh`, then run one build at a time. (Two concurrent
`kotlinc` runs each reserve 2 GB and starve a 4 GB phone.)

**If you see "no APK produced":** read the log written to disk; the terminal screen
truncates. This is SPI-4: *log to disk, read from disk; the terminal is a liar.*

---

## 8. The gates (what runs and why)

`bash tools/ci.sh` runs every check and exits `0` only if all pass. The important
gates, and the defect each one prevents:

| Gate | Prevents |
|---|---|
| `tools/fork_integrity_gate.sh` | divergent trees; foreign symbols; unversioned inputs; non-compiling code |
| `tools/delivery_gate.sh` | declaring "delivered" while any named loophole is open |
| `tools/nt_gate.py` | a corpus claim cited but not carried; an unresolved contradiction |
| `tools/nt_sensor.py` | the Healer example naming a symbol the reference jar does not carry |
| `tools/syntax_gate.py` | unclosed block comments in Kotlin |
| `tools/api_level_gate.py` | a high-API call with no version guard (crashes older phones) |
| `tools/secret_gate.py` | a credential committed to the tree |
| `tools/board_gate.py` | a board item marked done with no evidence |
| `tools/stall_gate.py` | a named deficit left open across deliveries |
| `tools/law_gate.py` | a rule with no executable gate (a "note" masquerading as a law) |
| `tools/synchrony_gate.py` | a surface with no clock; a hand-edited time runtime |
| `tools/convergence_gate.py` | two derivations of one fact that disagree |
| `tools/circadian_gate.py` | time reported in the wrong zone |
| `tools/download_gate.py` | a download link that opens a viewer instead of downloading |
| `tools/kb_index.py` | a readable file that is unfiled, duplicated, or index-stale |
| `tools/icon_gate.py` | a missing or malformed app icon |
| `tools/install_gate.py` | an installable APK that fails its install checks |

> **POV correction.** You might think gates are "extra work." They are the opposite:
> each gate is a failure this project already paid for once, converted into a check so
> it can never recur silently (SPI-15). The gate is cheaper than the failure.

---

## 9. Honest limits (what this does NOT do)

A README that hides its limits creates follow-up questions. These are the real ones.

1. **It does not build on a computer in the normal way.** There is no Gradle project
   file. Use `build.sh` or `build&install.sh`.
2. **It does not use AndroidX or Compose.** Code that needs them will not compile
   here. Use raw `android.*` equivalents ([§3.8](#38-androidx-and-compose)).
3. **The signing key is not in the repo.** By design (a key in git is a leaked key).
   The build self-reports its signer so a mismatch is visible before install.
4. **The in-app forge's child-build inputs are partly on-device only.** `android.jar`
   and the signing pair are staged at build time, never committed.
5. **The on-phone build is the same chain but not run in this repository's
   automation.** The automation runs the identical `build.sh`; the physical phone run
   is a named boundary (`DEFICITS.json`, item E1).
6. **The local-assistant / terminal features described in
   `docs/ARCHITECTURE-OMEGA.md` are design-stage.** They are grounded in verified
   upstream facts but are not all implemented.
7. **There is no license file.** Treat the code as private unless the owner says
   otherwise.

---

## 10. FAQ (each answer is terminal)

**Q. What is this project, in one sentence?**
An Android app and offline web studio, built on the phone itself with a
Gradle-free toolchain, governed by automatic checks.

**Q. Do I need a computer?**
No. You need the Termux app on the Android phone.

**Q. Do I need internet?**
Once, to fetch the toolchain (`bash tools/fetch_toolchain.sh`). After that, no.

**Q. What command builds it?**
`bash build&install.sh`.

**Q. What command checks it?**
`bash tools/ci.sh`. It ends in `CI: PASS` when everything holds.

**Q. Where is the version number?**
In `app/src/main/AndroidManifest.xml`. It is currently `1.1.0-omega` (`versionCode 2`).

**Q. Why is Gradle forbidden?**
It exhausts this phone's memory and freezes the device. See
[§3.4](#34-gradle-and-why-it-is-forbidden). It is rule SPI-1.

**Q. Why not use AndroidX/Compose?**
The Gradle-free chain does not load them. See [§3.8](#38-androidx-and-compose).

**Q. What is a "gate"?**
An automatic check that must pass. See [§3.10](#310-the-gates).

**Q. What is the "NT corpus"?**
The project's graded reasoning documents. See [§3.12](#312-the-nt-corpus-and-savf).

**Q. What is SAVF?**
The offline auditing engine. See [§3.11](#311-savf).

**Q. Where do I start if I want to change the code?**
Read `AGENTS.md` and `DARKITH.md`, then change files under
`app/src/main/java/com/darkith/transliaison/`, then run `bash tools/ci.sh`.

**Q. What if a gate fails?**
Read the gate's message; it names the file and the reason. Fix the cause, re-run
`bash tools/ci.sh`. Do not disable the gate; a disabled gate is the defect it was
built to catch.

**Q. How do I know this README is complete?**
Read [§11](#11-the-questions-this-file-pre-answers-the-loop-breaker). If your
question is not there, add it, and answer it in the body.

---

## 11. The questions this file pre-answers (the loop breaker)

This is Law 5 in action. These are the follow-up questions a reader would ask next.
Each is answered here in one or two terminal sentences, so the chain ends.

1. **"Where do I type the commands?"** In the Termux app, from the repo root. If you
   are on a computer instead, any terminal works the same.
2. **"How do I get the repo onto the phone?"** Clone it with `git`, or copy the
   folder to the phone; then open Termux in that folder.
3. **"What is a 'repo root'?"** The top folder of the project — the one that contains
   `build.sh`. Run commands from there.
4. **"The build said `aapt2 not found`."** The toolchain is not provisioned. Run
   `bash tools/fetch_toolchain.sh`, then rebuild.
5. **"The build said `kotlinc not found`."** Same cause and fix: provision the
   toolchain, then rebuild.
6. **"It says 'Unclosed comment'."** A Kotlin comment block is missing its closer.
   Run `python3 tools/syntax_gate.py app/src/main/java` to locate it; fix that file.
7. **"It says 'unresolved reference: androidx'."** Some file imports AndroidX, which
   this chain cannot load. Replace the import with its raw `android.*` equivalent
   ([§3.8](#38-androidx-and-compose)).
8. **"The install prompt never appeared."** Use `bash build&install.sh --build`, then
   install `app-signed.apk` manually from the file manager.
9. **"Which file declares permissions?"** `app/src/main/AndroidManifest.xml`.
10. **"Where is the main screen defined?"** `HomekeeperActivity.kt` (dashboard) and
    `MainActivity.kt` (launcher), both under
    `app/src/main/java/com/darkith/transliaison/`.
11. **"How do I add a screen?"** Add an `<activity>` to the manifest, add the Kotlin
    class in the tree, then run `bash tools/ci.sh`.
12. **"How do I read the reasoning behind a rule?"** Open `DARKITH.md` for the rule,
    and `docs/nt/NT-INDEX.md` for the corpus that argues it.
13. **"What is the difference between `DARKITH.md` and `AGENTS.md`?"** `DARKITH.md`
    is the canonical record for humans and machines; `AGENTS.md` is working
    knowledge for an AI agent or a returning developer.
14. **"Why do so many files mention 'NEVER' and 'MUST'?"** They are the rule
    families; each is a real failure converted into a check
    ([§3.9](#39-spi-never-must-the-rule-vocabulary)).
15. **"Can I just use Android Studio?"** Not for this repo as shipped: there is no
    Gradle project. The point is the phone-only, Gradle-free chain.
16. **"Is the app on the Play Store?"** No. It is installed from the built `.apk`.
17. **"What does the app actually do on launch?"** It opens a web dashboard
    (Homekeeper) hosted in a `WebView`, bridged to device features.
18. **"Where is the data stored?"** The durable home is `/sdcard/Darkith/` (SPI-8).
19. **"How do I know a claim in the corpus is true?"** The claim carries a grade and,
    where it touches reality, a command that re-runs; `tools/nt_gate.py` enforces it.
20. **"What if I disagree with a rule?"** Change the rule *and* its gate together, and
    say why in `DARKITH.md`; a rule with no gate is not a rule (SPI-15).

If you reached this line with a question that is not in this list, the correct action
is written at the top of this file: add it here, and answer it above. The list is not
a courtesy; it is the acceptance test.

---

## 12. The invariant format (the reusable spec)

This README is an instance of a reusable shape. To apply it to any repository, follow
these steps. The shape is the deliverable; the Darkith text is the worked example.

**Step 1 — Declare the audience and the prerequisite.** State who the file is for and
what the reader must already know (ideally nothing). *(Law 6.)*

**Step 2 — Define before use.** For every specialist term and abbreviation, define it
at first use and list it in a glossary. *(Law 1.)*

**Step 3 — Narrate three tongues.** For each load-bearing concept, write a **Plain**
line (beginner), a **Precise** line (engineer), and a **Machine** line (literal
symbol/command). *(Law 2.)*

**Step 4 — Correct the point of view.** Where the reader's default assumption is
wrong, name it and correct it explicitly, before it is built upon. *(Law 3.)*

**Step 5 — Answer terminally.** End every answer with the reader able to act. Never
end with a bare pointer; if you point, say what is there. *(Law 4.)*

**Step 6 — Break the loop.** Close with an enumerated list of the questions the reader
would ask next, each already answered in the body. *(Law 5.)*

**Step 7 — Tell the story once.** Include a short chronicle that narrates the project
in dependency order, so ideas arrive only after what they depend on.

**Why this shape works (the mechanism).** A confusing README fails in four ways: it
uses a term before defining it; it serves only the expert; it leaves a wrong mental
model uncorrected; and it ends each answer by opening a new question. The four
corresponding laws — define-first, three tongues, POV correction, terminal answers —
close those four leaks, and the loop breaker proves the closure. This is why a
Tri-Tongue README can claim to leave the reader with no follow-up question.

---

*This file is the README for `Deobfugazi/darkith-forge`. It is governed by the same
rules it describes: if it is unclear, that is a defect here, and the fix is a change
to this file.*
