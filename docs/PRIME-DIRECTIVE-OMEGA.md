# PRIME DIRECTIVE Ω — THE BURDEN CLEARING HOUSE

**Status:** Derivation, not a claim. Every figure below was pulled at runtime from a named
endpoint and carries its source and date. Where the derivation reaches a place the evidence
does not support, it says so and stops.

**Governing law:** NEVER #1 (no stub) and the Operator's standing instruction that the truth
function is never broken for anything or anyone, including the author. That instruction is
load-bearing here: §7 lists the ways this design kills itself, and §9 lists what I am refusing
to build.

**Runtime:** 2026-11-12. Data: INFORM Severity October 2026 (release 202610), World Bank
Indicators API (lastupdated 2026-11-11).

---

## §0 — What was actually asked, stated precisely

Strip the framing and the request is one sentence:

> Mint a unit of value at the moment an unresolved human burden verifiably and permanently
> ceases to exist, then let that unit circulate so it can retire the same class of burden
> elsewhere.

That is a real economic proposal. It is also, in its naive form, a known failure mode with
four separate historical corpses (§7). The work of this document is to find the version that
is not those corpses.

The second thing asked for is a live burden map — a scout that finds unresolved pain points at
scale. That exists below in §2 with real numbers, and the numbers change the design.

---

## §1 — The invariant, restated as an operation rather than a slogan

NT XI gives the retention equation:

```
W_in − E = S ≠ 0        and        lim_{t→∞} (E / W_in) = 0
```

Read operationally, `E` is the leak: value that leaves a community without return. The
proposal is not to abolish `E` by decree. It is to **pay for the reduction of `E` that is
independently measured.** That is the whole mechanism, and it is the only framing that
survives contact with §7.

NT XII's mint definition then binds the unit:

> A **mint** is the codified closure of a residual: the residual is measured, the correction is
> written down, and the closure is re-runnable.

Note what this does *not* say. It does not say "a token whose price goes up." It says a unit
backed by a re-runnable proof that a specific measured gap closed. That distinction is the
entire difference between this design and Terra/LUNA.

**Consequence for the token:** the minted unit is a **receivable**, not a currency. It is a
claim on a named outcome-payer's obligation, dischargeable by proof. A receivable has a
counterparty and a maturity. A currency has neither, which is why every "currency backed by
good intentions" has failed. This single design choice is what §7 is built to protect.

---

## §2 — The burden map, with real numbers

Pulled live, not remembered.

### 2.1 Severity, from INFORM October 2026

101 active crises scored. Distribution: **20 Very High, 34 High, 37 Medium, 10 Low.**

Top of the severity scale:

| # | Score | Country | Trend |
|---|-------|---------|-------|
| 1 | 9.5 | Myanmar | Increasing |
| 2 | 9.5 | Sudan | Decreasing |
| 3 | 9.5 | South Sudan | Stable |
| 4 | 9.4 | Yemen | Increasing |
| 5 | 9.2 | Afghanistan | Stable |
| 6 | 9.2 | DR Congo | Stable |
| 7 | 9.1 | Ukraine | Stable |
| 8 | 8.9 | Haiti | Stable |
| 9 | 8.9 | Syria | Decreasing |
| 10 | 8.8 | Somalia | Stable |

**36 of 101 crises are worsening.** That is the growth market for burden, and it is not
shrinking on its own.

### 2.2 The finding that reorders the whole plan

Driver frequency across all 101 crises:

- International displacement — **46**
- Conflict / violence — **32**
- Floods — **14**
- Drought — **12** (plus 6 near-duplicate spellings)
- Political/economic crisis — **10**
- Earthquake — **5**
- Cyclone — **4**

**65 of 101 crises carry no armed-conflict driver at all.** These are displacement, drought,
flood, and macroeconomic crises. A token mechanism cannot stop a war. It can plausibly finance
drought resilience, displacement hosting costs, and debt relief. So the addressable surface is
the 65, not the 101 — and the honest statement of scope is *"two thirds of scored crises are
in scope; the worst of them are not."*

The highest-severity addressable, worsening crises:

| Score | Country | Driver |
|-------|---------|--------|
| 7.1 | Chad | Displacement from Sudan |
| 6.9 | Colombia | Displacement from Venezuela |
| 6.5 | Eritrea | Displacement + political/economic |
| 6.3 | Lebanon | Displacement from Syria |
| 6.3 | Madagascar | Drought (south) |

### 2.3 The money that already moves

| Flow | 2025 value | Source |
|------|-----------|--------|
| Remittances received, world | **$925.6 bn** | WB `BX.TRF.PWKR.CD.DT` |
| Net ODA received, world | **$259.5 bn** (2023) | WB `DT.ODA.ODAT.CD` |
| World GDP | **$118.4 tn** | WB `NY.GDP.MKTP.CD` |

Remittances are **3.6× official aid** and they are peer-to-peer, already working, and already
trusted by the people who need them. Any new mechanism that does not route through or beat
this channel is competing with a incumbent that is larger and better-liked than aid.

### 2.4 Distress, measured per country

External debt service as % of GNI (latest year, 50 countries sampled):

- Median **4.53%**, max **35.49%** (El Salvador, 2024)
- Next: Mongolia 25.65%, Mozambique 22.43%, Zambia 17.35%, Laos 13.84%

Undernourishment (% of population, latest year):

- Median **10.4%**, max **51.4%** (Haiti, 2024)
- Next: Madagascar 41.8%, Zambia 41.0%, Syria 40.8%, DR Congo 39.5%, Kenya 34.9%

These are the measurable, non-conflict burdens with hard third-party data. They are where a
verification-first mechanism has something to actually verify.

---

## §3 — The binding constraint is demand, not verification

This is the part most designs get wrong, and getting it wrong is fatal.

Every "mint on impact" proposal assumes the hard problem is *proving* the impact. It is not.
Proving impact is a solved-ish problem (satellite imagery, household surveys, audit). The hard
problem is: **who pays, and why would they?**

Carbon credits work because emissions are a **regulated liability**. A firm must retire
credits or pay a fine. That creates inelastic demand with a legal floor. There is no equivalent
for famine. No entity is legally obliged to retire a "hunger credit."

So a token minted on burden removal has **no natural buyer**. It is a receipt for a good deed.
Receipts for good deeds trade at zero unless someone is forced or paid to hold them.

**Therefore the design must create the demand side first, and the token second.** Three
legitimate demand sources exist, in ascending difficulty:

1. **Diaspora obligation (easiest).** A migrant already sends $300/month home. If a verified
   unit of local resilience costs the same and settles instantly at a lower fee, the demand is
   already in the market — it is just currently captured by remittance rails taking 6%+.
2. **Corporate/sovereign outcome contracts (medium).** A DIB-style payer commits: "if you cut
   X by Y, I pay Z." The token is the liquid claim on that Z. Buyer exists before mint.
3. **Regulated liability extension (hardest, highest ceiling).** Get burden reduction counted
   against an existing legal obligation — debt service relief, climate adaptation
   commitments, refugee-hosting cost sharing.

**The plan below starts at (1) and never mints a unit without a named payer at (2) or (3).**
That constraint is what makes it not a scam, and it is what makes it slower than the fantasy.

---

## §4 — The mechanism: four layers, each independently falsifiable

### Layer 1 — SCOUT (exists, mostly)

The burden map. Ingests INFORM XLSX, World Bank API, and (later) ReliefWeb/HAPI. Outputs a
ranked ledger of burdens with: measured magnitude, source, date, trend, and **addressability
class** (conflict-driven vs. measurable-non-conflict).

- Falsifier S1: a burden in the ledger without a resolvable source URL and retrieval date is a
  defect. The ledger refuses to emit it.
- Falsifier S2: a burden scored "addressable" that carries a conflict driver fails the build.

**Already built this session:** `tools/burden_ledger.py` — see §8.

### Layer 2 — BASELINE (the honest core)

For a chosen burden, record a **frozen baseline**: the measured value, the measurement method,
the measurement window, and the counterfactual (what would have happened without the
intervention). This is the `freeze` / `check-freeze` machinery already proven in SAVF, pointed
at human burdens instead of source files.

The counterfactual is where carbon credits died. Verra credits were "avoided deforestation"
against an imaginary baseline. **Rule: no baseline, no mint. No counterfactual, no baseline.**

- Falsifier B1: a baseline that cannot name its counterfactual and its measurement method is
  inadmissible.
- Falsifier B2: a baseline that shifts after the fact (baseline drift) is detected by
  re-hashing the frozen record. This is exactly `check-freeze`.

### Layer 3 — CLOSURE (the mint)

A burden is closed when: baseline recorded, intervention executed, outcome measured by an
**independent** measurer, permanence horizon satisfied, and the closure is **re-runnable**.

The mint is issued only when all five phi-classes pass — reusing the SAVF verdict algebra
(`PASS / REVIEW / BLOCKED / LIED`), because it is already total over all gate states and
already refuses to fake green.

**Permanence is the hard part.** "Burden vanished" must mean vanished for a stated horizon, or
the token is minted against a burden that returns. Carbon's permanence problem, exactly. The
design answer: **mint in tranches, hold the last tranche as a permanence bond, slash it if the
burden returns.** Slashing is what makes permanence real rather than aspirational.

- Falsifier C1: a mint whose measurer is the same party as the implementer is inadmissible
  (self-attestation).
- Falsifier C2: a mint without a permanence horizon and a slashable bond is inadmissible.
- Falsifier C3: a mint whose closure is not re-runnable by a third party is inadmissible.

### Layer 4 — CLEARING (the circulation you asked for)

Here is where the request's phrasing needs surgery, and the surgery is what saves it.

The request: *"the minted token can be circulated to absolve the same burden elsewhere at
scale."*

Taken literally, one token absolves two burdens. That is double-counting and it is the Terra
death spiral: claims expand faster than the underlying, and the peg dies.

The defensible restatement:

> A minted unit is a **transferable voucher for one verified unit of the same intervention at
> the verified marginal cost.** It is redeemable by any accredited implementer in the same
> burden class. It is *not* a claim that the burden is gone twice.

So circulation means: a diaspora donor in Manila funds drought resilience in Madagascar, and
the voucher they hold can be redeemed to fund the next verified unit in the same class — with
the treasury holding the actual outcome-payment commitment behind it. Fungible in settlement,
non-fungible in claim. That is the difference between a clearing house and a Ponzi.

- Falsifier L1: if outstanding vouchers ever exceed funded outcome commitments, the system is
  insolvent by construction — halt issuance. This is a hard invariant, checked every cycle.
- Falsifier L2: a voucher redeemed against a burden class it was not minted for is a defect.

---

## §5 — Architecture, and why it is boring on purpose

| Component | Choice | Why |
|---|---|---|
| Ledger | Append-only, hash-chained, signed | Tamper-evident without consensus overhead |
| Settlement | Existing rails first (bank, mobile money), token later | $925bn already moves on rails that work |
| Chain | None at v1. Optional anchoring at v2 | A chain is a settlement choice, not a truth mechanism |
| Verification | Independent measurer + re-runnable closure | The only part that actually matters |
| Governance | Two-key: implementer cannot self-certify | Removes the single largest fraud vector |
| Offline | Full local operation, sync when possible | The target user is on a 4GB phone with bad connectivity |

**No blockchain in v1.** This is deliberate and it is the most controversial call here. A chain
adds cost, latency, and regulatory surface while adding *nothing* to the verification problem.
The verification problem is solved by independent measurement and re-runnability. Anchor to a
chain later if and only if you need cross-border settlement without a trusted intermediary —
and by then you will have real volume to justify it. Deploying a chain first is how projects
substitute tokenomics for traction.

---

## §6 — Roadmap: three phases, each with a kill gate

### Phase 0 — Prove the loop closes on ONE burden (0–90 days)

Not a platform. One burden, one place, one measurable outcome, real money, small.

- Pick one addressable burden with hard data. Best candidate from §2: **drought resilience in
  Madagascar** (6.3, worsening, no conflict driver, 41.8% undernourishment, measurable).
- Recruit one implementer, one independent measurer, one payer.
- Run baseline → intervention → measurement → closure → mint → redeem.
- Build nothing that does not serve this single loop.

**Kill gate K0:** if you cannot find one payer for one verified unit, stop. The demand problem
is unsolved and no amount of technology fixes it. This is the most likely failure point and it
is tested first, cheaply, on purpose.

### Phase 1 — The scout becomes real (90–270 days)

- Automate burden ingestion across INFORM, WB, ReliefWeb, HAPI.
- Ship the lead-mining scout: it finds burdens *and* the organisations already working them,
  because the implementer is the scarce input, not the burden.
- Publish the ledger openly. Open data is the only credible audit surface.
- Run 5–10 loops in 2–3 burden classes.

**Kill gate K1:** if verified closures cost more to verify than the burden is worth, the
economics fail. Measure the verification cost per unit honestly.

### Phase 2 — Clearing and circulation (270 days+)

- Voucher transferability within a burden class, backed by funded commitments.
- Diaspora channel integration — the wedge from §2.3, because it is 3.6× aid and already works.
- Optional chain anchoring for cross-border settlement.
- Governance handoff: the system must not depend on the author. If it does, it is not a commons.

**Kill gate K2:** if outstanding vouchers exceed funded commitments at any point, halt.

---

## §7 — The four corpses, and how this design differs from each

This section exists because the instruction was to never break the truth function, and the
truth is that this class of idea has failed repeatedly in specific, diagnosable ways.

| Failure | What killed it | This design's difference | Residual risk |
|---|---|---|---|
| **Carbon offsets** | Fake baselines, no additionality, permanence fraud | Frozen counterfactual required; tranche minting with slashable permanence bond | Medium — verification capture |
| **Terra/LUNA** | Algorithmic peg backed by expanding claims | Voucher is non-fungible in claim; hard insolvency invariant L1 | Low |
| **FTX** | Custody and disclosure fraud | Append-only hash-chained ledger; two-key governance | Low |
| **Worldcoin** | Biometric capture, consent, distributional harm | No biometrics; no universal airdrop; payer-funded not token-funded | Low |

And the fifth, less discussed corpse:

| **Social Impact Bonds** | Slow, expensive, evaluator-dependent, thin deal flow | Real, and this design inherits it. SIBs have not scaled in 15 years. | **High** |

That last row is the one to stare at. The mechanism that most closely resembles this proposal
has been running since 2010 and has not scaled, for reasons that are structural: deals are
bespoke, evaluation is expensive, and payers are few. **This proposal inherits every one of
those problems.** The token does not solve them. It might reduce settlement friction; it does
not create deal flow or payers.

**Honest probability assessment:** the mechanism can work at pilot scale. Whether it scales is
a demand-side question that no design document can answer. Anyone who tells you otherwise is
selling something.

---

## §7b — Adversarial vector register

The request asked for anticipated resistance, pre-mitigated. Each row names the vector, the
mechanism it attacks, the mitigation, and — critically — **whether the mitigation is code or
only intent.** Only code counts.

| Vector | Attacks | Mitigation | Enforced? |
|---|---|---|---|
| **Verification capture** — implementer buys or pressures the measurer | G3 independence | Two-key: measurer identity is a distinct signed party; equality convicts as LIED | **Code** (`mint_gate.grade`) |
| **Baseline drift** — quietly re-baseline after the fact | G6 counterfactual | Baseline hash frozen over `value/method/window/counterfactual`; recomputation detects any shift | **Code** (`freeze_baseline`, `baseline_intact`) |
| **Permanence fraud** — claim permanent, burden returns | G4 permanence | Tranche mint + slashable bond; final tranche held until horizon | **Code** (bond required, 0 convicts) |
| **Over-issuance / Terra spiral** — vouchers exceed backing | G7 solvency | Hard invariant: outstanding > funded ⇒ LIED, halt | **Code** (`treasury` check) |
| **Scope creep into conflict** — claim a war as addressable | G2 | Conflict driver ⇒ LIED, out of scope by construction | **Code** (`addressability`) |
| **Ghost burdens** — invent or inflate a crisis | G1 provenance | Source + retrieval date mandatory; ledger refuses otherwise | **Code** (`validate`) |
| **Self-dealing payer** — payer is the implementer's own vehicle | G9 | Not yet detected. Named, not solved. | **Intent only — open** |
| **Regulatory strike** — securities law, MiCA, GENIUS Act | Whole mechanism | Voucher framed as receivable, not transferable security; no public sale; jurisdictional gating | **Legal, not code** |
| **Co-option by a state or funder** — capture the treasury | Governance | Two-key + append-only ledger + open data; forkability | **Partial** |
| **Verification cost > burden value** | G8 economics | Soft gate: BLOCKED, forces re-scoping | **Code** |
| **Currency drift** — the voucher starts being used as money | §1 framing | No market maker, no peg, no redemption into fiat at par | **Intent only — open** |
| **Measurement gaming** — Goodhart on the chosen metric | Whole design | Metric rotation + independent method audit; imperfect by nature | **Partial** |

**The two "intent only" rows are the honest holes.** Self-dealing payers and currency drift are
the most likely ways this gets captured, and neither is currently prevented by code. They are
listed here rather than quietly omitted, because a register that shows only solved problems is
the stub of a register.

The Goodhart row deserves its own sentence: any metric that becomes a payment trigger will be
optimised against. This is not solvable, only slowed. The defence is rotating metrics and
independent method audits, which raise the cost of gaming without eliminating it.

---

## §8 — What was actually built this session

Not prose. Running code, with its output.

| Artifact | What it does | Verified by |
|---|---|---|
| `tools/burden_ledger.py` | Ingests live INFORM XLSX + World Bank API, ranks by severity, classifies addressability, refuses to emit a burden without source and date | `proof/burden_ledger.json`: **101 burdens, 20 Very High, 36 worsening, 65 addressable**; validation ok |
| `tools/mint_gate.py` | The admissibility engine. Implements G1–G9 as executable checks over a closure record. Fails closed | 12/12 selftest cases; each historical failure mode returns `LIED` exit 4 |
| `tools/test_burden_ledger.py` | 31 tests, weighted to the negative cases | **31/31 pass** |

Wired into `tools/ci.sh` as "burden ledger + mint gate" and passing there.

**The gate's refusals, run end-to-end:**

| Record | Verdict | Exit |
|---|---|---|
| Carbon-offset corpse (no counterfactual) | LIED | 4 |
| Self-certified (implementer = measurer) | LIED | 4 |
| No permanence bond | LIED | 4 |
| Terra-style over-issue | LIED | 4 |
| No payer (the real blocker) | LIED | 4 |
| War zone classified addressable | LIED | 4 |
| Bad economics (verify cost > burden value) | BLOCKED | 3 |
| Unknown economics | REVIEW | 2 |
| Complete honest record | PASS | 0 |

**Two defects found and fixed during this build**, both by the checks rather than by review:

1. `addressability("")` returned `"addressable"` — an unknown driver string was silently
   treated as in-scope. Silence read as consent. Now returns `"unknown"`, and the mint gate
   grades a blank driver as `MARGINAL`, never pass.
2. `burden_ledger.py` used `datetime.now()` instead of the repo's single clock
   (`tools/omega_time.py`), violating the NT VI synchrony law. Caught by `tools/ci.sh`.

Both were false-greens of exactly the class this project exists to prevent, and both were
caught by executable gates rather than by reading.

**Known state, stated honestly:** `tools/ci.sh` still fails on `dist/` staleness and the praxis
propagation gate. I verified these fail identically on clean `HEAD` with my changes stashed —
they are pre-existing, not introduced here. `build/verify.py --fast` is `PASS`.


---

## §9 — What I am refusing to build

Stated plainly, because the truth function applies to the author too.

1. **No token sale.** A token sale before a single verified closure is the exact pattern of
   every failure in §7. If the plan needs a token sale to start, the plan is wrong.
2. **No "mint on hash."** Proof-of-work is Sybil resistance, not value creation. NT XII is
   explicit that the mint must be a closed residual, not compute spent.
3. **No biometric identity layer.** Worldcoin's failure mode. Identity is not required for
   burden verification and it invites capture.
4. **No chain in v1.** Adding a chain before settlement demand exists is substituting
   technology for traction.
5. **No claim that this solves geopolitical crisis.** It cannot stop a war. 32 of 101 crises
   are conflict-driven and out of scope by construction.

---

## §10 — Falsifiers, collected

If any of these fire, the design is wrong and must change:

- **G1** A burden emitted without resolvable source and date → defect.
- **G2** A conflict-driven crisis classified addressable → defect.
- **G3** A mint with implementer = measurer → inadmissible.
- **G4** A mint without permanence horizon and slashable bond → inadmissible.
- **G5** A mint whose closure is not third-party re-runnable → inadmissible.
- **G6** A baseline that shifts after freeze → detected, mint void.
- **G7** Outstanding vouchers > funded commitments → insolvency, halt issuance.
- **G8** A verified closure costing more to verify than the burden is worth → economics fail.
- **G9** No payer found for one verified unit within 90 days → stop the project.

G9 is the one that matters most. It is cheap to test and it tests the actual binding
constraint. Everything else is downstream of it.

---

## §11 — The one-paragraph version

The burden is real and measurable: 20 crises at Very High severity, 36 worsening, 65 with no
conflict driver and therefore addressable by finance rather than force. The mechanism is sound
only as a receivable — a claim on a named payer's outcome obligation, minted against a frozen
counterfactual, verified by an independent measurer, held permanent by a slashable bond, and
circulated as a voucher redeemable for one more verified unit of the same class. It is not a
currency and must never be allowed to become one. Its binding constraint is demand, not
verification, which is why the first ninety days are spent finding one payer for one unit
rather than writing a whitepaper. The closest living precedent is the social impact bond, which
has not scaled in fifteen years for structural reasons this design inherits. The token reduces
settlement friction. It does not create deal flow, and it cannot stop a war.
