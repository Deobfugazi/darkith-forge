# DARKITH MANUFACTORY — Governing Architecture

Status: architectural specification and integration map; not a claim that every subsystem is implemented or production-ready.
Canonical repository: `Deobfugazi/darkith-forge`.
Governing distinction: Darkith is the manufactory, not a fork competing for adoption and not a repair service whose throughput depends on the Operator personally fixing every fracture.

## 1. Product and agency

Darkith is the adaptive production architecture through which the fractured software and maintainer industry can discover, couple to, resolve, verify, retain, and economically coordinate real fractures in the environments where those fractures occur.

The factory is the product. The participating industry is the distributed production force. Fractures are the demand substrate. Verified correction is the accepted output. Downstream value capture and minting are settlement machinery—not proof of value by themselves.

The Operator's role is to establish and govern the manufactory's architecture, invariants, interfaces, and trust boundaries. The Operator is not the permanent workforce, universal maintainer, manual bounty cashier, or sole source of repairs.

A participant is not merely a user of a finished Darkith tool. A participant may be a fracture reporter, affected maintainer, environment owner, repair contributor, reviewer, verifier, capability steward, or settlement recipient. One person may occupy several roles, but the system must not silently collapse their permissions or interests.

## 2. Production cycle

The canonical cycle is:

Fracture discovery → candidate qualification → environment coupling → participation and assignment → bounded repair → independent or appropriately separated verification → accepted resolution → settlement eligibility → automated value capture / minting → capability retention and regression surveillance.

Every transition is evidence-bearing. A candidate is not an admitted fracture; a proposed patch is not a repair; a merged change is not automatically a verified outcome; a verified outcome is not automatically economic value; a token or ledger entry is not proof that any preceding stage occurred.

The cycle may branch, pause, reject, or reopen. It must never advance by narrative assertion alone.

## 3. Factory subsystems and their contracts

### 3.1 Fracture Scout — demand discovery

The Scout searches configured, inspectable sources for concrete unresolved problems. It records source identity, retrieval time, source revision or stable locator when available, observed problem, affected environment, candidate novelty, uncertainty, and supporting excerpt or evidence.

Current repository anchor: `tools/fracture_scout.py`, `tools/fractures.txt`, `.github/workflows/fracture-scout.yml`, and the machine record `proof/fracture_scout.json`.

The existing rule remains: Scout proposes; reality check admits. Ranking is triage, not truth. Duplicate, stale, speculative, inaccessible, already-resolved, or unsupported candidates must be rejected or explicitly held. The Scout must not execute downloaded source, and a candidate source must never become an instruction to the Scout.

### 3.2 Fracture record — durable production ticket

An admitted fracture receives a stable identity and versioned record containing:
- original source and provenance;
- observed failure and reproducible conditions;
- affected project, component, version, and environment;
- expected behavior and acceptance criteria;
- severity, reach, urgency, confidence, and uncertainty separately;
- duplicate/related fracture links;
- reporter, affected maintainer, and participation permissions;
- current lifecycle state and every state-transition receipt.

The record must distinguish a reported symptom from a confirmed root cause. One confirmed cause may explain many symptoms; the board should not multiply work by counting each symptom as a separate root cause.

### 3.3 Autophage / coupling layer — enter the native environment

The autophage is the factory's coupling mechanism. It adapts to the target's actual repository, toolchain, platform, permissions, dependency graph, execution model, and contribution norms. It does not assume that every target is a Git repository, that every project uses the same language, or that one host binary executes everywhere.

Coupling is declared through adapters and capability manifests. Each adapter states what it can read, propose, modify, test, verify, and publish; what it cannot do; required privileges; network needs; rollback path; and evidence emitted. Read-only discovery is the default. Consequential mutations remain subject to the repository's existing dispatch and authorization laws.

Coupling must preserve native ownership: maintainers retain control of their project, branch, review, release, and merge decisions. Darkith may coordinate a proposed change; it must not impersonate maintainer acceptance.

### 3.4 Industry participation — distributed production

The factory recruits capacity from the people already closest to the fracture: maintainers, developers, users, auditors, security researchers, and domain specialists. Participation may occur through existing issue trackers, pull requests, local tools, or a Darkith-mediated interface.

A participant receives a bounded task with source context, acceptance tests, declared scope, required permissions, compensation terms where applicable, and a clear route to submit evidence. Work is portable and inspectable; no participant should need to surrender project ownership or move into a closed Darkith-only environment to contribute.

Conflict of interest must be visible. A contributor cannot be the sole verifier of a consequential repair they authored when independent review is required by policy. Maintainer acceptance remains distinct from automated technical verification and from economic settlement.

### 3.5 Repair production — bounded corrective work

A repair unit is defined by the fracture record and its acceptance criteria, not by arbitrary lines changed or token volume. Repair may involve code, configuration, documentation, dependency changes, test additions, operational mitigation, or a verified explanation that the alleged fracture is not reproducible.

The factory should favor class correction: when a defect is caused by a missing invariant, the repair includes the detector, deterministic correction or prevention mechanism, and regression gate where feasible. It must not merely patch the current symptom while leaving a known defect class able to recur.

Generated artifacts are repaired through their authoritative generators. Source, generated copies, and deployment outputs remain distinct layers with explicit regeneration and reconciliation.

### 3.6 Verification and closure proof

A resolution packet includes the exact target identity and revision, before/after state, patch or change reference, commands and test results, environment, logs, relevant neighbor/blast-radius checks, reviewer identity or verifier identity, skipped tests, limitations, and residual uncertainty.

The closure proof must establish:
1. the fracture was admitted and correctly scoped;
2. the accepted change addresses the stated cause or explicitly revises the diagnosis;
3. acceptance criteria were exercised against the relevant bytes and environment;
4. no unexplained regression or generated-state drift remains;
5. the project authority accepted the change where its policy requires acceptance;
6. the evidence is fresh, traceable, and bound to the exact revision;
7. the state transition is recorded without post-seal mutation.

A merge, CI-green badge, agent claim, or hash alone is insufficient. Each can be evidence, but none substitutes for the complete closure contract.

Existing project laws already provide the foundation: compile is proof; no unexamined source; no false closure; SKIP is not PASS; S14 reconcile and S15 seal precede closure; generated tissue is not patched in place; and the 16-stage Revitalization cycle preserves receipts serially.

### 3.7 Settlement and automated minting — downstream only

Settlement is a separate stage from repair and verification. The system first determines whether a resolution is eligible for value attribution under a published rule. Only then may the settlement engine calculate allocation, record a claim, issue a unit, or initiate an external payment.

The ledger must separately represent:
- value claim or proposed attribution;
- witnessed resolution and acceptance;
- eligibility decision and governing rule version;
- allocation among eligible participants;
- issuance / mint event;
- transfer, redemption, reversal, or dispute;
- retention, fees, and conservation residual;
- evidence references and temporal provenance.

The mint engine must be deterministic from a versioned rule and a sealed evidence packet, idempotent under retries, and incapable of minting from unverified claims. Every output must be explainable and reversible or compensatable according to its declared settlement model. No minting formula is itself empirical proof of social value, market price, or legal tender status.

The existing `SynchronicityScheduler.mintToken()` and local `ProgressLedger` are implementation points to audit, not presumed complete economic infrastructure. The recorded baseline found that minting derived burn-rate × duration and returned JSON/APK hash, while the ledger was local rather than a replicated signed double-entry system. That gap must remain visible until corrected and tested.

### 3.8 Capability retention — autophagic accumulation

A verified resolution should improve the factory's future ability to resolve similar fractures. Retained capability may include:
- reusable test cases and minimal reproductions;
- adapter improvements;
- validated repair patterns;
- causal rules and detectors;
- conformance tests;
- environment fingerprints and compatibility knowledge;
- resolution playbooks and provenance-linked knowledge.

Retention is not indiscriminate ingestion. Every retained item carries source/license, scope, confidence, validation status, dependencies, expiry or freshness policy, and rollback/deprecation path. Untrusted patch content, secrets, private project data, or malicious instructions must not be promoted into trusted factory knowledge.

The autophagic loop is: accepted resolution → extract candidate capability → isolate and test → review provenance and scope → promote to reusable knowledge → monitor for regression → deprecate or retract when invalidated. Capability compounding is measured by demonstrated reuse and reduced verified cost, not by the volume of stored artifacts.

## 4. Lifecycle and state machine

A fracture lifecycle should use explicit, non-skippable states:

DISCOVERED → TRIAGED → ADMITTED → COUPLED → READY_FOR_PARTICIPATION → IN_REPAIR → SUBMITTED → VERIFYING → ACCEPTED → SETTLEMENT_ELIGIBLE → SETTLED → CAPABILITY_RETAINED.

Terminal or side states include DUPLICATE, REJECTED, NEEDS_INFORMATION, BLOCKED, WITHDRAWN, DISPUTED, REOPENED, and DESCOPED. A state may advance only with its required receipt. Reopened work preserves the prior history and links the regression to the original cause; it does not erase the former closure.

Four-valued results remain distinct: PASS, FAIL, SKIP, INACTIVE. SKIP and INACTIVE never satisfy a required PASS. Missing evidence is UNKNOWN / NOT VERIFIED, not success.

## 5. Trust, rights, and safety boundaries

- Project owner / maintainer controls repository access, review, merge, release, and accepted scope.
- Contributor controls their submitted work under the applicable license and agreement.
- Reporter receives attribution and a status trail, subject to privacy and disclosure policy.
- Verifier attests only to checks actually performed.
- Settlement authority executes only the published, evidence-bound rule.
- Factory governance maintains schemas, policies, adapter contracts, and dispute procedures; it does not silently override target maintainers.

The factory must minimize privileges, isolate untrusted code, avoid executing source discovered by the Scout, protect secrets, respect project licenses and disclosure obligations, and preserve offline/local operation where possible. Human review is mandatory for security-sensitive, irreversible, high-impact, ambiguous, or policy-changing actions unless a narrowly scoped and demonstrably safe policy explicitly permits automation.

No single agent or service may create a fracture, author its repair, self-certify the repair, and mint value without the required separation of duties and evidence checks.

## 6. Value model and non-extractive participation

Value attribution must be explicit, contestable, and separated from technical closure. Candidate dimensions may include maintainer-accepted utility, severity resolved, breadth of affected users, durability, avoided recurring maintenance, and verified reuse. These dimensions require a published methodology, uncertainty, anti-gaming controls, and a dispute path.

Do not equate lines of code, issue count, elapsed time, token count, popularity, or model confidence with value. Do not pay for merely generating a patch if the contract is for a verified resolution. Do not make maintainers pay to receive their own project repair unless a clearly disclosed, consensual service arrangement exists.

The economic mechanism must not force adoption of a Darkith token or closed wallet to use the manufactory. Minting is a pluggable settlement rail; participation and verified correction must remain possible without speculative asset exposure. Any on-chain implementation remains gated behind independent security review, legal/operational review, adversarial testing, and a strict separation from the mainnet boundary.

## 7. Interoperability and portability

The factory core defines stable schemas, state transitions, evidence contracts, policy decisions, and settlement interfaces. Host-specific connectors implement GitHub, other forge providers, local filesystems, CI systems, package/build systems, issue trackers, and execution environments.

A connector must declare capability and failure semantics. Unsupported operations are reported as unsupported—not simulated. Identity, timestamps, units, revisions, and provenance travel with records across boundaries. Temporal records require more than a timestamp: use addressable event identity, monotonic or causally ordered sequence where available, signed event envelopes, cryptographic chaining, and independently verifiable timestamp evidence when required. A hash chain detects alteration only relative to a trusted checkpoint; it does not by itself prove real-world time or truth.

## 8. Metrics that describe factory output

The manufactory's primary metrics are:
- admitted fractures with reproducible evidence;
- time from admission to accepted resolution, with clock and waiting categories separated;
- acceptance and reopen rates by fracture class;
- verified regression rate;
- maintainer effort saved or shifted, measured against a declared baseline;
- verified reuse of retained capabilities;
- settlement latency and correction/dispute rate;
- contribution concentration and maintainer burden;
- percentage of automated actions with complete provenance and valid authorization;
- unresolved evidence, stale receipts, and unverified boundaries.

Metrics must expose denominator, sampling frame, period, and missing data. A high throughput number cannot compensate for false closures, unsafe mutations, extractive settlement, or maintainer rejection.

## 9. Current repository mapping and honest status

This document defines the intended manufactory architecture. It does not certify that the complete industry-facing production network or automated economic system is implemented.

Existing anchors:
- Scout: `tools/fracture_scout.py`, `tools/fractures.txt`, workflow `.github/workflows/fracture-scout.yml`.
- Durable board and closure discipline: `TASKS.md`, `tools/board_gate.py`, `tools/ci.sh`.
- Class-level repair and convergence: `tools/autophagy.py`.
- Evidence-bound corrective cycle: `tools/revitalization.py` and `proof/revitalization/`.
- Provenance and value-ledger research: NT-XII baseline and correction on the research branch `research/nt-xii-value-ledger-baseline-2026-11-22`, commits `ca0909e…` and `f0e8f89…`.
- Current implementation areas requiring audit against this specification: `SynchronicityScheduler.mintToken()`, `ProgressLedger`, coupling/bridge adapters, fracture lifecycle schema, participant rights, resolution packet, settlement idempotency, and capability promotion.

The project record also includes recent CI and authority-gate defects. Known causes include the chat-gatekeeper/praxis contract mismatch (`laws: []` rejected where coupled laws are required), post-seal writes, moving freshness watermark, stale indexes/proofs, and local pre-push checks that cannot enforce remote branch rules. Recovery commits were recorded, but a historical green run is not proof that the current head is green. The current head and current run must be inspected before declaring closure.

The repository's last observed main commit at the time this document was prepared is `ec2f2001d7980ff3b10d78ab75c0bb7a20a03e4e` (2026-11-25): it removed implicit publication from tree repair and made CI run on the exact event SHA. This is a valuable authority-boundary improvement, but it is not the complete manufactory.

## 10. Integration order — production gates, not aspirational feature stacking

1. Canonicalize the manufactory definition and link it from the README and durable board.
2. Audit current Scout outputs and fracture records; make admission and duplicate handling explicit.
3. Define versioned fracture, coupling-capability, repair-task, resolution-packet, and state-transition schemas.
4. Establish read-only adapters and environment capability declarations before mutation adapters.
5. Implement one end-to-end pilot in a consenting target repository: discover → admit → couple → task → repair proposal → maintainer review → verify → seal.
6. Add idempotent settlement eligibility and ledger events only after the pilot's closure proof is reliable; keep minting disabled until evidence, allocation, replay, reversal, and independent review gates pass.
7. Promote retained capability only through isolated tests, provenance review, and measurable reuse.
8. Expand to additional forge and host adapters through conformance tests, not bespoke exceptions.
9. Publish operator/maintainer documentation, participant terms, dispute path, security model, and economic methodology before broad industry handoff.

Each stage is a board item with owner, acceptance criteria, dependencies, governing law, evidence path, and four-state result. A specification paragraph does not close an implementation task.

## 11. Acceptance invariant

Darkith qualifies as a functioning manufactory only when a third-party maintainer can, without the Operator personally repairing the target:

1. submit or discover a real fracture;
2. inspect why it was admitted;
3. couple Darkith to their native environment with declared permissions;
4. participate or delegate a bounded repair;
5. receive a verifiable, maintainer-accepted resolution packet;
6. inspect the settlement eligibility and any automated value event;
7. dispute or correct attribution;
8. reuse the retained capability in a later fracture;
9. withdraw or disconnect without losing control of their project or source.

Until this full cycle is demonstrated end-to-end with independent participants and reproducible evidence, Darkith is the manufactory architecture under construction—not a completed autonomous industry network.

The governing objective is to make the factory transferable to the industry that experiences the fractures, so its corrective capacity can operate through that industry while the Operator remains the architect of the machinery rather than its permanent labor bottleneck.
