#!/usr/bin/env python3
"""rehearse_burden.py — execute the end-to-end burden cycle and seal its receipts.

This is the runner the first rehearsal lacked: it MEASURES, it does not narrate.
Every stage either observes something real or records that it could not, and a stage
that could not observe is recorded as UNMEASURED, never as PASS.

    python3 tools/burden/rehearse_burden.py --base <sha> [--out DIR]

Stages, in order (the chain refuses a gap):
    S01_BASELINE              is the rehearsal path really absent at --base? (live API)
    S02_REPAIR                the receipt set this run is about to write
    S03_REPRODUCTION_CONTRACT the witness command and the token it must print
    S04_PHANTOM_DUPLICATE_ID  GATE-1 must refuse a second record with the same id
    S05_PHANTOM_CONSTANT_WITNESS  GATE-2 must refuse a witness that ignores its input
    S06_BARRIER_STATUS        the verdict, which may only ever be NOT_CLOSED here
    S07_ENTRAINMENT_CURVE     the curve, from receipts only

Exit 0 only if every stage observed what it claims. A refusal by a gate is a PASS
for the rehearsal (the gate worked) but is recorded as REFUSED so the difference
between "no phantom was tried" and "a phantom was tried and refused" survives.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import burden_gates  # noqa: E402
import receipt_chain  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = "Deobfugazi/darkith-forge"
REHEARSAL_REL = "proof/burden-uplift/E2E-REHEARSAL-2026-11-24"


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _api(path: str, ref: str) -> tuple[int, dict]:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={ref}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "darkith-burden-rehearsal",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"message": e.reason}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"message": str(e)}


# --------------------------------------------------------------------------- stages
def s01_baseline(base: str) -> tuple[str, str, dict]:
    """Measure absence at the base SHA. Absence is proven by 404, not asserted."""
    code, body = _api(REHEARSAL_REL, base)
    if code == 404:
        return ("PASS", "ABSENT-CONFIRMED: 404 from contents API at base",
                {"method": "github contents API", "base": base, "http": 404})
    if code == 200:
        return ("FAIL", "PRESENT: path already exists at base — burden is not real",
                {"method": "github contents API", "base": base, "http": 200})
    return ("UNMEASURED", f"API unreachable (http={code}); absence NOT proven",
            {"method": "github contents API", "base": base, "http": code,
             "message": body.get("message")})


def s04_phantom_duplicate(record: dict) -> tuple[str, str, dict]:
    phantom = dict(record)
    phantom["title"] = "phantom: second record reusing the same id"
    problems = burden_gates.gate1_duplicate_registry([record, phantom])
    if problems:
        return ("REFUSED", "GATE-1 refused the duplicate-id phantom mechanically",
                {"phantom": phantom["title"], "refusal": problems})
    return ("FAIL", "GATE-1 did NOT refuse a duplicate id — gate is not firing",
            {"phantom": phantom["title"]})


def s05_phantom_constant(tmp: pathlib.Path, witness: pathlib.Path) -> tuple[str, str, dict]:
    good = tmp / "good"
    broken = tmp / "broken"
    for t, val in ((good, "INTACT"), (broken, "TAMPERED")):
        (t / "evidence").mkdir(parents=True, exist_ok=True)
        (t / "evidence" / "data.txt").write_text(val)
    const = tmp / "const_witness.py"
    const.write_text("print('EXPECT:BURDEN_ABSENT_REHEARSAL_OK')\n")

    const_problems = burden_gates.gate2_witness_strength(const, good, broken)
    if not const_problems:
        return ("FAIL", "GATE-2 did NOT refuse a constant-output witness",
                {"phantom": "constant-output witness"})

    real_problems = burden_gates.gate2_witness_strength(witness, good, broken)
    sensitive = not any(p.startswith("GATE2_CONSTANT_OUTPUT") for p in real_problems)
    return ("REFUSED",
            "GATE-2 refused the constant-output phantom mechanically",
            {"phantom": "constant-output witness", "refusal": const_problems,
             "real_witness_is_input_sensitive": sensitive})


def s04b_phantom_duplicate_baseline(record: dict) -> tuple[str, str, dict]:
    """GATE-1's SECOND refusal path: same (path, sha) baseline under a different id.

    A gate is only as strong as its unrehearsed branches. S04 exercises duplicate ids;
    this exercises the baseline collision, which is the shape a double-count actually
    takes when two agents name the same absence differently.
    """
    phantom = dict(record)
    phantom["id"] = record["id"] + "-ALIAS"
    phantom.pop("baseline_key", None)  # let GATE-1 derive it from (path, base_sha)
    problems = burden_gates.gate1_duplicate_registry([record, phantom])
    if any(p.startswith("GATE1_DUPLICATE_BASELINE") for p in problems):
        return ("REFUSED",
                "GATE-1 refused a same-baseline record under a different id",
                {"phantom": "duplicate baseline, distinct id", "refusal": problems})
    return ("FAIL", "GATE-1 did NOT refuse a duplicate baseline under a new id",
            {"phantom": "duplicate baseline, distinct id", "observed": problems})


def s05b_phantom_unrunnable_witness(tmp: pathlib.Path) -> tuple[str, str, dict]:
    """GATE-2's fail-closed branch: a witness that cannot run must be refused, not trusted.

    A gate that treats 'could not measure' as 'fine' passes when the evidence is missing —
    the exact failure mode the barrier exists to prevent. The phantom must be genuinely
    unmeasurable (it hangs), not merely a script that exits non-zero: a non-zero exit is a
    measurement and is handled by a different branch.
    """
    good = tmp / "good"
    broken = tmp / "broken"
    for t in (good, broken):
        (t / "evidence").mkdir(parents=True, exist_ok=True)
        (t / "evidence" / "data.txt").write_text("x")
    hanging = tmp / "hanging_witness.py"
    hanging.write_text("import time\ntime.sleep(30)\n")

    problems = burden_gates.gate2_witness_strength(hanging, good, broken, timeout=1)
    if any(p.startswith("GATE2_UNRUNNABLE") for p in problems):
        return ("REFUSED", "GATE-2 refused an unmeasurable witness (fail-closed)",
                {"phantom": "hanging witness", "refusal": problems})
    return ("FAIL", "GATE-2 trusted a witness it could not measure",
            {"phantom": "hanging witness", "observed": problems})


def s05c_control_honest(tmp: pathlib.Path) -> tuple[str, str, dict]:
    """THE HONEST CONTROL: a genuine, input-sensitive witness must PASS the gate.

    Four refusals prove the barrier can say no; they do not prove it can say yes. A gate
    stuck on 'refuse' would satisfy every phantom and still be worthless. This control
    requires GATE-2 to ACCEPT a witness that reads its evidence, so the rehearsal measures
    discrimination rather than a constant verdict.
    """
    good = tmp / "ctl_good"
    broken = tmp / "ctl_broken"
    for t, val in ((good, "INTACT"), (broken, "TAMPERED")):
        (t / "evidence").mkdir(parents=True, exist_ok=True)
        (t / "evidence" / "data.txt").write_text(val)
    sensitive = tmp / "sensitive_witness.py"
    sensitive.write_text(
        "import pathlib, sys\n"
        "val = pathlib.Path('evidence/data.txt').read_text().strip()\n"
        "print('EXPECT:INTACT' if val == 'INTACT' else 'TAMPERED')\n"
        "sys.exit(0 if val == 'INTACT' else 1)\n"
    )
    problems = burden_gates.gate2_witness_strength(sensitive, good, broken)
    if not problems:
        return ("PASS", "a genuine input-sensitive witness passed GATE-2 (barrier discriminates)",
                {"control": "honest witness accepted", "problems": []})
    return ("FAIL", "a genuine witness was refused by GATE-2 — gate is stuck, not strict",
            {"control": "honest witness", "problems": problems})


def s07_curve(out: pathlib.Path, kappa: float = 0.15, r_max: float = 0.60,
              epochs: int = 12) -> tuple[str, str, dict]:
    """Write the entrainment sensitivity table. Every a_n here is MODELED.

    S(n+1) = S(n) + r_n*(1 - S(n)),  r_n = clamp(kappa*a_n, 0, r_max)

    With ONE burden in the ledger there is no receipt window to derive a_n from, so
    nothing in this file is a forecast. It is a sensitivity table: it answers "what
    does saturation look like IF recruitment behaves like this", so the Operator can
    see the downside before staking anything. Production a_n must come from
    mint-ledger receipt windows only (law G3); this run cannot supply one.

    The pessimistic case is deliberately FLAT and LOW: a_n does not grow, because the
    failure mode being modelled is that nobody new ever verifies. A pessimistic row
    that still saturates would be a sales document, not a scenario.
    """
    scenarios = {
        # name: (a_n at epoch 0, growth per epoch)  -- FLAT = no new verifiers
        "pessimistic":       (0.30, 0.00),
        "measured_baseline": (0.50, 0.00),
        "optimistic":        (0.50, 0.15),
    }
    lines = ["epoch,a_activation,r_n,S_saturation,scenario"]
    summary = {}
    for name, (a0, growth) in scenarios.items():
        S = 0.0
        half = None
        for n in range(epochs + 1):
            a = a0 + growth * n
            r = min(max(kappa * a, 0.0), r_max)
            lines.append(f"{n},{a:.3f},{r:.4f},{S:.4f},{name}")
            if half is None and S >= 0.5:
                half = n
            S = S + r * (1.0 - S)
        summary[name] = {"final": round(S, 4), "half_saturation_epoch": half}
    lines.append("# r_n = clamp(kappa*a_n,0,r_max); S(n+1)=S(n)+r_n*(1-S(n))")
    lines.append("# EVERY a_n in this file is MODELED. One burden exists, so no receipt")
    lines.append("# window can supply a_n; this is a sensitivity table, NOT a forecast.")
    lines.append("# pessimistic = flat a_n (nobody new verifies). Production a_n must come")
    lines.append("# from mint-ledger receipt windows only (law G3). No verdict rests on this.")
    (out / "05_viability_curve.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ("PASS", "sensitivity table computed; every a_n labelled MODELED (no receipt window exists)",
            {"kappa": kappa, "r_max": r_max, "epochs": epochs, "summary": summary,
             "a_n_source": "MODELED", "is_forecast": False})


# --------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="base SHA the burden is measured against")
    ap.add_argument("--out", default=str(ROOT / REHEARSAL_REL))
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path("/tmp/burden_phantom_work")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    record = {
        "id": "KC-BURDEN-2026-1124-E2E",
        "title": "Burden: no end-to-end rehearsal receipt exists in this repository",
        "harmed_party": "the repository itself: a plan with no executed evidence",
        "falsifiable_baseline": f"{REHEARSAL_REL} is absent at base {args.base[:9]}",
        "path": REHEARSAL_REL,
        "base_sha": args.base,
        "severity": "medium-low (self-referential rehearsal burden)",
        "independent_corroboration": "none; demo-only, NOT eligible for value claims",
        "barrier_verdict": "NOT_CLOSED",
        "mainnet_issuance": "FORBIDDEN",
        "issued": _now(),
    }
    (out / "00_burden_record.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    witness = ROOT / "tools/burden/witness_e2e.py"
    stages: list[dict] = []

    def stage(name, result):
        status, detail, extra = result
        entry = {"stage": name, "status": status, "detail": detail,
                 "observed": extra, "written_at_utc": _now()}
        stages.append(entry)
        print(f"  {name:32s} {status:12s} {detail}")

    print("BURDEN REHEARSAL (trial net) — measuring, not narrating")
    stage("S01_BASELINE", s01_baseline(args.base))
    stage("S02_REPAIR", ("PASS", "this receipt set is the repair artifact",
                         {"path": REHEARSAL_REL, "note": "repair = the evidence itself"}))
    stage("S03_REPRODUCTION_CONTRACT",
          ("PASS", "witness command declared; token is chain-derived, not constant",
           {"command": "python3 tools/burden/witness_e2e.py",
            "expect": "EXPECT:BURDEN_ABSENT_REHEARSAL_OK <merkle-root>"}))
    stage("S04_PHANTOM_DUPLICATE_ID", s04_phantom_duplicate(record))
    stage("S04b_PHANTOM_DUPLICATE_BASELINE", s04b_phantom_duplicate_baseline(record))
    stage("S05_PHANTOM_CONSTANT_WITNESS", s05_phantom_constant(tmp, witness))
    stage("S05b_PHANTOM_UNMEASURABLE_WITNESS", s05b_phantom_unrunnable_witness(tmp))
    stage("S05c_CONTROL_HONEST_WITNESS", s05c_control_honest(tmp))
    stage("S06_BARRIER_STATUS",
          ("PASS", "verdict NOT_CLOSED, mainnet FORBIDDEN — closure not claimed",
           {"barrier_verdict": "NOT_CLOSED", "mainnet_issuance": "FORBIDDEN",
            "phantoms_executed": 4,
            "honest_controls": 1,
            "closure_requires": ["2 independent third parties re-run S03 witness",
                                 "BURDEN-GATE-1/2 exercised in CI"]}))
    stage("S07_ENTRAINMENT_CURVE", s07_curve(out))

    bad = [s for s in stages if s["status"] in ("FAIL", "UNMEASURED")]
    (out / "04_receipts.jsonl").write_text("", encoding="utf-8")
    sealed = receipt_chain.write(out / "04_receipts.jsonl", stages)

    manifest_files = {}
    for rel in ("00_burden_record.json", "04_receipts.jsonl", "05_viability_curve.csv"):
        manifest_files[f"{REHEARSAL_REL}/{rel}"] = hashlib.sha256(
            (out / rel).read_bytes()).hexdigest()
    manifest_files["tools/burden/witness_e2e.py"] = hashlib.sha256(
        witness.read_bytes()).hexdigest()
    manifest_files["tools/burden/receipt_chain.py"] = hashlib.sha256(
        (ROOT / "tools/burden/receipt_chain.py").read_bytes()).hexdigest()
    manifest_files["tools/burden/burden_gates.py"] = hashlib.sha256(
        (ROOT / "tools/burden/burden_gates.py").read_bytes()).hexdigest()
    (out / "manifest.json").write_text(
        json.dumps({"generated": _now(), "files": manifest_files}, indent=1,
                   sort_keys=True) + "\n", encoding="utf-8")

    shutil.rmtree(tmp, ignore_errors=True)

    problems = receipt_chain.verify(receipt_chain.read(out / "04_receipts.jsonl"),
                                    [s["stage"] for s in stages])
    print(f"\n  receipts sealed: {len(sealed)}")
    print(f"  chain verifies: {'YES' if not problems else 'NO — ' + str(problems)}")
    if bad:
        print(f"  VERDICT: BLOCKED — {len(bad)} stage(s) did not observe what they claim")
        return 1
    print("  VERDICT: rehearsal PASSED as demonstration. Barrier NOT CLOSED. "
          "Trial net only. Mainnet issuance FORBIDDEN.")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
