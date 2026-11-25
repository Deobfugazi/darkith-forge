# DARKITH — The Forge of Verifiable Sovereignty

> **The mind is a fortress, not a cage. Freedom is earned through action. Truth is pursued, never claimed.**
>
> Darkith turns those convictions into an apparatus: a local software forge, a correction system, and a body of law that refuses to confuse a declared result with a demonstrated one.

## SIGNATURE PRIME — WHAT THIS MAKES IMPOSSIBLE

False completion. False verification. False accounting. Silent extraction. Untraceable correction. Manufactured certainty. Symbol collisions mistaken for equivalent meaning. Arithmetic presented as empirical proof. Reused infrastructure relabeled as the capability it merely hosts. A descope reported as absolution. A machine-generated claim promoted to reality without evidence.

Everything in this repository must synchronously serve that singular end. A displacement, duplicating noise, or defect is not an additional feature; it is something the system must detect and correct.

This README is the public bridge into the work: a nested field guide to the purpose, principles, machinery, evidence, limits, and practical answers a reader would otherwise have to ask for separately.

---

# 0. Start here

## 0.1 What is Darkith in one sentence?

Darkith is a local-first Android and offline-software forge built to turn inspectable source into usable tools while making claims, corrections, and progress accountable to evidence.

## 0.2 What is it trying to accomplish?

The immediate work is software: an Android host, offline interfaces, build machinery, audit tools, and repository gates.

The deeper objective is sovereignty as an operational condition: people should be able to understand the tools shaping their work, run and inspect those tools locally, correct them without surrendering control, and retain meaningful control over the value they create.

The economic and civic destination is not claimed as completed by the current app. It is the direction that gives the engineering its purpose.

## 0.3 Who is this for?

For builders, researchers, operators, and potential collaborators who look past feature lists and ask:

- What does this system refuse to lie about?
- What does it measure, and what does it merely infer?
- Can I reproduce the claim without trusting its author?
- Who controls the tool and the value created through it?
- Does the mechanism reduce dependence—or merely move it somewhere less visible?

The invitation is not to accept the doctrine. Inspect the source, run the checks, challenge the claims, and help close the gap between stated principle and actual behavior.

## 0.4 Fast paths

| I want to… | Start here |
|---|---|
| Understand the governing doctrine | [Principles](#2-the-governing-principles) |
| Build/install the Android app | [Build and install](#9-build-install-and-run) |
| Run repository checks | [Verification](#10-verification-and-evidence) |
| Understand SAVF | [SAVF](#6-savf--the-correction-and-verification-engine) |
| Explore the app and studio surfaces | [Surface catalogue](#7-the-offline-studio-and-tools) |
| Read the technical law corpus | [Noveltreatise index](#11-the-noveltreatise-law-corpus) |
| Know what exists vs. what remains | [Capability truth table](#12-what-exists-and-what-does-not) |
| Find a source or tool | [Repository map](#14-repository-map) |
| Get answers without a follow-up | [Nested FAQ](#16-the-nested-faq) |
| Use Darkith or understand a subsystem | [Operational mini-wiki](#17-operational-mini-wiki) |
| Diagnose a build, install, or verification failure | [Troubleshooting](#18-troubleshooting-and-recovery) |
| Decode Darkith terminology | [Glossary](#19-glossary-and-concept-map) |

---

# 1. The will behind the work

Darkith begins with a refusal: **no system earns authority by sounding certain.**

A result must be grounded in what exists. A capability must be judged by its own behavior—not by a nearby file, reusable framework, or convincing explanation. A correction must preserve the defect's origin, identify the governing rule, and leave evidence that can be checked again.

The long-range objective is economic and civic as well as technical: tools and systems that increase people's ability to produce, retain, govern, and circulate value without surrendering it through silent extraction. The destination is not merely a green build or completed task list. It is a world in which people can understand the machinery shaping their lives, participate in its governance, and retain meaningful control over the value they create.

The project ledger may reach zero. That is project completion. The world Darkith is meant to serve begins where project completion stops.

---

# 2. The governing principles

## 2.1 Never counterfeit a capability

A stub that returns success is a lie with a clean exit code. If a mechanism is absent, its absence must be explicit. A named boundary is honest; simulated completion is not.

## 2.2 Evidence belongs to the claim

Documentation is not execution. Execution is not verification. Verification is not closure. Each claim must retain its actual evidence state, including uncertainty, contradiction, skipped checks, and unresolved work.

## 2.3 Status belongs to the capability

A file may exist while the capability it names remains absent. General-purpose admission machinery does not become economic admission because economic work intends to use it. Reused infrastructure is an asset—not inherited proof.

## 2.4 Preserve meaning through correction

A repair must not erase the original directive, silently change its meaning, or fill a gap with invented facts. Corrected material is a traceable derivative. Conflicts are resolved by the governing invariant, not by majority vote or convenience.

## 2.5 Keep accounting systems distinct

Project progress and economic extraction are different measurements.

Project accounting asks what registered work remains. Economic accounting asks what a community produces, what leaves it, and what value it retains and controls. A zero project deficit cannot prove zero extraction; a low extraction ratio cannot prove a project complete.

The economic invariant is:

W_in − E = S

W_in is verified community-generated wealth; E is external extraction; S is retained value. Retention is not merely a positive number: value must be accessible, locally controlled, and able to circulate.

The project progress-deficit indicator uses similar notation in a separate project-bound model. tools/omega_deficit.py reads the durable board and deficit ledger. It measures registered work—not community wealth.

## 2.6 No false greens

PASS, FAIL, SKIP, and INACTIVE are not interchangeable. A skipped check did not pass. A descope is a boundary with a cost, not absolution. Project-level success must never be presented as proof of a larger system-level outcome.

## 2.7 Build by hand; verify by machine

The app's load-bearing Kotlin is written directly rather than produced by an app-class code-generation pipeline. The machine then compiles, checks, measures, and tests what the hand has derived. Hand-written code is not inherently correct; this choice keeps source inspectable and the transformation path explicit.

## 2.8 Sovereignty is operational

Local execution, offline access, readable source, portable verification, and control over one's own work are not aesthetic preferences. They reduce dependence on systems that can deny access, obscure behavior, or extract value without meaningful consent.

## 2.9 A law must be a gate

A principle that is only written down can be ignored. The intended pattern is:

**law → detector → classification → authorized correction → prevention gate → regression test → evidence**

A repair without a prevention mechanism leaves the failure class alive.

## 2.10 Correct classes, not symptoms

When a defect recurs, ask what class of failure was permitted and what mechanism failed to prevent it. The durable correction belongs at the source, generator, configuration, or governing rule—not as a patch to generated output.

---

# 3. The four-core invariant and repository model

The Homekeeper specification uses the four-core invariant **A ∧ B ∧ C ∧ D**. It tests whether a claimed unit is a real, bounded, authoritative repository rather than a loose collection of files.

The canonical decomposition names four conditions:

- **A — Relational:** the unit has a defined relationship to what it holds or governs.
- **B — Structural:** its organizing apparatus is distinct from raw content.
- **C — Functional:** it provides the relevant preservation, retrieval, modification, distribution, or reconstruction function.
- **D — Authority:** it has a defined boundary and authority; it is not merely a cache or arbitrary copy.

The invariant is conjunctive. Strength in one condition cannot compensate for a missing condition.

The full terminological argument and its falsifiers are in docs/DARKITH-OMEGA-repo.txt. The executable Homekeeper model is in darkith-omega-homekeeper/.

## 3.1 Why this applies to the repository itself

The repository applies the same logic to its own structure:

- one governing record per layer;
- apparatus separated from knowledge and runtime assets;
- one retrieval index;
- canonical sources distinguished from generated mirrors;
- claims linked to the bytes and checks that support them.

The filesystem is not merely storage. It is part of the system's truth-accounting boundary.

---

# 4. System architecture

## 4.1 Major layers

| Layer | Responsibility | Main location |
|---|---|---|
| Governing law | Principles, invariants, status rules, boundaries | DARKITH.md, docs/nt/ |
| Android host | App lifecycle, permissions, native bridge, local surfaces | app/src/main/ |
| Offline studio | Standalone HTML applications and tools | repository-root HTML files |
| Forge/build | Raw APK build, toolchain staging, child-forge inputs | build.sh, build&install.sh, tools/ |
| Verification | CI, gates, tests, source and contract audits | tools/, tests/, proof/ |
| Knowledge index | Deterministic inventory of readable source and apparatus | docs/INDEX.md, tools/kb_index.py |
| Economic Omega | Specified sovereign-economy objective and domain architecture | NT XI–XIII, Omega documents |

## 4.2 Android host and web surfaces

The Android host is a native Kotlin application with WebView-based surfaces. It exposes native capabilities through Kotlin bridge classes to local HTML interfaces.

The package is com.darkith.transliaison. The manifest declares versionCode 4 and versionName 2.1.0-omega; VERSION.json is the update/release manifest. The app targets API 34 and has a minimum SDK of 24 in the governing build record.

The manifest requests capabilities including network state, storage/media, camera, microphone, location, notifications, foreground data sync, and package installation. Actual access remains subject to Android's runtime permission model and device settings. A declaration does not mean permission has been granted or that a feature is active.

## 4.3 The native bridge

The Kotlin bridge is the boundary between the web interface and Android/device functions. Key source includes:

- app/src/main/java/com/darkith/transliaison/DarkithBridge.kt
- HomekeeperBridge.kt
- DeviceBridge.kt
- BuildEngine.kt
- ChimeraBuilder.kt
- NativeTools.kt

tools/bridge_contract_audit.py checks the UI/native contract. A method existing on one side does not prove that the other side calls or handles it correctly.

## 4.4 Raw build, not Gradle

The supported Android build is a direct toolchain chain rather than Gradle. The seven-step chain is governed by NT IX and the build scripts. It uses Android resource compilation, Kotlin compilation, DEX conversion, packaging, alignment, and signing, with required intermediate steps and checks.

This is a project design choice to keep the build path visible and device-runnable under constrained conditions—not a claim that Gradle is universally inferior.

## 4.5 On-device forge

The host carries engine inputs under app/src/main/assets/engine/ so its forge can use them locally. tools/stage_engine_inputs.sh stages device-specific inputs, including the Android framework jar and signing material, without committing private signing keys.

A host APK build does not prove the child-forge path. The child artifact must itself be built, linked, signed, and checked against its manifest and runtime requirements.

---

# 5. The Android host and forge

## 5.1 What the app is

The app is the installable Android entry point for Darkith's local interfaces and forge machinery. It is not the whole repository, and the repository is not reducible to the APK.

## 5.2 What it carries

The tracked Android source and assets provide a launcher and Homekeeper surface, local HTML applications, a native-to-web bridge, device-oriented interfaces, APK build/install and child-forge mechanisms, local audit/correction surfaces, and supporting runtime/recovery machinery.

## 5.3 Identify the installed build

The installed package metadata—not a README claim or filename—is the authority.

In Termux:

~~~sh
pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'
~~~

If the app surface exposes darkith.apkVersion(), it reports the bridge/package version. Inspect the APK with Android build tools:

~~~sh
aapt dump badging app-signed.apk | grep -E '^package'
~~~

The version manifest, package manifest, displayed version, and updater metadata must agree. CI checks that consistency.

## 5.4 Device realities

Darkith is developed for constrained Android hardware and Termux. Memory, thermal budgets, Android storage/executable-location rules, runtime permissions, and physical-device testing all matter.

A successful remote build is not universal device-compatibility proof. The repository names device-only verification boundaries instead of pretending a sandbox can test a phone it does not possess.

---

# 6. SAVF — the correction and verification engine

## 6.1 What SAVF is

SAVF is the Signed Axis Verification Formulary / Universal Audit Engine family carried by this repository. It combines a formal axis/formulary core with audit gates that inspect source, reachability, mutation behavior, evidence, and claim records.

Primary surfaces:

- savf.py — Python core and CLI.
- savf.html — full browser-facing audit engine.
- darkith-inscriber.html — SAVF Lite studio.
- app/src/main/assets/savf_core.html — packaged runtime core.
- tools/savf_parity_gate.py — Python/JavaScript parity checks.
- tools/savf_ui_gate.py — interface and behavior checks.

## 6.2 Defects it is designed to catch

SAVF and surrounding gates target stubs that return canned success, mocks that claim work without doing it, phantom references to absent symbols/evidence, unreachable checks, contract-breaking mutations, swallowed syntax/comment defects, unreproducible claims, and divergence between Python and browser implementations.

The core principle is reproduction: a claim should carry a bounded means of rerunning relevant work and comparing the result. A digest is an integrity witness for bytes; it is not proof that the bytes are true, useful, novel, or reality-aligned.

## 6.3 What it cannot prove automatically

SAVF cannot infer every external fact from source. It cannot prove that a real-world dependency exists merely because a command is recorded, that a community accepted a result, that a market value is real, or that a specification is implemented in the physical world.

A command can be rerun and attested. Its real referent still needs independent grounding.

## 6.4 Its role in the whole system

SAVF is not an independent truth authority. It is a verification/correction component governed by the repository's laws and evidence model. It makes defects more detectable and repeatable; it does not grant Omega completion.

---

# 7. The offline studio and tools

Darkith carries standalone HTML interfaces at the repository root and related runtime assets inside the Android app. Root HTML files are development/inspection surfaces; packaged copies are runtime assets. Declared mirrors must remain byte-identical through parity/index gates.

## 7.1 Main studio surfaces

| Surface | File | Purpose |
|---|---|---|
| Sovereign Homekeeper | darkith home forge.html | Main Homekeeper/web studio |
| Omega terminal + assistant | d-arkith-omega.html, omega.html | Terminal/local-assistant interface surfaces |
| Code/audit studio | darkith code studio.html | Code and audit workbench |
| SAVF Lite / Inscriber | darkith-inscriber.html | Lightweight SAVF studio |
| SAVF-1 Universal Audit Engine | savf.html | Full audit engine interface |
| ClearanceLoop | clearanceloop.html | Debt-clearance ratchet |
| Icon Forge | icon_forge.html | Icon creation |
| Omega Master | darkith-omega-master.html | Master blueprint/executable specification |
| Omega Reader | omega-reader.html | Four-register repository reader |
| Omega Apps | darkith-omega-apps.html | App collection surface |

## 7.2 Device-app surfaces

The repository contains separate interfaces for Apps, Camera, Clock, Contacts, Files, Media Player, Messages, and Phone.

Standalone files are at the repository root; packaged copies are under app/src/main/assets/. The packaged files are the shipped versions. Edit canonical sources and propagate them through the documented process rather than creating divergent twins.

## 7.3 ClearanceLoop — debt as a rate, not a snapshot

ClearanceLoop's law is that health is a rate of clearance, not a static tolerance:

- **Monotone:** when debt drops, the per-class high-water mark drops with it.
- **Regression:** debt above the mark is a net addition and fails.
- **Stasis:** debt that does not clear across the delivery window is force-degraded.
- **Waiver:** a rise is permitted only through a recorded, reasoned, expiring exception.

A waiver does not raise the high-water mark. The ratchet does not permanently loosen.

The headless implementation is clearanceloop.py; the browser engine is app/src/main/assets/vendor/clearanceloop.js. Python, JavaScript, and UI implementations are intended to agree verdict-for-verdict.

## 7.4 Fracture Scout — novelty from real unresolved problems

tools/fracture_scout.py is a configurable source scout for real-world unresolved problems. It parses boolean query expressions, uses source adapters, and ranks candidate fractures rather than naively matching one topic word.

The corpus defines a fracture as a real problem anchored to a real source and unresolved need. “Deep webspace” means structured research, defect, standards, and practitioner sources beyond naive surface search—not Tor or .onion services.

A candidate is not automatically a validated task, bounty, or solved problem. It requires source inspection and admission.

## 7.5 Darkbot — provider-neutral dependency watcher

tools/darkbot.py reads the dependency manifest, checks public package registries, reports version drift, can update pins, exports Python requirements, retrieves release digests, and verifies local artifacts.

The manifest is tools/deps.txt. Generated requirements-dev.txt is an export, not a second independent source of truth.

## 7.6 Nodal — receipt and coordination substrate

The nodal/ package carries a receipt schema, append-only hash-chained ledger, and bot/engine logic for ordered firing and reconciliation. The implementation includes storage immutability and restart-safe sequence handling.

Nodal does not provide arbitrary-code sandboxing or cross-machine consensus.

## 7.7 Homekeeper — executable repository model

The darkith-omega-homekeeper/ project models the four-core invariant, units, claim records, admission/validation, capability deltas, fixed-point calculation, and reader generation.

Its canonical reader shell is a byte-exact twin of omega-reader.html; the parity gate prevents design drift. The project includes a TypeScript CLI and tests for the invariant, separation of powers, and Omega calculation.

## 7.8 Portable Co-ordinasync toolkit

kit/COORDINASYNC.md documents the portable one-file toolkit; kit/coordinasync.py is intended to travel between projects without reconstructing its apparatus. It can install tools, self-test, ingest/propagate directives, check law-to-gate coverage, and coordinate the durable board.

---

# 8. Local terminal and assistant: design vs. implementation

The repository contains terminal and local-assistant interfaces, but the architecture document distinguishes intended design from current host behavior.

## 8.1 Intended terminal tiers

1. **Native interpreter tier:** Android-native binaries packaged as APK native libraries and executed from the allowed native library location.
2. **Wasm/WASI tier:** sandboxed modules run inside a JVM-compatible WebAssembly runtime.
3. **Optional PRoot tier:** an on-demand Linux root filesystem for broader toolchains and packages.

The design is motivated by Android executable-location restrictions. App-writable storage is not a safe executable location for a modern target-SDK app; copying a binary into shared storage does not make it executable.

## 8.2 Intended local assistant

The architecture proposes a tiered local GGUF assistant with device-bounded memory/context budgets and tool calls into the terminal and forge.

A local model is not claimed to equal a frontier cloud model. Its intended advantages are privacy, offline availability, and integration with the on-device forge. Model size, speed, memory, and reasoning capability remain constraints.

## 8.3 Current honesty boundary

docs/ARCHITECTURE-OMEGA.md is explicitly a design document grounded in verified upstream facts. It records that current runtime-host/Alpine-guest behavior contains stubs that report a start-like result without properly streaming process output, and that executable placement must obey Android's W^X constraints.

Therefore:

- a terminal UI is not proof every language runtime is available;
- a “started” string is not proof a process ran correctly;
- native/Wasm/PRoot tiers are not implemented merely because they are specified;
- the local GGUF architecture is not a production-ready shipped model runtime unless artifacts and tests demonstrate it.

---

# 9. Build, install, and run

## 9.1 Requirements

- Android device with Termux for the on-device path.
- Repository checked out locally.
- Network for initial toolchain provisioning; cached tools may be reused.
- Android resource compiler, Kotlin compiler/JDK, DEX tooling, zipalign, apksigner, and Android framework jar, supplied by provisioning/staging or the local environment.
- Local signing pair. Private signing keys must never be committed.

## 9.2 One-shot build and install

From the repository root:

~~~sh
bash 'build&install.sh'
~~~

The script provisions the raw toolchain, stages child-forge inputs when available, runs build.sh, and hands the APK to Android's installer when supported. The user confirms the Android installation prompt where required.

## 9.3 Build without installing

~~~sh
bash 'build&install.sh' --build
~~~

The APK is left at app-signed.apk.

## 9.4 Provision and build, install nothing

~~~sh
bash 'build&install.sh' --verify
~~~

This builds without installing. It does not claim every physical-device installation path has been exercised.

## 9.5 Direct raw build

~~~sh
bash build.sh . Darkith com.darkith.transliaison
~~~

The raw script discovers the manifest/source tree, locates tools, checks the API ceiling, compiles/packages/aligns/signs, and emits the APK. It does not invoke Gradle.

## 9.6 Output and signing

Default output: app-signed.apk in the project root.

Signing identity matters to Android update/install behavior. A different key may prevent updating an existing package. A remote sandbox cannot infer the user's installed signer; the device installation is the final authority.

Never commit release_key, release_cert, keystore files, tokens, or credentials. Secret and continuity gates exist to block this leak class.

---

# 10. Verification and evidence

## 10.1 One CI entry point

~~~sh
bash tools/ci.sh
~~~

This is provider-neutral. GitHub Actions or another CI service should be a thin adapter that calls the same script rather than maintaining duplicate test logic.

The script records output to proof/ci_last.log by default and can emit/verify receipts from the run log.

## 10.2 What CI checks

The suite covers active repository responsibilities, including:

- session boot and repository fast verification;
- SAVF CLI contracts and self-tests;
- Darkbot and Fracture Scout self-tests;
- secret detection and secret-gate self-test;
- Kotlin syntax/comment integrity;
- API-level and icon checks;
- durable board/evidence and law-citation checks;
- build/fork integrity and delivery contracts;
- Noveltreatise corpus admission and reconciliation;
- SAVF Python/JavaScript parity and UI behavior;
- bridge contract and runtime/build checks;
- generated-copy, tree, version, and drift consistency;
- installer/delivery requirements and receipt accounting.

The exact executed gates are the ones named in the current tools/ci.sh output—not a static number copied into this README.

## 10.3 Verdict meanings

- **PASS / exit 0:** the named check ran and met its acceptance condition.
- **FAIL / nonzero:** the named check ran and did not meet its condition.
- **SKIP:** the required runtime or artifact was unavailable; this is not PASS.
- **INACTIVE:** the check/capability is not active in that context; it does not imply healthy.

A CI exit code 0 means the script's required checks passed under that run's conditions. It is not proof of every external, physical, economic, or philosophical claim in the repository.

## 10.4 Focused test harness

~~~sh
bash tools/tests/run.sh
~~~

This compiles and runs the offline alert/comment/pending test layer. It requires kotlinc and does not require Gradle, network, or an Android device.

Other tests live under tests/ and tools/tests/. CI is the recommended complete selection because it includes the current gate wiring.

## 10.5 SAVF CLI

~~~sh
python3 savf.py --help
~~~

Use the help output for the exact CLI options in the checked-out revision. SAVF is Python standard-library based and includes self-test/gate paths. Browser behavior is checked separately for parity and UI conditions.

## 10.6 Re-vouch the bytes, not memory

For any current-state claim:

1. identify the exact source file or artifact;
2. read the actual bytes;
3. run the relevant reproducer or gate;
4. preserve command, result, and log;
5. distinguish verified facts from inference and skipped checks.

A previous green run is not proof that a later tree is green.

---

# 11. The Noveltreatise law corpus

The Noveltreatise (NT) corpus is the law layer that repository gates enforce. DARKITH.md is the state layer; it references the corpus rather than duplicating it. The map is docs/nt/NT-INDEX.md.

| Treatise | Governing subject |
|---|---|
| NT I | Basal floor/cortical surface; RSA as correlate |
| NT II | Offload inversion and re-enterability |
| NT III | Assignment by rescue assay: dosage, geometry, energetics |
| NT IV | Pre-registration gate and reflexive Stage 0 |
| NT V | The cut, two-clock payroll gap, autophagic recycle |
| NT VI | Coupling law across scales; disjointness, continuity, synchrony |
| NT VII | Screen-stack layer order and adjacency necessity |
| NT VIII | Bond Formation Number and cross-scale bond criterion |
| NT IX | Multiplicative triad and seven-step raw Android build |
| NT X | Hardware ground truth, autophagic allocator, Healer, Σ = 0 |
| NT XI | Autophagic Sovereign Economy (ASE) |
| NT XII | Terminal convergence, Triadic Resolver, SAVF Generative Manufactory, proto-node, ASE |
| NT XIII / OFIF | Field-invariant formulary: premises, prior-art verdicts, derivation, falsifiers |

NT I–IV share NT-I-IV-protocol.md; NT V–XIII have their own files. NT XII's mechanics are classified separately from externally exposable figures and cross-scale inference. NT XIII is a prior-art scan and falsifier set—not a claim that every fixture is unprecedented.

## 11.1 How the law is enforced

The NT-to-gate map is in docs/nt/NT-INDEX.md. Representative gates:

- tools/nt_gate.py — corpus carried, reconciled, and contradiction-free;
- tools/absolution_admission.py — corpus count/admission checks;
- tools/fork_integrity_gate.sh — raw-chain and no-foreign-symbol constraints;
- tools/api_level_gate.py — API-level hazards;
- tools/law_gate.py and tools/syntax_gate.py — stub/law and syntax constraints;
- tools/bridge_contract_audit.py — continuity across the UI/native boundary;
- tools/synchrony_gate.py — shared-clock condition.

A law without an executable gate is only a note.

---

# 12. What exists and what does not

The public description must distinguish implementation from architecture.

| Capability | Evidence boundary |
|---|---|
| Android app | Source, manifest, build scripts, packaged assets exist. Device-specific install/runtime behavior requires device verification. |
| Raw APK build | Build chain and one-shot script exist. A physical on-device build is a separate verification condition. |
| Offline studio | Standalone HTML interfaces and packaged assets exist. Feature completeness belongs to each implementation and its tests. |
| SAVF | Python/browser implementations, audit gates, parity/UI checks exist. Not universal proof of semantic or empirical truth. |
| CI and repository gates | Provider-neutral script and many named gates exist. SKIP is not PASS; coverage has a defined scope. |
| Correction/autophagy | Defect-class registry and corrective machinery exist. A class closes only when detector, repair, prevention gate, and test prove it. |
| Project accounting | Durable task/deficit accounting exists and is computed by tools/omega_deficit.py. It measures registered work. |
| Nodal | Receipt schema, append-only ledger, coordination engine exist. No arbitrary-code sandbox or cross-machine consensus is established. |
| Homekeeper | Four-core invariant, admission/validation, capability delta, Omega calculation, reader, and tests exist. |
| Economic Omega / ASE | Governing corpus and architecture exist. Production sovereign economy, community wealth measurement, universal reciprocal settlement, and independently proven zero extraction are not established by documents alone. |
| Local assistant/terminal | Design is documented. Architecture records current host stubs and Android constraints; proposed tiers need artifacts and tests. |
| AegisVM | The implementation explicitly reports ERROR: NOT_IMPLEMENTED; it is not a completed VM. |

## 12.1 Status vocabulary

- **Specified:** the rule or design is stated.
- **Implemented:** the capability exists in executable form.
- **Verified:** a relevant check/measurement supports the claim under stated conditions.
- **Qualified:** the capability meets explicit admission criteria.
- **Partial:** some required behavior exists, but the whole capability does not.
- **Missing:** searched for and not found in the inspected implementation.
- **Descoped:** explicitly removed from the current delivery, with a reason.
- **Skipped / inactive:** the check or stage did not run; it is not a pass.

A capability's status belongs to the capability—not to the file, folder, or infrastructure that hosts it.

---

# 13. Omega, absolution, and the economic objective

## 13.1 What Omega means

Omega is the singular end condition: a system whose capabilities, accounting, governance, and evidence converge without contradiction or extraction hidden behind success labels.

It is not a decorative version suffix or a status a README can award itself.

## 13.2 Project absolution

The project progress-deficit indicator reads the durable board and deficit ledger:

- W_in: all named work;
- E: unreturned/open work;
- S: completed or formally descoped work;
- E/W_in: the project progress-deficit ratio.

The ledger must balance: W_in = E + S. A formal descope is a named boundary, not proof that the removed capability exists.

## 13.3 Economic absolution

The economic corpus describes retained value and extraction. It must be measured at the economic capability itself. Project completion, a balanced task board, a successful build, or general-purpose admission infrastructure cannot substitute for operational economic accounting.

The goal is to measure and govern value flows—not declare “zero extraction” because a document says so.

## 13.4 The minting/witness thesis

The Black & Whitepaper describes a contribution record based on reproducible closure: a bounded command and expected result are rerun by a party who need not trust the issuer. The record is admitted by the work and its reproducibility—not by purchase, popularity, or recipient acceptance.

The paper states its limits: the ledger is single-writer and tamper-evident, not a blockchain or global-consensus system; semantic novelty is not proven by textual novelty; timing-side-channel hardening is not complete.

Read docs/BLACK-AND-WHITEPAPER-2026-11-23.md and docs/NT-XII-IN-THE-OPEN.md for the full claim, practitioner architecture, command register, prior-art boundary, evidence, and open frontier.

---

# 14. Repository map

## 14.1 Governing and project files

| Path | Function |
|---|---|
| README.md | Public-facing nested field guide |
| DARKITH.md | Canonical state/governing record |
| AGENTS.md | Detailed executor/agent operating law; not the public introduction |
| TASKS.md | Durable project board |
| DEFICITS.json | Explicit deficit/closure/descope ledger |
| RESUME.md | Recovery and continuity instructions |
| VERSION.json | Release/update manifest |
| STALL_BUDGET.json | Time-bound stall budget |
| docs/INDEX.md | Deterministic knowledge-skill base index |
| docs/nt/NT-INDEX.md | Law corpus index |

## 14.2 Android source and assets

| Path | Function |
|---|---|
| app/src/main/AndroidManifest.xml | Package, SDK, permissions, activities/services |
| app/src/main/java/com/darkith/transliaison/ | Kotlin app and bridge source |
| app/src/main/assets/ | HTML/JS runtime surfaces packaged into the app |
| app/src/main/assets/engine/ | Child-forge engine inputs |
| omega-app/ | Separate Omega app tree and GitHub/Studio assets |

## 14.3 Build and package

| Path | Function |
|---|---|
| build.sh | Raw APK build chain |
| build&install.sh | Provision, build, and optionally install |
| tools/fetch_toolchain.sh | Toolchain provisioning |
| tools/stage_engine_inputs.sh | Stage on-device forge inputs |
| tools/pack_delivery.py | Generate delivery bundles/mirrors |
| tools/rebuild_template_dex.sh | Rebuild template DEX |
| zipalign.py | Alignment support |

## 14.4 Verification, correction, and evidence

| Path | Function |
|---|---|
| tools/ci.sh | One provider-neutral CI entry point |
| tools/autophagy.py | Defect-class registry/corrective loop |
| tools/revitalization.py | Sixteen-stage evidence-bound corrective cycle |
| tools/nt_gate.py | Noveltreatise corpus gate |
| tools/absolution_admission.py | Corpus admission |
| tools/savf_parity_gate.py | SAVF implementation parity |
| tools/savf_ui_gate.py | SAVF interface checks |
| tools/bridge_contract_audit.py | UI/native bridge contract |
| tools/secret_gate.py | Fail-closed credential-shaped string scan |
| tools/security_alert.py | Deduplicated security alert path |
| tools/board_gate.py | Durable board/evidence integrity |
| tools/board_law_gate.py | Priority/law citation integrity |
| tools/omega_deficit.py | Project progress-deficit computation |
| tools/ci_receipts.py | Run receipt emission/verification |
| proof/ | Logs, claims, reconciliation, receipts, and evidence |

## 14.5 Tool families

| Family | Representative tools | Purpose |
|---|---|---|
| Build/delivery | build.sh, delivery_gate.sh, fork_integrity_gate.sh | Reproducible build and delivery admission |
| Source integrity | syntax_gate.py, kt_comment_scan.py, comment_audit.py | Syntax/comment defects |
| Security | secret_gate.py, security_alert.py | Credential detection and notification |
| Contract/runtime | bridge_contract_audit.py, runtime_gate.py, install_gate.py | Boundary and artifact behavior |
| Knowledge/law | kb_index.py, nt_gate.py, law_gate.py, blueprint_gate.py | Index and governing-law admission |
| Drift/convergence | drift_gate.py, divergence_gate.py, convergence_gate.py, sync.sh | Tree and branch consistency |
| Correction | autophagy.py, revitalization.py, praxis_propagate.py | Defect-class repair and durable directives |
| Discovery | fracture_scout.py, darkbot.py | Unresolved problems and dependency drift |
| Accounting | mint_ledger.py, omega_deficit.py, run_feed.py | Witness, project deficit, run receipts |
| App tests | test_device_apps.js, test_files.js, test_media_player.js, test_omega_reader.js | Browser/app behavior |

## 14.6 Knowledge corpus

docs/INDEX.md is generated from tracked bytes by tools/kb_index.py. It is not a hand-authored second source of truth.

Major documents:

- docs/ARCHITECTURE-OMEGA.md — local assistant/polyglot terminal design, current stubs, and constraints.
- docs/BLACK-AND-WHITEPAPER-2026-11-23.md — three-register contribution/minting thesis.
- docs/FAILURE-MODE-LEDGER.md — failure, cause, guard, and proof.
- docs/GITHUB-STUDIO-MANUAL.md — GitHub app/web action map and operator workflow.
- docs/SECURITY_REMEDIATION.md — credential leak class, guard, and remediation boundary.
- docs/NT-XII-IN-THE-OPEN.md — public evidence, prior art, and open frontier.
- docs/evidence/SECTOR-PAIN-LEDGER.md — sector pain observations and primary-source evidence.
- docs/evidence/NODAL-ZIP-VS-OURS.md — measured comparison of the earlier Nodal package and current implementation.
- docs/RECOVERY_MANIFEST.md — recovery provenance for reconstructed files.
- docs/UPDATES.md — integrated client-coupling update record.

---

# 15. Security, privacy, portability, and licensing

## 15.1 Secrets

Never commit tokens, private keys, keystores, signing credentials, or credential-bearing remote URLs. The repository documents a committed-credential failure and remediation; the secret gate scans tracked/staged content for credential-shaped patterns.

A credential that entered Git history must be treated as exposed. Removing it from the current file does not revoke it; rotate it at the provider.

## 15.2 Local data and permissions

The project aims for local/offline capability, but the Android manifest requests network and device permissions for specific functions. Offline-first does not mean the app never requests network permission. Review the manifest and Android permission settings to determine what is granted and what a given surface uses.

## 15.3 Executable placement

Android 10+ restricts executing files from app-writable locations for apps targeting modern SDKs. A binary copied into app storage or shared storage is not automatically executable. Any shipped runtime must prove its actual execution path.

## 15.4 Portability

Scripts aim to be provider-neutral and usable in Termux or ordinary development environments where the required runtime/toolchain exists. Portability does not mean every command runs everywhere without dependencies. Each command's prerequisites and skips matter.

## 15.5 License

The repository currently has no root LICENSE file. Public visibility does not grant permission to reuse, modify, or redistribute the work. All rights remain reserved unless an explicit license is added.

---

# 16. The nested FAQ

## 16.1 What is Darkith?

Darkith is an Android/offline software forge and a verification-driven project. The app provides a local interface; the repository contains the source, build chain, tools, laws, tests, and evidence that govern it.

### Is it just an Android app?
No. The APK is one delivery surface. The repository also contains standalone web tools, build/correction apparatus, a knowledge corpus, and the economic Omega specification.

### Is it a company, token, or finished economy?
This repository does not establish that. The sovereign-economy objective is specified and researched, but a production economy and independently measured zero extraction are not claimed as implemented.

## 16.2 Why the philosophy?

The doctrine is expressed through the Signature Prime and its governing principles: sovereignty, evidence, correction, and refusal to counterfeit completion.

### Is the philosophy just branding?
It is intended to be operational. Each principle should have corresponding implementation, gate, or explicit open boundary. A principle without enforcement is incomplete.

## 16.3 What can I run today?

You can inspect the Android source, run the raw build path when its toolchain is available, run repository checks, use standalone HTML tools, and run Python verification/accounting utilities with their prerequisites.

### Can I build without Gradle?
Yes. The supported Android build uses build.sh and build&install.sh. Gradle is not invoked.

### Can I build on Android itself?
The scripts are designed for Termux and stage the required toolchain/engine inputs. A physical-device build is distinct evidence from a remote build.

### Can I install over my existing Darkith APK?
Only if package identity and signing key are compatible. A different signer can cause Android to reject the update. Check the installed package and signer on the device.

## 16.4 What is SAVF?

SAVF is the audit/correction engine family. It scans source and claims, checks reachability and contracts, records evidence, and supports correction/verification workflows.

### Does a hash prove truth?
No. A hash proves byte identity relative to a known digest. It does not prove accuracy, usefulness, novelty, or acceptance by reality.

### Can SAVF prove any claim?
Only within the claim's actual evidence/reproducer boundary. External referents must still be grounded. A test that rejects every case proves nothing; honest controls must survive the same test.

## 16.5 What does PASS mean?

PASS means the named check ran and met its acceptance condition under the recorded environment.

### Does CI PASS mean Omega is complete?
No. CI covers gates wired into that run. It cannot prove external economic outcomes, universal compatibility, every device behavior, or every philosophical claim.

### Is SKIP a pass?
No. SKIP means the check did not run, often because a runtime or artifact was unavailable. It must remain visible.

## 16.6 Project accounting vs. economic accounting?

Project accounting measures registered work: named, open, completed, closed, or descoped.

Economic accounting measures value: what is produced, extracted, retained, who controls it, and whether it can circulate.

### Why use similar symbols?
The corpus uses shared invariant vocabulary, but referents must remain separated. The project deficit tool reads task/deficit records; it does not read a community economy.

## 16.7 What is Omega?

Omega is the convergence condition in which capabilities, accounting, governance, and evidence serve one end without contradiction or duplicated machinery.

### Can a document declare Omega?
No. A document can specify acceptance conditions. Omega must be demonstrated by capabilities and independent evidence satisfying those conditions.

## 16.8 What is the local assistant/terminal status?

The repository contains terminal/assistant surfaces and an architecture for native, Wasm/WASI, and optional PRoot execution tiers. The architecture also records current host stubs and Android execution restrictions.

### Does the terminal support every language?
Not by virtue of its UI. A language is supported only when its runtime/module is present and its execution path is verified.

### Is the local assistant equivalent to a frontier model?
No such equivalence is claimed. The design targets a private, offline, device-bounded assistant integrated with the forge. Model size, speed, memory, and reasoning capability are real constraints.

## 16.9 What is ClearanceLoop?

ClearanceLoop is a debt-clearance ratchet. It measures whether debt clears over time, prevents regressions from silently raising tolerance, and permits only bounded, reasoned, expiring waivers.

### Why not a static threshold?
A static threshold can hide stagnation or allow the baseline to creep upward. ClearanceLoop treats clearance rate and regression as part of the health signal.

## 16.10 What is Fracture Scout?

It searches configured structured sources for real unresolved problems, using boolean query parsing and ranking to reduce noise. A result is not automatically a validated fracture or task.

### Does it search the dark web?
No. Its documented scope is structured research, defect, standards, and practitioner sources—not Tor or .onion marketplaces.

## 16.11 What is Nodal?

Nodal is a receipt/coordination substrate with a closed verdict vocabulary, hash-chained append-only ledger, and engine for firing/reconciliation.

### Is it distributed consensus?
No. The current implementation does not establish cross-machine consensus or arbitrary-code sandboxing.

## 16.12 What is Homekeeper?

Homekeeper is the executable model of the repository invariant: a unit has defined structure, claim record, admission/validation behavior, capability delta, and Omega calculation. It also generates the four-register reader.

## 16.13 Why so many gates and documents?

Because the project's failure history showed that a correct component can still fail when its caller, timer, generator, integration, or evidence chain is missing. Gates make those failure classes visible and repeatable.

### Isn't that bureaucracy?
It becomes bureaucracy if it duplicates work or prevents no real defect. Every layer must serve the Signature Prime. Duplicated registers, dead gates, stale mirrors, or documentation that does not help a reader are defects to remove—not sacred paperwork.

## 16.14 How can I contribute?

Read the relevant law and source, reproduce current behavior, and identify the smallest capability-level gap. A useful contribution includes:

1. exact observed behavior;
2. source and conditions;
3. governing invariant;
4. root-cause correction;
5. prevention gate or regression test;
6. evidence from the corrected tree.

Do not claim a capability is complete when only its interface or specification exists.

## 16.15 How do I report a defect?

Provide exact file/commit, device/runtime conditions, reproduction steps, expected and actual results, and relevant logs. Reproducible defects can be classified and prevented.

## 16.16 Can I use or redistribute Darkith?

The repository is public but has no explicit root license. Do not assume public access grants reuse or redistribution rights. Contact the project owner or wait for a license.

## 16.17 Where is canonical truth?

- Current repository state: tracked bytes on the active branch.
- Governing state: DARKITH.md.
- Detailed executor rules: AGENTS.md.
- Knowledge index: docs/INDEX.md.
- Law corpus: docs/nt/NT-INDEX.md.
- Project work: TASKS.md and DEFICITS.json.
- Verification: the actual tools/ci.sh run and its evidence.
- Release/package version: VERSION.json and Android manifest, checked for agreement.

If this README disagrees with source or executable gate, the README is defective and must be corrected. It is a bridge, not a superior source of truth.

---

# 17. Operational mini-wiki

This section is the practical answer layer. It is organized by the questions a reader, user, tester, or contributor is likely to ask after understanding the purpose and architecture. The governing rules remain in the sections above; this section explains how to act within them.

## 17.1 I just arrived. What should I do first?

1. Read the [Signature Prime](#signature-prime--what-this-makes-impossible).
2. Read [What Darkith is](#0-start-here) and [the governing principles](#2-the-governing-principles).
3. If you want to run it, follow [Build, install, and run](#9-build-install-and-run).
4. If you want to judge whether a claim is real, follow [Verification and evidence](#10-verification-and-evidence).
5. If you want the complete technical argument, follow the [reading path](#20-reading-path-conviction-to-evidence).

Do not begin by treating a feature name, roadmap entry, or architecture diagram as proof of implementation.

## 17.2 What exactly do the build flags do?

| Command | Behavior |
|---|---|
| `bash 'build&install.sh'` | Provision the raw toolchain, stage child-forge inputs when available, build the APK, and hand it to the Android installer when available |
| `bash 'build&install.sh' --build` | Provision and build; do not install |
| `bash 'build&install.sh' --no-install` | Alias for `--build` |
| `bash 'build&install.sh' --verify` | Provision and build; install nothing |
| `bash build.sh . Darkith com.darkith.transliaison` | Run the raw build directly |

The ampersand in the script filename is a shell metacharacter. Quote the filename exactly as shown. Running `bash build&install.sh` unquoted does not invoke the intended script.

## 17.3 Where does the APK go, and how do I install it?

The default output is `app-signed.apk` in the repository root.

In install mode, the wrapper uses `termux-open` when available, or a package-manager path when available. Android may show an installer confirmation or require permission to install unknown apps. The script handing off the APK is not the same as Android confirming installation.

## 17.4 Why might Android reject an update?

Android update compatibility depends on package identity and signing identity.

- The package name must match the installed app.
- The new APK must be signed with a compatible signing key.
- A different signer may require uninstalling the old package before installing the new one; uninstalling can erase app-private data.
- A filename or matching versionName cannot override signer mismatch.

Check the installed package on the device before changing or removing it. Do not assume a remote build environment knows the installed app's signer.

## 17.5 How do I identify the installed version?

Use the installed package metadata:

```sh
pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'
```

Inspect a local APK:

```sh
aapt dump badging app-signed.apk | grep -E '^package'
```

The current release manifest is `VERSION.json`; the Android manifest declares package/build metadata. The repository's version and delivery gates are responsible for detecting disagreement. A README version statement is not a substitute for inspecting the actual installed artifact.

## 17.6 What is the difference between the repository and the installed app?

The repository is the full source and governing apparatus: Kotlin, HTML/JavaScript, build scripts, audit tools, law corpus, tests, and proof records.

The APK is one packaged delivery of selected Android source and runtime assets. It does not contain every repository document, research file, test, or development tool. Conversely, a root-level HTML tool may be inspectable in the repository without being exposed as an app screen.

## 17.7 Which HTML file should I edit?

Use the source and mirror rule in [the offline studio section](#7-the-offline-studio-and-tools):

- Root-level HTML files are development/inspection surfaces.
- Files under `app/src/main/assets/` are packaged runtime assets.
- Where the repository declares a mirror, update the canonical source and propagate the change through the repository's defined process.
- Do not independently hand-edit both copies; that creates two authorities.
- Run the relevant parity, tree, and CI gates after propagation.

The exact canonical/mirror relationship is determined by the repository's index, packaging rules, and parity gates—not by whichever file is easier to open.

## 17.8 Which app or surface should I open?

| I want to… | Surface |
|---|---|
| Enter the Homekeeper environment | `darkith home forge.html` / packaged Homekeeper |
| Inspect code and audit work | `darkith code studio.html` |
| Use the lightweight audit interface | `darkith-inscriber.html` |
| Open the full SAVF interface | `savf.html` |
| Work with the terminal/local-assistant interface | `d-arkith-omega.html` or `omega.html` |
| Explore the standalone device-app interfaces | Apps, Camera, Clock, Contacts, Files, Media Player, Messages, Phone |
| Inspect the repository's four-register presentation | `omega-reader.html` |
| Review the master Omega specification | `darkith-omega-master.html` |
| Create icons | `icon_forge.html` |
| Inspect debt-clearance behavior | `clearanceloop.html` |

A listed surface is a navigable interface or artifact. It does not imply every control is connected to a complete native capability. For behavior claims, inspect the bridge, implementation, and relevant tests.

## 17.9 Does offline-first mean no network or no permissions?

No. Offline-first describes the intended local availability and control model. The manifest still declares network and device permissions for particular capabilities.

- A manifest declaration means the app requests or may use a permission; it does not mean the user granted it.
- A permission grant does not prove a feature works on every device.
- Some provisioning and dependency downloads require network access on first use.
- Cached toolchains may allow later build steps without downloading again.
- Inspect the manifest and Android's app-permission settings for the actual package on your device.

Do not describe Darkith as network-free, permission-free, or fully offline in every workflow unless the specific workflow has been tested under that condition.

## 17.10 What does the terminal actually support?

A terminal interface is not a runtime inventory. A language or command is supported only when the corresponding executable/runtime is present and the execution path works under Android's restrictions.

The architecture distinguishes native, Wasm/WASI, and optional PRoot tiers. These are not all automatically available because the interface mentions them. See [the terminal and assistant boundary](#8-local-terminal-and-assistant-design-vs-implementation).

## 17.11 What is the local assistant intended to provide?

The intended local assistant is private, device-bounded, and integrated with the forge. Its potential advantages are offline availability and local control.

It is not claimed to equal a frontier cloud model. Context length, model size, memory, latency, and device thermals constrain it. A chat panel or model-selection control is not proof that a production model runtime is installed.

## 17.12 How do I use SAVF without guessing its CLI?

Start with the CLI's own help:

```sh
python3 savf.py --help
```

Use the options exposed by the checked-out file. Then run the appropriate self-test or repository gate and preserve the output. The browser engine and Python engine have separate parity/UI checks; passing one does not automatically prove the other.

SAVF's verdict is bounded by the checks and evidence it actually performs. A digest establishes byte identity, not truth. A source scan cannot establish an external fact merely because the fact appears in a comment or manifest.

## 17.13 How do I interpret ClearanceLoop?

ClearanceLoop tracks whether a debt class is being cleared rather than merely remaining below a static threshold.

- A decrease establishes a lower high-water mark.
- A regression above that mark is treated as new debt.
- Stasis over the defined window triggers degradation.
- A waiver must be recorded, justified, and expire; it does not permanently reset the ratchet.

Use the implementation and test output for the configured window and thresholds. Do not infer a specific current debt value from the general law.

## 17.14 What does Fracture Scout return?

It returns ranked candidates from configured sources and query expressions. A candidate is not automatically:

- a verified real-world need;
- novel prior art;
- a task authorized for implementation;
- a bounty or payment;
- a solved problem.

Inspect the original source, confirm that the problem remains unresolved, identify a bounded capability, and apply the project's admission rules.

## 17.15 What can I trust from Nodal?

Nodal's current documented role is a receipt and coordination substrate: closed verdict vocabulary, hash-chained append-only records, and ordered firing/reconciliation.

A hash chain can make later alteration detectable relative to retained records. It does not by itself establish truth, distributed consensus, decentralized governance, or an arbitrary-code sandbox.

## 17.16 What does Homekeeper's four-core invariant test?

The invariant is conjunctive: relational, structural, functional, and authority conditions must all hold. A unit cannot compensate for a missing condition by being strong in another.

The model evaluates a bounded repository unit and its claim/admission behavior. It is not a universal proof that every file, economy, or institution is sovereign.

## 17.17 What is the minting/witness idea—and what is it not?

The contribution thesis centers on reproducible closure: a bounded command and expected result that another party can rerun without trusting the issuer.

The current ledger is described as single-writer and tamper-evident. It is not a blockchain or global consensus system. A textual difference does not prove semantic novelty, and a reproducible command does not automatically prove that its real-world premise is true.

## 17.18 How do I contribute a meaningful correction?

A useful contribution should answer all of these before it is called complete:

1. What capability is defective?
2. What exact behavior was observed?
3. What source, environment, and conditions produced it?
4. Which invariant governs the defect?
5. What is the root cause—not merely the visible symptom?
6. What correction changes the defective class?
7. What detector, prevention gate, or regression test makes recurrence inadmissible?
8. What evidence proves the corrected behavior?
9. What remains skipped, partial, or outside the test boundary?

Do not submit a success message in place of the artifact or evidence. Do not mark a specification as an implementation.

## 17.19 What is the correct way to report a defect?

Include:

- repository commit or exact source revision;
- exact file and relevant line/function;
- device, Android version, runtime, and toolchain when relevant;
- minimal reproduction steps;
- expected result and actual result;
- complete relevant log, not only the final error line;
- whether the check was PASS, FAIL, SKIP, or not run.

A report that cannot be reproduced may still be useful, but it must be labeled as unconfirmed rather than promoted to a verified defect.

## 17.20 Where should I look for a specific answer?

| Question | Canonical starting point |
|---|---|
| What is the project state? | `DARKITH.md` |
| What is the current work/deficit? | `TASKS.md`, `DEFICITS.json`, and `tools/omega_deficit.py` |
| What is the app package/version? | `AndroidManifest.xml`, `VERSION.json`, installed package metadata |
| What governs a build? | `build.sh`, `build&install.sh`, NT IX |
| What checks ran? | Actual `tools/ci.sh` output and `proof/ci_last.log` |
| What laws govern a subsystem? | `docs/nt/NT-INDEX.md` and the relevant NT file |
| What is known about a failure class? | `docs/FAILURE-MODE-LEDGER.md` and the relevant gate |
| What is the local assistant/terminal design? | `docs/ARCHITECTURE-OMEGA.md` |
| What is the contribution/witness thesis? | `docs/BLACK-AND-WHITEPAPER-2026-11-23.md` and `docs/NT-XII-IN-THE-OPEN.md` |
| What is the recovery procedure? | `RESUME.md` and `docs/RECOVERY_MANIFEST.md` |

---

# 18. Troubleshooting and recovery

Troubleshooting follows the same evidence rule as the rest of Darkith: capture the actual failure, identify the responsible layer, and correct the cause. Do not infer success from a script starting or from an artifact filename existing.

## 18.1 The build script does not start

If the script filename contains `&`, quote it:

```sh
bash 'build&install.sh' --build
```

If the shell reports a syntax error or starts a background process, the filename was likely passed unquoted.

## 18.2 Toolchain provisioning fails

1. Read the complete provisioning output.
2. Check whether the required network download is available or a cached toolchain is present.
3. Inspect `tools/fetch_toolchain.sh` for the exact component and destination.
4. Confirm that the downloaded archive is valid and the expected executable exists.
5. Re-run the build only after the failing dependency is corrected.

Do not replace a missing tool with a fake executable or a stub that returns success.

## 18.3 Kotlin compilation cannot find Java or the Android framework

Check the actual toolchain environment:

- Is a JDK available and executable?
- Does `JAVA_HOME` point to that JDK?
- Is `kotlinc` available or selected through `KOTLINC`?
- Is the correct Android framework `android.jar` staged?
- Are required libraries present in the build classpath?

The raw build and provisioning scripts are the source for exact paths. A compilation error is not resolved by changing the README's claimed SDK level.

## 18.4 The build completes but no APK exists

Confirm the working directory and output path. The default wrapper expects `app-signed.apk` in the repository root after `build.sh` succeeds.

Check the full build log for the first failing stage: resource compilation, Kotlin, DEX, packaging, alignment, or signing. Later “done” text cannot override a missing artifact or a failed stage.

## 18.5 Android says the package cannot be installed

Check, in order:

1. package name matches the installed app;
2. APK signature is compatible with the installed signer;
3. Android allows installation from the current source;
4. the APK is valid and aligned;
5. device SDK and manifest constraints are satisfied.

If signer identity differs, do not uninstall reflexively. Uninstalling may remove app-private data. Confirm backup and installation consequences first.

## 18.6 The app installs but crashes at launch

A successful package install proves only that Android accepted the package. It does not prove runtime initialization or every bridge call works.

Capture the device crash log, identify the first causal exception, and check the relevant DEX linkage, manifest, native bridge, and packaged asset. Re-run the app-specific gate and physical-device test after correction. Do not diagnose a crash from the last line of a truncated log.

## 18.7 A button or web surface does nothing

Check the complete interaction path:

1. the HTML control has an actual handler;
2. the handler calls the intended bridge/API;
3. the bridge method exists and is exposed;
4. Android permission or device capability is available;
5. the return/error path reaches the UI;
6. the behavior is covered by an applicable test.

The bridge contract audit detects some boundary mismatches; it cannot replace testing the actual device behavior.

## 18.8 A terminal command says it started but produces no output

A start-like status is not proof of process execution. Check whether the selected runtime exists, whether Android permits execution from its location, whether output is streamed, and whether the process exit code is propagated.

The architecture document explicitly distinguishes current terminal stubs from intended runtime tiers. Treat unverified execution as unverified.

## 18.9 CI is green but a capability is still missing

CI only evaluates the gates wired into that run. It cannot certify a capability whose implementation is absent, a check that was skipped, or an external economic outcome.

Inspect the individual gate list and verdicts. Then inspect the capability's own implementation and admission evidence. If the relevant gate is missing, the correct finding is a verification gap—not an assumed pass.

## 18.10 CI reports SKIP

A SKIP means the check did not run because its required runtime, dependency, or artifact was unavailable. It is not a pass and must not be counted as one.

Install/provision the missing prerequisite and rerun, or explicitly preserve the skip as an unresolved verification boundary.

## 18.11 The root HTML and packaged HTML disagree

Do not choose whichever copy looks newer. Identify the canonical source and declared mirror, propagate the change through the repository's mechanism, and run the relevant parity/index gate.

A mismatch is a source-of-truth defect. Editing both copies independently is not a durable fix.

## 18.12 The version shown in the app differs from the APK or manifest

Inspect the actual installed package, APK metadata, Android manifest, and `VERSION.json`. Determine which artifact was installed and whether generated delivery metadata is stale.

Do not “fix” a mismatch by changing only the README or displayed label. Correct the canonical version source and regenerate/verify all derived surfaces.

## 18.13 The app requests a permission I did not expect

Inspect `app/src/main/AndroidManifest.xml` and Android's per-app permission settings. A declared permission may support a surface that is not currently used; a granted permission does not prove active use.

If a permission is unnecessary for a capability, the correct correction is to remove or gate the request and verify that the dependent feature still behaves honestly.

## 18.14 I need to recover after a failed or interrupted session

Use `RESUME.md` for the current continuation instructions and `docs/RECOVERY_MANIFEST.md` for reconstruction provenance. Reopen the exact source and proof artifacts; do not rely on a remembered summary.

Before resuming writes, identify the current branch, commit, working-tree state, and any concurrent edits. A previously fetched blob SHA is not valid after the file changes.

## 18.15 I found a secret in the repository

Treat it as compromised if it was committed or pushed.

1. Revoke or rotate the credential at its issuer.
2. Remove it from the current tracked source.
3. Follow the repository's security remediation procedure for history exposure.
4. Run the secret gate and preserve its result.
5. Add or strengthen the detector/prevention gate that missed the class.

Deleting the current line does not revoke a credential or erase copies from forks, caches, backups, and Git history.

---

# 19. Glossary and concept map

| Term | Meaning in Darkith | Do not confuse it with |
|---|---|---|
| Signature Prime | The governing end: make false completion, false verification, false accounting, silent extraction, and related corruption inadmissible | A slogan or decorative opening |
| Sovereignty | Operational control over tools, understanding, correction, and retained value | Merely owning a device or using local software |
| Omega | The convergence condition for capability, accounting, governance, and evidence | A version suffix or self-awarded status |
| Absolution | A defined closure condition with evidence and explicit boundaries | A project reaching zero by deleting unresolved scope |
| Project deficit | Remaining registered work under the project ledger | Economic extraction or community wealth |
| Economic extraction | Value leaving the community's control under the economic model | Project debt or a CI failure count |
| SAVF | Verification and correction engine family | A universal truth oracle |
| NT / Noveltreatise | The governing technical/philosophical law corpus | A set of optional essays |
| ASE | Autophagic Sovereign Economy: the economic architecture and objective | A production economy already proven operational |
| Homekeeper | Executable repository model and four-core invariant apparatus | A universal proof of sovereignty |
| A∧B∧C∧D | Conjunctive relational, structural, functional, and authority conditions | A score where one strong condition compensates for another missing |
| ClearanceLoop | Debt-clearance ratchet that tracks progress, regression, stasis, and bounded waiver | A static threshold or permanent waiver |
| Fracture Scout | Candidate discovery/ranking for unresolved problems from configured sources | Automatic novelty proof, bounty, or task authorization |
| Darkbot | Provider-neutral dependency watcher and artifact-verification utility | An autonomous authority to change every dependency without review |
| Nodal | Receipt/coordination substrate with hash-chained ledger and ordered reconciliation | Blockchain, cross-machine consensus, or arbitrary-code sandbox |
| Homekeeper four-register reader | Generated presentation of repository units through four distinct registers | Four competing canonical repositories |
| PASS | Named check ran and met its condition | Universal correctness |
| FAIL | Named check ran and failed its condition | A vague warning |
| SKIP | Check did not run | PASS or “close enough” |
| INACTIVE | Capability/check is not active in that context | Healthy or verified |
| Specified | Design or rule is stated | Implemented |
| Implemented | Executable capability exists | Verified under all conditions |
| Verified | Evidence supports a bounded claim under recorded conditions | Universal truth |
| Qualified | Capability meets explicit admission criteria | Merely present |
| Descoped | Capability intentionally excluded with a recorded boundary | Capability completed |
| Receipt | Structured record of a bounded event/result | Proof that the real-world premise is true |
| Hash chain | Tamper-evident ordering/byte relationship among retained records | Distributed consensus or truth |
| Canonical source | The authoritative source from which declared copies are derived | Any file with a similar name |
| Mirror | A generated or maintained copy whose parity is checked | A second authority |
| Gate | Executable admission/check enforcing a law or invariant | Documentation that merely describes a law |
| Defect class | Reusable category of failure corrected at its cause and guarded against recurrence | One isolated symptom |
| W^X | Write/execute separation principle relevant to Android runtime placement | Permission to execute arbitrary app-writable files |
| Raw build chain | Direct non-Gradle APK build sequence | A claim that the build has no dependencies |
| Child forge | On-device build path carried by the host app | Automatically proven by building the host APK |

## 19.1 The concept map in one line

**Signature Prime → governing invariants → capability-level status → implementation → gate and reproducer → evidence → correction/prevention → project closure → independently demonstrated Omega.**

Economic sovereignty is measured at its own capability boundary; it cannot be inferred from project closure.

---

# 20. Reading path: conviction to evidence

For the complete argument, follow this sequence:

1. **README** — public purpose, architecture, and capability boundaries.
2. **DARKITH.md** — canonical state and governing record.
3. **docs/nt/NT-INDEX.md** — law corpus and enforcement map.
4. **NT XI and NT XII** — Autophagic Sovereign Economy and terminal convergence.
5. **NT XIII / OFIF** — field-invariant fixtures, prior-art verdicts, derivation, and falsifiers.
6. **Black & Whitepaper** — plain/practitioner/executor registers for reproducible contribution and minting.
7. **NT XII in the Open** — public evidence and honest frontier.
8. **Architecture Omega** — local assistant/terminal design and current boundaries.
9. **Failure Mode Ledger** — failures, root causes, guards, and proofs.
10. **tools/ci.sh** — executable verification entry point.

---

# 21. The final boundary

Darkith does not ask to be trusted because it declares itself sovereign.

It must earn trust by making its workings inspectable, its limits visible, its claims reproducible, and its corrections accountable.

The app is a tool. The repository is the apparatus. The law is the constraint. The evidence is the witness. The human purpose is the end.

No README, register, test suite, or machine may declare that destination achieved on its own.

**Only demonstrated capability and independent evidence can do that.**
