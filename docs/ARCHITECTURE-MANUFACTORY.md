# DARKITH MANUFACTORY — Industry-Coupled Fracture-to-Capability Architecture

Status: governing architecture and integration specification. This document defines the manufactory model; it does not claim that every described industry-facing service is already implemented.

## 0. Governing identity

Darkith is the manufactory, not a derivative product assembled by scavenging repositories and competing for adoption.

The factory is the product: a transferable architecture that discovers fractures in existing software and operating environments, couples to the affected context, coordinates the people and tools already capable of resolving them, preserves verified corrections, and operates the downstream evidence and value machinery.

Darkith is not intended to make its founder the permanent repair workforce. The founder's responsibility is to establish the factory's governing architecture, safeguards, interfaces, and ownership model. Developers, maintainers, operators, and affected communities remain participants with their own agency, native environments, expertise, and authority.

This does not mean Darkith never uses a fork, branch, patch, or upstream repository. Those are ordinary engineering mechanisms. The distinction is the unit of purpose: Darkith does not seek to become another competing copy of every project it encounters. It couples to the project where the fracture exists and supports correction in the project's own context.

## 1. The manufactory cycle

The intended production cycle is:

Fracture discovery
→ source and environment confirmation
→ bounded factory coupling
→ fracture dossier and admission
→ participant routing
→ distributed repair
→ independent reproduction and verification
→ affected-project disposition
→ correction preservation
→ eligible economic accounting
→ downstream minting or settlement
→ reusable capability accumulation
→ renewed discovery

No arrow is implied by the existence of the previous stage. Each transition has its own evidence, authority, and failure state.

### 1.1 Fracture discovery — Fracture Scout

Fracture Scout is the discovery and ranking entry point. It identifies candidate problems from configured sources and expressions.

A Scout candidate is not automatically:
- a confirmed current defect;
- a novel problem;
- a task authorized for implementation;
- an accepted upstream repair;
- a bounty, payment, or mint;
- proof of social or economic value.

Admission must confirm the source, revision, reproduction conditions, affected capability, current status, and whether the candidate is already resolved or duplicated. Discovery must preserve the original source reference and retrieval time so the candidate can be re-examined.

### 1.2 Confirmation and fracture dossier

Before production begins, the factory assembles a bounded dossier:

- stable fracture identifier;
- original source and exact revision;
- affected project, component, or environment;
- observed behavior and expected behavior;
- minimal reproduction or explicit reason a reproduction is unavailable;
- severity and impact basis;
- governing invariant or acceptance contract;
- dependencies, permissions, and execution boundary;
- existing fixes, duplicates, and prior-art findings;
- proposed verification procedure;
- responsible decision authority;
- participant scope and compensation terms, if any;
- known uncertainty and exclusions.

The dossier is the production contract. It prevents a vague complaint from becoming an unbounded assignment and prevents a generated summary from replacing the source evidence.

### 1.3 Factory coupling — autophage and adapters

The autophage is the coupling machinery: it connects the factory to the environment that contains the fracture, rather than copying that environment into a competing product by default.

Coupling is explicit and bounded. It may use repository metadata, local source, build/test commands, issue context, artifacts, or host capabilities, but each adapter must declare:
- what it can read;
- what it can write;
- which identity or credentials it uses;
- which commands may execute;
- which network and filesystem boundaries apply;
- what it cannot observe or guarantee;
- how the coupling can be removed.

A coupling adapter is not granted authority merely because it can connect. Read-only discovery, proposed patch generation, local execution, remote issue updates, branch creation, and upstream submission are separate capabilities. Mutations require the applicable policy and authorization path.

The factory must preserve the affected project's own source-of-truth and review process. A local repair branch is a work surface, not a new authoritative project.

### 1.4 Industry participation

The fractured developer and maintainer industry is the production force, not a captive labor pool.

Participants may include:
- maintainers with authority over the affected project;
- developers who can reproduce or repair the defect;
- security and reliability specialists;
- users who can provide environment-specific evidence;
- organizations that supply testing infrastructure;
- independent reviewers and reproducibility witnesses.

Participation is not equivalent to surrendering repository ownership, credentials, intellectual property, or governance. The factory must support participant choice, clear scope, attribution, opt-out, and portable evidence.

The participant does not need to adopt Darkith as their primary development environment. Darkith should meet the industry where work already happens through interoperable adapters and documented contracts.

### 1.5 Distributed resolution

A repair may be performed by a maintainer, an external contributor, an automated executor, or a combination. The manufactory coordinates the work but does not replace the target project's authority.

A repair packet contains:
- the original fracture dossier;
- proposed change and provenance;
- exact source revision and patch;
- affected files and dependencies;
- reproduction before and after;
- tests and their actual verdicts;
- security and compatibility implications;
- residual risk and known limitations;
- maintainer or project disposition where applicable.

Automated execution must remain bounded by policy. Unknown provenance, scope drift, privilege escalation, destructive action, failed tests, or missing rollback evidence must halt the operation rather than silently promote it.

## 2. Verification and correction preservation

### 2.1 SAVF is the evidence engine, not a truth oracle

SAVF and the repository's existing verification gates provide the correction and evidence substrate. The factory must distinguish:

- source inspected;
- reproduction executed;
- test passed;
- independent reproduction completed;
- target project accepted, rejected, or has not reviewed;
- correction merged, released, or remains in a branch;
- real-world impact measured, inferred, or unknown.

A digest proves byte identity under the declared procedure. It does not prove that a premise is true, that a fix is safe in every environment, or that a community benefited.

The existing phantom barrier and reproducer doctrine remain applicable: a claim must survive its own declared reproduction, and honest control cases must survive the same barrier. A system that rejects every candidate is not a valid verifier.

### 2.2 Repair the defect class

Darkith's existing autophagy doctrine requires class-level correction: detector, deterministic repair where appropriate, prevention gate, and regression evidence. The manufactory extends that rule to production records.

A completed repair must identify:
1. the defect class;
2. the root cause;
3. the correction;
4. the detector that recognizes recurrence;
5. the prevention or admission gate;
6. the regression reproducer;
7. the verified boundary.

A one-off patch without recurrence control may still be a useful external contribution, but it must not be represented as a completed Darkith class correction.

### 2.3 Preservation and capability accumulation

Accepted corrections become reusable capability only when their provenance and reuse boundary are explicit.

The capability record must retain:
- source and license;
- original and corrected revision;
- patch or artifact digest;
- verification commands and environment;
- upstream disposition;
- known incompatibilities;
- dependency and security status;
- reuse permissions;
- evidence expiry or revalidation conditions.

The factory must not absorb a correction into a generic knowledge base while stripping the context that makes it valid. Reuse is conditional on matching the original assumptions or rerunning the relevant checks.

## 3. Economic machinery: separate the rails

The manufactory has distinct economic operations. They must not be collapsed into one ambiguous “mint” action.

### Rail A — NT XII issuance

The current Black & Whitepaper doctrine defines issuance through its claim gates and reproducible evidence. It explicitly states that purchaser, recipient acceptance, adoption, and price are not issuance conditions. This is the current repository doctrine and must not be silently rewritten by this architecture.

The manufactory can supply qualifying original work, provenance, cost evidence, and reproducibility to that issuance path. A repair's existence alone does not automatically qualify it for issuance; the claim must meet the applicable NT XII gates.

### Rail B — repair compensation and settlement

Issue-linked bounties, contracts, grants, service fees, or other compensation are separate from NT XII issuance.

Where a repair contract uses acceptance as its settlement condition, the contract must state:
- payer and payee;
- bounded deliverable;
- acceptance authority;
- acceptance tests;
- amount and currency or unit;
- release conditions;
- dispute and appeal path;
- refund, reversal, or failure handling;
- applicable fees and disclosures.

This rail may release compensation after verified and contractually accepted resolution. It must not be misrepresented as NT XII issuance, and NT XII issuance must not be made dependent on a buyer or adoption unless the governing doctrine is deliberately amended through its own reconciliation process.

### 3.1 Automated downstream value capture

Automation begins only after the required evidence and policy checks exist. The pipeline may prepare a mint or settlement transaction, but each operation must use the authorization level appropriate to its consequence.

The minimum economic receipt records:
- fracture and repair identifiers;
- evidence bundle digest;
- eligibility rule and version;
- verification verdicts;
- contributor attribution and consent basis;
- cost / effort provenance, where relevant;
- issuance or settlement rail;
- amount and unit, if any;
- recipient and authorization;
- transaction identifier or explicit NOT EXECUTED status;
- reversals, disputes, or later invalidation.

A generated receipt is not itself a payment. A local ledger is not automatically a decentralized consensus network. A token is not proof of market demand, adoption, or retained community value.

### 3.2 Economic sovereignty

The existing economic invariant remains distinct from project progress:

W_in − E = S

W_in is verified community-generated wealth; E is external extraction; S is retained value.

The manufactory must not infer community retention from the number of repaired issues, minted units, merged pull requests, or project deficit reaching zero. Retention requires evidence of control, accessibility, and circulation under the applicable economic model.

## 4. Governance and authority boundaries

The factory is transferable into the industry, but transferability is not unrestricted authority.

The architecture must separate:
- factory maintainer authority;
- target-project maintainer authority;
- contributor authority over their work;
- user authority over local data and execution;
- verifier authority over evidence;
- economic issuer authority;
- settlement provider authority.

No single role should be able to fabricate a fracture, approve its own evidence, authorize its own payment, and erase the resulting audit trail without independent controls.

Where the system is currently single-writer, local, or centrally administered, it must say so. Distributed participation does not equal distributed consensus. Open contribution does not equal permissionless mutation. A hash chain is tamper-evident, not a substitute for external witnesses or governance.

## 5. Interoperability contract

A participant-facing adapter should expose a minimal contract rather than require adoption of Darkith's entire stack.

The contract includes:
- discovery input and source provenance;
- project identity and revision;
- issue/fracture identifier;
- read-only inspection;
- bounded patch or artifact exchange;
- reproduction and test invocation;
- evidence receipt;
- status and disposition;
- optional compensation terms;
- export and disconnect.

Adapters must be replaceable. A participant should be able to inspect the dossier and patch without depending on a proprietary Darkith runtime. The factory's value lies in orchestration, verification, preservation, and coordination—not in trapping the participant's source or identity.

## 6. Operational states

Each fracture should have an explicit state, with transitions supported by evidence:

- DISCOVERED — candidate found; not yet confirmed.
- CONFIRMED — source and current behavior examined.
- ADMITTED — bounded dossier and governing criteria recorded.
- COUPLED — authorized adapter attached to the relevant environment.
- ROUTED — participants or execution path selected.
- IN_PROGRESS — repair work is active.
- SUBMITTED — repair packet is available for review.
- VERIFIED — declared checks and reproductions passed within scope.
- ACCEPTED / REJECTED / UNREVIEWED — affected project's disposition, kept distinct.
- MERGED / RELEASED — upstream or deployment state confirmed.
- PRESERVED — correction and provenance admitted to reusable capability.
- SETTLED — contract compensation completed, if applicable.
- ISSUANCE_ELIGIBLE / ISSUED — NT XII claim gate and transaction state, if applicable.
- DISPUTED / REVOKED / REVALIDATION_REQUIRED — evidence or authority has changed.

States may branch. A verified patch can remain unreviewed upstream. A project may reject a technically reproducible change for policy or compatibility reasons. Such a result is not rewritten as a successful merge.

## 7. Failure modes the manufactory must prevent

The architecture must detect or explicitly expose:

- duplicate fractures routed as novel work;
- stale issues presented as active;
- false or fabricated reproduction;
- patch applied to the wrong revision;
- adapter scope exceeding authorization;
- test results copied from another environment;
- self-verification presented as independent verification;
- accepted repair claimed before project disposition;
- mint or payment claimed before transaction execution;
- contributor attribution without a valid basis;
- compensation terms changed after work begins;
- reused capability detached from its license or assumptions;
- market adoption inferred from issuance;
- community retention inferred from gross output;
- a single-writer ledger presented as decentralized consensus;
- a successful project gate presented as proof of industry-wide sovereignty.

Each recurring failure must become a registered defect class with a detector, prevention mechanism, and regression fixture under the repository's existing law.

## 8. Evidence and performance measures

The manufactory must report both production throughput and evidence quality. Useful measures include:

- candidate precision: confirmed fractures / reviewed candidates;
- duplicate and stale-candidate rate;
- time from discovery to reproducible dossier;
- time from admission to verified repair;
- participant distribution and repeat participation;
- repair regression rate;
- upstream disposition and merge/release rate;
- reproducibility rate across independent environments;
- preservation and revalidation coverage;
- compensation settlement latency and dispute rate;
- issuance eligibility and issuance state, separately;
- participant costs and value retained, where independently measured.

No single metric should become a proxy for the whole system. High throughput with low verification is failure. High issuance with no evidence of retained value is not economic sovereignty. A low merge rate may reflect project policy, abandoned upstreams, or poor repair quality; the cause must be classified rather than guessed.

## 9. Integration map to the current Darkith repository

This architecture composes existing named components; it does not rename them or claim missing integration as complete.

| Existing component | Manufactory role | Current boundary |
|---|---|---|
| Fracture Scout | candidate discovery and ranking | candidate is not confirmation, authorization, novelty, or payment |
| autophage / coupling law | attach to the affected environment | adapter capability and mutation authority must remain explicit |
| Homekeeper | repository unit, admission, and authority model | conjunctive invariant; not universal proof of industry sovereignty |
| SAVF | reproduction, correction, and verification machinery | verdict bounded by checks actually run |
| autophagy | defect-class correction and recurrence prevention | class fix requires detector, repair, prevention, and re-detection |
| Nodal | receipt and ordered coordination substrate | single-writer / tamper-evident boundary; not consensus |
| NT XII | qualifying original work and issuance doctrine | existing gates and no purchaser/adoption/acceptance condition remain authoritative |
| Black & Whitepaper | plain, practitioner, and executor registers | doctrine of record for issuance must be reconciled before any change |
| DARKITH.md | canonical project state | generated policy block and single-source rules must be respected |
| tools/ci.sh | repository gate orchestration | only gates actually wired and run can be reported as evidence |

## 10. Implementation sequence and admission gates

The architecture should be implemented in capability-sized increments. Each increment must have a runnable artifact or clearly named non-runnable status, source, test, and evidence.

### M0 — Doctrine and contract
- Record this architecture in the canonical documentation index.
- Resolve vocabulary and economic-rail distinctions against NT XII and the Black & Whitepaper.
- Define fracture dossier schema and state vocabulary.
- Gate: no contradiction between architecture, doctrine, and executable issuance rules.

### M1 — Dossier and provenance
- Normalize Scout candidates into a stable dossier.
- Preserve source, revision, retrieval context, duplicate checks, and uncertainty.
- Gate: malformed, stale, duplicate, or provenance-free candidates cannot be admitted as confirmed work.

### M2 — Coupling adapter boundary
- Define read-only inspection and bounded mutation interfaces.
- Record capability, identity, scope, and disconnect behavior.
- Gate: adapter cannot silently exceed its declared permission or target revision.

### M3 — Participant handoff
- Export a portable repair packet that a maintainer can inspect without adopting the whole Darkith stack.
- Track participant choice, attribution, and disposition.
- Gate: no contribution is treated as accepted or owned by Darkith merely because it entered the factory.

### M4 — Verification and preservation
- Bind repair packets to exact revisions and reproducible commands.
- Attach SAVF verdicts, regression gates, and revalidation conditions.
- Gate: unverified or scope-mismatched repairs cannot enter the reusable capability corpus as verified.

### M5 — Economic automation
- Implement separate issuance and settlement rails.
- Enforce eligibility, authority, receipts, idempotency, dispute, and failure handling.
- Gate: no transaction is reported as executed without external or ledger evidence; no mint bypasses NT XII doctrine.

### M6 — Industry-scale operation
- Add interoperable provider adapters, independent witnesses, governance, and operational monitoring as actual capabilities.
- Gate: scale claims require measured participant, reliability, security, and economic evidence—not architecture diagrams alone.

## 11. Definition of manufactory completion

The manufactory is not complete when it can find a repository, generate a patch, or mint a unit.

A bounded end-to-end manufactory capability is demonstrated only when an independent participant can:

1. inspect a sourced fracture dossier;
2. connect or use the factory without surrendering project authority;
3. perform or contribute a bounded repair in the affected project's context;
4. reproduce the verification from the declared source revision;
5. inspect the evidence and the project's disposition;
6. preserve the correction with license and provenance intact;
7. distinguish any compensation settlement from NT XII issuance;
8. verify the actual transaction state;
9. export the record and disconnect without losing access to their own work.

Until that path is demonstrated with real participants and real target projects, the industry-wide manufactory remains the governing architecture and objective—not a completed production service.

## 12. Governing statement

Darkith manufactures the capacity for the fractured industry to produce its own corrections.

The factory supplies discovery, coupling, coordination, verification, preservation, and downstream economic machinery. The industry supplies situated knowledge, repair capacity, review, and ongoing maintenance. The founder establishes the architecture and its law; the founder is not the factory's permanent workforce.

The factory is the product. The industry's corrective capacity is the production force. Fractures are the demand substrate. Evidence governs admission. Minting and settlement remain distinct downstream operations. Reusable capability compounds only through verified, provenance-preserving correction.

The system must prove each of those statements at the capability boundary where it is made.
