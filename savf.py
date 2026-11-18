#!/usr/bin/env python3
"""savf: Signed Axis Verification Formulary utility (SAVF-1).  Python 3.9+, stdlib only.

Two halves, one interface:
  axis core   Axis/Tau/charts/exp-log pair/handedness   (corrected SBAF-1)
  gates       scan(F1,F2,F3,F6) reach(F4) mutate(F7) freeze(F0) manifest(F10)
              ledger (claim kinds D/N/R/W/C/A/U) verdict (total, one PASS state)
Phi5, Phi8, Phi9 need a real referent: the tool re-runs recorded evidence commands
but cannot prove the dependency is real, so those results are labelled attested.
"""
import argparse, ast, hashlib, hmac, importlib, importlib.util, io, itertools
import json, math, os, random, re, shlex, shutil, subprocess, sys, tempfile, tokenize
from enum import IntEnum

_LOAD_SPEC = importlib.util.find_spec  # resolved once; find_spec is the hot path in scan

__version__ = "1.0.0"

# ======================================================================
# AXIS CORE
# ======================================================================
class Tau(IntEnum):
    POS = 1
    NEG = -1


class Axis:
    """Axis with poles P0, P1.  start(POS)=P0, start(NEG)=P1.
    at(s, tau) = start(tau) + tau*s*(P1-P0), s in [0,1]."""

    def __init__(self, P0, P1):
        self.P0 = tuple(float(x) for x in P0)
        self.P1 = tuple(float(x) for x in P1)
        if len(self.P0) != len(self.P1) or not self.P0:
            raise ValueError("poles must be non-empty and the same dimension")
        if self.P0 == self.P1:
            raise ValueError("poles must differ")

    @staticmethod
    def _tau(t):
        try:
            return Tau(t)
        except ValueError:
            raise ValueError(f"tau must be +1 or -1, got {t!r}") from None

    def start(self, t):
        return self.P0 if self._tau(t) == Tau.POS else self.P1

    def end(self, t):
        return self.P1 if self._tau(t) == Tau.POS else self.P0

    def at(self, s, t):
        """Point at fraction s along the axis, starting from start(tau) and
        moving toward end(tau).  at(0,tau)=start(tau), at(1,tau)=end(tau)."""
        t = self._tau(t)
        if not (-1e-12 <= s <= 1 + 1e-12):
            raise ValueError("s must lie in [0,1]")
        return tuple(c + int(t) * s * (q - p) for c, p, q in zip(self.start(t), self.P0, self.P1))


def f_exp(s, b, k, L):
    """Map [0,L]->[0,1]: (b^(ks)-1)/(b^(kL)-1).  Exact inverse is g_log."""
    _chk_exp(b, k, L)
    if not (0 <= s <= L):
        raise ValueError("s must lie in [0,L]")
    lb = math.log(b)
    return math.expm1(k * s * lb) / math.expm1(k * L * lb)


def g_log(u, b, k, L):
    """Inverse of f_exp on [0,1]: log_b(1+u(b^(kL)-1))/k."""
    _chk_exp(b, k, L)
    if not (0 <= u <= 1):
        raise ValueError("u must lie in [0,1]")
    lb = math.log(b)
    return math.log1p(u * math.expm1(k * L * lb)) / (k * lb)


def _chk_exp(b, k, L):
    if b <= 0 or b == 1:
        raise ValueError("b must be >0 and !=1")
    if k == 0 or L <= 0:
        raise ValueError("k must be nonzero and L>0")


# viewer frame: (right, up, toward-viewer).  Axis vectors per chart.
CHARTS = {
    "math":   {"x": (1, 0, 0), "y": (0, 1, 0),  "z": (0, 0, 1)},
    "raster": {"x": (1, 0, 0), "y": (0, -1, 0), "z": (0, 0, -1)},
    "sbaf0":  {"x": (-1, 0, 0), "y": (0, 1, 0), "z": (0, 0, -1)},
}
MOVES = {"L2R": (1, 0, 0), "R2L": (-1, 0, 0), "B2T": (0, 1, 0), "T2B": (0, -1, 0),
         "TOWARD": (0, 0, 1), "AWAY": (0, 0, -1), "NEAR2FAR": (0, 0, -1), "FAR2NEAR": (0, 0, 1)}


def _dot(a, b): return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def chart_sign(chart, axis, move):
    """+1/-1: sign of a physical move along a chart's axis."""
    d = _dot(MOVES[move], CHARTS[chart][axis])
    if d == 0:
        raise ValueError(f"move {move} is not along axis {axis}")
    return 1 if d > 0 else -1


def handedness(x, y, z):
    t = _dot(x, _cross(y, z))
    return "right" if t > 0 else "left" if t < 0 else "degenerate"


# ======================================================================
# VERDICT (total)
# ======================================================================
HARD = ("phi0", "phi1", "phi2", "phi3", "phi8", "phi9", "phi10")
SOFT = ("phi4", "phi5", "phi6", "phi7")
ALL_PHI = tuple(f"phi{i}" for i in range(11))
STATES = ("pass", "marginal", "fail")


def verdict(states):
    """Total over every assignment.  Missing or unknown = 'marginal' (unattested)."""
    s = {p: (states.get(p) if states.get(p) in STATES else "marginal") for p in ALL_PHI}
    if any(s[p] == "fail" for p in HARD): return "LIED"
    if any(s[p] == "fail" for p in SOFT): return "BLOCKED"
    if any(v == "marginal" for v in s.values()): return "REVIEW"
    return "PASS"


EXIT = {"PASS": 0, "REVIEW": 2, "BLOCKED": 3, "LIED": 4}

# ======================================================================
# STATIC SCAN  (phi1 stubs/markers, phi2 phantom symbols, phi3 tests, phi6 swallowed)
# ======================================================================
STDLIB = getattr(sys, "stdlib_module_names", frozenset())
NO_IMPORT = {"antigravity", "this", "idlelib", "turtle", "tkinter"}
SKIP_DIRS = {".git", "__pycache__", ".savf", "node_modules", "venv", ".venv", ".tox", "build", "dist"}
MARK = re.compile(r"\b(TODO|FIXME|STUB|PLACEHOLDER|HACK)\b")
FAKE_NAME = re.compile(r"^(MOCK|SAMPLE|FAKE)_[A-Z0-9_]+$")


def py_files(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        out += [os.path.join(d, f) for f in fs if f.endswith(".py")]
    return sorted(out)


def is_test_file(p):
    b = os.path.basename(p)
    return b.startswith("test_") or b.endswith("_test.py") or f"{os.sep}tests{os.sep}" in p


def local_modules(root):
    base = root if os.path.isdir(root) else os.path.dirname(root) or "."
    names = set()
    for d, ds, fs in os.walk(base):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        names.update(f[:-3] for f in fs if f.endswith(".py"))
        names.update(ds)
    return names


def _dec_names(fn):
    out = set()
    for d in fn.decorator_list:
        n = d.func if isinstance(d, ast.Call) else d
        out.add(n.attr if isinstance(n, ast.Attribute) else getattr(n, "id", ""))
    return out


def _is_stub_body(body):
    """True if a function body does nothing but pass, ..., raise NotImplementedError,
    a bare return/None, or a docstring.  Such a body is a stub (phi1)."""
    body = list(body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:] or [ast.Pass()]
    if len(body) != 1:
        return False
    n = body[0]
    if isinstance(n, ast.Pass):
        return True
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and n.value.value is Ellipsis:
        return True
    if isinstance(n, ast.Raise) and n.exc is not None:
        e = n.exc.func if isinstance(n.exc, ast.Call) else n.exc
        return getattr(e, "id", "") == "NotImplementedError"
    if isinstance(n, ast.Return):
        return n.value is None or (isinstance(n.value, ast.Constant) and n.value.value is None)
    return False


def _finding(rule, phi, path, line, msg, sev):
    return {"rule": rule, "phi": phi, "file": path, "line": line, "msg": msg, "sev": sev}


def scan_file(path, local, installed=None):
    try:
        # Decode exactly as CPython does: a UTF-8 BOM or a PEP 263 `coding:`
        # cookie on line 1 or 2 selects the codec.  A file Python can run must
        # never be reported as unparseable.
        with tokenize.open(path) as fh:
            src = fh.read()
        tree = ast.parse(src, path)
    except (SyntaxError, UnicodeDecodeError, LookupError, RecursionError, ValueError) as e:
        # CPython's own compiler recurses, so a long enough expression raises
        # RecursionError.  That is a failure to parse, not a reason to abort the
        # whole scan: report it as a parse finding like any other.
        return [_finding("PARSE", 1, path, getattr(e, "lineno", 0) or 0, f"cannot parse: {e}", "high")]
    test_file = is_test_file(path)
    F = []
    # markers: comments and identifiers only (never string literals)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT and MARK.search(tok.string) and not test_file:
                F.append(_finding("MARKER", 1, path, tok.start[0], f"marker in comment: {tok.string.strip()[:60]}", "medium"))
            if tok.type == tokenize.NAME and FAKE_NAME.match(tok.string) and not test_file:
                F.append(_finding("FAKE_DATA", 1, path, tok.start[0], f"mock-style identifier {tok.string}", "medium"))
    except tokenize.TokenError:
        pass
    # imports (phi2)
    mod_alias = {}
    for n in ast.walk(tree):
        names = []
        if isinstance(n, ast.Import):
            for a in n.names:
                names.append((a.name, a.asname or a.name.split(".")[0], n.lineno))
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            names.append((n.module, None, n.lineno))
        for full, bound, line in names:
            root = full.split(".")[0]
            if root in STDLIB or root in local or root == "__future__":
                if root in STDLIB and bound and "." not in full:
                    mod_alias[bound] = root
                continue
            if installed is not None:
                # An explicit set keeps the verdict identical on every host and
                # every interpreter, instead of depending on what is installed.
                if root in installed:
                    continue
            else:
                try:
                    if _LOAD_SPEC(root) is not None:
                        continue
                except (ImportError, ValueError):
                    pass
            F.append(_finding("PHANTOM_IMPORT", 2, path, line,
                              f"'{root}' is not stdlib, installed, or local", "high"))
    for n in ast.walk(tree):  # hallucinated stdlib attribute: json.loads_async
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in mod_alias:
            m = mod_alias[n.value.id]
            if m in NO_IMPORT:
                continue
            try:
                mod = importlib.import_module(m)
            except Exception:
                continue
            if hasattr(mod, n.attr):
                continue
            # A dotted access to a real submodule (logging.handlers, email.message)
            # is valid once that submodule is imported, but hasattr() only sees it
            # if something already imported it.  find_spec() is order-independent.
            try:
                if importlib.util.find_spec(m + "." + n.attr) is not None:
                    continue
            except Exception:
                pass
            F.append(_finding("PHANTOM_API", 2, path, n.lineno, f"{m}.{n.attr} does not exist", "high"))
    # stubs (phi1) and swallowed exceptions (phi6)
    proto_classes = set()
    for c in ast.walk(tree):
        if isinstance(c, ast.ClassDef):
            bases = {getattr(b, "id", getattr(b, "attr", "")) for b in c.bases}
            if bases & {"Protocol", "ABC"}:
                proto_classes.add(c)
    exempt = set()
    for c in proto_classes:
        exempt.update(id(x) for x in ast.walk(c))
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(n) in exempt or _dec_names(n) & {"abstractmethod", "overload"}:
                continue
            if n.name.startswith("__") and n.name.endswith("__"):
                continue
            # a stub test is reported by phi3 (VACUOUS_TEST); phi1 is for production code
            if not test_file and _is_stub_body(n.body):
                F.append(_finding("STUB", 1, path, n.lineno, f"function '{n.name}' has a stub body", "high"))
        if isinstance(n, ast.ExceptHandler):
            if len(n.body) == 1 and isinstance(n.body[0], ast.Pass):
                F.append(_finding("SWALLOWED", 6, path, n.lineno, "exception swallowed with pass", "medium"))
    # test integrity (phi3)
    if test_file:
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                F += _check_test(path, n)
    return F


def _check_test(path, fn):
    """phi3: a test function must contain at least one real assertion, and none of
    them may be tautological.  Counts both `assert` statements and unittest-style
    assert* calls (self.assertEqual(a, b), assertTrue(True), ...)."""
    asserts, weak, taut = 0, 0, 0

    def is_taut_call(call):
        nm = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
        args = call.args
        if nm in ("assertEqual", "assertIs", "assertListEqual", "assertDictEqual", "assertSetEqual",
                  "assertTupleEqual", "assertSequenceEqual") and len(args) >= 2:
            return ast.dump(args[0]) == ast.dump(args[1])
        if nm in ("assertTrue", "assertFalse") and len(args) >= 1:
            return isinstance(args[0], ast.Constant) and bool(args[0].value) == (nm == "assertTrue")
        return False

    for n in ast.walk(fn):
        if isinstance(n, ast.Assert):
            asserts += 1
            t = n.test
            if isinstance(t, ast.Constant) and t.value:
                taut += 1
            elif isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq) \
                    and ast.dump(t.left) == ast.dump(t.comparators[0]):
                taut += 1
            elif isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.IsNot) \
                    and isinstance(t.comparators[0], ast.Constant) and t.comparators[0].value is None:
                weak += 1
        elif isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nm.startswith("assert") or nm in {"fail", "raises", "approx"}:
                asserts += 1
                if is_taut_call(n):
                    taut += 1
    out = []
    if asserts == 0:
        out.append(_finding("VACUOUS_TEST", 3, path, fn.lineno, f"test '{fn.name}' asserts nothing", "high"))
    elif taut:
        out.append(_finding("TAUTOLOGY", 3, path, fn.lineno, f"test '{fn.name}' contains a tautological assert", "high"))
    elif weak and weak == asserts:
        out.append(_finding("WEAK_ASSERT", 3, path, fn.lineno, f"test '{fn.name}' only asserts 'is not None'", "medium"))
    return out


def scan(root, installed=None):
    local = local_modules(root)
    F = []
    for p in py_files(root):
        F += scan_file(p, local, installed)
    return F


def phi_from_findings(F, phi):
    xs = [f for f in F if f["phi"] == phi]
    return "fail" if any(f["sev"] == "high" for f in xs) else "marginal" if xs else "pass"


# ======================================================================
# REACHABILITY (phi4)
# ======================================================================
RUNNER = r'''
import sys, os, json, threading, runpy
root = os.path.realpath(sys.argv[1]); out = sys.argv[2]; mod = sys.argv[3]; args = sys.argv[4:]
entered = set()
def tr(frame, event, arg):
    if event == "call":
        fn = os.path.realpath(frame.f_code.co_filename)
        if fn.startswith(root + os.sep) or fn == root:
            entered.add((fn, frame.f_code.co_firstlineno))
    return None
sys.argv = [mod] + args
sys.path.insert(0, root)
threading.settrace(tr); sys.settrace(tr)
code = 0
try:
    runpy.run_module(mod, run_name="__main__", alter_sys=True)
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
finally:
    sys.settrace(None)
json.dump({"code": code, "entered": [list(x) for x in entered]}, open(out, "w"))
'''


def defined_functions(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _dec_names(n) & {"abstractmethod", "overload"}:
                continue
            first = min([d.lineno for d in n.decorator_list] + [n.lineno])
            out.append((n.name, first))
    return out


def reach(root, src_paths, test_module_args):
    """Run tests under a call tracer; list src functions never entered."""
    root = os.path.realpath(root)
    with tempfile.TemporaryDirectory() as td:
        r, o = os.path.join(td, "runner.py"), os.path.join(td, "out.json")
        open(r, "w").write(RUNNER)
        parts = shlex.split(test_module_args)
        p = subprocess.run([sys.executable, r, root, o] + parts, cwd=root, capture_output=True, text=True, timeout=600)
        if not os.path.exists(o):
            raise RuntimeError("tracer produced no output:\n" + p.stderr[-800:])
        data = json.load(open(o))
    entered = {(f, l) for f, l in data["entered"]}
    total, missed = 0, []
    for sp in src_paths:
        rp = os.path.realpath(sp)
        for name, line in defined_functions(sp):
            total += 1
            if (rp, line) not in entered:
                missed.append({"file": sp, "line": line, "function": name})
    return {"tests_exit": data["code"], "functions": total, "entered": total - len(missed), "missed": missed}


# ======================================================================
# MUTATION (phi7)
# ======================================================================
_CMP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE,
        ast.LtE: ast.Gt, ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}
_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}


class _Mut(ast.NodeTransformer):
    def __init__(self, target):
        self.target, self.n, self.line = target, -1, 0

    def _tick(self, node):
        self.n += 1
        if self.n == self.target:
            self.line = getattr(node, "lineno", 0)
            return True
        return False

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            if type(op) in _CMP and self._tick(node):
                node.ops[i] = _CMP[type(op)]()
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in _BIN and self._tick(node):
            node.op = _BIN[type(node.op)]()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self._tick(node):
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._tick(node):
            return node.operand
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            if self._tick(node):
                return ast.copy_location(ast.Constant(not node.value), node)
        elif isinstance(node.value, int):
            if self._tick(node):
                return ast.copy_location(ast.Constant(node.value + 1), node)
        return node


def mutant_count(src):
    m = _Mut(-1)
    m.visit(ast.parse(src))
    return m.n + 1


def make_mutant(src, idx):
    m = _Mut(idx)
    tree = m.visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), m.line


def _cmd(cmd):
    parts = shlex.split(cmd)
    if parts and parts[0] in ("python", "python3"):
        parts[0] = sys.executable
    return parts


def mutate(root, src_paths, test_cmd, max_mutants=30, seed=1, timeout=120):
    root = os.path.realpath(root)
    base = subprocess.run(_cmd(test_cmd), cwd=root, capture_output=True, text=True, timeout=timeout)
    if base.returncode != 0:
        raise RuntimeError("baseline tests are red; mutation meaningless:\n" + (base.stdout + base.stderr)[-600:])
    sites = []
    for sp in src_paths:
        src = open(sp, encoding="utf-8").read()
        sites += [(sp, i) for i in range(mutant_count(src))]
    random.Random(seed).shuffle(sites)
    sites = sites[:max_mutants]
    killed, survived = 0, []
    for sp, i in sites:
        src = open(sp, encoding="utf-8").read()
        try:
            msrc, line = make_mutant(src, i)
        except Exception:
            continue
        with tempfile.TemporaryDirectory() as td:
            dst = os.path.join(td, "p")
            shutil.copytree(root, dst, ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"))
            rel = os.path.relpath(os.path.realpath(sp), root)
            open(os.path.join(dst, rel), "w", encoding="utf-8").write(msrc)
            try:
                rc = subprocess.run(_cmd(test_cmd), cwd=dst, capture_output=True, text=True, timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                rc = 1
        if rc != 0:
            killed += 1
        else:
            survived.append({"file": sp, "line": line, "site": i})
    n = killed + len(survived)
    return {"mutants": n, "killed": killed, "score": (killed / n) if n else None, "survivors": survived}


# ======================================================================
# FREEZE (phi0), MANIFEST (phi10)
# ======================================================================
LOCK = os.path.join(".savf", "contract.lock")
MANIFEST = os.path.join(".savf", "manifest.json")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()


def _canon(d): return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def freeze(paths, thresholds=None, exemptions=(), chart="unspecified", lock=LOCK, force=False):
    if os.path.exists(lock) and not force:
        raise SystemExit(f"{lock} exists; refusing to overwrite (overwriting is a tamper event; use --force)")
    for p in paths:
        if not os.path.isfile(p):
            raise SystemExit(f"freeze: no such file: {p}")
    d = {"version": 1, "files": {p: sha256_file(p) for p in paths},
         "thresholds": {"theta_mut": 0.6, "theta_cov": 0.8, **(thresholds or {})},
         "exemptions": sorted(exemptions), "chart": chart}
    d["seal"] = hashlib.sha256(_canon(d)).hexdigest()
    os.makedirs(os.path.dirname(lock) or ".", exist_ok=True)
    json.dump(d, open(lock, "w"), indent=2, sort_keys=True)
    return d


def load_lock(lock=LOCK):
    if not os.path.exists(lock):
        return None
    try:
        d = json.load(open(lock))
    except (json.JSONDecodeError, OSError) as e:
        raise SystemExit(f"{lock} is unreadable or not valid JSON: {e}")
    if not isinstance(d, dict) or "files" not in d or not isinstance(d["files"], dict):
        raise SystemExit(f"{lock} is not a SAVF contract lock (missing 'files')")
    return d


def load_evidence(path=None):
    """phi5/phi8/phi9 recorded evidence.  A missing file is empty; a corrupt one
    is a hard error (silently ignoring it would hide tampering)."""
    path = path or os.path.join(".savf", "evidence.json")
    if not os.path.exists(path):
        return {}
    try:
        d = json.load(open(path))
    except (json.JSONDecodeError, OSError) as e:
        raise SystemExit(f"{path} is unreadable or not valid JSON: {e}")
    if not isinstance(d, dict):
        raise SystemExit(f"{path} must contain a JSON object keyed by phi")
    return d


def check_freeze(lock=LOCK):
    """Returns (ok, problems).  Never raises: a corrupt lock is itself a problem."""
    try:
        d = load_lock(lock)
    except SystemExit as e:
        return False, [str(e)]
    if d is None:
        return False, ["no contract lock: contract not frozen"]
    body = {k: v for k, v in d.items() if k != "seal"}
    probs = []
    if hashlib.sha256(_canon(body)).hexdigest() != d.get("seal"):
        probs.append("lock seal mismatch: thresholds/exemptions edited after freeze")
    for p, h in d["files"].items():
        if not os.path.exists(p):
            probs.append(f"missing frozen file {p}")
        elif sha256_file(p) != h:
            probs.append(f"changed after freeze: {p}")
    return (not probs), probs


def manifest_create(paths, key, out=MANIFEST):
    files = {p: sha256_file(p) for p in paths}
    m = {"files": files, "mac": hmac.new(key.encode(), _canon(files), hashlib.sha256).hexdigest(),
         "alg": "HMAC-SHA256 (shared key; proves integrity, not public origin)"}
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(m, open(out, "w"), indent=2)
    return m


def manifest_verify(key, out=MANIFEST):
    if not os.path.exists(out):
        return None, ["no manifest"]
    try:
        m = json.load(open(out))
    except (json.JSONDecodeError, OSError) as e:
        return False, [f"manifest unreadable or not valid JSON: {e}"]
    if not isinstance(m, dict) or not isinstance(m.get("files"), dict) or not isinstance(m.get("mac"), str):
        return False, ["manifest is malformed (missing 'files' or 'mac')"]
    probs = []
    if not hmac.compare_digest(m["mac"], hmac.new(key.encode(), _canon(m["files"]), hashlib.sha256).hexdigest()):
        probs.append("manifest MAC invalid (wrong key or edited manifest)")
    for p, h in m["files"].items():
        if not os.path.exists(p) or sha256_file(p) != h:
            probs.append(f"artifact differs from manifest: {p}")
    return (not probs), probs


# ======================================================================
# LEDGER (claim kinds)
# ======================================================================
KINDS = {"D", "N", "R", "W", "C", "A", "U"}


def run_evidence(ev, timeout=120):
    """Re-run a recorded evidence command.  Returns (ok, sha256[:12] of output)."""
    if not isinstance(ev, dict) or not ev.get("cmd"):
        return False, "no-cmd"
    p = subprocess.run(_cmd(ev["cmd"]), capture_output=True, text=True, timeout=timeout)
    out = p.stdout + p.stderr
    ok = p.returncode == 0 and ev.get("expect", "") in out
    return ok, hashlib.sha256(out.encode()).hexdigest()[:12]


def ledger(claims, run=False):
    if not isinstance(claims, list):
        raise SystemExit("ledger expects a JSON array of claim objects")
    by_id, res, visiting = {c.get("id"): c for c in claims}, {}, set()
    bad = 0

    def eff(c):
        cid, k = c.get("id"), c.get("kind")
        if cid in res:
            return res[cid]
        if cid in visiting:
            r = {"id": cid, "kind": k, "effective": k, "status": "invalid", "note": "cycle in derived_from"}
            res[cid] = r
            return r
        visiting.add(cid)
        r = {"id": cid, "kind": k, "effective": k, "status": "", "note": ""}
        res[cid] = r
        ev = c.get("evidence") or {}
        if k not in KINDS:
            r.update(status="invalid", note="unknown kind")
        elif k == "D":
            r["status"] = "declared"
        elif k in ("N", "W"):
            if k == "W" and not (ev.get("external") and c.get("referent")):
                r.update(effective="D", status="declared", note="downgraded: witness lacks an external referent")
            elif not ev.get("cmd") or "expect" not in ev:
                r.update(status="invalid", note="needs evidence.cmd and evidence.expect")
            elif run:
                ok, h = run_evidence(ev)
                r.update(status="verified" if ok else "failed", note=f"output sha256:{h}")
            else:
                r["status"] = "unrun"
        elif k == "R":
            parents = c.get("derived_from") or []
            if not parents or any(p not in by_id for p in parents):
                r.update(status="invalid", note="derived_from missing or unknown id")
            else:
                ps = [eff(by_id[p]) for p in parents]
                good = all(x["status"] in ("declared", "verified") for x in ps)
                r.update(status="verified" if good else "unsupported",
                         note="" if good else "a parent is not declared/verified")
        elif k == "C":
            r["status"] = "unverified"
        elif k == "A":
            r["status"] = "analysis"
        else:
            r["status"] = "unverified"
        visiting.discard(cid)
        return r

    for c in claims:
        eff(c)
    rows = list(res.values())
    bad = sum(1 for r in rows if r["status"] in ("invalid", "failed", "unsupported"))
    return rows, bad


# ======================================================================
# SELFTEST (executed checks of the corrected core)
# ======================================================================
def selftest(n=2000, seed=11):
    R = []
    rng = random.Random(seed)

    def rec(name, ok, detail=""):
        R.append((name, bool(ok), detail))

    near = lambda a, b: all(abs(x - y) < 1e-9 for x, y in zip(a, b))
    bad = 0
    for _ in range(n):
        d = rng.choice([1, 2, 3])
        P0 = [rng.uniform(-9, 9) for _ in range(d)]
        P1 = [rng.uniform(-9, 9) for _ in range(d)]
        A, s = Axis(P0, P1), rng.random()
        mid = tuple(x + y for x, y in zip(P0, P1))
        sm = tuple(x + y for x, y in zip(A.at(s, 1), A.at(s, -1)))
        ok = (near(A.at(0, 1), A.start(1)) and near(A.at(1, 1), A.end(1)) and near(A.at(1, -1), A.end(-1))
              and near(A.at(s, 1), A.at(1 - s, -1)) and near(sm, mid))
        bad += not ok
    rec("axis law: endpoints, reversal, reflection", bad == 0, f"{n} random axes, failures={bad}")

    def orig(P0, P1, s, t):  # the defective SBAF-1 law, kept as a mutant
        return tuple(a + t * s * (b - a) for a, b in zip(P0, P1))
    P0, P1 = (0., 0.), (100., 0.)
    suite = {"avg=(P0+P1)/2": lambda L: near(tuple((a + b) / 2 for a, b in zip(L(P0, P1, .3, 1), L(P0, P1, .3, -1))), (50., 0.)),
             "+ends at P1,- ends at P0": lambda L: near(L(P0, P1, 1, 1), P1) and near(L(P0, P1, 1, -1), P0),
             "- reverses +": lambda L: near(L(P0, P1, .25, 1), L(P0, P1, .75, -1))}
    fixed = lambda a, b, s, t: Axis(a, b).at(s, t)
    survives = [k for k, p in suite.items() if p(orig)]
    rec("mutation adequacy: suite kills the defective law", not survives and all(p(fixed) for p in suite.values()),
        f"survivors={survives}")
    rec("original midpoint test passes the defective law (why it was inadequate)",
        near(tuple((a + b) / 2 for a, b in zip(orig(P0, P1, .3, 1), orig(P0, P1, .3, -1))), P0))
    try:
        Axis(P0, P1).at(.5, 5)
        rec("tau must be +-1", False, "accepted 5")
    except ValueError:
        rec("tau must be +-1", True)
    rec("spreadsheet COLUMN() delta is + in raster, - in sbaf0",
        chart_sign("raster", "x", "L2R") == 1 and chart_sign("sbaf0", "x", "L2R") == -1)
    rec("sbaf0 handedness is right",
        handedness(*(tuple(CHARTS["sbaf0"][a]) for a in "xyz")) == "right")
    rec("raster with z toward viewer is left",
        handedness((1, 0, 0), (0, -1, 0), (0, 0, 1)) == "left")
    badx = 0
    for _ in range(3000):
        b, k, L = rng.choice([2, math.e, 10, .5]), rng.uniform(.1, 3), rng.uniform(.5, 5)
        if abs(k * L * math.log(b)) > 15:
            continue
        s = rng.uniform(0, L)
        u = f_exp(s, b, k, L)
        badx += not (abs(f_exp(0, b, k, L)) < 1e-12 and abs(f_exp(L, b, k, L) - 1) < 1e-9
                     and abs(g_log(u, b, k, L) - s) < 1e-6)
    rec("exp/log pair: f(0)=0, f(L)=1, g is the exact inverse", badx == 0, f"failures={badx}")
    cnt, tot = {}, 0
    for combo in itertools.product(STATES, repeat=11):
        v = verdict(dict(zip(ALL_PHI, combo)))
        cnt[v] = cnt.get(v, 0) + 1
        tot += 1
    rec("verdict total over 3^11 states, one PASS", tot == 3 ** 11 and cnt.get("PASS") == 1, str(cnt))
    return R


# ======================================================================
# GATE (orchestrates everything automatable)
# ======================================================================
def gate(root, src, test_cmd, reach_args, max_mutants, seed):
    res, notes = {}, {}
    ok, probs = check_freeze()
    res["phi0"], notes["phi0"] = ("pass" if ok else "fail"), "; ".join(probs) or "contract unchanged since freeze"
    lock = load_lock() or {"thresholds": {}, "exemptions": []}
    th = {"theta_mut": 0.6, "theta_cov": 0.8, **lock.get("thresholds", {})}
    src_files = [p for p in py_files(src) if not is_test_file(p)]
    F = scan(root)
    for phi in (1, 2, 3, 6):
        n = [f for f in F if f["phi"] == phi]
        res[f"phi{phi}"] = phi_from_findings(F, phi)
        notes[f"phi{phi}"] = f"{len(n)} finding(s)" + ("".join(f"\n      {f['file']}:{f['line']} {f['rule']} {f['msg']}" for f in n[:8]))
    try:
        r = reach(root, src_files, reach_args)
        frac = r["entered"] / r["functions"] if r["functions"] else 1.0
        res["phi4"] = "pass" if not r["missed"] and r["tests_exit"] == 0 else ("marginal" if frac >= th["theta_cov"] and r["tests_exit"] == 0 else "fail")
        notes["phi4"] = f"{r['entered']}/{r['functions']} functions entered; tests exit {r['tests_exit']}" + \
            "".join(f"\n      never entered: {m['file']}:{m['line']} {m['function']}" for m in r["missed"][:8])
    except Exception as e:
        res["phi4"], notes["phi4"] = "fail", f"trace error: {e}"
    try:
        m = mutate(root, src_files, test_cmd, max_mutants, seed)
        sc = m["score"]
        res["phi7"] = "marginal" if sc is None else "pass" if sc >= th["theta_mut"] else "marginal" if sc >= th["theta_mut"] - .15 else "fail"
        notes["phi7"] = f"killed {m['killed']}/{m['mutants']} (theta {th['theta_mut']})" + \
            "".join(f"\n      survived: {s['file']}:{s['line']}" for s in m["survivors"][:8])
    except Exception as e:
        res["phi7"], notes["phi7"] = "fail", f"mutation error: {e}"
    try:
        ev = load_evidence()
    except SystemExit as e:
        ev = {}
        notes["_evidence"] = str(e)
    for phi in ("phi5", "phi8", "phi9"):
        if phi in lock.get("exemptions", []) and phi != "phi5":
            res[phi], notes[phi] = "pass", "exempt (declared in lock; residual risk)"
            continue
        e = ev.get(phi)
        if not e:
            res[phi], notes[phi] = "marginal", "unattested: no evidence recorded"
            continue
        try:
            ok, h = run_evidence(e)
        except Exception as ex:
            res[phi], notes[phi] = "fail", f"evidence command error: {ex}"
            continue
        attested = bool(e.get("real_dependency")) and bool(e.get("signed_off_by")) if phi != "phi5" else bool(e.get("held_out_sealed"))
        res[phi] = "pass" if ok and attested else "marginal" if ok else "fail"
        notes[phi] = f"evidence re-run {'ok' if ok else 'FAILED'} sha256:{h}; attested={attested} (tool cannot prove the referent is real)"
    key = os.environ.get("SAVF_KEY")
    if key:
        ok, probs = manifest_verify(key)
        res["phi10"] = "marginal" if ok is None else "pass" if ok else "fail"
        notes["phi10"] = "; ".join(probs) or "manifest verified"
    else:
        res["phi10"], notes["phi10"] = "marginal", "unattested: SAVF_KEY not set"
    return res, notes


# ======================================================================
# CLI
# ======================================================================
def _is_data_token(tok):
    """True for a value like `-3`, `-1.5`, or `-41.4,-8.1` -- data that merely
    happens to start with a minus sign."""
    if len(tok) < 2 or tok[0] != "-" or tok[1] == "-":
        return False
    for part in tok[1:].split(","):
        try:
            float(part)
        except ValueError:
            return False
    return True


def _normalize_argv(argv):
    """argparse reads a leading '-' as an option, so `--p0 -41.4,-8.1` fails with
    "expected one argument".  Fold such a value onto the option it follows
    (`--p0=-41.4,-8.1`), which argparse accepts.  Real flags are untouched."""
    out = []
    for tok in argv:
        if (out and out[-1].startswith("--") and "=" not in out[-1]
                and _is_data_token(tok)):
            out[-1] += "=" + tok
        else:
            out.append(tok)
    return out


def _parse_pt(s):
    try:
        return tuple(float(x) for x in s.split(","))
    except ValueError:
        raise SystemExit(f"point must be comma-separated numbers, got {s!r}")


def _load_json_arg(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read JSON from {path}: {e}")


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(prog="savf", description=__doc__.split("\n")[0])
    ap.add_argument("--version", action="version", version=__version__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("axis", help="evaluate P(s;tau) on an axis")
    a.add_argument("--p0", required=True); a.add_argument("--p1", required=True)
    a.add_argument("--s", type=float, required=True); a.add_argument("--tau", type=int, required=True, choices=[1, -1])
    c = sp.add_parser("sign", help="sign of a physical move in a named chart")
    c.add_argument("--chart", choices=sorted(CHARTS), required=True)
    c.add_argument("--axis", choices="xyz", required=True); c.add_argument("--move", choices=sorted(MOVES), required=True)
    sp.add_parser("selftest", help="execute the corrected-core checks")
    s = sp.add_parser("scan", help="phi1/2/3/6 static scan"); s.add_argument("path"); s.add_argument("--json", action="store_true")
    s.add_argument("--installed", default=None,
                   help="comma-separated third-party modules to treat as importable")
    r = sp.add_parser("reach", help="phi4: functions never entered by tests")
    r.add_argument("--root", default="."); r.add_argument("--src", required=True)
    r.add_argument("--test", required=True, help='module and args, e.g. "unittest discover -s tests"')
    m = sp.add_parser("mutate", help="phi7 mutation score")
    m.add_argument("--root", default="."); m.add_argument("--src", required=True)
    m.add_argument("--test-cmd", required=True); m.add_argument("--max", type=int, default=30)
    m.add_argument("--seed", type=int, default=1)
    f = sp.add_parser("freeze", help="phi0: hash the contract files and thresholds")
    f.add_argument("files", nargs="+"); f.add_argument("--theta-mut", type=float); f.add_argument("--theta-cov", type=float)
    f.add_argument("--exempt", default=""); f.add_argument("--chart", default="unspecified"); f.add_argument("--force", action="store_true")
    sp.add_parser("check-freeze", help="phi0: detect tampering since freeze")
    mf = sp.add_parser("manifest", help="phi10: create/verify an HMAC manifest (key in SAVF_KEY)")
    mf.add_argument("action", choices=["create", "verify"]); mf.add_argument("files", nargs="*")
    l = sp.add_parser("ledger", help="validate a claims ledger (JSON)"); l.add_argument("file"); l.add_argument("--run", action="store_true")
    v = sp.add_parser("verdict", help="verdict from a JSON of phi0..phi10 states"); v.add_argument("file")
    g = sp.add_parser("gate", help="run every automatable gate and print the verdict")
    g.add_argument("--root", default="."); g.add_argument("--src", required=True)
    g.add_argument("--test-cmd", required=True); g.add_argument("--reach-test", required=True)
    g.add_argument("--max", type=int, default=30); g.add_argument("--seed", type=int, default=1); g.add_argument("--out")

    A = ap.parse_args(_normalize_argv(list(argv)))
    if A.cmd == "axis":
        try:
            ax = Axis(_parse_pt(A.p0), _parse_pt(A.p1))
            print(json.dumps({"point": ax.at(A.s, A.tau), "start": ax.start(A.tau), "end": ax.end(A.tau)}))
        except ValueError as e:
            raise SystemExit(f"axis: {e}")
    elif A.cmd == "sign":
        print(chart_sign(A.chart, A.axis, A.move))
    elif A.cmd == "selftest":
        R = selftest()
        for n, ok, d in R:
            print(f"[{'PASS' if ok else 'FAIL'}] {n} {d}")
        good = all(ok for _, ok, _ in R)
        print("selftest: ok" if good else "selftest: FAILED")
        return 0 if good else 1
    elif A.cmd == "scan":
        if not os.path.exists(A.path):
            raise SystemExit(f"scan: no such file or directory: {A.path}")
        inst = None
        if A.installed is not None:
            inst = {x.strip() for x in A.installed.split(",") if x.strip()}
        F = scan(A.path, inst)
        if A.json:
            print(json.dumps(F, indent=2))
        else:
            for x in F:
                print(f"{x['file']}:{x['line']} [{x['sev']}] phi{x['phi']} {x['rule']}: {x['msg']}")
            print(f"{len(F)} finding(s)")
        return 1 if any(x["sev"] == "high" for x in F) else 0
    elif A.cmd == "reach":
        if not os.path.isdir(A.root):
            raise SystemExit(f"reach: no such root directory: {A.root}")
        out = reach(A.root, [p for p in py_files(A.src) if not is_test_file(p)], A.test)
        print(json.dumps(out, indent=2))
        return 0 if not out["missed"] and out["tests_exit"] == 0 else 1
    elif A.cmd == "mutate":
        if not os.path.isdir(A.root):
            raise SystemExit(f"mutate: no such root directory: {A.root}")
        out = mutate(A.root, [p for p in py_files(A.src) if not is_test_file(p)], A.test_cmd, A.max, A.seed)
        print(json.dumps(out, indent=2))
    elif A.cmd == "freeze":
        th = {k: v for k, v in (("theta_mut", A.theta_mut), ("theta_cov", A.theta_cov)) if v is not None}
        d = freeze(A.files, th, [x for x in A.exempt.split(",") if x], A.chart, force=A.force)
        print(f"frozen {len(d['files'])} file(s); seal {d['seal'][:12]}")
    elif A.cmd == "check-freeze":
        ok, probs = check_freeze()
        print("\n".join(probs) or "contract unchanged since freeze")
        return 0 if ok else 1
    elif A.cmd == "manifest":
        key = os.environ.get("SAVF_KEY")
        if not key:
            print("set SAVF_KEY", file=sys.stderr); return 1
        if A.action == "create":
            manifest_create(A.files, key); print(f"manifest for {len(A.files)} file(s)")
        else:
            ok, probs = manifest_verify(key); print("\n".join(probs) or "manifest verified")
            return 0 if ok else 1
    elif A.cmd == "ledger":
        rows, bad = ledger(_load_json_arg(A.file), A.run)
        for r in rows:
            print(f"{r['id']:8s} {r['kind']}->{r['effective']}  {r['status']:11s} {r['note']}")
        print(f"{len(rows)} claims, {bad} problem(s)")
        return 1 if bad else 0
    elif A.cmd == "verdict":
        states = _load_json_arg(A.file)
        if not isinstance(states, dict):
            raise SystemExit("verdict expects a JSON object mapping phi0..phi10 to states")
        v = verdict(states); print(v); return EXIT[v]
    elif A.cmd == "gate":
        res, notes = gate(A.root, A.src, A.test_cmd, A.reach_test, A.max, A.seed)
        for p in ALL_PHI:
            print(f"{p:6s} {res[p]:9s} {notes[p]}")
        v = verdict(res)
        print(f"\nVERDICT: {v}")
        if A.out:
            json.dump(res, open(A.out, "w"), indent=2)
        return EXIT[v]
    return 0


if __name__ == "__main__":
    # The tool promises bad input yields a clean, non-zero error, never a raw
    # traceback. SystemExit (argparse usage, deliberate messages) passes through;
    # every other operational failure is reported as one line on stderr.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        sys.stderr.write(f"savf: {type(e).__name__}: {e}\n")
        sys.exit(2)
