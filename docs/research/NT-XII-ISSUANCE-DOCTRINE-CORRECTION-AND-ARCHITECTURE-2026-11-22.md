# NT XII — Issuance Doctrine Correction and Architecture Addendum
Date: 2026-11-22
Timezone: Asia/Manila (UTC+8)
Status: Research / design record; not a production implementation
Parent record: `docs/research/NT-XII-GLOBAL-VALUE-LEDGER-RD-BASELINE-2026-11-22.md`
Branch: `research/nt-xii-value-ledger-baseline-2026-11-22`

## 1. Supersession notice

This addendum corrects the economic interpretation in the parent baseline. Any parent-report statement that treats recipient purchase, recipient acceptance, market uptake, or a recipient-benefit event as a necessary precondition for recognizing the value of an NT XII treatise is withdrawn.

The baseline's proposed generic sequence—contribution → recipient acceptance → reciprocal settlement → issuance—does not faithfully encode the author's clarified NT XII issuance doctrine. It must not be implemented as the mint rule.

The governing intent, as clarified by the author on 2026-11-22:

- The mintable object is an original, codified noveltreatise/solution addressing a demonstrable, unresolved global pain point.
- The solution is judged against the actual constraints of the problem, with the rock-bottom accessibility floor deliberately lowered so marginalized populations are not excluded by avoidable prerequisites.
- The treatise must close a real residual: it must be reproducible, independently examinable, falsifiable, and capable of permanently reducing or removing the identified burden.
- The mint recognizes the verified achievement and enduring solution value. It does not require a purchaser, recipient's acceptance, market adoption, or prior monetary exchange for that value to exist.
- Exhaustion, attention, time, and energy are provenance/cost evidence of derivation, not a standalone unit-price formula. A hash is integrity/provenance evidence, not the source of value.

This author clarification governs the implementation interpretation. It does not authorize silently changing the canonical NT XII text; the textual discrepancy below remains an explicit source-reconciliation item.

## 2. Exact manuscript reconciliation required

The current NT XII source contains two formulations that must be read together and reconciled explicitly:

- §0.7 describes attention, exhaustion, irreversible time, and energy expenditure as the physical cost/provenance of derivation.
- §0.8 is titled “The Mint is Backed by Exhaustion” and says tokens are backed by physical, irreversible energy spent.
- §15.4 defines the mint as the codified harvest of a zeroed residual and calls the token the non-arbitrary value of the defect resolved and bond held; it also references GPU time and pixel-grid continuity.
- §15.5 describes the manufactory producing a signed, aligned, tokenized proof of work.
- §16 defines the Autophagic Sovereign Economy and the retention equation.

The clarified intended doctrine makes the resolved treatise and its verified burden-removing solution the mintable value-bearing achievement. The manuscript currently gives exhaustion a stronger backing role in §0.8 than this clarification permits. This is not to be hidden by reinterpretation. It is a flagged authorial text reconciliation.

Required future editorial action: revise §0.8 and align §15.4–15.5 so that (a) derivation cost/provenance, (b) mechanical closure evidence, (c) verified solution value, and (d) any later monetary redemption are distinct but coupled records. Do not modify the NT XII source file as part of this research-only correction.

## 3. Four distinct records; one coupled manufactory

The implementation must not collapse these dimensions:

1. Derivation provenance
   - Author/key, version lineage, timestamps with clock-quality metadata, source materials, derivation trace, resource/effort observations where voluntarily recorded.
   - Establishes provenance and cost. It is not the token valuation equation.

2. Residual closure / execution proof
   - Exact problem statement, baseline state, formal residual, transformation, postcondition, falsifier, reproducible command or protocol, environment, input/output digests, test vectors, and independent replay attestations.
   - Establishes that the claimed mechanism actually closes the specified residual under stated conditions.
   - A green test is evidence only for the property actually tested; it is not a universal proof of social impact or permanence.

3. Treatise-level solution-value record
   - Novelty/prior-art search record; unresolved pain-point evidence; causal mechanism; reproducibility; accessibility floor; performance against baseline; failure envelope; maintenance/decay conditions; independent review; and versioned evidence of durable burden reduction.
   - This is the issuance basis for NT XII recognition.
   - Recognition does not depend on sale, recipient acceptance, adoption volume, or market price.
   - Novelty is a bounded literature/prior-art conclusion, never an absolute claim that no one anywhere has thought of it.

4. Economic/settlement record
   - Token class, issuance authority, quantity rule, supply constraints, transferability, redemption terms if any, community allocation, treasury/reserve obligations if any, dispute/reversal policy, and legal classification.
   - Determines what economic rights the token actually carries. It must not retroactively redefine whether the treatise solved the problem.
   - A cryptographically scarce token is not automatically a fiat-denominated claim or guaranteed market price. If the token promises redemption, that promise needs an identified obligor, reserves or productive backing, enforceable rules, and jurisdiction-specific legal review.

The four records are linked by content digests and signed attestations. A hash proves byte identity relative to a digest; it does not prove truth, novelty, correctness, or social value.

## 4. NT XII treatise issuance state machine

Use explicit states. No state may be skipped, and an absent mechanism is a named boundary, never a fabricated success.

`DRAFT → PROBLEM_REGISTERED → PRIOR_ART_MAPPED → CANDIDATE_DERIVED → REPRODUCIBLE → INDEPENDENTLY_REVIEWED → ACCESSIBILITY_VERIFIED → RESIDUAL_CLOSED → VALUE_ATTESTED → ISSUANCE_AUTHORIZED → MINTED → MAINTENANCE_MONITORED`

Terminal/exception states:
- `REJECTED`: falsifier disproved the claim or evidence is invalid.
- `INCONCLUSIVE`: required evidence/dependency unavailable; retry or obtain evidence.
- `DISPUTED`: credible conflicting attestations; issuance/transfer of the disputed claim freezes.
- `REVOKED`: fraud, invalid provenance, or material falsification is established; append a revocation event, never erase history.
- `DEPRECATED`: later evidence supersedes the solution; preserve the original mint record and link the successor.

Minimum gates:

- Problem gate: define the pain point, affected population, present burden, geographic/context scope, and baseline evidence.
- Prior-art gate: search open literature, standards, patents where relevant, public repositories, and existing deployments; preserve queries, dates, inclusion criteria, and negative results.
- Derivation gate: show the treatise's new integration/derivation, not merely renamed prior art; cite all borrowed components.
- Reproduction gate: independent operator can follow the recorded steps using disclosed prerequisites and obtain the expected result.
- Falsifier gate: publish tests that could make the claim fail; include adversarial and boundary cases.
- Accessibility gate: measure required device, bandwidth, electricity, cost, literacy, language, skills, physical access, and institutional permission. Compare against the declared rock-bottom floor; do not assume that “open source” alone makes a solution accessible.
- Closure gate: the claimed residual is zero within a stated, dimensionally valid tolerance, or the remaining residual is explicitly exposed.
- Durability gate: specify maintenance, dependency, degradation, update, and failure conditions. “Permanent” is a claim to test over a declared horizon and under declared assumptions, not a magic property conferred by minting.
- Independent review gate: reviewers are plural, conflict-disclosed, geographically/institutionally diverse where practicable, and not all controlled by one funder, employer, state, platform, or author.
- Issuance gate: a deterministic policy maps the accepted evidence class to a token amount/class; the policy version and all inputs are published. Human governance may authorize policy changes, but cannot silently alter past evidence.

Recipient adoption and market price are useful optional impact observations, not mandatory mint gates.

## 5. Valuation discipline: value recognition is not price discovery

The protocol should avoid inventing a universal “scientific price” for a treatise. The scientific layer can establish and compare measurable properties: burden removed, error/risk reduced, time/resources saved, access expanded, reliability, reproducibility, and durability under stated conditions. It cannot by itself determine a universally correct exchange rate between unlike social goods.

Therefore:

- Define a versioned NT XII issuance schedule mapping independently verified solution classes and evidence grades to issuance units.
- Publish the rationale, units, caps, uncertainty, reviewer quorum, conflicts, and appeal path.
- Prevent duplicate issuance for the same underlying solution by canonical problem/solution lineage and prior-mint checks; allow a genuinely novel improvement to receive a linked incremental record rather than pretending the prior solution never existed.
- Keep market price, liquidity, redemption, and legal claim separate from the treatise's verified solution record.
- Measure external extraction and community retention under NT XI; issuance must not create a new rent-extracting intermediary or force marginalized users to pay merely to access the solution.

The token quantity rule is a governance/economic design decision requiring empirical calibration and stress testing. It must not be presented as a physical constant unless a valid dimensional derivation and empirical calibration establish that claim.

## 6. Offline-first architecture and the offline double-spend boundary

Offline-first means users can create, inspect, sign, and preserve contribution/treatise evidence without continuous connectivity. It does not mean disconnected devices can globally coordinate scarce spendable balances without a shared state.

Recommended separation:

- Local node: encrypted local event store; append-only signed events; local content-addressed artifacts; user-controlled export/backup; no network requirement for authoring or verification of already-held evidence.
- Sync layer: anti-entropy exchange; deterministic event validation; explicit causal metadata; idempotent event identifiers; conflict records rather than silent last-write-wins for economic events.
- Evidence layer: W3C Verifiable Credentials-compatible attestations and selective disclosure; key rotation/revocation; verifier policies; privacy minimization.
- Replication layer: multiple independent community-operated peers; content-addressed artifact distribution; append-only transparency checkpoints; reproducible snapshots.
- Settlement layer: deterministic double-entry postings, issuance caps, replay protection, and globally agreed ordering for final spend/transfer.
- Governance layer: plural community authority, published rule versions, appeals, transparent treasury/retention accounting, and exit/fork portability.

Critical boundary: two fully disconnected devices can each spend the same apparently available offline balance unless the system constrains offline spending or relies on trusted hardware/another non-colluding shared authority. Do not claim impossible offline global double-spend prevention.

Acceptable options to test:
1. Offline evidence capture and provisional local mint certificates; final globally spendable status only after quorum settlement.
2. Pre-allocated offline spending quotas/escrow per device or community, with strict caps and reconciliation.
3. Hardware-backed monotonic counters as an optional higher-assurance mode, never the only access path because device cost/exclusion and hardware compromise remain.
4. Mutual-credit limits and bounded exposure for communities willing to accept settlement risk.

The system must label provisional, settled, disputed, and revoked states visibly. Offline users must not be falsely told that a provisional entry is globally final.

## 7. Mainnet/testnet and phantom-containment architecture

The user's requested rule is absolute: synthetic phantoms, specters, stubs, mocks, and trial artifacts are confined to the remote test environment and must never acquire mainnet authority.

Isolation requirements:

- Distinct chain/network identifiers and genesis state.
- Distinct signing keys, issuer identities, credentials, endpoints, RPC URLs, databases, object stores, and secrets.
- Test-only token denominations and namespaces that cannot be interpreted as mainnet assets.
- No mainnet private keys or signing service reachable from test runners.
- Mainnet mint authorization rejects test-network chain IDs, test issuers, synthetic evidence flags, fixture namespaces, mock signatures, and unrecognized schema versions.
- Every artifact carries environment, build provenance, source revision, dependency/SBOM digest, and evidence digest.
- Promotion is by reviewed immutable artifact digest, never by copying mutable test state or promoting a test ledger snapshot.
- Testnet may deliberately inject adversarial and synthetic events; production/mainnet validation code must reject them.
- A mock may exist inside a test harness only when the test is explicitly about the harness boundary. A mock cannot satisfy a production mechanism or mint proof.
- Negative tests must prove that test credentials, replayed events, stale schema, duplicate solution IDs, invalid signatures, manipulated clocks, quorum capture, and missing dependencies are rejected or marked inconclusive.
- Production signing is a separate, manually governed trust domain. CI can prove artifact eligibility; it cannot silently exercise a mainnet mint key.

CI architecture should have three isolated lanes:
A. Static/reproducible research validation: schema, source digests, dimensional checks, docs consistency, deterministic local tests. No deployment credentials.
B. Remote adversarial testnet: synthetic population, fault injection, partition/replay/Sybil/collusion scenarios, test-only keys and assets.
C. Mainnet release gate: read-only eligibility checks and human/community authorization; no automatic minting from CI. A later independently operated mainnet service consumes an approved, signed issuance authorization.

## 8. Open-source components: fit assessment, not stack worship

| Component / standard | Useful role | Limitation / boundary |
|---|---|---|
| W3C Verifiable Credentials 2.0 | Portable, tamper-evident issuer/holder/verifier claims; privacy and accessibility considerations | A credential authenticates a claim/signature structure; it does not prove the claim is true without trustworthy evidence and issuer policy |
| W3C DID Core | Identifier architecture and DID methods | DID method governance and resolution can reintroduce centralization; choose methods based on threat model |
| Automerge | Local-first document state and CRDT synchronization | CRDT convergence does not decide economic truth, prevent duplicate spending, or resolve contested valuation |
| Holochain | Agent-centric source chains and deterministic validation of DHT operations | Validation must be deterministic; unavailable dependencies yield inconclusive validation; peer governance and availability remain operational concerns |
| Hyperledger Fabric | Pluggable endorsement, channel/private-data patterns, organizational policies | Permissioned consortium governance is not automatically decentralized; membership administrators can become concentrated authorities |
| Duniter | Web-of-trust identity and universal-dividend currency prior art | Certification graph assumptions, social exclusion, capture, and local governance need adversarial study; not a ready-made NT XII value engine |
| GNU Taler | Privacy-preserving payment architecture and separation of payment from identity | It is payment infrastructure, not a scientific novelty/solution-value evaluator or a global communal ledger |
| RFC 9162 transparency logs | Append-only Merkle log concepts, inclusion/consistency proofs | A log can prove inclusion/consistency, not truth of submitted claims; independent monitors and gossip are required to detect equivocation |

Do not select a global chain before threat-model and workload comparison. A federation of community-operated validation/settlement peers with portable evidence may fit the project better than one globally dominant L1. Benchmark at least (a) Holochain-style agent/DHT validation, (b) Fabric-style governed federation, and (c) a minimal content-addressed event log plus independently operated settlement quorum. Keep the local-first application layer chain-agnostic.

## 9. Immediate codebase findings to carry forward

From the inspected branch files:

- `SynchronicityScheduler.mintToken()` currently gates on `deltaZ`, computes `calculateBurnRate(c,t) * d`, and emits a JSON string with a value, APK hash, and deltaZ. This is not yet the treatise-level state machine or an independently verified solution-value issuance protocol.
- `ProgressLedger.onEvent()` appends local JSONL rows to two files but catches and suppresses `Throwable`; that can make a failed persistence operation invisible. It is not yet proof of durable, replicated, signed, double-entry settlement.
- Existing proof files (`proof/nt_xii_claims.json`, `proof/nt_xii_reconciliation.json`) already distinguish witnessed claims, derived claims, assumptions, and contradictions. The new issuance protocol should extend this discipline, not bypass it.
- The NT corpus itself requires source, transformation, and falsifier at each step, and forbids fake success. The proposed architecture inherits that requirement.

These are scoped observations, not a complete repository audit. No production code was changed by this addendum.

## 10. Research references and evidence status

Standards and primary technical documentation reviewed for this correction:

1. W3C, Verifiable Credentials Data Model v2.0, Recommendation (2025-05-15): https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/
   - Supports portable issuer/holder/verifier claims and security/privacy/accessibility considerations. Does not establish truth of the underlying claim.
2. Android Developers, Build an offline-first app: https://developer.android.com/topic/architecture/data-layer/offline-first
   - Describes local/network synchronization, pull/push/hybrid models, versioning, and conflict resolution. Its “last write wins” example is not suitable as the sole policy for contested economic events.
3. Holochain Developer Documentation, Validation: https://developer.holochain.org/concepts/7_validation/
   - Requires deterministic validation; unavailable dependencies are inconclusive and retried. Useful for peer validation, not a substitute for economic governance.
4. Hyperledger Fabric documentation, Private data: https://hyperledger-fabric.readthedocs.io/en/latest/private-data/private-data.html
   - Shows private-data collections and endorsement-based controls. Useful for federation experiments; organization membership and endorsement power remain governance risks.
5. Hyperledger Fabric, Endorsement policies: https://hyperledger-fabric.readthedocs.io/en/latest/endorsement-policies.html
   - Demonstrates collection-level endorsement policy controls. Permissioned endorsement must be evaluated for power concentration.
6. Duniter, Web of Trust: https://duniter.org/web-of-trust/
   - Documents one-person-one-account certification design and its social-graph assumptions. Treat as prior art and a threat-model input, not proof of Sybil immunity.
7. IETF RFC 9162, Certificate Transparency v2: https://www.rfc-editor.org/rfc/rfc9162.html
   - Defines append-only Merkle log operations and consistency/inclusion concepts. Logs prove what was recorded, not the truth or value of a record.
8. NISTIR 8202, Blockchain Technology Overview: https://csrc.nist.gov/pubs/ir/8202/final
   - Background on blockchain components and consensus trade-offs. Blockchain consensus does not create the value of the records it orders.
9. GNU Taler project: https://taler.net/
   - Privacy-preserving payment-system prior art. Evaluate payment separation and privacy; do not treat it as an issuance-value oracle.
10. Automerge project: https://github.com/automerge/automerge
    - Local-first CRDT prior art. Convergence is a data synchronization property, not a global economic settlement rule.

Evidence discipline:
- The standards and project documentation above support the technical capabilities stated, not the entire NT XII thesis.
- “Novel,” “permanent,” “global,” and “marginalized-accessible” are hypotheses to operationalize and falsify for each treatise, not labels that a mint operation can make true.
- Every future report must record exact source version/date, retrieval time, quoted claim, transformation, and falsifier. Prefer primary standards, peer-reviewed research, reproducible datasets, and open implementations; label vendor claims and author synthesis separately.

## 11. Research work queue — ordered, persistent

R0 — Doctrine reconciliation
- [ ] Author resolves §0.8 against §15.4–15.5 and the clarified treatise-value issuance doctrine.
- [ ] Canonical glossary distinguishes derivation cost, residual closure, solution value, token issuance, market price, and redemption.

R1 — Formal value-evidence schema
- [ ] Define problem identity, baseline, burden metrics, solution lineage, novelty search manifest, reproducibility bundle, accessibility floor, falsifiers, reviewer attestations, durability horizon, and uncertainty.
- [ ] Define deterministic duplicate/derivative detection with human appeal; do not claim perfect plagiarism or novelty detection.

R2 — Threat model
- [ ] Sybil identities, collusion, reviewer capture, coercion, censorship, credential revocation, stolen keys, device loss, clock manipulation, replay, equivocation, partition, malicious update, dependency compromise, and governance capture.
- [ ] Include undocumented, low-connectivity, low-literacy, low-power, disability, language-minority, and low-cost-device users in adversarial accessibility tests.

R3 — Offline event protocol
- [ ] Canonical event envelope, signature format, content addressing, causal metadata, idempotency, key rotation, revocation, backup, and deterministic merge.
- [ ] Explicitly test partition behavior and bounded offline settlement.

R4 — Testnet containment
- [ ] Separate test genesis/network, keys, issuers, endpoints, secrets, databases, assets, and artifact namespaces.
- [ ] Build adversarial fixtures and prove every fixture is rejected by mainnet validators.

R5 — Economic design
- [ ] Publish issuance schedule, supply/decay policy if any, community allocation, retention measurement, transferability, redemption and dispute rules.
- [ ] Model who controls issuance, who captures value, and who bears externalities.

R6 — Implementation decision
- [ ] Benchmark candidate federated/local-first designs against the same test corpus.
- [ ] Select only after security, privacy, accessibility, operational-cost, and governance comparison.

R7 — Legal and operational boundary
- [ ] Obtain jurisdiction-specific review before offering transferable/redeemable tokens or operating a payment/exchange service.
- [ ] Keep testnet and research issuance non-monetary and non-redeemable until the legal and backing model is explicit.

## 12. Safety boundary and execution record

This is a documentation-only research addendum.

- No production source files modified.
- No workflow files modified.
- No workflow_dispatch or test commands invoked.
- No mainnet/testnet deployed.
- No token minted or transferred.
- No secrets, keys, or signing credentials accessed.
- No pull request opened.
- The repository workflows were inspected: dependency auto-merge push trigger is limited to `main` and `master`; fracture scout is schedule/workflow_dispatch only. The research branch is not included in those push branches. This commit therefore does not intentionally target the production CI trigger paths.
- Existing main-branch workflow runs were observed independently of this research work. At inspection, two newest main runs were still in progress; one recent main run was successful and another prior main run failed. This report does not claim the current pipeline is uniformly green.

End of addendum.
