#!/usr/bin/env python3
"""unit_ledger_gate.py — SPI-37: a quantity crosses a boundary with its unit.

The compiler cannot see dimension. `Long` is bytes, vertices, params and scale factors
indistinguishably, so a vertex count passed into a byte parameter compiles clean and every
number computed from it afterwards is meaningless while remaining type-correct.

What this gate does NOT do. It does not infer a unit from every name in the tree. That was
tried first and produced 32 accusations out of 53 call sites, almost all false: `ns` matched
a namespace, `block` matched a code block, `params` matched `FileChooserParams`. A detector
that cries wolf gets switched off, and a switched-off detector is worse than none.

What it does. A boundary is DECLARED in tools/unit_ledger.json — a function and the unit of
each parameter, with the reason. The gate then reads every call to that boundary and fails
only on a POSITIVE CONTRADICTION: an argument whose own name declares a different unit than
the parameter demands. An argument that declares nothing is reported as an advisory, never a
failure, because silence is not evidence. That is the exact shape of the defect SPI-37 was
inscribed for: `reciprocate(usedRam, allocation.vertexBudget)` — the parameter wanted bytes,
the argument's name declares vertices, and both are `Long`.

The durable cure is still the compiler: `@JvmInline value class Bytes` / `Vertices` makes
the crossing a compile error. This gate is the tripwire that catches the next `Long`-to-`Long`
crossing at a declared boundary before it ships, and the ledger is the record of which
boundaries a human has actually looked at.

Usage:
  python3 tools/unit_ledger_gate.py [root] [--selftest] [--verbose]
Exit: 0 = every declared boundary is honoured; 1 = a positive unit contradiction;
      3 = no declared boundary is present in the tree (nothing judged — never a silent pass).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# Deliberately tight. Every token here is unambiguous as a unit; words that double as
# ordinary identifiers (`ns` namespace, `block` code block, `param` parameter) are excluded,
# because a token that is ambiguous produces accusations instead of findings.
UNIT_TOKENS = {
    "bytes": "bytes", "byte": "bytes", "ram": "bytes", "heap": "bytes",
    "vertices": "vertices", "vertex": "vertices",
    "ms": "time", "millis": "time", "nanos": "time",
    "scale": "scale", "ratio": "ratio",
    "tokens": "tokens", "layers": "layers",
}

CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
FUN_DECL_RE = re.compile(r"\bfun\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", re.S)
PARAM_RE = re.compile(r"([A-Za-z_]\w*)\s*:\s*([A-Za-z_][\w<>?., ]*)")


def unit_of(name: str) -> str | None:
    """The unit a name declares, or None when it declares none."""
    for token in reversed(re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", name)):
        u = UNIT_TOKENS.get(token.lower())
        if u:
            return u
    return None


def split_args(argtext: str) -> list[str]:
    """Top-level comma split, ignoring commas inside nested parens/brackets/generics."""
    out, depth, cur = [], 0, []
    for ch in argtext:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def arg_unit(expr: str) -> str | None:
    """Unit declared by the argument's own name (last identifier segment), or None."""
    expr = expr.strip()
    if re.fullmatch(r"-?\d[\d_]*L?", expr):
        return "literal"
    m = re.search(r"([A-Za-z_]\w*)\s*\(?\s*\)?$", expr)
    return unit_of(m.group(1)) if m else None


def scan(root: pathlib.Path, ledger: dict) -> tuple[list[str], list[str], int]:
    kt = sorted(root.glob("**/*.kt"))
    if not kt:
        return [], [], 0

    boundaries = {b["call"]: b for b in ledger.get("boundaries", [])}
    if not boundaries:
        return [], [], 0

    sigs: dict[str, list[str | None]] = {}
    for f in kt:
        for m in FUN_DECL_RE.finditer(f.read_text(errors="replace")):
            params = [PARAM_RE.search(p.strip()) for p in m.group(2).split(",") if p.strip()]
            sigs.setdefault(m.group(1), [unit_of(p.group(1)) if p else None for p in params])

    deficits, advisories, judged = [], [], 0
    for name, spec in boundaries.items():
        if name not in sigs:
            deficits.append(f"boundary `{name}` is declared in the ledger but has no declaration in the tree")
            continue
        want_units = spec["units"]
        for f in kt:
            code = "\n".join(re.sub(r"//.*$", "", ln) for ln in f.read_text(errors="replace").splitlines())
            for m in CALL_RE.finditer(code):
                if m.group(1) != name:
                    continue
                args = split_args(m.group(2))
                if len(args) != len(want_units):
                    continue
                line = code[: m.start()].count("\n") + 1
                for i, arg in enumerate(args):
                    want, got = want_units[i], arg_unit(arg)
                    judged += 1
                    if got == "literal" or got == want:
                        continue
                    where = f"{f.relative_to(root)}:{line}"
                    if got is None:
                        advisories.append(f"{where}: `{arg}` declares no unit; `{name}` param {i} wants {want}")
                    else:
                        deficits.append(
                            f"{where}: `{arg}` declares {got} but `{name}` param {i} wants {want}"
                        )
    return deficits, advisories, judged


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv[1:])

    if a.selftest:
        assert unit_of("modelAllocatedBytes") == "bytes"
        assert unit_of("rendererMaxBytes") == "bytes"
        assert unit_of("vertexBudget") == "vertices"
        assert unit_of("frameMs") == "time"
        assert unit_of("resolutionScale") == "scale"
        # ambiguous words must NOT be read as units
        assert unit_of("namespace") is None
        assert unit_of("block") is None
        assert unit_of("fileChooserParams") is None
        assert unit_of("apk") is None
        # the argument reader must see through a property access and a call
        assert arg_unit("allocation.vertexBudget") == "vertices"
        assert arg_unit("renderer.modelAllocatedBytes()") == "bytes"
        assert arg_unit("16L") == "literal"
        assert split_args("a, f(b, c), d") == ["a", "f(b, c)", "d"]
        print("unit_ledger_gate selftest: PASS — units read from names, ambiguity refused, nesting respected")
        return 0

    root = pathlib.Path(a.root)
    ledger_path = root / "tools" / "unit_ledger.json"
    if not ledger_path.exists():
        print(f"unit_ledger_gate: SKIP — no {ledger_path}; no boundary is declared, nothing was judged")
        return 3
    ledger = json.loads(ledger_path.read_text())

    deficits, advisories, judged = scan(root, ledger)
    if judged == 0:
        print("unit_ledger_gate: SKIP — declared boundaries have no call sites in the tree; nothing was judged")
        return 3

    if a.verbose:
        for adv in advisories:
            print("  advisory: " + adv)
    if deficits:
        print(f"unit_ledger_gate: FAIL — {len(deficits)} unit contradiction(s) across {judged} judged argument(s)")
        for d in deficits:
            print("  " + d)
        print("  cure: pass the value in the parameter's unit, or give the two quantities distinct")
        print("        types so the crossing cannot compile. Do not relabel the parameter.")
        return 1
    print(f"unit_ledger_gate: PASS — {judged} judged argument(s) at declared boundaries, "
          f"{len(advisories)} advisory (argument declares no unit)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
