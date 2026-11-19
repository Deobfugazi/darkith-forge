#!/usr/bin/env python3
"""clearanceloop.py — the Homeokinetic Debt Ratchet, as a headless utility.

One law, carried by three engines that must agree verdict-for-verdict:

    app/src/main/assets/vendor/clearanceloop.js   the browser engine (canonical)
    clearanceloop.html                            the webapp that drives it
    clearanceloop.py                              this CLI, for CI and scripts

The law: health is a RATE of clearance, not a static tolerance.

    L1 MONOTONE    when debt drops, the per-class high-water mark drops with it
    L2 REGRESSION  debt above the mark is a net addition = a regression = FAIL
    L3 STASIS      debt that does not clear across WINDOW deliveries is force-degraded
    L4 WAIVER      a rise is permitted only by a recorded, reasoned, EXPIRING exception

A waiver never raises the high-water mark. Raising it would loosen the gate for good,
and the ratchet only ever tightens; the waiver merely lets the debt exist for a bounded
number of deliveries, after which it is a plain regression again.

State lives in `--state` (default `.clearanceloop/state.json`), so a repo can commit or
cache it. Every command prints JSON to stdout; the exit code is the verdict, so a shell
can gate on it directly:

    0  PASS
    1  FAIL
    2  WARN

Usage:
  python3 clearanceloop.py report  [--state P] [--json]
  python3 clearanceloop.py observe switching=7 waiting=4
  python3 clearanceloop.py advance [--justify REASON] [--state P]
  python3 clearanceloop.py waive   CLASS REASON
  python3 clearanceloop.py reset   [--state P]
  python3 clearanceloop.py restore FILE
  python3 clearanceloop.py export  [FILE]
  python3 clearanceloop.py selftest [--verbose]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys

CLASSES = ("switching", "waiting", "searching", "correcting", "review")
WINDOW = 5      # deliveries of non-clearance before force-degradation
WAIVER = 5      # a waiver's budget, in deliveries; it then expires
LAW = "homeokinesis: debt may only flux downward; stasis is force-degraded"
EXIT = {"PASS": 0, "FAIL": 1, "WARN": 2}

DEFAULT_STATE = pathlib.Path(".clearanceloop") / "state.json"


# ──────────────────────────────────────────────────────────────────────────────
# state
# ──────────────────────────────────────────────────────────────────────────────
def empty_state() -> dict:
    return {"hwm": {}, "justified": {}, "since": {}, "delivery": 0, "history": [], "_acc": {}}


def _finite_int(v, default: int = 0) -> int:
    """Waiver bookkeeping is not law-bearing, so a hostile number degrades to `default`
    rather than aborting the run. inf/NaN must never reach `int()`."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return int(v)


def norm_waiver(w) -> dict | None:
    """Normalise a waiver record. A legacy bare-string waiver carried no expiry, so it
    granted permanent immunity; it is normalised to an ALREADY-EXPIRED waiver so the
    operator must re-justify. Failing closed is the only safe direction."""
    if not w:
        return None
    if isinstance(w, str):
        return {"reason": w, "at": 0, "expires": 0}
    if isinstance(w, dict):
        return {"reason": str(w.get("reason") or "waiver"),
                "at": _finite_int(w.get("at")), "expires": _finite_int(w.get("expires"))}
    return None


def _int(raw, *, field: str, path: pathlib.Path, nonneg: bool = True):
    """Coerce one JSON number to int, refusing inf/NaN/bool loudly instead of raising.

    `int(float('inf'))` and `int(float('nan'))` raise OverflowError/ValueError, which
    escaped as a traceback on a hostile state file. JSON permits `1e309` and `NaN`, so
    this is reachable from a hand-edited or corrupted file.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SystemExit(f"clearanceloop: state {path}: {field} must be an integer, got {raw!r}")
    if not math.isfinite(raw):
        raise SystemExit(f"clearanceloop: state {path}: {field} must be finite, got {raw!r}")
    iv = int(raw)
    if nonneg and iv < 0:
        raise SystemExit(f"clearanceloop: state {path}: {field} is negative ({iv})")
    return iv


def _int_map(raw, field: str, path: pathlib.Path) -> dict:
    """Coerce a JSON object of non-negative integers, rejecting anything else loudly.

    A corrupt state file must never reach the law: a string where a count belongs would
    either crash the CLI or, worse, silently coerce into a wrong high-water mark.
    """
    val = raw.get(field)
    if val is None:
        return {}
    if not isinstance(val, dict):
        raise SystemExit(f"clearanceloop: state {path}: '{field}' must be an object, got {type(val).__name__}")
    out = {}
    for k, v in val.items():
        out[str(k)] = _int(v, field=f"'{field}.{k}'", path=path)
    return out


def load_state(path: pathlib.Path) -> dict:
    """Load state, normalising every waiver and refusing a malformed file loudly.

    Accepts both shapes this tool produces: a flat state file (what `save_state`
    writes) and the wrapped `{state, report}` document `export` writes. Accepting only
    the flat shape made `restore` silently return an empty ratchet for our own export,
    which is data loss dressed as success.
    """
    if not path.exists():
        return empty_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        raise SystemExit(f"clearanceloop: unreadable state {path}: {e}")
    if not isinstance(raw, dict):
        raise SystemExit(f"clearanceloop: state {path} is not an object")
    if isinstance(raw.get("state"), dict):
        raw = raw["state"]

    st = empty_state()
    st["hwm"] = _int_map(raw, "hwm", path)
    st["since"] = _int_map(raw, "since", path)
    st["_acc"] = {k: v for k, v in _int_map(raw, "_acc", path).items() if k in CLASSES}

    st["delivery"] = _int(raw.get("delivery", 0), field="'delivery'", path=path)

    hist = raw.get("history")
    if hist is None:
        hist = []
    if not isinstance(hist, list):
        raise SystemExit(f"clearanceloop: state {path}: 'history' must be a list, got {type(hist).__name__}")
    clean_hist = []
    for i, row in enumerate(hist[-40:]):
        if not isinstance(row, dict) or not isinstance(row.get("now"), dict):
            raise SystemExit(f"clearanceloop: state {path}: 'history[{i}]' is not a delivery record")
        clean_hist.append({
            "delivery": _int(row.get("delivery") or 0, field=f"'history[{i}].delivery'", path=path),
            "now": {k: _int(v, field=f"'history[{i}].now.{k}'", path=path)
                    for k, v in row["now"].items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)},
            "score": _int(row.get("score") or 0, field=f"'history[{i}].score'", path=path, nonneg=False),
        })
    st["history"] = clean_hist

    just = raw.get("justified")
    if just is not None and not isinstance(just, dict):
        raise SystemExit(f"clearanceloop: state {path}: 'justified' must be an object, got {type(just).__name__}")
    for k, v in (just or {}).items():
        nw = norm_waiver(v)
        if nw:
            st["justified"][str(k)] = nw
    return st


def save_state(path: pathlib.Path, st: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise SystemExit(f"clearanceloop: cannot create {path.parent}: {e}")
    payload = {
        "_law": LAW, "delivery": st["delivery"], "hwm": st["hwm"],
        "justified": st["justified"], "since": st["since"], "history": st["history"][-40:],
        "_acc": st.get("_acc") or {},
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        raise SystemExit(f"clearanceloop: cannot write {path}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# the law
# ──────────────────────────────────────────────────────────────────────────────
def observe(st: dict, counts: dict) -> dict:
    """Record friction accrued since the last delivery (mutates the pending accumulator)."""
    acc = st.setdefault("_acc", {})
    for c, n in counts.items():
        if c in CLASSES:
            acc[c] = int(n)
    return acc


def advance(st: dict, justify: str | None = None) -> dict:
    """Apply the law for one delivery. Returns the events, degradations and expiries."""
    acc = st.get("_acc") if isinstance(st.get("_acc"), dict) else {}
    now = {}
    for c in CLASSES:
        v = acc.get(c, 0)
        now[c] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else 0
    hwm = dict(st["hwm"])
    since = dict(st["since"])
    justified = dict(st["justified"])
    events: list[str] = []
    expired: list[str] = []

    # expire first: a waiver's budget is a fixed number of deliveries, never forever
    for cls in list(justified):
        if st["delivery"] >= justified[cls]["expires"]:
            events.append(f"EXPIRED waiver {cls} ({justified[cls]['reason']}): the apoptotic exception ended")
            expired.append(cls)
            del justified[cls]

    for cls in CLASSES:
        n = now[cls]
        if cls not in hwm:
            hwm[cls] = n
            since[cls] = 0
            events.append(f"seeded {cls}: HWM {n}")
            continue
        prev = hwm[cls]
        if n < prev:
            events.append(f"cleared {cls}: {prev} -> {n} (flux down)")
            hwm[cls] = n
            since[cls] = 0
        elif n == prev:
            since[cls] = since.get(cls, 0) + 1
        elif justify:
            # a waiver permits the debt for a bounded window; it NEVER raises the HWM
            justified[cls] = {"reason": str(justify), "at": st["delivery"],
                              "expires": st["delivery"] + WAIVER}
            events.append(f"JUSTIFIED waiver {cls}: {prev} -> {n} for {WAIVER} deliveries "
                          f"({justify}); HWM stays {prev}")
            since[cls] = 0
        # else: net addition left in place; the HWM is NOT raised and the verdict fails

    for cls in list(hwm):
        if now.get(cls, 0) == 0 and hwm[cls] != 0:
            events.append(f"cleared {cls}: {hwm[cls]} -> 0 (flux down)")
            hwm[cls] = 0
            since[cls] = 0

    degraded = [cls for cls, d in since.items()
                if now.get(cls, 0) > 0 and d >= WINDOW and cls not in justified]

    st["delivery"] += 1
    st["hwm"] = hwm
    st["since"] = since
    st["justified"] = justified
    st["history"] = (st["history"] + [{"delivery": st["delivery"], "now": now,
                                       "score": sum(now.values())}])[-40:]
    st["_acc"] = {}
    return {"events": events, "degraded": degraded, "expired": expired,
            "now": now, "delivery": st["delivery"]}


def flux(st: dict) -> int:
    h = st["history"]
    if len(h) < 2:
        return 0
    return h[-1]["score"] - h[-2]["score"]


def report(st: dict) -> dict:
    pending = st.get("_acc") if isinstance(st.get("_acc"), dict) else {}
    last = st["history"][-1] if st.get("history") else None
    now = last["now"] if isinstance(last, dict) and isinstance(last.get("now"), dict) \
        else {c: int(pending.get(c, 0) or 0) for c in CLASSES}
    classes = []
    outstanding = 0
    for cls in CLASSES:
        n = int(now.get(cls, 0))
        h = int(st["hwm"].get(cls, n))
        since = int(st["since"].get(cls, 0))
        w = st["justified"].get(cls)
        # a waiver past its budget is dead even before the next advance sweeps it
        if w and st["delivery"] >= w["expires"]:
            w = None
        left = max(0, w["expires"] - st["delivery"]) if w else 0
        if n > h and not w:
            status = "regression"
        elif n > 0 and since >= WINDOW and not w:
            status = "stale"
        elif n > 0:
            status = "waived" if w else "tracked"
        else:
            status = "clear"
        if n > 0:
            outstanding += n
        classes.append({"cls": cls, "now": n, "hwm": h, "since": since, "status": status,
                        "waived": bool(w), "reason": w["reason"] if w else None,
                        "remaining": left})

    regress = [c["cls"] for c in classes if c["status"] == "regression"]
    stale = [c["cls"] for c in classes if c["status"] == "stale"]
    f = flux(st)
    if regress:
        verdict, reason = "FAIL", "net addition of debt: " + ", ".join(regress)
    elif stale:
        verdict, reason = "FAIL", "stasis force-degraded to blocker: " + ", ".join(stale)
    elif outstanding > 0 and f == 0:
        verdict, reason = "WARN", "stasis: debt outstanding and not clearing"
    else:
        verdict, reason = "PASS", ("debt fluxing down" if outstanding else "no friction debt")

    return {"law": LAW, "verdict": verdict, "reason": reason, "flux": f,
            "delivery": st["delivery"], "outstanding": outstanding, "window": WINDOW,
            "waiverBudget": WAIVER, "classes": classes}


# ──────────────────────────────────────────────────────────────────────────────
# self-test — every law, on a throwaway state
# ──────────────────────────────────────────────────────────────────────────────
def selftest(verbose: bool = False) -> int:
    results: list[tuple[str, bool, str]] = []

    def case(name: str):
        def deco(fn):
            try:
                fn()
                results.append((name, True, ""))
            except AssertionError as e:
                results.append((name, False, str(e) or "assertion failed"))
            except Exception as e:  # a law that raises is a law that failed
                results.append((name, False, f"{type(e).__name__}: {e}"))
            return fn
        return deco

    def find(rep, cls):
        return next(c for c in rep["classes"] if c["cls"] == cls)

    def fresh():
        return empty_state()

    @case("L1 seed: the first delivery seeds the mark, no false regression")
    def _():
        st = fresh()
        observe(st, {"switching": 5, "correcting": 3})
        advance(st)
        assert report(st)["verdict"] != "FAIL", "seed failed"
        assert find(report(st), "switching")["hwm"] == 5, "HWM not seeded"

    @case("L2 clearance: less debt ratchets the mark down")
    def _():
        st = fresh()
        observe(st, {"switching": 5}); advance(st)
        observe(st, {"switching": 2}); advance(st)
        assert find(report(st), "switching")["hwm"] == 2, "HWM did not move down"

    @case("L3 regression: debt above the mark fails and never raises it")
    def _():
        st = fresh()
        observe(st, {"switching": 5}); advance(st)
        observe(st, {"switching": 2}); advance(st)
        observe(st, {"switching": 4}); advance(st)
        assert report(st)["verdict"] == "FAIL", "regression did not fail"
        assert find(report(st), "switching")["hwm"] == 2, "HWM was raised"

    @case("L4 waiver: permits debt without raising the mark")
    def _():
        st = fresh()
        observe(st, {"waiting": 3}); advance(st)
        observe(st, {"waiting": 6}); advance(st, "spike")
        c = find(report(st), "waiting")
        assert c["waived"], "waiver not recorded"
        assert c["hwm"] == 3, "waiver raised the HWM"
        assert report(st)["verdict"] != "FAIL", "waived debt failed"

    @case("L5 time-box: the waiver expires and the debt fails again")
    def _():
        st = fresh()
        observe(st, {"waiting": 3}); advance(st)
        observe(st, {"waiting": 6}); advance(st, "spike")
        for _i in range(WAIVER):
            observe(st, {"waiting": 6}); advance(st)
        c = find(report(st), "waiting")
        assert not c["waived"], "waiver never expired"
        assert report(st)["verdict"] == "FAIL", "expired waiver still passing"
        assert c["hwm"] == 3, "HWM rose across the waiver"

    @case("L6 stasis: stagnant debt is force-degraded")
    def _():
        st = fresh()
        observe(st, {"searching": 2}); advance(st)
        for _i in range(WINDOW):
            observe(st, {"searching": 2}); advance(st)
        assert report(st)["verdict"] == "FAIL", "stasis did not fail"
        assert "searching" in report(st)["reason"], "reason does not name the class"

    @case("L7 persistence: the mark survives a save/load round-trip")
    def _():
        import tempfile
        st = fresh()
        observe(st, {"review": 9}); advance(st)
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "s.json"
            save_state(p, st)
            back = load_state(p)
        assert find(report(back), "review")["hwm"] == 9, "mark lost on round-trip"

    @case("L8 fail-closed: a legacy bare-string waiver grants no immunity")
    def _():
        st = empty_state()
        st["hwm"] = {"waiting": 3}
        st["delivery"] = 4
        st["history"] = [{"delivery": 4, "now": {"waiting": 9}, "score": 9}]
        for k, v in {"waiting": "legacy"}.items():
            nw = norm_waiver(v)
            if nw:
                st["justified"][k] = nw
        assert not find(report(st), "waiting")["waived"], "legacy waiver was live"
        assert report(st)["verdict"] == "FAIL", "legacy waiver did not fail closed"

    @case("verdict is total: only PASS/WARN/FAIL are ever produced")
    def _():
        st = fresh()
        seen = set()
        for a in range(3):
            for b in range(3):
                observe(st, {"switching": a, "waiting": b})
                advance(st)
                seen.add(report(st)["verdict"])
        assert seen <= {"PASS", "WARN", "FAIL"}, f"unknown verdict {seen}"

    passed = sum(1 for _n, ok, _d in results if ok)
    failed = len(results) - passed
    if verbose:
        for name, ok, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    print(f"clearanceloop selftest: {passed}/{len(results)} laws hold" if not failed
          else f"clearanceloop selftest: FAIL — {failed} of {len(results)} laws broken")
    return 0 if not failed else 1


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def parse_counts(pairs: list[str]) -> dict:
    out: dict[str, int] = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"clearanceloop: expected class=count, got: {p}")
        k, v = p.split("=", 1)
        k = k.strip().lower()
        if k not in CLASSES:
            raise SystemExit(f"clearanceloop: unknown class {k!r} (choose from {', '.join(CLASSES)})")
        try:
            n = int(v)
        except ValueError:
            raise SystemExit(f"clearanceloop: count for {k} is not an integer: {v!r}")
        if n < 0:
            raise SystemExit(f"clearanceloop: count for {k} is negative: {n}")
        out[k] = n
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="clearanceloop", description="The Homeokinetic Debt Ratchet.")
    ap.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE,
                    help=f"state file (default {DEFAULT_STATE})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("report", help="print the current verdict and per-class state")
    p.add_argument("--json", action="store_true", help="(default) machine-readable output")

    p = sub.add_parser("observe", help="record friction counts for the next delivery")
    p.add_argument("counts", nargs="+", metavar="CLASS=N")

    p = sub.add_parser("advance", help="apply the law for one delivery")
    p.add_argument("--justify", default=None, help="record a reasoned, expiring waiver")

    p = sub.add_parser("waive", help="observe a count and advance with a waiver in one step")
    p.add_argument("cls", choices=CLASSES)
    p.add_argument("count", type=int)
    p.add_argument("reason", nargs="+", help="why the rise is justified")

    p = sub.add_parser("reset", help="clear the ratchet (destroys the high-water history)")

    p = sub.add_parser("restore", help="adopt a state file produced by export")
    p.add_argument("file", type=pathlib.Path)

    p = sub.add_parser("export", help="write the state to a file (or stdout)")
    p.add_argument("file", nargs="?", type=pathlib.Path, default=None)

    p = sub.add_parser("selftest", help="prove every law on a throwaway state")
    p.add_argument("--verbose", action="store_true")

    A = ap.parse_args(argv)

    if A.cmd == "selftest":
        return selftest(A.verbose)

    if A.cmd == "restore":
        if not A.file.exists():
            raise SystemExit(f"clearanceloop: no such file: {A.file}")
        st = load_state(A.file)
        save_state(A.state, st)
        print(json.dumps(report(st), indent=2))
        return EXIT[report(st)["verdict"]]

    st = load_state(A.state)

    if A.cmd == "observe":
        counts = parse_counts(A.counts)
        observe(st, counts)
        save_state(A.state, st)
        print(json.dumps({"observed": counts, "pending": st.get("_acc") or counts}, indent=2))
        return 0

    if A.cmd == "advance":
        out = advance(st, A.justify)
        save_state(A.state, st)
        rep = report(st)
        print(json.dumps({"events": out["events"], "degraded": out["degraded"],
                          "expired": out["expired"], "report": rep}, indent=2))
        return EXIT[rep["verdict"]]

    if A.cmd == "waive":
        if A.count < 0:
            raise SystemExit(f"clearanceloop: count is negative: {A.count}")
        observe(st, {A.cls: A.count})
        out = advance(st, " ".join(A.reason))
        save_state(A.state, st)
        rep = report(st)
        print(json.dumps({"events": out["events"], "report": rep}, indent=2))
        return EXIT[rep["verdict"]]

    if A.cmd == "reset":
        st = empty_state()
        save_state(A.state, st)
        print(json.dumps(report(st), indent=2))
        return 0

    if A.cmd == "export":
        st.pop("_acc", None)
        text = json.dumps({"state": st, "report": report(st)}, indent=2)
        if A.file:
            A.file.parent.mkdir(parents=True, exist_ok=True)
            A.file.write_text(text + "\n", encoding="utf-8")
            print(f"clearanceloop: wrote {A.file}")
            return 0
        print(text)
        return 0

    # report (the default, and the CI gate)
    rep = report(st)
    print(json.dumps(rep, indent=2))
    return EXIT[rep["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
