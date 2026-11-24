#!/usr/bin/env python3
"""Burden ledger: ingest live burden data, rank by severity, classify addressability.

Every emitted burden carries its source and retrieval date.  A burden without a
resolvable source is a defect, not a data point (falsifier G1).  A conflict-driven
crisis marked addressable is a defect (falsifier G2): finance cannot retire a war.

Stdlib only, except openpyxl for the INFORM workbook (optional; the World Bank path
needs nothing).

    python3 tools/burden_ledger.py --inform path/to/inform.xlsx --out proof/burden_ledger.json
    python3 tools/burden_ledger.py --live --out proof/burden_ledger.json
"""

import argparse
import json
import sys
import time
import urllib.request

from omega_time import stamp as _omega_stamp

CONFLICT_TOKENS = ("conflict", "violence")
# Spelling variants appear in the real INFORM sheet ("Drought/drier conditi...").
DROUGHT_TOKENS = ("drought",)

WB_SERIES = {
    "remittances_usd": "BX.TRF.PWKR.CD.DT",
    "oda_usd": "DT.ODA.ODAT.CD",
    "gdp_usd": "NY.GDP.MKTP.CD",
    "undernourishment_pct": "SN.ITK.DEFC.ZS",
    "debt_service_gni_pct": "DT.TDS.DECT.GN.ZS",
    "u5_mortality": "SH.DYN.MORT",
}


def _now():
    return _omega_stamp()


def _get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "darkith-burden-ledger/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def addressability(drivers):
    """Return 'conflict', 'addressable', or 'unknown' from an INFORM driver string.

    Conflict is checked first: a crisis that is both drought- and conflict-driven is
    not addressable by finance, because the finance cannot reach the drought while the
    conflict persists.  An absent driver string is 'unknown', never 'addressable' —
    silence must not be read as in-scope.
    """
    d = (drivers or "").strip().lower()
    if not d:
        return "unknown"
    if any(t in d for t in CONFLICT_TOKENS):
        return "conflict"
    return "addressable"


def load_inform(path):
    """Parse the INFORM Severity workbook into burden records.

    The sheet layout is fixed: row 1 title, row 2 headers, rows 3-4 weight/range notes,
    data from row 5.  Column F (index 5) is the severity score.
    """
    try:
        import openpyxl
    except ImportError:
        raise SystemExit(
            "openpyxl is required for --inform. Install it, or use --live for the "
            "World Bank path only."
        )
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["INFORM Severity - all crises"]
    out = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        if not row or not row[0] or row[5] is None:
            continue
        try:
            sev = float(row[5])
        except (TypeError, ValueError):
            continue
        drivers = str(row[4] or "")
        out.append(
            {
                "crisis": str(row[0]).strip(),
                "crisis_id": row[1],
                "country": row[2],
                "iso3": row[3],
                "drivers": drivers,
                "severity": sev,
                "severity_class": row[7],
                "trend": row[8],
                "impact": row[10],
                "addressability": addressability(drivers),
                "source": "INFORM Severity October 2026 (release 202610)",
                "retrieved": _now(),
            }
        )
    return out


def wb_series(indicator, date_range="2019:2026"):
    """Fetch one World Bank indicator for the world aggregate.

    Returns (values, source).  values maps year -> float.  Raises on a transport error
    so the caller can decide; returns {} when the indicator exists but is unpopulated,
    which is a real state for WLD aggregates.
    """
    url = (
        f"https://api.worldbank.org/v2/country/WLD/indicator/{indicator}"
        f"?format=json&per_page=60&date={date_range}"
    )
    for attempt in range(3):
        try:
            d = _get(url)
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
    if not isinstance(d, list) or len(d) < 2 or not d[1]:
        return {}, f"World Bank {indicator}"
    vals = {r["date"]: r["value"] for r in d[1] if r.get("value") is not None}
    updated = (d[0] or {}).get("lastupdated")
    return vals, f"World Bank {indicator} (lastupdated {updated})"


def build_ledger(inform_path=None, live=False):
    burdens = []
    if inform_path:
        burdens = load_inform(inform_path)
    elif not live:
        raise SystemExit("Nothing to do: pass --inform PATH or --live.")

    indicators = {}
    if live:
        for name, code in WB_SERIES.items():
            try:
                vals, src = wb_series(code)
                if vals:
                    latest_year = max(vals)
                    indicators[name] = {
                        "value": vals[latest_year],
                        "year": latest_year,
                        "source": src,
                        "retrieved": _now(),
                    }
            except Exception as e:  # transport failure is reported, never silently dropped
                indicators[name] = {"error": f"{type(e).__name__}: {e}"}
            time.sleep(0.4)

    return {
        "generated": _now(),
        "counts": _counts(burdens),
        "burdens": sorted(burdens, key=lambda b: -b["severity"]),
        "indicators": indicators,
    }


def _counts(burdens):
    c = {"total": len(burdens), "very_high": 0, "high": 0, "worsening": 0,
         "addressable": 0, "conflict": 0}
    for b in burdens:
        cls = (b.get("severity_class") or "").lower()
        if cls == "very high":
            c["very_high"] += 1
        elif cls == "high":
            c["high"] += 1
        if b.get("trend") == "Increasing":
            c["worsening"] += 1
        if b.get("addressability") == "addressable":
            c["addressable"] += 1
        elif b.get("addressability") == "conflict":
            c["conflict"] += 1
    return c


def validate(ledger):
    """Enforce G1 and G2 over a ledger.  Returns a list of problem strings."""
    problems = []
    for b in ledger.get("burdens", []):
        if not b.get("source") or not b.get("retrieved"):
            problems.append(f"G1: burden without source/date: {b.get('crisis')!r}")
        if b.get("addressability") == "addressable" and addressability(b.get("drivers")) == "conflict":
            problems.append(f"G2: conflict crisis marked addressable: {b.get('country')!r}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the burden ledger.")
    ap.add_argument("--inform", metavar="XLSX", help="INFORM Severity workbook")
    ap.add_argument("--live", action="store_true", help="pull World Bank indicators")
    ap.add_argument("--out", default="-", help="output path, or - for stdout")
    a = ap.parse_args(argv)

    ledger = build_ledger(inform_path=a.inform, live=a.live)
    problems = validate(ledger)
    ledger["validation"] = {"ok": not problems, "problems": problems}

    text = json.dumps(ledger, indent=1, ensure_ascii=False)
    if a.out == "-":
        print(text)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        c = ledger["counts"]
        print(f"wrote {a.out}: {c['total']} burdens, {c['very_high']} very high, "
              f"{c['worsening']} worsening, {c['addressable']} addressable")
        if problems:
            print(f"VALIDATION FAILED ({len(problems)}):", file=sys.stderr)
            for p in problems[:10]:
                print("  " + p, file=sys.stderr)
            return 1
        print("validation: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
