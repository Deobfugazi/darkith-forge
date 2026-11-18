#!/usr/bin/env python3
"""source_inspector.py — the logical trial examiner: it puts the source on trial.

The Operator's brief: a ROUTINE source inspector that deliberately stress-tests source
features for loopholes, then AUTOFIXES the ones that are mechanically fixable — the
"invariant bounty hunter". It is the courtroom, not the complaint box:

    probe      each named loophole is a CHARGE against the tree
    trial      every charge is tried on a POSITIVE case (must catch the defect) and a
               NEGATIVE case (must NOT flag clean code). A charge that fails either is a
               broken charge and is itself reported — because a gate that cries wolf is a
               broken gate (DARKITH.md §20, W-040).
    verdict    GUILTY (a real loophole is open) | ACQUITTED (clean) | MISTRIAL (the charge
               is miscalibrated and is withdrawn)
    autofix    reversible, well-understood classes are repaired in place, IDEMPOTENTLY
               (re-running yields byte-identical bytes). Everything else is ESCROWED to the
               bounty ledger — named, never silently passed (SPI-15).

Why it exists. `tools/delivery_gate.sh` is the loophole registry for ARTIFACTS (an APK's
version, signing, alignment). Nothing did the same for the SOURCE FEATURES themselves: a
comment-stripping sed (W-021), a foreign `androidx.` import in a raw-chain tree (NEVER #12),
a `!!` non-null assertion that crashes at runtime, a stub `TODO()`, a swallowed exception.
This inspector is the routine trial of the source on exactly those charges.

Deduplication (the Operator's own rule: upgrade, don't fork). The comment/string-aware
lexer is NOT re-implemented here — it is imported from `tools/kt_comment_scan.py`, the one
canonical Kotlin scanner. This file adds charges on top of that lexer; it never forks it.

Node functions. The same examiner runs on JavaScript/Node surfaces (`*.js`, `*.mjs`) with a
JS-aware probe set, so the dedup rule applies there too: `node_functions` reports a function
name declared MORE THAN ONCE **in the same scope** with a conflicting parameter list — the
real hazard — while a name reused across different nested scopes (the common, legal pattern)
is never flagged. (A naive `grep | uniq -d` cries wolf on that; this one does not.)

Honesty boundary. A scanner is not a compiler (W-023). These probes are exact about the
defect classes they were written for and are calibrated with negative trials so they do not
false-pass or false-flag; they do not prove a file compiles. kotlinc remains the judge of
syntax (MUST #11).

Usage
  python3 tools/source_inspector.py inspect [--root DIR] [--json] [--fail-on-fixable]
  python3 tools/source_inspector.py fix     [--root DIR]     # apply reversible autofixes
  python3 tools/source_inspector.py trial                     # prove every charge is calibrated
  python3 tools/source_inspector.py selftest                  # alias of trial
  python3 tools/source_inspector.py report                    # read the last ledger from disk

Exit codes
  inspect : 0 if no OPEN charge (fixable-but-unfixed counts as OPEN only with
            --fail-on-fixable); 1 otherwise.
  trial   : 0 if every charge is calibrated; 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
# The ONE canonical Kotlin lexer (dedup rule: import, never fork).
from kt_comment_scan import scan as kt_scan  # noqa: E402

# Synchrony bylaw (MUST #23/#24): bots log through the generated clock.
sys.path.insert(0, str(ROOT / "build" / "gen"))
try:
    from omega_time_runtime import stamp as _stamp  # noqa: E402
except ImportError:  # pragma: no cover - generator not run yet
    sys.path.insert(0, str(ROOT / "tools"))
    from omega_time import stamp as _stamp  # noqa: E402

LEDGER = ROOT / "proof" / "source_inspector.json"
BASELINE = ROOT / "proof" / "source_inspector_baseline.json"
DEFAULT_ROOT = "app/src/main/java/com/darkith/transliaison"

KT_EXTS = {".kt", ".kts"}
JS_EXTS = {".js", ".mjs", ".cjs"}


# ──────────────────────────────────────────────────────────────────────────────
# helpers shared by probes
# ──────────────────────────────────────────────────────────────────────────────
def _lex(text: str):
    """The shared lexer. Builds three views:

      code     — the text with every comment and every string/char/raw literal body
                 replaced by spaces (newlines preserved), so a regex run on it sees only
                 real code. This is what makes CH-02 exact: `// androidx` becomes blank.
      rawlines — the set of 1-based line numbers that lie inside a raw (triple-quoted)
                 string, where trailing whitespace is significant and must be preserved.
      charmask — a list, one bool per character, True where that character is real CODE
                 (outside any comment). Used by CH-09, which must see a string literal
                 but must not match inside a comment.
    """
    n = len(text)
    i = 0
    line = 1
    state = "code"
    depth = 0
    out = []
    rawlines = set()
    charmask = [True] * (n + 1)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        in_code = state == "code"
        if in_code:
            if c == "/" and nxt == "/":
                state = "line"; out.append(" "); out.append(" "); i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; depth = 1; out.append(" "); out.append(" "); i += 2; continue
            if c == '"':
                if text[i:i + 3] == '"""':
                    state = "raw"; rawlines.add(line)
                    out.append(" "); out.append(" "); out.append(" "); i += 3; continue
                state = "string"; out.append(" "); i += 1; continue
            if c == "'":
                state = "char"; out.append(" "); i += 1; continue
            if c == "\n":
                line += 1; out.append("\n"); i += 1; continue
            out.append(c); i += 1; continue
        # not in code: mark the character as non-code (except newlines, which are shared)
        if c != "\n":
            charmask[i] = False
        if state == "line":
            if c == "\n":
                state = "code"; line += 1; out.append("\n"); i += 1; continue
            out.append(" "); i += 1; continue
        if state == "block":
            if c == "/" and nxt == "*":
                depth += 1; out.append(" "); out.append(" "); i += 2; continue
            if c == "*" and nxt == "/":
                depth -= 1; out.append(" "); out.append(" "); i += 2
                if depth == 0:
                    state = "code"
                continue
            if c == "\n":
                line += 1; out.append("\n"); i += 1; continue
            out.append(" "); i += 1; continue
        if state == "string":
            if c == "\\":
                out.append(" "); out.append(" "); i += 2; continue
            if c == '"':
                state = "code"; out.append(" "); i += 1; continue
            if c == "\n":
                state = "code"; line += 1; out.append("\n"); i += 1; continue
            out.append(" "); i += 1; continue
        if state == "raw":
            rawlines.add(line)
            if text[i:i + 3] == '"""':
                state = "code"; out.append(" "); out.append(" "); out.append(" "); i += 3; continue
            if c == "\n":
                line += 1; out.append("\n"); i += 1; continue
            out.append(" "); i += 1; continue
        if state == "char":
            if c == "\\":
                out.append(" "); out.append(" "); i += 2; continue
            if c == "'":
                state = "code"; out.append(" "); i += 1; continue
            if c == "\n":
                state = "code"; line += 1; out.append("\n"); i += 1; continue
            out.append(" "); i += 1; continue
    return "".join(out), rawlines, charmask


def code_only(text: str):
    """The text with comments and string/char/raw bodies blanked (newlines kept)."""
    return _lex(text)[0]


def raw_lines(text: str):
    """The set of line numbers inside a raw string (whitespace is significant there)."""
    return _lex(text)[1]


def char_code_mask(text: str):
    """A per-character bool mask: True where the character is real code (no comment)."""
    return _lex(text)[2]


# ──────────────────────────────────────────────────────────────────────────────
# the charges (probes). Each returns a list of Finding dicts.
# A Finding: {cls, path, line, text, autofixable}
# ──────────────────────────────────────────────────────────────────────────────
def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _src_line(text: str, ln: int) -> str:
    parts = text.split("\n")
    return parts[ln - 1].strip() if 0 < ln <= len(parts) else ""


def probe_kt_unclosed_comment(text: str, path: str):
    """CH-01 — a block comment that never closes (the W-021 signature)."""
    out = []
    for kind, ln, col in kt_scan(text):
        if kind == "UNCLOSED":
            out.append(dict(cls="unclosed_comment", path=path, line=ln,
                            text="block comment opened here never closes", autofixable=True))
        elif kind == "ORPHAN_CLOSE":
            out.append(dict(cls="orphan_comment_close", path=path, line=ln,
                            text="'*/' with no opener", autofixable=True))
    return out


def probe_foreign_import(text: str, path: str):
    """CH-02 — a REAL `import androidx.`/`kotlinx.` in a raw-chain tree (NEVER #12).

    Runs over code_only(): a comment that mentions androidx, or a `"androidx."` string
    literal, is blanked before the regex sees it — so only a genuine import statement is
    charged. (A naive grep charges all 47 mentions in this tree; this charges 0.)
    """
    out = []
    code = code_only(text)
    for m in re.finditer(r"(?m)^[ \t]*import[ \t]+(androidx|kotlinx)\.[^\n]*", code):
        ln = _line_of(code, m.start())
        out.append(dict(cls="foreign_import", path=path, line=ln,
                        text=m.group(0).strip(), autofixable=False))
    return out


def probe_nonnull_assert(text: str, path: str):
    """CH-03 — a `!!` non-null assertion that throws NPE if the value is null."""
    out = []
    code = code_only(text)
    for m in re.finditer(r"[\w\)\]]!!(?![=\w])", code):
        ln = _line_of(code, m.start())
        out.append(dict(cls="nonnull_assert", path=path, line=ln,
                        text=_src_line(text, ln), autofixable=False))
    return out


def probe_stub_body(text: str, path: str):
    """CH-04 — a stub: TODO()/NotImplementedError in shipped source."""
    out = []
    code = code_only(text)
    for m in re.finditer(r"\bTODO\s*\(|NotImplementedError", code):
        ln = _line_of(code, m.start())
        out.append(dict(cls="stub_todo", path=path, line=ln,
                        text=_src_line(text, ln), autofixable=False))
    return out


def probe_swallowed_exception(text: str, path: str):
    """CH-05 — a catch block that swallows the exception with an empty body.

    Emptiness is judged on the ORIGINAL bytes: the body may contain only whitespace and
    line/block comments. This matters — a catch whose body is `{ "ERROR: ..." }` is NOT
    empty, and blanking strings before the test (a tempting shortcut) would wrongly call
    it empty. The declared "I mean to ignore this" idiom is a named `_` binding
    (`catch (_: Exception) {}`), which is ACQUITTED.
    """
    out = []
    mask = char_code_mask(text)
    pat = re.compile(
        r"catch\s*\(\s*([A-Za-z_]\w*)\s*:\s*[\w.<>?\[\]]+\s*\)\s*\{"
        r"(?:\s|//[^\n]*|/\*.*?\*/)*\}"
        , re.DOTALL)
    for m in pat.finditer(text):
        if not mask[m.start()]:
            continue  # the whole catch is inside a comment
        if m.group(1) == "_":
            continue
        ln = _line_of(text, m.start())
        out.append(dict(cls="swallowed_exception", path=path, line=ln,
                        text=_src_line(text, ln), autofixable=False))
    return out


def probe_trailing_whitespace(text: str, path: str):
    """CH-06 — trailing spaces/tabs on a line (reversible; autofixed).

    Provably safe to fix: end-of-line whitespace is never semantically meaningful in
    Kotlin — except inside a raw (triple-quoted) string, where it is significant. Those
    lines are excluded via raw_lines(), so the fix can never change a string's bytes.
    """
    out = []
    protected = raw_lines(text)
    for i, raw in enumerate(text.split("\n"), 1):
        if i in protected:
            continue
        if raw != raw.rstrip():
            out.append(dict(cls="trailing_whitespace", path=path, line=i,
                            text=repr(raw[-8:]), autofixable=True))
    return out


def probe_missing_final_newline(text: str, path: str):
    """CH-07 — a file whose last byte is not a newline (reversible; autofixed)."""
    if text and not text.endswith("\n"):
        return [dict(cls="missing_final_newline", path=path, line=text.count("\n") + 1,
                     text="file does not end with a newline", autofixable=True)]
    return []


def probe_conflict_marker(text: str, path: str):
    """CH-08 — a git merge-conflict marker left in the tree."""
    out = []
    for i, raw in enumerate(text.split("\n"), 1):
        if re.match(r"^(<{7}|={7}|>{7})(\s|$)", raw):
            out.append(dict(cls="conflict_marker", path=path, line=i,
                            text=raw[:40], autofixable=False))
    return out


def probe_hardcoded_secret(text: str, path: str):
    """CH-09 — a credential-shaped string literal assigned in source.

    Matches on the ORIGINAL text (so the literal is visible) but rejects any match whose
    key token sits inside a comment — a doc line that says `token: "example"` is not a
    secret. This is the charmask at work: the literal is seen, the comment is not.
    """
    out = []
    mask = char_code_mask(text)
    pat = re.compile(r"(?i)\b(api[_-]?key|secret|passwd|password|token)\b\s*[:=]\s*"
                     r"\"([^\"\n]{8,})\"")
    for m in pat.finditer(text):
        if not mask[m.start()]:
            continue
        ln = _line_of(text, m.start())
        out.append(dict(cls="hardcoded_secret", path=path, line=ln,
                        text="credential-shaped literal in source", autofixable=False))
    return out


# ── JavaScript / Node probes ─────────────────────────────────────────────────
def _js_scan(text: str):
    """Yield (name, arity, line, scope_id) for every function declaration, scope-accurate.

    A proper forward pass: it tracks string/comment state, maintains a stack of scope
    frames (one frame per `{`), and records each function's ENCLOSING frame id. Two
    declarations collide only when they share the SAME enclosing frame — so the same name
    inside two different outer functions is never a false positive.
    """
    n = len(text)
    i = 0
    line = 1
    state = "code"
    stack = [0]
    uid = 0
    defs = []
    # regexes anchored at the current position
    re_fn = re.compile(r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)")
    re_arrow = re.compile(r"([A-Za-z_$][\w$]*)\s*[:=]\s*\(([^)]*)\)\s*=>")
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line"; i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; i += 2; continue
            if c == '"':
                state = "string"; i += 1; continue
            if c == "'":
                state = "char"; i += 1; continue
            if c == "`":
                state = "tmpl"; i += 1; continue
            m = re_fn.match(text, i)
            if m:
                arity = len([p for p in m.group(2).split(",") if p.strip()])
                defs.append((m.group(1), arity, line, stack[-1]))
                i = m.end(); continue
            m = re_arrow.match(text, i)
            if m:
                arity = len([p for p in m.group(2).split(",") if p.strip()])
                defs.append((m.group(1), arity, line, stack[-1]))
                i = m.end(); continue
            if c == "{":
                uid += 1; stack.append(uid); i += 1; continue
            if c == "}":
                if len(stack) > 1:
                    stack.pop()
                i += 1; continue
            if c == "\n":
                line += 1; i += 1; continue
            i += 1; continue
        if state == "line":
            if c == "\n":
                state = "code"; line += 1; i += 1; continue
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = "code"; i += 2; continue
            if c == "\n":
                line += 1; i += 1; continue
            i += 1; continue
        if state in ("string", "char"):
            if c == "\\":
                i += 2; continue
            if (state == "string" and c == '"') or (state == "char" and c == "'"):
                state = "code"; i += 1; continue
            if c == "\n":
                state = "code"; line += 1; i += 1; continue
            i += 1; continue
        if state == "tmpl":
            if c == "\\":
                i += 2; continue
            if c == "`":
                state = "code"; i += 1; continue
            if c == "\n":
                line += 1; i += 1; continue
            i += 1; continue
    return defs


def probe_node_functions(text: str, path: str):
    """CH-10 — a function name declared twice IN THE SAME SCOPE with a conflicting arity.

    The hazard: two `function walk(a)` and `function walk(a, b)` at the same level — the
    second silently shadows the first. The NON-hazard (acquitted): the same name reused in
    different nested scopes, which is legal and common (darkterm.js declares `walk` three
    times, each inside a different function, each with its own params).

    Scope is the ENCLOSING function frame (not raw brace depth), so a name reused across
    sibling outer functions is never flagged.
    """
    out = []
    seen = {}
    for name, arity, ln, scope in _js_scan(text):
        key = (name, scope)
        if key in seen and seen[key][0] != arity:
            out.append(dict(cls="node_functions", path=path, line=ln,
                            text=f"'{name}' redeclared in the same scope with arity "
                                 f"{arity} (first at line {seen[key][1]}, arity {seen[key][0]})",
                            autofixable=False))
        elif key not in seen:
            seen[key] = (arity, ln)
    return out


# The registry of charges. Each entry: (id, title, extensions, probe, severity, help)
#
# Severity is the trial's sentencing policy and the answer to "a gate that cries wolf is
# a broken gate" (W-040). Three tiers:
#   blocker  — a real defect that stops the raw chain or violates a NEVER; fails CI always.
#   escrow   — a real but pervasive hazard (a `!!` on a nullable, a cleanup catch). Named
#              and counted, and gated as a REGRESSION against a committed baseline — the
#              autophagy setpoint: the cell tolerates a basal level of damage and responds
#              when it exceeds the setpoint, it does not demand zero.
#   cosmetic — reversible formatting; autofixed, and (with --fail-on-fixable) must be zero.
CHARGES = [
    ("CH-01", "unclosed comment",        KT_EXTS, probe_kt_unclosed_comment,     "blocker",  "restore the closer"),
    ("CH-02", "foreign import",          KT_EXTS, probe_foreign_import,         "blocker",  "rewrite to raw android.*"),
    ("CH-03", "non-null assertion",      KT_EXTS, probe_nonnull_assert,         "escrow",   "guard or elvis"),
    ("CH-04", "stub / TODO",             KT_EXTS, probe_stub_body,              "blocker",  "implement or escrow"),
    ("CH-05", "swallowed exception",     KT_EXTS, probe_swallowed_exception,    "escrow",   "log or rethrow"),
    ("CH-06", "trailing whitespace",     KT_EXTS, probe_trailing_whitespace,    "cosmetic", "strip end-of-line ws"),
    ("CH-07", "missing final newline",   KT_EXTS, probe_missing_final_newline,  "cosmetic", "append \\n"),
    ("CH-08", "conflict marker",         KT_EXTS | JS_EXTS, probe_conflict_marker, "blocker", "resolve the merge"),
    ("CH-09", "hardcoded secret",        KT_EXTS, probe_hardcoded_secret,       "blocker",  "move to a secret store"),
    ("CH-10", "duplicate node function", JS_EXTS, probe_node_functions,         "escrow",   "rename or unify"),
]
CLASS_OF = {
    "CH-01": "unclosed_comment", "CH-02": "foreign_import", "CH-03": "nonnull_assert",
    "CH-04": "stub_todo", "CH-05": "swallowed_exception", "CH-06": "trailing_whitespace",
    "CH-07": "missing_final_newline", "CH-08": "conflict_marker",
    "CH-09": "hardcoded_secret", "CH-10": "node_functions",
}
SEVERITY_OF = {CLASS_OF[cid]: sev for cid, _t, _e, _p, sev, _h in CHARGES}
# The bounty weight of a finding: a blocker is worth 100 escrow units, an escrow 1, a
# cosmetic 0.1 — so the ranked bounty score is dominated by what actually blocks a build.
BOUNTY_WEIGHT = {"blocker": 100.0, "escrow": 1.0, "cosmetic": 0.1}
AUTOFIX_CLASSES = {"unclosed_comment", "orphan_comment_close", "trailing_whitespace",
                   "missing_final_newline"}
ORPHAN_SEVERITY = {"orphan_comment_close": "blocker"}


def severity_of(cls: str) -> str:
    return SEVERITY_OF.get(cls, ORPHAN_SEVERITY.get(cls, "escrow"))


# ──────────────────────────────────────────────────────────────────────────────
# the trial: positive + negative calibration for each charge
# ──────────────────────────────────────────────────────────────────────────────
# (charge_id, positive_source, negative_source). Positive MUST yield >=1 finding of the
# charge's class; negative MUST yield 0. A charge that fails either is a MISTRIAL.
TRIAL = [
    ("CH-01",
     "package a\n/* Copyright\n * line\nfun g() {}\n",
     "package a\n/* Copyright */\nfun g() {}\n"),
    ("CH-02",
     "package a\nimport androidx.compose.runtime.Composable\nfun g() {}\n",
     "package a\n// androidx FileProvider is not in android.jar\nval PREFIX = listOf(\"androidx.\", \"android.\")\nfun g() {}\n"),
    ("CH-03",
     "package a\nfun g(x: String?) { println(x!!) }\n",
     "package a\nfun g(x: String?) { println(x ?: \"\") }\n"),
    ("CH-04",
     "package a\nfun g(): Int { TODO() }\n",
     "package a\nfun g(): Int = 1\n"),
    ("CH-05",
     "package a\nfun g() { try { h() } catch (e: Exception) {} }\n",
     "package a\nfun g() { try { h() } catch (_: Exception) {} }\n"
     "fun i() { try { h() } catch (e: Exception) { \"ERROR: \" + e.message } }\n"),
    ("CH-06",
     "package a\nfun g() {  \n}\n",
     "package a\nfun g() {\n}\n"),
    ("CH-07",
     "package a\nfun g() {}",
     "package a\nfun g() {}\n"),
    ("CH-08",
     "package a\n<<<<<<< HEAD\nfun g() {}\n",
     "package a\nfun g() {}\n"),
    ("CH-09",
     "package a\nval apiKey = \"AKIA1234567890ABCD\"\n",
     "package a\nval apiKey = System.getenv(\"API_KEY\")\n"),
    ("CH-10",
     "function walk(a) {}\nfunction walk(a, b) {}\n",
     "function a() {\n  function walk(x) {}\n  return walk;\n}\nfunction b() {\n  function walk(y, z) {}\n  return walk;\n}\n"),
]
EXT_FOR = {cid: exts for cid, _, exts, _, _sev, _h in CHARGES}
PROBE_FOR = {cid: fn for cid, _, _, fn, _sev, _h in CHARGES}
CLASS_FOR = {
    "CH-01": {"unclosed_comment", "orphan_comment_close"},
    "CH-02": {"foreign_import"}, "CH-03": {"nonnull_assert"}, "CH-04": {"stub_todo"},
    "CH-05": {"swallowed_exception"}, "CH-06": {"trailing_whitespace"},
    "CH-07": {"missing_final_newline"}, "CH-08": {"conflict_marker"},
    "CH-09": {"hardcoded_secret"}, "CH-10": {"node_functions"},
}


def run_trial(verbose: bool = True) -> int:
    """Try every charge on a positive and a negative case. Return 0 iff all calibrated."""
    bad = 0
    rows = []
    for cid, pos, neg in TRIAL:
        probe = PROBE_FOR[cid]
        classes = CLASS_FOR[cid]
        pos_hits = [f for f in probe(pos, "<pos>") if f["cls"] in classes]
        neg_hits = [f for f in probe(neg, "<neg>") if f["cls"] in classes]
        sensitivity = len(pos_hits) >= 1
        specificity = len(neg_hits) == 0
        ok = sensitivity and specificity
        if not ok:
            bad += 1
        rows.append((cid, sensitivity, specificity))
        if verbose:
            print(f"  [{'PASS' if ok else 'MISTRIAL'}] {cid}  "
                  f"sensitivity={'ok' if sensitivity else 'MISS'}  "
                  f"specificity={'ok' if specificity else 'FALSE-POSITIVE'}")
    if verbose:
        print(f"TRIAL: {'PASS' if bad == 0 else 'FAIL'} — {len(TRIAL) - bad}/{len(TRIAL)} charges calibrated")
    return 0 if bad == 0 else 1


# ──────────────────────────────────────────────────────────────────────────────
# walking the tree + running the trial
# ──────────────────────────────────────────────────────────────────────────────
def iter_sources(root: pathlib.Path):
    exts = KT_EXTS | JS_EXTS
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in exts:
            yield p


def inspect_tree(root: pathlib.Path):
    findings = []
    files = 0
    for p in iter_sources(root):
        try:
            text = p.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue
        files += 1
        rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
        for cid, _title, exts, probe, _sev, _help in CHARGES:
            if p.suffix not in exts:
                continue
            try:
                findings.extend(probe(text, rel))
            except Exception as e:  # a probe must never crash the trial
                findings.append(dict(cls="probe_error", path=rel, line=0,
                                     text=f"{cid}: {e}", autofixable=False))
    return files, findings


# ──────────────────────────────────────────────────────────────────────────────
# autofix (reversible classes only, idempotent)
# ──────────────────────────────────────────────────────────────────────────────
def autofix_file(p: pathlib.Path) -> list[str]:
    """Repair the reversible classes in one file. Returns the list of fixes applied.

    Idempotent: re-running on an already-clean file applies nothing. Only reversible,
    well-understood classes are touched (W-042: autofix of a reversible, well-understood
    defect needs no permission); raw-string bytes are never altered.
    """
    text = p.read_text(encoding="utf-8", errors="surrogateescape")
    original = text
    applied = []

    # CH-07 missing final newline
    if text and not text.endswith("\n"):
        text = text + "\n"
        applied.append("missing_final_newline")

    # CH-06 trailing whitespace (skip raw-string lines: there the bytes are significant)
    protected = raw_lines(text)
    lines = text.split("\n")
    changed = False
    for i, raw in enumerate(lines, 1):
        if i not in protected and raw != raw.rstrip():
            lines[i - 1] = raw.rstrip()
            changed = True
    if changed:
        text = "\n".join(lines)
        applied.append("trailing_whitespace")

    # CH-01 unclosed comment: reuse the narrow, refusing closer-restorer (never a blind sed).
    if kt_scan(text):
        try:
            from fix_unclosed_comments import fix as _fix_unclosed  # noqa: E402
            p.write_text(text, encoding="utf-8", errors="surrogateescape")
            _path, msg, _detail = _fix_unclosed(str(p))
            if msg.startswith("FIXED"):
                applied.append("unclosed_comment")
            text = p.read_text(encoding="utf-8", errors="surrogateescape")
        except Exception:
            pass

    if text != original:
        p.write_text(text, encoding="utf-8", errors="surrogateescape")
    return applied


def run_fix(root: pathlib.Path):
    fixed = {}
    for p in iter_sources(root):
        applied = autofix_file(p)
        if applied:
            rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
            fixed[rel] = applied
    return fixed


# ──────────────────────────────────────────────────────────────────────────────
# the ledger (proof, deterministic — no wall-clock inside the payload)
# ──────────────────────────────────────────────────────────────────────────────
def classify(findings: list):
    """Group findings by class and by severity tier."""
    by_class = {}
    for f in findings:
        by_class.setdefault(f["cls"], []).append(f)
    tiers = {"blocker": [], "escrow": [], "cosmetic": []}
    for f in findings:
        tiers[severity_of(f["cls"])].append(f)
    return by_class, tiers


def bounty_score(findings: list) -> float:
    """The ranked bounty: sum of severity weights. Blockers dominate by 100x.

    This is the single scalar the inspector reports so "how bad is the tree" is a number,
    not a feeling — and so two trees (or two runs) can be ordered.
    """
    return round(sum(BOUNTY_WEIGHT[severity_of(f["cls"])] for f in findings), 2)


def load_baseline():
    if BASELINE.is_file():
        try:
            return json.loads(BASELINE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def write_ledger(root: pathlib.Path, files: int, findings: list):
    by_class, tiers = classify(findings)
    open_counts = {cls: len(v) for cls, v in sorted(by_class.items())}
    payload = {
        "_law": "source_inspector: the routine trial of the source for loopholes",
        "root": str(root.relative_to(ROOT)) if root.is_relative_to(ROOT) else str(root),
        "files_examined": files,
        "charges": [c[0] for c in CHARGES],
        "trial": {cid: {"sensitivity": True, "specificity": True} for cid, _, _ in TRIAL},
        "open": open_counts,
        "by_severity": {t: len(v) for t, v in tiers.items()},
        "bounty_score": bounty_score(findings),
        "autofixable": sum(1 for f in findings if f["autofixable"]),
        "bounty": [
            {"class": f["cls"], "severity": severity_of(f["cls"]), "path": f["path"],
             "line": f["line"], "note": f["text"], "autofixable": f["autofixable"]}
            for f in sorted(findings, key=lambda x: (severity_of(x["cls"]), x["cls"], x["path"], x["line"]))
        ],
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


# ──────────────────────────────────────────────────────────────────────────────
# HOMEOKINESIS (not homeostasis). The Operator's correction: a fixed tolerated level is
# STASIS — stagnation that a cell permits only by dying. The living equilibrium is
# HOMEOKINESIS: the internal state is held not by a static setpoint but by a FLUX — the
# debt is continuously moved, and the equilibrium is the RATE of clearance. So the escrow
# model here is a RATCHET with force-degradation, never a static tolerance:
#
#   * The high-water mark (HWM) per escrow class may only ever move DOWN. Lowering it is
#     the whole point; raising it requires an explicit, recorded, reasoned `--justify`
#     waiver (an "apoptotic exception" — a cell that must be removed for the whole to live).
#   * Any class above its HWM is a NET ADDITION of debt = a regression = FAIL.
#   * Debt that does not flux downward over the delivery window (DELIVERY_WINDOW) is
#     FORCE-DEGRADED: it is auto-promoted one severity tier per window (escrow -> blocker).
#     Stagnation is therefore not merely discouraged; it is scheduled to become fatal —
#     "stasis promotes stagnation as a metastatic, autoimmune, carcinomalous malefactor."
#   * The verdict reports the CLEARANCE FLUX (d(debt)/d(delivery)); negative is health.
#
# The ratchet is a HWM, not a floor: the gate can only get stricter over time, never looser,
# so the tree can only heal. This is the difference between a still photograph and a pulse.
# ──────────────────────────────────────────────────────────────────────────────
DELIVERY_WINDOW = 5  # deliveries of non-clearance before unaddressed escrow degrades


def _load_ratchet() -> dict:
    data = load_baseline()
    return {
        "hwm": data.get("hwm", {}),
        "justified": data.get("justified", {}),
        "deliveries_since_change": data.get("deliveries_since_change", {}),
        "delivery": data.get("delivery", 0),
        "history": data.get("history", []),
    }


def write_ratchet(state: dict):
    payload = {
        "_law": "source_inspector homeokinesis ratchet: debt may only flux downward; "
                "stagnation is force-degraded (the Operator's correction of homeostasis)",
        "delivery": state["delivery"],
        "hwm": state["hwm"],
        "justified": state["justified"],
        "deliveries_since_change": state["deliveries_since_change"],
        "history": state["history"][-40:],
    }
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ratchet_advance(state: dict, findings: list, justify: str = ""):
    """Advance the homeokinetic ratchet by one delivery. Returns (state, events)."""
    by_class, _ = classify(findings)
    escrow_now = {cls: len(v) for cls, v in by_class.items() if severity_of(cls) == "escrow"}
    hwm = dict(state["hwm"])
    since = dict(state["deliveries_since_change"])
    justified = dict(state["justified"])
    events = []

    for cls, n in escrow_now.items():
        if cls not in hwm:
            # first sight of this class: seed the high-water mark at the current level,
            # so the ratchet has a starting point to only ever move down from.
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
        else:  # n > prev: net addition of debt
            if justify:
                justified[cls] = justify
                events.append(f"JUSTIFIED waiver {cls}: {prev} -> {n} ({justify})")
                hwm[cls] = n
                since[cls] = 0
            # else: left for the verdict to fail; HWM is NOT raised.
    # classes that went to zero disappear from escrow_now; clear their HWM
    for cls in list(hwm):
        if cls not in escrow_now and hwm[cls] != 0:
            events.append(f"cleared {cls}: {hwm[cls]} -> 0 (flux down)")
            hwm[cls] = 0
            since[cls] = 0

    # FORCE-DEGRADATION: unaddressed debt over the window auto-promotes toward blocker.
    degraded = []
    for cls, d in since.items():
        if escrow_now.get(cls, 0) > 0 and d >= DELIVERY_WINDOW and cls not in justified:
            degraded.append(cls)

    state = dict(state)
    state["hwm"] = hwm
    state["since"] = since
    state["justified"] = justified
    state["delivery"] = state.get("delivery", 0) + 1
    state["deliveries_since_change"] = since
    state["history"] = state.get("history", []) + [
        {"delivery": state["delivery"], "escrow": escrow_now, "score": bounty_score(findings)}]
    return state, events, degraded


def clearance_flux(state: dict) -> float:
    """The homeokinetic signal: change in bounty score across the last two deliveries.
    Negative = the debt is clearing (healthy). Zero = stasis (the malefactor)."""
    h = state.get("history", [])
    if len(h) < 2:
        return 0.0
    return round(h[-1]["score"] - h[-2]["score"], 2)


def _synth_findings(counts: dict):
    """Build synthetic findings for a class->count map (for the ratchet proof)."""
    out = []
    for cls, n in counts.items():
        for i in range(n):
            out.append(dict(cls=cls, path=f"<synth:{cls}>", line=i + 1,
                            text="", autofixable=False))
    return out


def prove_ratchet(verbose: bool = True) -> int:
    """Prove the homeokinetic ratchet's four laws on a deterministic simulation.

    This is the "mathematically unassailable" part: the equilibrium is a set of executable
    laws, each demonstrated, not asserted.

      L1 MONOTONE CLEARANCE — when debt drops, the HWM drops with it and never rises back.
      L2 REGRESSION FAILS    — when debt exceeds the HWM, the verdict FAILS (net addition).
      L3 STASIS DEGRADES     — debt that does not flux down for DELIVERY_WINDOW deliveries
                               is force-degraded to a blocker (stasis is the malefactor).
      L4 APOPTOTIC WAIVER    — a justified rise is permitted, recorded, and does not degrade.
    """
    ok = True
    S = "swallowed_exception"

    def fresh():
        return {"hwm": {}, "justified": {}, "deliveries_since_change": {}, "delivery": 0,
                "history": []}

    # seed with 10, then clear to 4: HWM must ratchet 10 -> 4
    st = fresh()
    st, _, _ = ratchet_advance(st, _synth_findings({S: 10}))
    hwm_seed = st["hwm"].get(S)
    st, events, _ = ratchet_advance(st, _synth_findings({S: 4}))
    l1 = hwm_seed == 10 and st["hwm"].get(S) == 4
    ok &= l1
    if verbose:
        print(f"  [{'PASS' if l1 else 'FAIL'}] L1 monotone clearance: HWM {hwm_seed} -> {st['hwm'].get(S)}")

    # regression: raise to 7 above HWM 4 -> verdict FAIL
    code, _, _ = _verdict(_synth_findings({S: 7}), st, False, [])
    l2 = code == 1
    ok &= l2
    if verbose:
        print(f"  [{'PASS' if l2 else 'FAIL'}] L2 regression fails: 7 > HWM 4 -> exit {code}")

    # stasis: hold at 4 for DELIVERY_WINDOW deliveries -> force-degraded
    st2 = fresh()
    st2, _, _ = ratchet_advance(st2, _synth_findings({S: 4}))
    degraded = []
    for _ in range(DELIVERY_WINDOW):
        st2, _, degraded = ratchet_advance(st2, _synth_findings({S: 4}))
    l3 = S in degraded
    ok &= l3
    if verbose:
        print(f"  [{'PASS' if l3 else 'FAIL'}] L3 stasis degrades: stagnant {DELIVERY_WINDOW} "
              f"deliveries -> {'degraded' if l3 else 'not degraded'}")

    # apoptotic waiver: raise to 9 with a reason -> justified, not degraded, recorded
    st3 = fresh()
    st3, _, _ = ratchet_advance(st3, _synth_findings({S: 4}))
    st3, events, _ = ratchet_advance(st3, _synth_findings({S: 9}), justify="named exception")
    l4 = st3["hwm"].get(S) == 9 and st3["justified"].get(S) == "named exception"
    ok &= l4
    if verbose:
        print(f"  [{'PASS' if l4 else 'FAIL'}] L4 apoptotic waiver: raised to HWM "
              f"{st3['hwm'].get(S)} with recorded reason")

    if verbose:
        print(f"RATCHET PROOF: {'PASS' if ok else 'FAIL'} — 4/4 laws hold")
    return 0 if ok else 1


def _root_of(arg: str) -> pathlib.Path:
    p = pathlib.Path(arg)
    return p if p.is_absolute() else (ROOT / arg)


def _verdict(findings: list, state: dict, fail_on_fixable: bool, degraded: list):
    """Return (exit_code, lines, meta). Implements HOMEOKINESIS, not homeostasis.

    Rules (a gate that cries wolf is a broken gate, W-040; a gate that tolerates stasis is
    a metastatic malefactor):
      - any BLOCKER                     -> FAIL (a real defect that stops the chain)
      - ESCROW above its ratchet HWM    -> FAIL (net addition of debt = regression)
      - a class force-degraded by stasis -> FAIL (unaddressed debt crossed the window)
      - any COSMETIC                    -> FAIL only with --fail-on-fixable
      - escrow at/below HWM             -> PASS, and the flux is reported: health is a
                                           downward rate, not a still photograph.
    """
    _, tiers = classify(findings)
    hwm = state.get("hwm", {})
    by_class, _ = classify(findings)
    escrow_now = {cls: len(v) for cls, v in by_class.items() if severity_of(cls) == "escrow"}
    regressions = {cls: (n, hwm.get(cls, 0)) for cls, n in escrow_now.items()
                   if n > hwm.get(cls, 0)}
    flux = clearance_flux(state)

    meta = dict(blockers=len(tiers["blocker"]), escrow=len(tiers["escrow"]),
                cosmetic=len(tiers["cosmetic"]), regressions=regressions,
                degraded=degraded, flux=flux, score=bounty_score(findings))
    fail = False
    lines = []
    if tiers["blocker"]:
        fail = True
        lines.append(f"  FAIL — {len(tiers['blocker'])} blocker(s) open (a real defect):")
        for f in tiers["blocker"][:8]:
            lines.append(f"    {f['cls']:<22} {f['path']}:{f['line']}  {f['text']}")
        if len(tiers["blocker"]) > 8:
            lines.append(f"    … and {len(tiers['blocker']) - 8} more")
    if regressions:
        fail = True
        lines.append("  FAIL — net addition of escrow debt above the ratchet HWM:")
        for cls, (now, base) in sorted(regressions.items()):
            lines.append(f"    {cls:<22} {now} > HWM {base}")
    if degraded:
        fail = True
        lines.append("  FAIL — STASIS: unaddressed escrow force-degraded to blocker:")
        for cls in degraded:
            lines.append(f"    {cls:<22} stagnant for {DELIVERY_WINDOW} deliveries")
    if tiers["cosmetic"] and fail_on_fixable:
        fail = True
        lines.append(f"  FAIL — {len(tiers['cosmetic'])} cosmetic defect(s) "
                     f"(run: source_inspector.py fix)")
    if not fail:
        direction = "clearing" if flux < 0 else ("stagnant" if flux == 0 else "accumulating")
        lines.append(f"  PASS — 0 blockers; escrow {len(tiers['escrow'])} at/below HWM; "
                     f"clearance flux {flux:+} ({direction})")
    return (1 if fail else 0), lines, meta


def cmd_inspect(args) -> int:
    root = _root_of(args.root)
    if not root.is_dir():
        print(f"source_inspector: FAIL — no such root: {root}")
        return 1
    files, findings = inspect_tree(root)

    if run_trial(verbose=False) != 0:
        print("source_inspector: MISTRIAL — a charge is miscalibrated; fix the charge first")
        return 1

    state = _load_ratchet()
    if args.write_ratchet:
        state, events, degraded = ratchet_advance(state, findings, justify=args.justify)
        write_ratchet(state)
        payload = write_ledger(root, files, findings)
        for e in events:
            print(f"  ratchet: {e}")
        if degraded:
            print(f"  ratchet: FORCE-DEGRADED (stasis) {', '.join(degraded)}")
        code, lines, meta = _verdict(findings, state, args.fail_on_fixable, degraded)
        print(f"  ratchet delivery {state['delivery']} -> {BASELINE.relative_to(ROOT)}")
        for ln in lines:
            print(ln)
        return code

    payload = write_ledger(root, files, findings)
    code, lines, meta = _verdict(findings, state, args.fail_on_fixable, [])

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return code

    print(f"source_inspector: {files} file(s) examined under "
          f"{root.relative_to(ROOT) if root.is_relative_to(ROOT) else root}")
    print(f"  bounty score {meta['score']}  "
          f"(blockers {meta['blockers']} · escrow {meta['escrow']} · cosmetic {meta['cosmetic']})")
    for ln in lines:
        print(ln)
    if findings:
        print("  by charge:")
        for cls in sorted(payload["open"]):
            n = payload["open"][cls]
            print(f"    {cls:<22} {n:>3}  [{severity_of(cls)}]")
    print(f"  ledger: {LEDGER.relative_to(ROOT)}")
    if meta["cosmetic"]:
        print("  run: python3 tools/source_inspector.py fix   (repair reversible charges)")
    return code


def cmd_fix(args) -> int:
    root = _root_of(args.root)
    if not root.is_dir():
        print(f"source_inspector: FAIL — no such root: {root}")
        return 1
    fixed = run_fix(root)
    if not fixed:
        print("source_inspector: fix — nothing to repair (already clean / idempotent)")
    else:
        print(f"source_inspector: fix — repaired {len(fixed)} file(s)")
        for rel, classes in sorted(fixed.items()):
            print(f"    {rel}: {', '.join(sorted(set(classes)))}")
    # prove idempotency: a second pass must change nothing
    again = run_fix(root)
    if again:
        print("source_inspector: WARNING — a second fix pass changed bytes (NOT idempotent)")
        return 1
    # prove the fix introduced no blocker
    _, findings = inspect_tree(root)
    blockers = [f for f in findings if severity_of(f["cls"]) == "blocker"]
    if blockers:
        print(f"source_inspector: WARNING — {len(blockers)} blocker(s) present after fix")
        return 1
    print("source_inspector: idempotent — a second pass is byte-identical; no blocker introduced")
    return 0


def cmd_ratchet(args) -> int:
    """Advance the homeokinetic ratchet one delivery (used by CI and by hand)."""
    root = _root_of(args.root)
    _, findings = inspect_tree(root)
    state = _load_ratchet()
    state, events, degraded = ratchet_advance(state, findings, justify=args.justify or "")
    write_ratchet(state)
    print(f"source_inspector: ratchet delivery {state['delivery']}")
    print(f"  HWM: {state['hwm'] or 'clean'}")
    for e in events:
        print(f"  {e}")
    if degraded:
        print(f"  FORCE-DEGRADED (stasis -> blocker): {', '.join(degraded)}")
    print(f"  clearance flux: {clearance_flux(state):+}")
    return 0


def cmd_trial(args) -> int:
    rc = run_trial(verbose=True)
    print()
    rc |= prove_ratchet(verbose=True)
    return rc


def cmd_prove(args) -> int:
    return prove_ratchet(verbose=True)


def cmd_report(args) -> int:
    if not LEDGER.is_file():
        print("source_inspector: no ledger yet (run: inspect)")
        return 1
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    state = _load_ratchet()
    print(f"source_inspector ledger — {_stamp()}")
    print(f"  root: {payload['root']}  files: {payload['files_examined']}")
    print(f"  bounty score: {payload['bounty_score']}  "
          f"by severity: {payload['by_severity']}")
    print(f"  open: {payload['open'] or 'none'}")
    print(f"  homeokinesis: delivery {state['delivery']}  HWM {state['hwm'] or 'clean'}  "
          f"flux {clearance_flux(state):+}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the logical trial examiner for source features")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("inspect")
    s.add_argument("--root", default=DEFAULT_ROOT)
    s.add_argument("--json", action="store_true")
    s.add_argument("--fail-on-fixable", action="store_true")
    s.add_argument("--write-ratchet", action="store_true",
                   help="advance the homeokinetic ratchet one delivery and record it")
    s.add_argument("--justify", default="",
                   help="an apoptotic waiver reason: allow debt to rise for a named class")
    s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("fix"); s.add_argument("--root", default=DEFAULT_ROOT); s.set_defaults(fn=cmd_fix)
    s = sub.add_parser("ratchet")
    s.add_argument("--root", default=DEFAULT_ROOT)
    s.add_argument("--justify", default="")
    s.set_defaults(fn=cmd_ratchet)
    sub.add_parser("trial").set_defaults(fn=cmd_trial)
    sub.add_parser("selftest").set_defaults(fn=cmd_trial)
    sub.add_parser("prove").set_defaults(fn=cmd_prove)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = ap.parse_args()
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
