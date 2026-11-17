# NT CORPUS RECONCILIATION — the SAVF run and the absolution

Status: executed. Every claim in the noveltreatise corpus was run through SAVF
(`savf.py ledger --run`). Every contradiction against reality was resolved to a
status and re-verified by a command that re-runs green. The gate `tools/nt_gate.py`
enforces this in CI: a contradiction left unresolved stops the build.

- Corpus carried: `docs/nt/` (7 files; NT I–XI, with NT VI carried as a declared gap).
- Claims ledger: `proof/nt_claims.json` (45 claims).
- Reconciliation: `proof/nt_reconciliation.json` (9 resolutions).
- Pre-reconcile SAVF output: `proof/nt_ledger_prereconcile.txt`.
- Gate: `tools/nt_gate.py` (wired into `tools/ci.sh`).

## How the corpus was run

SAVF grades each claim by kind:

| kind | meaning | SAVF state |
|---|---|---|
| A | analysis (a design statement with no falsifier) | analysis |
| W | witness (re-runs its evidence command) | verified / failed |
| R | derived (holds iff its parents hold) | verified / unsupported |
| D | declared (a stated fact) | declared |
| C | contradiction (conflicts with reality, not yet resolved) | unverified |

Result of `savf.py ledger proof/nt_claims.json --run`:

```
45 claims, 0 problem(s)
```

Every one of the 15 witnesses re-ran green (its evidence command executed and
printed its marker). Every derivation held. The corpus is internally clean.

## The 15 witnesses (re-run against reality)

Each witness is a command that reads the carried corpus or the repo and asserts
the exact bytes. The `--run` pass executed all 15; each printed its marker.

| claim | what it witnessed |
|---|---|
| NT1-RSA-EVIDENCE | NT I downgraded RSA from readout to correlate and flagged the contested layer |
| NT2-RULE-W | the re-enterability rule (Source/Transformation/Falsifier; carry the citation verbatim) is carried |
| NT2-CI-EXIT0 | the re-enterability gates exist and are wired into one provider-neutral CI |
| NT3-CHR-W | NT III carries the 23-pair structure and its own count check |
| NT4-STATUS-W | the RESOLVED/EXPOSABLE/INFERRED labels are carried |
| NT5-CUT-W | NT V carries the cut's invariant statement |
| NT7-STACK-W | NT VII carries the bedrock-to-ceiling anchor order |
| NT8-BOND-W | NT VIII carries the bond criterion and its universal condition |
| NT9-MATH-W | the closed-triple algebra executes exactly (b^n=x, r=0, both unfold legs) |
| NT9-BUILD-W | build.sh realizes the 7-step chain in order |
| NT9-NOGRADLE-W | build.sh contains no Gradle invocation |
| NT10-PRIME-W | NT X carries the Prime Directive and the honest-boundary distinction |
| NT10-SIGMA-W | NT X carries the Sigma=0 closure criterion |
| NT11-RETENTION-W | NT XI carries the retention equation W_{in} − E = S ≠ 0 |
| NT11-AQP-W | NT XI carries the forced derivation result (6 BUILD / 7 ADOPT) |

## The 9 contradictions, resolved to absolution

A contradiction (kind C) is a claim that conflicts with reality and is not yet
resolved. Each is resolved to exactly one of three truthful states:

- RESOLVED — the path is inside the repo; re-walkable here.
- EXPOSABLE — the mechanism is carried; the external primary source is not. This
  is not a defect. It is a named boundary.
- INFERRED — the author's synthesis; the uncertainty is flagged, not hidden.

| id | resolution | what it is |
|---|---|---|
| NT6-SYNCHRONICITY | INFERRED | NT VI is cited by NT VIII and NT XI as a load-bearing peer (payload-to-donor graft; DEX collision avoidance C = D ∩ P = ∅) but has no body. The interface is carried; the derivation is an open upload. Declared, not hidden. |
| NT10-HEALER-ANDROIDX | RESOLVED (scoped) | NT X's Healer example repairs to `import androidx.compose.material3.Button`, which the repo law forbids (`fork_integrity_gate` SPI-13 / NEVER #12: zero `import androidx`). Compatible once scoped: the androidx symbol is an illustrative worked example of the Healer *mechanism*; it is not a claim about the delivered tree, which obeys the no-androidx law. Follow-up: re-point the corpus example to a raw `android.*` import. |
| NT4-RABTSEVICH | EXPOSABLE | NT IV's live demonstration (Rabtsevich TESS pre-registration; VAAR; FAIA) is an external referent; the mechanism is RESOLVED in-document. |
| NT7-PROCESS-ZERO | EXPOSABLE | NT VII Part 13 material-stream figures are carried without verbatim source, and NT VII itself flags this. |
| NT9-DEMO-ECON | EXPOSABLE | NT IX Part 4 economic demonstrations carry live source data; the arithmetic is re-walkable, the sources are external. |
| NT9-COMPILER-SAMPLES | EXPOSABLE | NT IX Part 8 compiler bug reports are external; the fault-localization structure is RESOLVED. |
| NT9-AAPT2-API35 | EXPOSABLE | the aapt2 API-35 fracture is an external citation; the rule (ceiling locked to 34) is RESOLVED and enforced. |
| NT10-HARDWARE | EXPOSABLE | NT X's TECNO KM4k / MT6768 ground truth is a declared device fact, external to the repo. |
| NT11-PRAXIS-ACTUALS | EXPOSABLE | NT XI Part 2 praxis actuals are external institutions; the mechanisms are RESOLVED as arithmetic. |

## The honest boundaries (nothing hidden)

1. **NT VI has no body.** It is carried as a title and cited as a peer. The
   interface is stated; the derivation is an open upload. Status: INFERRED.
2. **NT IX and NT X are now carried.** Before this run the repo cited both in
   Kotlin and docs but held neither. They are now in `docs/nt/` and hashed.
3. **Seven of the nine contradictions are EXPOSABLE, not defects.** They are the
   corpus doing exactly what its own engine requires: naming where the path
   leaves the document for an external source.
4. **One contradiction is scoped, not dissolved.** NT10-HEALER-ANDROIDX is
   compatible under a stated scope; the cleanest fix is a corpus edit to the
   example, which is recorded as a follow-up, not silently done.

## What this proves

The corpus is not a set of essays. It is a set of claims, and each claim now
carries a status and, where it touches reality, a command that re-runs. The gate
`tools/nt_gate.py` fails the build if the corpus is cited but not carried, if a
witness fails, or if a contradiction is left unresolved. The noveltreatise engine
("show the path, log the instant, carry the citation verbatim") is now itself an
executable gate. The engine is enforced on the engine.
