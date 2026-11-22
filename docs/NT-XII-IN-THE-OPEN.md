# NT XII IN THE OPEN — a contribution ledger that mints re-runnable closure

**Status:** R&D report, first pass. Code: `tools/mint_ledger.py`, tests:
`tools/tests/mint_ledger_test.py`. Everything marked VERIFIED was re-run in this tree.
Everything marked PRIOR ART was confirmed against the upstream repository by API call on
2026-11-10 — commit counts and star counts are as returned, and none of it is quoted from
memory.

---

## 1. The claim, stated so it can fail

Bitcoin's proof of work is honest about what it buys: energy burned, a hash found, no
product. The energy is real; the output is a lottery ticket whose only use is proving you
bought it. NT XII already names the alternative — a mint is *"the real, non-arbitrary value
of the defect resolved and the bond held"*, backed by a re-runnable command.

The testable difference is **whether the work can be re-executed by someone who does not
trust the minter.** A hash cannot be re-executed to produce anything new; a closure can.
So the unit of value here is not a hash, it is a **witness**: a bounded command plus the
token it must print. Minting is not a lottery and there is no difficulty knob — you cannot
mint by burning cycles, only by producing something another party can reproduce.

That is the whole thesis. It is small enough to be wrong, which is why it is stated first.

## 2. What the open-source record actually shows

The prior art was checked by API, not recalled. The pattern in the numbers is the finding.

### Proof of useful work has repeatedly failed to leave the lab

| Project | What it does | Stars | Reading |
|---|---|---|---|
| `primecoin/primecoin` | PoW whose work is prime chains | 322 | The work is *verifiable* but not *useful* — a prime chain has no consumer. |
| `gridcoin-community/Gridcoin-Research` | Rewards BOINC volunteer compute | 613 | Real science, but the chain pays for compute it does not verify — it trusts BOINC's report. |
| `golemfactory/golem` | Marketplace for rented compute | 20 | Useful work, but settlement assumes honest execution or heavy redundancy. |

The `proof of useful work` search returns a long tail of repos between 7 and 23 stars. The
category is not unexplored; it is a graveyard of attempts that stalled on the same rock:
**useful work is expensive to verify, and cheap to claim.** A miner who claims a solved
problem and did not solve it costs nothing to check *if* verification is cheaper than
recomputation — and for most useful work it is not.

That is the exact rock NT XII's formulary sidesteps. A build witness is not an expensive
computation to verify; it is *cheap to re-run and its answer is a token*. The verification
cost is the same order as the work, which is the only regime where PoUW has ever held up.

### Sybil resistance is a solved-shaped problem with a real open stack

| Project | Mechanism | Stars |
|---|---|---|
| `privacy-ethereum/maci` | Minimal anti-collusion infrastructure — collusion-resistant voting | 595 |
| `semaphore-protocol/semaphore` | ZK anonymous membership proofs | 1,094 |
| `worldcoin/world-id-contracts` | Proof of personhood via iris uniqueness | 200 |

These are real and load-bearing. The important honest note: **none of them solves
identity.** MACI prevents collusion in a known set; Semaphore proves you are *a* member
without saying which; World ID proves a unique human at the cost of a biometric
enrollment. Each is a *narrow* primitive. The design consequence is that this ledger must
not claim to solve Sybil resistance — it must compose with these rather than reinvent
them, and it must say plainly which of the three it assumes.

### Offline-first and the data layer are settled

`automerge/automerge` (6,747 stars) is the reference for convergent, offline-first,
mergeable data. `ipfs/ipfs` (23,051) is the reference for content addressing. NT XII's
SPI-8 — *the home is the SD card, not the cloud* — is not an eccentric constraint; it is
the same constraint that produced CRDTs, and the correct answer is to copy their result,
not to invent a fourth one.

### Signing and replay protection already have standards

Confirmed present in `ethereum/EIPs` on this date: **EIP-712** (typed structured data
hashing — a domain separator, so a signature cannot be replayed across contexts),
**EIP-191** (signed data), **EIP-4337** (account abstraction), **EIP-2771** (trusted
forwarder — the sender is attested by a relayer), **EIP-1271** (contract signature
validation). The domain-separator idea in EIP-712 is the single most reusable piece here:
it is precisely the mechanism that stops a mint's signature from being valid somewhere it
was never meant to be.

## 3. What was built, and what it refuses to do

`tools/mint_ledger.py` implements the formulary as mechanism. VERIFIED in this tree.

**A mint** is `{claim, witness, expect}`. Value exists only when an independent party
re-runs the witness and it prints `expect`. A claim with no witness is refused outright —
that is the stub, and the Prime Directive forbids it.

**The witness is bounded by construction.** `execute()` never uses `shell=True`, so shell
metacharacters are inert; the check rejects shell operators *as argv tokens*, names of
network binaries (`curl`, `wget`, `nc`, `ssh`, `scp`, `rsync`), and any path that leaves
the repository. A witness must be reproducible from the tree alone.

*Correction recorded honestly:* the first version scanned raw text for `;` and rejected
`python3 -c "import x; print(y)"` — a semicolon inside a quoted token, not a separator. It
also implied a protection it did not provide. It was rewritten to check structure, and the
comment in the source says why.

**Trial net and main net are separate files, and the barrier is the gate.**

```
proof/mint_ledger.jsonl    trial net: mints + phantoms + trial receipts
proof/mint_mainnet.jsonl   main net: only what survived a green trial
```

Promotion to mainnet requires all three, with no override:

1. **at least one phantom was executed** — an untested barrier is a claim, not a barrier;
2. **every phantom FAILED** — a phantom that passes is a **PATHOGEN BREACH** and blocks
   promotion absolutely. A barrier that lets its own test case through is not a barrier,
   and promoting past it would launder a stub into mainnet with a green light attached;
3. **every candidate re-executed green** in that same trial.

This is the anti-contagion mechanism in executable form. The mimetic pathogen — a
plausible-looking stub — is *injected on purpose* on the trial net, and the gate refuses to
promote while any of it survives.

**Both ledgers are hash-chained** (each entry hashes `prev` + payload, storage layer owns
`seq`), so a rewritten line is caught. Same discipline as `nodal/ledger.py`, same reason.

## 4. Evidence

VERIFIED, this tree, this session:

```
trial: green — phantoms 2/2 caught, candidates 5/5 green
promote: PASS — promoted 5 mint(s) to mainnet
mint_ledger: PASS — trial 13 entries, mainnet 5 entries, both chains intact
MINT LEDGER TEST: PASS
```

The 5 mainnet mints were then re-executed by a separate process, not through the minting
API, and all 5 printed their expected token:

```
ok  the NT XII treatise is carried in the tree        -> NT12_PRESENT
ok  the hash-chained ledger implementation exists     -> LEDGER_PRESENT
ok  the raw chain forbids Gradle at the gate level    -> NO_GRADLE_GATE
ok  the run feed reports severance                    -> FEED_PRESENT
ok  the board states the MUST contract                -> MUST_CONTRACT
```

And the barrier was tested against itself — a phantom whose witness *succeeds*:

```
trial status is breach | the breach is named | promotion is refused
the refusal says PATHOGEN BREACH | mainnet stayed empty
```

Two real bugs were found and fixed during this work, both recorded in source comments
because both were the kind that fails silently: a default argument that froze `LEDGER` at
definition time (so a caller read the wrong file and saw an empty ledger), and
caller-supplied `seq` values that made `verify` report a broken chain on a healthy one.

## 5. What is not proven — the honest boundary

This section exists because a report that only lists successes is a stub.

- **No consensus.** This is a single-writer append-only ledger. It is not a chain with
  independent validators, and calling it a mainnet would be exactly the inflation NT XII
  warns against. It becomes a network only when a second party re-executes the witnesses
  and signs the result. Until then it is a **local proof ledger**, and that is what the
  files are named.
- **No Sybil resistance of its own.** Nothing here stops one party writing every entry.
  Composition with Semaphore or World ID is a *plan*, not a built thing. Do not describe
  this as Sybil-resistant.
- **Witnesses are only as strong as their token.** A witness that prints a constant
  (`python3 -c "print('OK')"`) mints a claim about nothing. The check that a witness is
  *meaningful* is not mechanised — only that it is bounded and reproducible. This is the
  largest open hole in the design.
- **The work is not yet metered.** NT XII prices a mint by the physical cost of the closure
  (energy, time). This ledger records that a closure happened; it does not weigh it. A
  mint of a one-line check and a mint of a full raw-chain compile are currently equal.
- **Re-execution cost is unbounded in principle.** A witness that takes an hour makes
  verification as expensive as the work. The timeout is a guard, not a solution.

## 6. The next three things, in order

1. **Meter the mint.** Record witness wall-time and output size in the receipt, so a mint
   carries a cost, not just a verdict. Without this, "real value" is a word, not a number.
2. **Second-party attestation.** The moment a second identity re-executes a witness and
   signs the receipt, this stops being a local ledger. EIP-712's domain separator is the
   right primitive for that signature; EIP-1271 is the right primitive if the second party
   is a contract.
3. **A witness-strength check.** Mechanically reject witnesses whose output cannot vary —
   e.g. no input dependence, constant output, or a token that appears in the command
   itself. This closes the biggest hole in §5 and is the difference between a proof and a
   password.

## 7. Sources

Verified by API call on 2026-11-10; star counts as returned.

- `ethereum/EIPs` — 14,068 — EIP-712, 191, 4337, 2771, 1271 all present in `EIPS/`
- `privacy-ethereum/maci` — 595 — Minimal Anti-Collusion Infrastructure
- `semaphore-protocol/semaphore` — 1,094 — ZK anonymous membership
- `worldcoin/world-id-contracts` — 200 — proof of personhood contracts
- `automerge/automerge` — 6,747 — offline-first CRDT
- `ipfs/ipfs` — 23,051 — content addressing
- `primecoin/primecoin` — 322 — useful PoW (prime chains)
- `gridcoin-community/Gridcoin-Research` — 613 — BOINC reward chain
- `golemfactory/golem` — 20 — compute marketplace

Internal: `docs/nt/NT-XII.txt` §0.8 (the mint is backed by exhaustion), §15.4 (the mint),
`README.md` §2.4 (the mint and the coupling law), `nodal/ledger.py` (hash-chained storage),
`tools/run_feed.py` (the adjacent severance ledger).
