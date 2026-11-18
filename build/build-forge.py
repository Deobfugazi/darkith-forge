#!/usr/bin/env python3
"""DARKITH Forge build pipeline -- one source of truth, many hosts.

SAVF is one truth function.  This pipeline makes every host consume the same
core, so one input yields one verdict wherever it is computed:

    savf.html            standalone page          carries the core
    code studio          standalone code manager  carries the core
    darkith forge        fused shell              carries the core
    terminal (TermKit)   shell surface            `savf` builtin -> the core

Source of truth
---------------
`darkith home forge.html` is the canonical artifact: it carries the newest
studio and the newest TermKit.  The disk file `darkith code studio.html` and the
fused `darkith forge.html` are *outputs* regenerated from it, which is what ends
the drift between the three copies.

Idempotency
-----------
Every injected block is delimited by a marker pair and replaced on each build,
so running the pipeline twice never doubles a payload.

Run:  python3 build/build-forge.py
      python3 build/build-forge.py --check     (verify sync, write nothing)
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

FORGE = ROOT / "darkith home forge.html"      # canonical shell (source of truth)
FORGE_OUT = ROOT / "darkith forge.html"       # fused artifact
STUDIO = ROOT / "darkith code studio.html"    # standalone mirror of the studio
SAVF_HTML = ROOT / "savf.html"

CORE = BUILD / "savf-core.js"
HOST = BUILD / "savf-host.js"
FACADE = BUILD / "truth-facade.js"

# markers: studio blocks live inside the carrier, shell blocks outside it, so
# they get distinct names and can never be confused by the stripper.
SC_START, SC_END = "<!-- SAVF-CORE:START -->", "<!-- SAVF-CORE:END -->"
SH_START, SH_END = "<!-- SAVF-HOST:START -->", "<!-- SAVF-HOST:END -->"
SS_START, SS_END = "<!-- SAVF-SHELL:START -->", "<!-- SAVF-SHELL:END -->"
ST_START, ST_END = "/* SAVF-TERM:START */", "/* SAVF-TERM:END */"
DH_START, DH_END = "/* DUAL-HELP:START */", "/* DUAL-HELP:END */"
PF_START, PF_END = "<!-- SAVF-FACADE:START -->", "<!-- SAVF-FACADE:END -->"

CARRIER_RE = re.compile(r'<script type="text/plain" id="studio-src">')
BUILTINS_ANCHOR = "var builtins = Object.create(null);"

TERMINAL_BUILTIN = """%s
  /* `savf <file.py>` -- the terminal surface of the one truth function.  It
     calls the same core the page and the studio call, so the verdict printed
     here is the verdict they would give. */
  builtins["savf"] = function (args) {
    var T = globalThis.SavfTruth;
    if (!T || typeof T.auditSource !== "function") { out("savf: core not loaded"); return 1; }
    if (args[0] === "--gates") {
      for (var g = 0; g <= 10; g++) out("  phi" + g + "  " + (T.gateInfo["phi" + g] || ""));
      return 0;
    }
    var path = args[0] || "";
    if (!path) { out("usage: savf <file.py> | savf --gates"); return 1; }
    var node = sh.fs.resolve(sh.cwd, path);
    if (!node || node.type !== "file") { err("savf: " + path + ": no such file", 1); return 1; }
    var res = T.auditSource(path, sh.fs.read(node));
    out(res.verdict + "  " + res.counts.total + " finding(s) over " + res.files + " file(s)");
    for (var i = 0; i < res.findings.length; i++) {
      var f = res.findings[i];
      out("  phi" + f.phi + "  " + f.rule + "  line " + f.line + "  " + f.msg);
    }
    /* Mirror savf.py's EXIT map so `$?` here means the same as the CLI's:
       PASS 0, REVIEW 2, BLOCKED 3, LIED 4.  Collapsing every non-PASS to 1
       would hide which verdict was reached from `&&`, `||` and scripts. */
    var EXIT = { PASS: 0, REVIEW: 2, BLOCKED: 3, LIED: 4 };
    return (EXIT[res.verdict] != null) ? EXIT[res.verdict] : 1;
  };
%s""" % (ST_START, ST_END)


def wrap_script(js: str) -> str:
    body = js.replace("</script", "<\\/script")
    return "<script>\n" + body + "\n</script>"


def inject(text: str, start: str, end: str, payload: str) -> str:
    """Replace a marked block, or insert a fresh one before the closing body.

    The anchor is the LAST `</body>` in the document: the shell embeds whole HTML
    documents inside JavaScript string literals, so an earlier occurrence would
    land the block inside a string and break the page.
    """
    block = start + "\n" + payload + "\n" + end
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(lambda m: block, text, count=1)
    idx = text.rfind("</body>")
    if idx < 0:
        raise SystemExit("no </body> to anchor against")
    return text[:idx] + block + "\n" + text[idx:]


def strip(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)


def get_carrier(shell: str) -> str:
    m = CARRIER_RE.search(shell)
    if not m:
        raise SystemExit("shell carries no studio-src")
    end = shell.find("</script>", m.end())
    return shell[m.end():end].replace("<\\/script", "</script")


def set_carrier(shell: str, studio: str) -> str:
    m = CARRIER_RE.search(shell)
    end = shell.find("</script>", m.end())
    return shell[:m.end()] + studio.replace("</script", "<\\/script") + shell[end:]


def patch_studio(studio: str, core: str, host: str) -> str:
    studio = strip(studio, SC_START, SC_END)
    studio = strip(studio, SH_START, SH_END)
    studio = inject(studio, SC_START, SC_END, wrap_script(core))
    studio = inject(studio, SH_START, SH_END, wrap_script(host))
    return studio


# ======================================================================
# DUAL-REGISTER HELP  (the one place both registers are defined)
# ----------------------------------------------------------------------
# `help` prints the novice register; `help dev` prints the developer register;
# `help beginner`/`help novices` print the novice register explicitly.
#
# Two design laws hold everywhere in this file:
#   * every sample command + expected output is EXACT — probed from the live
#     shell, never invented. The invariant debugger (`self-test`, see the
#     "INVARIANTS" block) is what proves the samples still hold.
#   * the compact one-line `HELP` table stays the `help CMD` detail lookup, so
#     existing behaviour is preserved byte-for-byte.
#
# The content lives in the Python dicts below, and is serialised into the
# builtin as a JSON literal (so there is exactly one source for the prose).
# ======================================================================

_HELP_INVARIANT_LINES = [
    "INVARIANT DEBUGGER — the 'test' chip runs the fixture battery: `self-test N/N`",
    "  API: window.TermKit.selftest() -> true, and it prints `self-test N/N`.",
    "  It proves the samples below still hold, byte-for-byte.",
    "  echo hi == \"hi\\n\"                          pipe   echo abc | tr a-z A-Z == \"ABC\\n\"",
    "  arith  echo $((6*7)) == \"42\\n\"               vars   x=5; echo $((x+1)) == \"6\\n\"",
    "  for    for i in 1 2; do echo $i; done == \"1\\n2\\n\"",
    "  while  i=0; while [ $i -lt 2 ]; do echo $i; i=$((i+1)); done == \"0\\n1\\n\"",
    "  if     if [ 1 -eq 1 ]; then echo y; fi == \"y\\n\"",
    "  case   case a in a) echo m;; esac == \"m\\n\"",
    "  redir  echo z > f; cat f == \"z\\n\"          glob   cd d && echo *.txt == \"a.txt\\n\"",
    "  grep/sort/cut/sed pipelines == \"a\\n\" / \"a\\nb\\n\" / \"b\\n\" / \"aXc\\n\"",
    "  crypto sha256Hex(\"abc\") == ba7816bf...  md5Hex(\"abc\") == 900150983cd24fb0d6963f7d28e17f72",
    "  base64 B64.decode(B64.encode(\"hi\")) == \"hi\"   func f(){ echo $1; }; f ok == \"ok\\n\"",
    "  cmdsub echo $(echo inner) == \"inner\\n\"        pow  echo $((2**8)) == \"256\\n\"",
    "  ansi   printf '\\033[32mX\\033[0m' emits a real SGR sequence",
    "  stdin  read consumes stdin; cat/tr/base64 accept a FILE operand",
    "  A FAILURE line names the exact broken invariant. (Note: the `test` COMMAND",
    "  is the POSIX predicate [ -f / -d / -z ]; the battery is the chip.)",
]

_HELP_FRACTURE_LINES = [
    "FRACTURE CLOSURE — why dksh diverges from Linux on purpose",
    "  Each row is a fracture (a real divergence), its closed form (what dksh",
    "  guarantees), and the rationale (why the closed form is the correct one here).",
    "",
    "  FRACTURE: no kernel, no processes, no fork/exec, no network, no root.",
    "    CLOSED : a pure-JS userspace — a virtual FS (VFS) plus an interpreter, all",
    "             in one page. `&` records a job, it does not schedule a process.",
    "    WHY    : a phone that is offline, unrooted and 4 GB cannot host a kernel;",
    "             the audit must run everywhere, for everyone, with zero install.",
    "",
    "  FRACTURE: a fresh shell is `cd /sdcard/Darkith` (not $HOME).",
    "    CLOSED : the project root is the working directory; $HOME is /sdcard.",
    "    WHY    : the first thing a novice types must land in their project.",
    "",
    "  FRACTURE: no POSIX `[ ... ]` file tests beyond -e -f -d -z -n.",
    "    CLOSED : a deliberately small predicate set, documented by `help test`.",
    "    WHY    : a small, honest set beats a large set that silently lies.",
    "",
    "  FRACTURE: no `awk`; `sed` supports only s///; `grep` has no -r/-E.",
    "    CLOSED : cut/tr/sed/sort/uniq cover the common text transforms.",
    "    WHY    : an unimplemented tool must say so (`awk: not implemented`),",
    "             never fake an answer. Use cut/grep/sed instead.",
    "",
    "  FRACTURE: `echo 7*6 | bc` -> 42, but `bc <<< '2^10'` exits 1 (no heredoc).",
    "    CLOSED : bc reads stdin only; it has no here-string in this dialect.",
    "    WHY    : input is explicit — a pipe or a file, never an implicit here-doc.",
    "",
    "  FRACTURE: `printf '%5s|'` prints literally; width/format verbs are limited.",
    "    CLOSED : %s %d %x %o %c and \\n \\t \\033 escapes only.",
    "    WHY    : the escapes people actually need for ANSI colour, and no more.",
    "",
    "  FRACTURE: `clear` and `cd -` are not builtins (exit 127 / status 1).",
    "    CLOSED : use the terminal's Clear button; `cd -` is not implemented.",
    "    WHY    : naming a boundary is honest; a half-built command is a lie.",
    "",
    "  FRACTURE: `echo abc | md5sum` prints `  -` (stdin), not a filename.",
    "    CLOSED : hash of stdin is labelled `-`, exactly like Linux.",
    "    WHY    : the label states the true source of the bytes hashed.",
]

HELP_DEV = [
    "Darkith Forge Terminal (TermKit 2.0) — DEVELOPER REGISTER (AI + experts)",
    "  offline userspace shell · zero dependency · deterministic · the forge's terminal",
    "",
    "READ THIS FIRST (atomic model — an unfamiliar agent absorbs the whole shell from here)",
    "  1. The unit of execution is a LINE. `sh.run(line) -> {status, out, err, text}`.",
    "     `text` is the byte-faithful stdout, so a pipeline rebuilds exact bytes.",
    "  2. State is per-shell and persists across lines: cwd, vars, exported, funcs,",
    "     aliases, history, jobs. `cd`/`export` therefore 'stick' with no subshell.",
    "  3. Grammar: list = pipeline ((';'|'&&'|'||'|'&') pipeline)*  ;",
    "     pipeline = command ('|' command)*  ; command = simple | if | for | while",
    "     | until | case | funcdef  ; simple = assignments? words+ redirs*  ;",
    "     redirs: > >> <   words undergo $VAR, ${VAR:-def}, $(cmd), `cmd`,",
    "     $((arith)), ~ and glob expansion, in that order.",
    "  4. `$?` is the last status (0 ok). A pipeline's status is its LAST stage's.",
    "  5. Local builtins (ls, cat, grep, sed, savf, forge, aegis, ...) run in-page.",
    "     Anything else routes to the host bridge if present, else exits 127.",
    "     `savf <file.py>` is the terminal surface of the audit engine (see below).",
    "  6. There is no fork/exec/network/root. `&` records a job; it does not spawn.",
    "",
    "SHELL SYNTAX",
    "  a | b            pipeline              a > f / a >> f   redirect / append",
    "  a < f            stdin from file       a && b / a || b  and / or",
    "  a ; b            sequence              a & b            background job",
    "  $VAR ${V:-x}     variable / default    $(cmd) `cmd`     command substitution",
    "  $((1+2*3))       arithmetic            ~ * ? [a-z] {a,b}  tilde/glob/brace",
    "  if/elif/else/fi  for/while/until       case/esac        control flow",
    "  f(){ ...; }      function              test / [ ]       conditions",
    "  \\n \\t \\033 \\e    printf escapes        Tab              complete paths/commands",
    "",
    "COMMANDS (builtins — `help CMD` for the one-line signature)",
    "  CORE     echo printf cd pwd export unset set env alias unalias type history",
    "           true false : break continue return local source . read mapfile help",
    "  FILES    ls cat head tail wc touch mkdir rm rmdir cp mv ln find du df stat",
    "           basename dirname readlink which",
    "  TEXT     grep sed sort uniq tr cut rev tac nl seq tee xargs expr",
    "  CRYPTO   base64 sha256sum md5sum factor bc",
    "  DARKITH  forge aegis savf (audit a .py; `savf --gates` lists phi0..phi10)",
    "",
    "ATOMIC RECIPES — command, then the EXACT output this shell prints",
    "  echo hello world            ->  hello world",
    "  echo -n x; echo y           ->  xy",
    "  printf '%s-%s\\n' a b        ->  a-b",
    "  echo abc | tr a-z A-Z       ->  ABC",
    "  echo a:b:c | cut -d: -f2    ->  b",
    "  printf 'b\\na\\n' | sort      ->  a / b        (two lines)",
    "  printf '3\\n1\\n2\\n' | sort -n -> 1 / 2 / 3",
    "  printf 'a\\nb\\na\\n' | sort | uniq -c ->  '      2 a' / '      1 b'",
    "  seq 2 2 8                   ->  2 / 4 / 6 / 8",
    "  echo $((6*7))               ->  42          x=5; echo $((x+1)) -> 6",
    "  echo $((2**10))             ->  1024        echo $((7%3))       -> 1",
    "  echo {a,b,c}                ->  a b c       echo a{1,2}b        -> a1b a2b",
    "  echo hi | base64            ->  aGkK        echo aGk= | base64 -d -> hi",
    "  echo darkith | sha256sum    ->  2fd75422...  -",
    "  for i in 1 2 3; do echo $i; done            ->  1 / 2 / 3",
    "  i=0; while [ $i -lt 2 ]; do echo $i; i=$((i+1)); done -> 0 / 1",
    "  if [ 1 -eq 1 ]; then echo y; fi             ->  y",
    "  echo z > f; cat f           ->  z           printf 'a\\nb\\n' | grep -v b -> a",
    "  printf 'aXbXc\\n' | grep -o X -> X / X        printf 'Abc\\n' | grep -i abc -> Abc",
    "  printf 'a\\n' | nl           ->  '     1\\ta'   echo abc | rev -> cba",
    "  echo a:b:c | cut -c 3-5     ->  b:c         echo '2^10' | bc -> 1024",
    "  f(){ echo $1; }; f ok       ->  ok          echo $(echo inner) -> inner",
    "  savf clean.py               ->  REVIEW  0 finding(s) over 1 file(s);  exit 2",
    "  savf stub.py                ->  LIED  ... STUB finding;                  exit 4",
    "",
    "EXIT CODES (mirror savf.py: EXIT = {PASS:0, REVIEW:2, BLOCKED:3, LIED:4})",
    "  generic command 0 ok / non-zero fail; `savf` returns the verdict's code,",
    "  so `savf f.py && echo clean` runs only on PASS.",
    "",
    "QUICK REFERENCE vs TERMUX / LINUX (differences that bite)",
    "  pipelines & redirects & control flow & $(...) : identical",
    "  VAR=1 cmd        -> command-scoped env, like sh",
    "  functions        -> status is the LAST command's (true->0, false->1);",
    "                      a bare `return N` yields 127 (no custom code yet)",
    "  test -e/-f/-d/-z/-n, = != -eq -lt -gt : supported (see `help test`)",
    "  no fork/exec/network; no awk; sed s/// only; grep has no -r/-E; no heredoc",
    "  echo 7*6 | bc -> 42   but   bc <<< '2^10' -> exit 1 (no here-string)",
    "  printf '%5s|' literal; width verbs unsupported",
    "  `clear`, `cd -` are NOT builtins (exit 127 / status 1)",
    "  md5sum/sha256sum label stdin as `-`, exactly like Linux",
    "  shells out to the host bridge only when a native backend is attached",
    "",
] + _HELP_INVARIANT_LINES + [
    "",
] + _HELP_FRACTURE_LINES + [
    "",
    "See also: `help beginner` (novice register), `help CMD` (one-line signature),",
    "          the 'test' chip (invariant debugger), `forge` (userspace tools).",
]

HELP_BEGINNER = [
    "Darkith Forge Terminal — BEGINNER HELP (the plain-language register)",
    "",
    "WHAT THIS IS",
    "  A terminal that lives inside the app. It needs no Termux, no internet,",
    "  no root and no install. It has its own little filesystem and its own",
    "  commands, and it always works — even with the phone in aeroplane mode.",
    "",
    "HOW TO USE IT",
    "  * Type a command, press Enter.",
    "  * Press the up arrow to see what you typed before.",
    "  * Press Tab to finish a file name or a command for you.",
    "  * Tap a quick-key button under the box for symbols like | > $ *",
    "  * The chips above the box: env, help, tree, test, save, Clear.",
    "",
    "WHERE YOU ARE",
    "  You start in /sdcard/Darkith — that is your project folder.",
    "  Type  pwd  to see where you are.  Type  ls  to list what is here.",
    "",
    "THE TWELVE COMMANDS THAT DO 90% OF THE WORK",
    "  ls              list the files here           ls /sdcard      list a folder",
    "  cd folder       go into a folder              cd ..           go up one",
    "  cat file        show a file's contents        pwd             where am I",
    "  echo words      print words                   clear?          use Clear button",
    "  mkdir name      make a folder                 rm file         delete a file",
    "  cp a b          copy a to b                   mv a b          move/rename a",
    "  grep word file  find lines with a word        wc -l file      count lines",
    "  help dev        the expert register           test chip       check the shell",
    "",
    "PIPES — THE ONE BIG IDEA, IN PLAIN WORDS",
    "  The vertical bar  |  hands the left command's output to the right one.",
    "  Read it as 'and then'.  Try these; the output is shown after ->",
    "",
    "    echo hello | tr a-z A-Z     ->  HELLO",
    "    echo a:b:c | cut -d: -f2    ->  b",
    "    printf 'b\\na\\n' | sort      ->  a  then  b  (two lines)",
    "",
    "WATCH OUT (things that differ from a Linux computer)",
    "  * There is no internet here and no system programs — only the ones listed.",
    "  * 'awk' is not here. Use cut, grep and sed instead.",
    "  * The symbols > and >> write to a file; < reads from one.",
    "  * A command that fails prints a message and sets $? to a non-zero number.",
    "",
    "TRY THIS NOW (type it, line by line)",
    "    echo hello | tr a-z A-Z",
    "    for i in 1 2 3; do echo $i; done",
    "    mkdir -p /tmp/demo && echo hi > /tmp/demo/a.txt && cat /tmp/demo/a.txt",
    "",
    "  Stuck?  Type  help dev  for the full technical register, or  test  to",
    "  confirm the shell is healthy.",
]


def _help_literal(name: str, lines: list[str]) -> str:
    return name + " = " + json.dumps(lines, ensure_ascii=False, separators=(",", ":"))


def help_block() -> str:
    """The dual-register help: one place, injected over the pristine anchor.

    The whole block (dispatch + prose) sits inside DUAL-HELP markers, so a
    rebuild can restore the original `HELP_ANCHOR` and re-inject -- idempotent
    by construction, like every other injected block in this pipeline.
    """
    body = "\n".join(
        "    var " + _help_literal(n, v) + ";"
        for n, v in (("HELP_DEV", HELP_DEV), ("HELP_BEGINNER", HELP_BEGINNER))
    )
    return (
        "/* DUAL-HELP:START */\n"
        + HELP_DISPATCH + "\n"
        + body + "\n"
        + "    function helpEmitLines(lines) { for (var i = 0; i < lines.length; i++) out(lines[i]); }\n"
        + "    function helpText(reg) {\n"
        + "      reg = (reg || \"beginner\").toLowerCase();\n"
        + "      if (reg === \"dev\" || reg === \"developer\" || reg === \"expert\" || reg === \"ai\" || reg === \"full\") { helpEmitLines(HELP_DEV); return 0; }\n"
        + "      if (reg === \"beginner\" || reg === \"novice\" || reg === \"novices\" || reg === \"start\" || reg === \"simple\" || reg === \"plain\") { helpEmitLines(HELP_BEGINNER); return 0; }\n"
        + "      if (reg === \"help\") { out(\"help                 beginner register (default)\"); out(\"help dev             developer register (AI + experts)\"); out(\"help beginner        beginner register\"); out(\"help CMD             one-line help for a command\"); return 0; }\n"
        + "      return -1;\n"
        + "    }\n"
        + "/* DUAL-HELP:END */"
    )


# The original help dispatch (verbatim from TermKit 2.0 Part B). `patch_shell`
# replaces it with HELP_DISPATCH, which routes to the two registers.
HELP_ANCHOR = '''    var baseHelp = builtins["help"];
    builtins["help"] = function (args) {
      if (args.length && HELP[args[0]]) { out(HELP[args[0]]); return 0; }
      if (args.length && builtins[args[0]]) { out(args[0] + ": " + (HELP[args[0]] || "shell builtin")); return 0; }
      return baseHelp(args);
    };'''

# `help` (no arg) -> the beginner register + a pointer to the other register;
# `help <register>` -> that register; `help <cmd>` -> the one-line signature;
# anything else -> an honest "no such command or register" with the menu.
HELP_DISPATCH = '''    var baseHelp = builtins["help"];
    builtins["help"] = function (args) {
      if (args.length && HELP[args[0]]) { out(HELP[args[0]]); return 0; }
      if (args.length && builtins[args[0]]) { out(args[0] + ": " + (HELP[args[0]] || "shell builtin")); return 0; }
      if (!args.length) {
        /* no argument: the beginner register, then the register menu */
        helpEmitLines(HELP_BEGINNER);
        out("");
        out("  help dev         developer register (AI + experts)");
        out("  help CMD         one-line help for a command");
        out("  invariant battery: the 'test' chip above runs it");
        return 0;
      }
      var hr = helpText(args[0]);
      if (hr !== -1) return hr;
      out("help: no such command or register: " + args[0]);
      out("  help              beginner register (default)");
      out("  help dev          developer register (AI + experts)");
      out("  help beginner     beginner register");
      return 1;
    };'''

_DH_RE = re.compile(re.escape(DH_START) + r".*?" + re.escape(DH_END), re.S)


def restore_dual_help(shell: str) -> str:
    """Undo a previous injection by putting the pristine anchor back."""
    return _DH_RE.sub(lambda m: HELP_ANCHOR, shell, count=1)


def patch_shell(shell: str, core: str) -> str:
    shell = strip(shell, SS_START, SS_END)
    shell = strip(shell, ST_START, ST_END)
    shell = restore_dual_help(shell)
    shell = inject(shell, SS_START, SS_END, wrap_script(core))
    if BUILTINS_ANCHOR not in shell:
        raise SystemExit("TermKit anchor missing: cannot add the `savf` builtin")
    shell = shell.replace(BUILTINS_ANCHOR,
                          BUILTINS_ANCHOR + "\n" + TERMINAL_BUILTIN, 1)
    if HELP_ANCHOR not in shell:
        raise SystemExit("TermKit help anchor missing: cannot add the dual register")
    shell = shell.replace(HELP_ANCHOR, help_block(), 1)
    return shell


def patch_page(page: str, facade: str) -> str:
    """Give the standalone page the same unified facade as every other host.

    savf.html ships the raw modules (SavfScan/SavfCore/SavfAudit) but not the
    `SAVF.auditSource` entry point, so it would be the one surface whose API
    differs.  Injecting the facade makes the page, the studio, the forge and the
    terminal answer through one identical call.
    """
    page = strip(page, PF_START, PF_END)
    return inject(page, PF_START, PF_END, wrap_script(facade))


def build_core() -> None:
    subprocess.run([sys.executable, str(BUILD / "make_core.py")], check=True)


def syntax_gate(*paths: pathlib.Path) -> None:
    """Refuse to ship JavaScript that does not parse.

    The payloads are plain JS (the carrier escaping happens at wrap time), so
    `node --check` is an exact test.  A build that cannot parse is a build that
    would white-screen the app; it must fail here, not on the user's phone.
    """
    for p in paths:
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"syntax gate FAILED: {p.name}\n{r.stderr.strip()[:800]}")
        print(f"  syntax   {p.name:<20} ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify sync; write nothing")
    args = ap.parse_args()

    build_core()
    core = CORE.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    facade = FACADE.read_text(encoding="utf-8")
    syntax_gate(CORE, HOST)

    shell0 = FORGE.read_text(encoding="utf-8")
    studio0 = get_carrier(shell0)

    studio1 = patch_studio(studio0, core, host)
    shell1 = set_carrier(shell0, studio1)
    shell2 = patch_shell(shell1, core)
    page1 = patch_page(SAVF_HTML.read_text(encoding="utf-8"), facade)

    if args.check:
        ok = True
        # `darkith forge.html` is a GENERATED output (.gitignore). In a clean checkout it is
        # absent; an absent generated file is a skip, not drift. The canonical inputs
        # (darkith home forge.html, darkith code studio.html, savf.html) are always checked.
        for name, path, want in (
            ("darkith forge.html", FORGE_OUT, shell2),
            ("darkith code studio.html", STUDIO, studio1),
            ("savf.html", SAVF_HTML, page1),
        ):
            if not path.exists():
                print(f"skip: {name} absent (generated output)")
                continue
            if path.read_text(encoding="utf-8") != want:
                print(f"OUT OF SYNC: {name}", file=sys.stderr)
                ok = False
        print("check: " + ("in sync" if ok else "drift detected"))
        return 0 if ok else 1

    FORGE.write_text(shell2, encoding="utf-8")
    FORGE_OUT.write_text(shell2, encoding="utf-8")
    STUDIO.write_text(studio1, encoding="utf-8")
    SAVF_HTML.write_text(page1, encoding="utf-8")

    for label, text in (("studio", studio1), ("forge", shell2), ("page", page1), ("core", core)):
        print(f"  {label:<8} {len(text):>8} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
