# NT INDEX — the noveltreatise corpus, carried and reconciled

This directory carries the noveltreatise (NT) corpus: the law layer that the
gates in `tools/` enforce. `DARKITH.md` is the state layer and cites this corpus
rather than duplicating it (NEVER #16: one document per layer).

Every file here is run through SAVF and reconciled by `tools/nt_gate.py` (wired
into `tools/ci.sh`). The claims ledger is `proof/nt_claims.json`; the resolutions
are `proof/nt_reconciliation.json`; the absolution report is
`proof/NT_RECONCILIATION.md`.

## The corpus

| NT | file | governs in this repo | status |
|---|---|---|---|
| I | `NT-I-IV-protocol.md` | the basal floor / cortical surface; RSA as correlate | RESOLVED |
| II | `NT-I-IV-protocol.md` | the offload inversion; re-enterability — the philosophy the gates enforce | RESOLVED |
| III | `NT-I-IV-protocol.md` | assignment by rescue assay (DOSAGE/GEOMETRY/ENERGETICS) | RESOLVED |
| IV | `NT-I-IV-protocol.md` | the pre-registration gate; reflexive Stage 0 | RESOLVED |
| V | `NT-V.txt` | the cut; the two-clock payroll gap; the autophagic recycle bin | RESOLVED |
| VI | `NT-VI.txt` | the coupling law — the payload-to-donor graft across the whole stack (ore → silicon → neuron → code); C = D ∩ P = ∅; the clock is the invariant | RESOLVED |
| VII | `NT-VII.txt` | the screen stack layer order (adjacency necessity) | RESOLVED |
| VIII | `NT-VIII.txt` | the Bond Formation Number ℬ ≥ 1 (the cross-scale bond criterion) | RESOLVED |
| IX | `NT-IX.txt` | the multiplicative triad; the 7-step no-Gradle raw build chain | RESOLVED |
| X | `NT-X.txt` | hardware ground truth; the autophagic allocator; the Healer; Σ = 0 | RESOLVED |
| XI | `NT-XI.txt` | the Autophagic Sovereign Economy; the AQP implementation synthesis | RESOLVED |
| XII | `NT-XII.txt` | the terminal convergence: the Bond Formation Number closed across all scales; the Triadic Resolver; the SAVF Generative Manufactory; the no-Gradle proto-node; the Autophagic Sovereign Economy | RESOLVED (mechanics), EXPOSABLE (external figures), INFERRED (cross-scale synthesis) |

## The NT → gate map (SPI-15: a law that is not a gate is a note)

| NT | law | gate that enforces it |
|---|---|---|
| II | re-enterability (source/transformation/falsifier) | `tools/delivery_gate.sh`, `tools/fork_integrity_gate.sh`, `tools/board_gate.py` |
| II, XIII | no foreign symbol | `tools/fork_integrity_gate.sh` (SPI-13: zero `import androidx`) |
| IX | the 7-step raw chain; API-34 ceiling; align before sign | `build.sh`, `tools/api_level_gate.py`, `tools/fork_integrity_gate.sh` |
| X | never write a stub (Prime Directive) | `tools/law_gate.py`, `tools/syntax_gate.py` |
| XII | the corpus count is true; a treatise is carried, witnessed, and contradiction-free before admission | `tools/absolution_admission.py` |
| all | the corpus is carried, not merely cited; every contradiction resolved | `tools/nt_gate.py` |
| X, XII | the Healer repairs to a symbol the reference carries (raw `android.*`, not `androidx.*`) | `tools/nt_sensor.py` (reads the reference `android.jar`; SPI-13) |

## Status flags

- RESOLVED — the path is inside the repo; re-walkable here.
- EXPOSABLE — the mechanism is carried; the external primary source is not (a
  named boundary, not a defect).
- INFERRED — the author's synthesis; the uncertainty is flagged.

## The gap, filled

NT VI was cited by NT VIII and NT XI as a load-bearing peer but had no body. It
is now carried (`NT-VI.txt`): the coupling law — the graft by which a payload
joins a donor across every scale, from the ore body to the neuron to the
instruction set. The three legs of the coupling (disjointness, continuity,
synchrony) are enforced by three existing gates:

| NT VI leg | condition | gate that enforces it |
|---|---|---|
| Disjointness | D ∩ P = ∅ (no namespace collision) | `tools/fork_integrity_gate.sh` (SPI-13: no foreign symbol) |
| Continuity | the interface is load-bearing | `tools/bridge_contract_audit.py` (the HTML ↔ Kotlin contract) |
| Synchrony | payload and donor share one clock | `tools/synchrony_gate.py` (one clock, UTC+8) |

## The two the repo previously lacked

NT IX and NT X were cited throughout the Kotlin sources and `DARKITH.md` before
this run, but were not in the tree. They are carried here now.


## Manufactory architecture — cross-corpus integration

The industry-coupled manufactory is specified in [ARCHITECTURE-MANUFACTORY.md](../ARCHITECTURE-MANUFACTORY.md). It integrates the existing components without replacing their governing documents:

- Fracture Scout discovers and ranks candidates; it does not prove defect, novelty, authorization, or payment.
- The autophage/coupling layer connects to the affected environment through bounded adapters.
- Homekeeper governs repository-unit admission and authority boundaries.
- SAVF and the existing gates supply bounded reproduction and verification evidence.
- Autophagy turns recurring defects into class-level correction and prevention.
- Nodal supplies the current receipt/coordination substrate within its stated single-writer and tamper-evident limits.
- NT XII and the Black & Whitepaper remain authoritative for issuance. Repair compensation/settlement is a separate economic rail.

The manufactory document is a governing architecture and staged implementation specification. It does not promote industry-wide participant routing, autonomous settlement, or decentralized governance to implemented status without their own evidence.
