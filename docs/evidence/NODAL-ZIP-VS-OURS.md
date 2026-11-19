# nodal.zip vs the nodal/ already in this repo

Question asked: are the bots we have similar to the bots in nodal.zip?

Answer: they are the same design, not the same code. The zip is an earlier,
smaller, independently-written implementation of the identical contract. Ours is
a later, hardened superset. Every claim below was produced by running both, not
by reading the READMEs.

## Provenance

- `nodal.zip` — 12,305 bytes, sha256 `68eea5bda7f96a6d172f0a6893c56d40a81e1be5f1fae611b922a3807a1aacc8`,
  9 entries, dated 2026-11-19. Contains README.md, nodal/{schema,ledger,bot,example_bots,__init__}.py,
  tests/test_end_to_end.py.
- `nodal/` in this repo — tracked since commit `a7e46d6` ("Auto-Nodal Co-ordina-Sync
  substrate, Python authority + .js SAVF twin, MUST #37"). Contains
  {schema,ledger,bot,engine,__init__}.py plus tests/test_nodal.py.

Both implement the same core: a `Receipt` with a closed verdict enum where
DEGRADED requires a named `degraded_class` and every other verdict forbids one;
a hash-chained append-only ledger with an epoch read-barrier; and a `NodalBot`
whose `fire()` is total.

## Measured differences

| Property | nodal.zip | ours |
|---|---|---|
| Modules | 4 + test | 5 + test |
| Test count | 6 assertions in 1 script | 43 unittest cases |
| Test result | ALL END-TO-END ASSERTIONS PASSED | Ran 43 tests, OK |
| Extra module | none | `engine.py` (215 lines): fire ordering, reconcile, degraded propagation |
| Storage immutability | none | BEFORE UPDATE / BEFORE DELETE triggers RAISE(ROLLBACK) |
| Genesis witness | `""` | `sha256("DARKITH_NODAL_GENESIS_v1")` |
| seq after restart | collides (defect) | resumes from `MAX(seq)` |
| Returned receipt id | wrong after first fire (defect) | always matches stored id |
| Stale-epoch guard | none | stale writer may only append DEGRADED |
| `hash_input` on dicts | `repr()` — order-sensitive | `repr()` — order-sensitive |

## Defects found in the zip by running it

1. **Returned receipt id is wrong after the first fire.** `Ledger.append()`
   rebuilds the receipt with the ledger-computed witness, so the stored row has a
   different `receipt_id` than the `Receipt` object handed back to the caller. The
   caller then holds a receipt whose id is not in the ledger. Observed: fire #1
   matched, fire #2 returned `9403b854…` while the ledger stored `fac7b472…`.
   Ours fixes this: `AppendResult` carries the final receipt and both ids match.

2. **`seq` counter is per-instance and in-memory only.** Constructing a second
   `LineLengthGate` on the same lane restarts `_seq` at 0, so the next fire hits
   `UNIQUE(lane, seq)` and is rejected — while still returning a receipt object to
   the caller. Observed: `accepted=False`, `reason=duplicate seq in lane`, and the
   returned receipt was not in the ledger. Ours reads `MAX(seq)` in `__init__`, so
   the second instance correctly continued at seq=1.

3. **No storage-level immutability.** In the zip, a direct
   `UPDATE receipts SET clause='TAMPERED'` succeeds and `verify_chain` still
   returns `[]`, because the witness chain covers ancestry but not field content.
   Ours raises `receipts is append-only: UPDATE forbidden` from a SQLite trigger.

## What the zip has that ours does not

- `example_bots.py` — three concrete, runnable bots (`LineLengthGate`,
  `TodoRouteGate`, `BuggyGate`) with a real upstream chain and a deliberately
  broken bot that proves the total-function guarantee against an actual exception.
  Ours has the contract and the engine but no worked example bots. This is the one
  genuine thing worth taking from the zip.

## Semantic limitation shared by both, not a defect

The upstream-existence check is skipped when `verdict == DEGRADED`. That is
correct: a DEGRADED/UPSTREAM_MISSING receipt exists specifically to cite ids that
are absent. The consequence is that `upstream_ids` on a DEGRADED receipt are an
unverified claim rather than a checked fact. Neither implementation distinguishes
"these ids were missing when I looked" from "these ids are fabricated". If that
distinction matters, it needs a separate field, not a change to this check.

## The honest reading

The zip is not a competitor and not a regression. It is the same idea built
smaller and earlier, with two real bugs that ours does not have, plus one useful
artifact (worked example bots) that ours lacks. Copying the zip over `nodal/`
would be a downgrade. Copying `example_bots.py` in, adapted to our API, would be
a small upgrade.

Neither implementation sandboxes `decide()`, neither has cross-machine ledger
reconciliation, and neither implements the five "ClearanceLoop engines". The zip's
README says so plainly and that assessment is correct.

## Reproduction

    python3 -c "import zipfile;zipfile.ZipFile('nodal.zip').extractall('/tmp/nodal_x')"
    cd /tmp/nodal_x && python3 tests/test_end_to_end.py
    cd /workspace/project/darkith-forge && python3 tests/test_nodal.py
