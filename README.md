# DARKITH

> **The mind is a fortress, not a cage. Freedom is earned through action. Truth is pursued, never claimed.**
>
> Darkith turns those convictions into an apparatus: software that refuses counterfeit success, keeps evidence attached to claims, and makes sovereignty more than a word.

## SIGNATURE PRIME — WHAT THIS MAKES IMPOSSIBLE

False completion. False verification. False accounting. Silent extraction. Untraceable correction. Manufactured certainty. Symbol collisions mistaken for equivalent meaning. Arithmetic presented as empirical proof. Reused infrastructure relabeled as the capability it merely hosts. A descope reported as absolution. A machine-generated claim promoted to reality without evidence.

Everything here exists to make those outcomes inadmissible. Any feature, document, gate, or presentation that does not synchronously serve that end is displacement, duplication, or defect—and must be corrected.

---

## What Darkith is

Darkith is a hand-built Android and offline-software forge, developed under severe device constraints and governed by an explicit body of technical and philosophical law.

The repository contains:

- An Android application: `com.darkith.transliaison`.
- A Gradle-free build chain designed to run from Termux on Android.
- An offline web studio and standalone HTML tools.
- An on-device forge/build path and recovery-oriented application machinery.
- SAVF, an offline verification and correction engine.
- Governing documents, executable gates, tests, and proof records.

The app is the tangible substrate. The governing idea is the system that refuses to confuse an artifact with its claim about itself.

## The will behind the work

Darkith begins with a refusal: **no system earns authority by sounding certain.**

A result must be grounded in what exists. A capability must be judged by its own behavior—not by a nearby file, reusable framework, or convincing explanation. A correction must preserve the defect's origin, name the governing rule, and leave evidence that can be checked again.

The long-range objective is economic and civic as well as technical: tools and systems that increase people's ability to produce, retain, govern, and circulate value without surrendering it through silent extraction. The destination is not merely a green build or a completed task list. It is a world in which people can understand the machinery shaping their lives, participate in its governance, and retain meaningful control over the value they create.

That economic objective is **not claimed as implemented by this repository today**. It is the direction that gives the engineering its purpose.

## The governing principles

### Never counterfeit a capability
A stub that returns success is a lie with a clean exit code. If a mechanism is absent, its absence must be explicit. A named boundary is honest; simulated completion is not.

### Evidence belongs to the claim
Documentation is not execution. Execution is not verification. Verification is not closure. Claims retain their actual evidence state, including uncertainty, contradiction, skipped checks, and unresolved work.

### Status belongs to the capability
A file may exist while the capability it names remains absent. General admission machinery does not become economic admission because economic work intends to use it. Reused infrastructure is an asset—not inherited proof.

### Preserve meaning through correction
A repair must not erase the original directive, silently change its meaning, or fill a gap with invented facts. Corrected material is a traceable derivative. Conflicts are resolved by the governing invariant, not by majority vote or convenience.

### Keep accounting systems distinct
Project progress and economic extraction are different measurements.

Project accounting asks what registered work remains. Economic accounting asks what a community produces, what leaves it, and what value it retains and controls. A zero project deficit cannot prove zero extraction; a low extraction ratio cannot prove a project complete.

The economic invariant is:

`W_in − E = S`

where `W_in` is verified community-generated wealth, `E` is external extraction, and `S` is retained value. Retention is not merely a positive number: value must be accessible, locally controlled, and able to circulate.

### No false greens
PASS, FAIL, SKIP, and INACTIVE are not interchangeable. A skipped check did not pass. A descope is a boundary with a cost, not absolution. Project-level success must never be presented as proof of a larger system-level outcome.

### Build by hand; verify by machine
The app's load-bearing Kotlin is written directly rather than produced by an app-class code-generation pipeline. The machine then compiles, checks, measures, and tests what the hand has derived. Hand-written code is not inherently correct; this choice keeps source inspectable and the transformation path explicit.

### Sovereignty is operational
Local execution, offline access, readable source, portable verification, and control over one's own work are not aesthetics. They reduce dependence on systems that can deny access, obscure behavior, or extract value without meaningful consent.

---

## The distinctive engineering

### A bounded, feedback-driven renderer

The Android renderer contains a hardware-responsive allocation loop. At frame boundaries, it uses device measurements and tracked resource use to adjust bounded rendering budgets. The allocation feeds back into the next frame rather than remaining a fixed build-time assumption.

The implementation includes:

- `AutophagicAllocator` — bounded allocation logic.
- `MemoryGovernor` — reciprocal budgeting between renderer and model allocations.
- `GpuScanner` — queries supported limits from the active graphics context.
- `OmegaRenderer` — applies the allocation before rendering.
- An invariant witness that checks the generated grid against its allocation budget.

Some values are live device readings; others are renderer-owned accounting or derived estimates. Tracked GPU-side bytes are not a direct measurement of all physical GPU memory. This is an implemented control mechanism, not proof of universal crashlessness or optimal performance on every device.

### A raw Android build path

The build avoids Gradle and uses a direct toolchain sequence: Android resource compilation, Kotlin compilation, DEX conversion, packaging, alignment, and signing. The repository scripts provision and use the required tools. Signing credentials remain external to the repository.

### A correction system with evidence

SAVF and the repository gates are designed to detect defects, classify them, trace their causes, preserve evidence, apply authorized corrections, and rerun verification. The aim is not merely to report errors; it is to make known defect classes harder to repeat.

The current SAVF and CI machinery are real software assets. Their presence does not mean every semantic, empirical, economic, or reality-aligned verification responsibility is implemented. Those extensions remain work.

---

## What exists—and what remains a goal

Darkith keeps implementation and destination separate.

| Layer | Present in the repository | Not established by that fact |
|---|---|---|
| Android application | Kotlin app, WebView surfaces, build scripts | Universal device compatibility |
| Offline studio | Hand-authored HTML tools and local interfaces | Every proposed workflow is complete |
| Build and verification | Raw build chain, CI, tests, executable gates | Every gate proves every real-world claim |
| SAVF / correction machinery | Audit engine, parity/UI gates, claims and proof records | Universal semantic and empirical truth verification |
| Project accounting | Registered-work progress calculation | Community wealth or extraction measurement |
| Economic Omega | Governing architecture and domain specifications | Operational economic sovereignty or zero extraction |

Economic modules, community accounting, governance adapters, subsistence and ecological measurement, reciprocal settlement, and independent Omega completion proof must not be marked implemented merely because their architecture is described or their host infrastructure exists.

Omega is not a badge a document awards itself. It is a condition that must be demonstrated through independent operational evidence.

---

## Build and verify

### Requirements

- An Android device with Termux.
- The repository checked out locally.
- Network access for initial toolchain provisioning; cached tools may be reused afterward.
- A signing pair staged locally. No private signing key belongs in the public repository.

### Build and install

From the repository root in Termux:

```bash
bash 'build&install.sh'
```

Build without installing:

```bash
bash 'build&install.sh' --build
```

Provision and build without installing:

```bash
bash 'build&install.sh' --verify
```

The resulting APK is left at `app-signed.apk`. In install mode, the script hands it to Android's package installer when available; installation still requires the device's confirmation or applicable local permission.

### Run the repository checks

```bash
bash tools/ci.sh
```

Exit code `0` means the script's required checks passed. A check reported as SKIP did not pass. Read the recorded output and proof files; do not treat the final line as a universal guarantee.

---

## Repository map

| Path | Purpose |
|---|---|
| `app/src/main/java/com/darkith/transliaison/` | Android application source |
| `app/src/main/assets/` | Web assets packaged into the app |
| `build.sh` | Raw APK build chain |
| `build&install.sh` | Provision, build, and optionally install |
| `tools/ci.sh` | Provider-neutral verification entry point |
| `tools/` | Build, integrity, admission, audit, and correction tools |
| `savf.py` / `savf.html` | SAVF engine and browser-facing interface |
| `proof/` | Machine-readable claims, results, and evidence records |
| `DARKITH.md` | Canonical governing record |
| `AGENTS.md` | Operational instructions and working constraints |
| `docs/nt/` | Noveltreatise corpus and index |
| `omega-reader.html` | Offline reader for four presentation registers |
| `TASKS.md` / `DEFICITS.json` | Project work and registered deficits |

Start with `DARKITH.md` for the governing record, `docs/nt/NT-INDEX.md` for the reasoning corpus, and `tools/ci.sh` for the executable verification path.

---

## How to read a Darkith claim

Ask what capability is meant and what evidence supports it.

- **Specified:** the rule or design is stated.
- **Implemented:** the capability exists in executable form.
- **Verified:** a relevant check or measurement supports the claim under stated conditions.
- **Qualified:** the capability meets its explicit admission criteria.
- **Partial:** some required behavior exists, but the whole capability does not.
- **Missing:** the capability was searched for and not found in the inspected implementation.
- **Skipped / inactive:** the check or stage did not run; it is not a pass.

These labels describe different facts. They must not be collapsed into one reassuring status.

## Limits and boundaries

- Darkith is not a Gradle project. The supported build path is the repository's raw chain.
- AndroidX and Jetpack Compose are not part of the app's supported source path.
- Toolchain components and signing inputs may need to be staged locally.
- `AegisVM` explicitly reports `ERROR: NOT_IMPLEMENTED`; it is not a completed execution engine.
- Some local-assistant and terminal concepts in the architecture documents remain design-stage or incomplete.
- The economic Omega system is a governing objective and specified architecture, not a completed production economy.
- The repository is public but currently has no `LICENSE` file. Public visibility does not grant permission to reuse, modify, or redistribute the work. All rights remain reserved unless an explicit license is added.

---

## The peer this work is looking for

Darkith is for the person who looks past the feature list and asks:

What does this system refuse to lie about?  
What does it measure, and what does it merely infer?  
Who retains control when the tool succeeds?  
Can the claim be checked without trusting the person who made it?  
Does the mechanism reduce dependence—or merely move it somewhere less visible?

If those questions matter to you, you are reading the project at the level it was built to address.

The invitation is not to believe the doctrine. Inspect the source. Run the checks. Challenge the claims. Help reduce the gap between stated principle and actual behavior.

**Darkith does not ask to be trusted because it declares itself sovereign. It has to earn that trust by making its workings inspectable, its limits visible, and its corrections accountable.**

---

## The final boundary

The project ledger may reach its own zero. That is project completion.

The world Darkith is meant to serve begins where project completion stops: with people able to create, understand, govern, and retain the value of their own work.

No README, register, test suite, or machine may declare that destination achieved on its own. Only demonstrated capability and independent evidence can do that.
