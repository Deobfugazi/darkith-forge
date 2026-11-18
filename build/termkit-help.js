/* =====================================================================
   TermKit help — the dual-register manual and its invariant fixtures.

   ONE source of truth. Three consumers read this file and nothing else:
     1. `help beginner`  the plain-language register (novices)
     2. `help dev`       the machine register (an AI or an expert)
     3. tools/termkit_help_audit.mjs — executes every fixture below against
        the REAL shell core and asserts the documented output. The manual
        therefore cannot drift from the engine: if a sample lies, the gate
        goes red.

   Every `expect` here was produced by the engine, not by hand.
   ===================================================================== */
(function (global) {
  "use strict";

  /* ---- the invariant set -------------------------------------------------
     id      stable handle (the debugger prints it; the registers cite it)
     cmd     the exact command a user types
     expect  stdout with the trailing newline removed ("" = no stdout)
     status  the exit code the shell reports ($?)
     group   sectioning key
     why     the one-line reason this behaves the way it does (fracture)  */
  var FIXTURES = [
    { id: "pwd",            cmd: "pwd",                                       expect: "/",            status: 0, group: "basics", why: "the VFS starts at /; the phone's real fs is reached only through the bridge" },
    { id: "echo",           cmd: "echo hello",                                expect: "hello",        status: 0, group: "basics", why: "echo is a builtin, so it costs no process and never lies about IFS" },
    { id: "vars",           cmd: "echo $HOME",                                expect: "/sdcard",      status: 0, group: "basics", why: "$HOME is seeded to /sdcard so scripts are portable to Termux" },
    { id: "arith",          cmd: "echo $((6*7))",                             expect: "42",           status: 0, group: "basics", why: "arithmetic is integer-exact and precedence-correct; no eval, no float drift" },
    { id: "arith-pow",      cmd: "echo $((2**10))",                           expect: "1024",         status: 0, group: "basics", why: "** is integer power, matching bash; ^ would be xor and is not offered" },
    { id: "default",        cmd: "echo ${UNSET:-fallback}",                   expect: "fallback",     status: 0, group: "basics", why: ":- gives a script a default without a separate test" },
    { id: "brace",          cmd: "echo {1..3}",                               expect: "1 2 3",        status: 0, group: "basics", why: "brace expansion happens before the command runs, as in bash" },
    { id: "pipe-tr",        cmd: "echo hello | tr a-z A-Z",                   expect: "HELLO",        status: 0, group: "pipes",  why: "pipelines are byte-faithful: the producer's trailing newline is preserved" },
    { id: "pipe-wc",        cmd: "printf 'a\\nb\\n' | wc -l",                 expect: "2",            status: 0, group: "pipes",  why: "printf writes exactly the bytes given, so wc counts lines, not guesses" },
    { id: "pipe-sort",      cmd: "printf 'b\\na\\nc\\n' | sort",              expect: "a\nb\nc",      status: 0, group: "pipes",  why: "sort is stable and locale-free: the same input sorts the same everywhere" },
    { id: "pipe-cut",       cmd: "printf 'x:y:z\\n' | cut -d: -f2",           expect: "y",            status: 0, group: "pipes",  why: "-d/-f mirrors cut; field indexing is 1-based, as in coreutils" },
    { id: "pipe-sed",       cmd: "echo abc | sed 's/b/X/'",                   expect: "aXc",          status: 0, group: "pipes",  why: "sed implements s/// with /g and /i only — a small, exact subset" },
    { id: "pipe-head",      cmd: "printf 'a\\nb\\nc\\n' | head -2",           expect: "a\nb",         status: 0, group: "pipes",  why: "head -N keeps N lines; it does not close the pipe early, so no SIGPIPE" },
    { id: "pipe-tail",      cmd: "printf 'a\\nb\\nc\\n' | tail -1",           expect: "c",            status: 0, group: "pipes",  why: "tail -N keeps the last N lines and preserves the final newline" },
    { id: "seq",            cmd: "seq 1 3",                                   expect: "1\n2\n3",      status: 0, group: "text",   why: "seq takes start/step/end; one token or three, never a guess" },
    { id: "base64",         cmd: "echo hello | base64",                       expect: "aGVsbG8K",     status: 0, group: "text",   why: "base64 encodes the exact byte stream (the trailing newline is data)" },
    { id: "base64-d",       cmd: "echo aGk= | base64 -d",                     expect: "hi",           status: 0, group: "text",   why: "-d is the inverse; round-trip is a self-test, not a claim" },
    { id: "rev",            cmd: "echo abc | rev",                            expect: "cba",          status: 0, group: "text",   why: "rev reverses per line, keeping the line count identical" },
    { id: "factor",         cmd: "factor 12",                                 expect: "12: 2 2 3",    status: 0, group: "text",   why: "factor prints the prime factorisation in coreutils' exact format" },
    { id: "expr",           cmd: "expr 3 + 4",                                expect: "7",            status: 0, group: "text",   why: "expr takes three tokens: LHS OP RHS — the form that cannot be ambiguous" },
    { id: "for",            cmd: "for i in 1 2 3; do echo $i; done",          expect: "1\n2\n3",      status: 0, group: "control", why: "for/while/until/case/if all parse as real control flow, not string tricks" },
    { id: "while",          cmd: "i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done", expect: "0\n1\n2", status: 0, group: "control", why: "the loop condition is re-evaluated each pass, so $i really advances" },
    { id: "if",             cmd: "if [ 1 -eq 1 ]; then echo y; else echo n; fi", expect: "y",         status: 0, group: "control", why: "[ is a builtin alias of test, so conditions cost no process" },
    { id: "func",           cmd: "f(){ echo $1; }; f ok",                     expect: "ok",           status: 0, group: "control", why: "functions capture $1..$n; this is the same f(){ } grammar bash uses" },
    { id: "cmdsub",         cmd: "echo $(echo inner)",                        expect: "inner",        status: 0, group: "control", why: "$( ) runs a full sub-shell and splices its stdout; backticks work too" },
    { id: "mkdir-ls",       cmd: "mkdir -p /tmp/d && touch /tmp/d/a.txt && ls /tmp/d", expect: "a.txt", status: 0, group: "files", why: "&& short-circuits on failure, so a failed mkdir never reports success" },
    { id: "redirect",       cmd: "echo x > /tmp/f && cat /tmp/f",             expect: "x",            status: 0, group: "files", why: "> truncates, >> appends, < feeds stdin — the three the shell promises" },
    { id: "test-d",         cmd: "test -d /tmp && echo yes",                  expect: "yes",          status: 0, group: "files", why: "test reports through the exit code, so && reads it as a boolean" },
    { id: "true-status",    cmd: "true; echo $?",                             expect: "0",            status: 0, group: "errors", why: "$? always holds the last status; true and false set 0 and 1" },
    { id: "false-status",   cmd: "false; echo $?",                            expect: "1",            status: 0, group: "errors", why: "a nonzero status is a value, not a crash — scripts branch on it" },
    { id: "err-cat",        cmd: "cat /nope",                                 expect: "",             status: 1, group: "errors", why: "a missing file is status 1 with a diagnostic on stderr, never on stdout" },
    { id: "err-nocmd",      cmd: "nosuchcmd",                                 expect: "",             status: 127,group: "errors", why: "command not found is 127 (bash's code), so scripts can tell it apart" },
    { id: "err-ls",         cmd: "ls /nope",                                  expect: "",             status: 2, group: "errors", why: "ls uses status 2 for an operand error, matching coreutils" },
    { id: "awk-absent",     cmd: "awk '{print}'",                             expect: "",             status: 127,group: "errors", why: "awk is deliberately NOT implemented: absent (127) beats approximate" }
  ];

  /* ---- register 1: beginner --------------------------------------------- */
  var BEGINNER = [
    { title: "WHAT THIS IS", lines: [
      "A shell that lives inside the app. It runs offline, on this phone.",
      "No Termux, no root, no network. It cannot damage your files: it",
      "reads and writes a private in-memory filesystem until you ask it",
      "(through a command) to touch the real SD card."
    ]},
    { title: "THE SIX THINGS TO KNOW", lines: [
      "1. Type a command, press Enter. That is the whole interface.",
      "2. Words are split by spaces. $VAR is replaced by its value.",
      "3. | sends one command's output into the next:  a | b",
      "4. > writes to a file, >> appends, < reads from a file.",
      "5. && runs the next command only if this one worked.",
      "6. 'help CMD' explains one command; 'help' lists them all."
    ]},
    { title: "TRY THESE (the line under $ is what you type; the rest is what you get)", fixtureIds: [
      "echo", "arith", "pipe-tr", "vars", "seq", "test-d", "for"
    ]},
    { title: "FILES AND FOLDERS", fixtureIds: [ "pwd", "mkdir-ls", "redirect" ] },
    { title: "WHEN IT SAYS NO", fixtureIds: [ "err-cat", "err-nocmd" ] },
    { title: "WHERE TO GO NEXT", lines: [
      "help dev        the full model: grammar, every builtin, the fixtures",
      "help CMD        one command, in detail",
      "type CMD        is it a builtin or a program?",
      "selftest        run the shell's own checks and see them pass"
    ]}
  ];

  /* ---- register 2: dev --------------------------------------------------- */
  var DEV_INTRO = [
    "TermKit 2.0 — a deterministic, offline userspace shell.",
    "",
    "MODEL",
    "  * A virtual filesystem (VFS) rooted at '/'. HOME is /sdcard.",
    "  * A parser (Part A) produces an AST; an interpreter (Part B) walks it.",
    "  * Output is a byte stream: each line records whether it was newline-",
    "    terminated, so a pipeline reconstructs bytes instead of guessing.",
    "  * Determinism: no wall-clock dependence (date reads the fs clock),",
    "    no network, no randomness except $RANDOM.",
    "",
    "GRAMMAR (subset of POSIX shell)",
    "  cmd | cmd      pipeline            cmd > f / >> f   redirect out / append",
    "  cmd < f        redirect in         a && b / a || b  short-circuit",
    "  a ; b          sequence            a & b            background job",
    "  $VAR ${V:-x}   expansion           $(cmd) `cmd`     command substitution",
    "  $((e))         integer arithmetic  ~ * ? [a-z] {1..9}  tilde/glob/brace",
    "  if/elif/else/fi  for/while/until/case/esac  f(){ }  functions",
    "",
    "INVARIANTS (each is a fixture the audit executes)",
    "  I1  pipelines are byte-faithful (trailing newline preserved)",
    "  I2  arithmetic is integer-exact and precedence-correct; ** is power",
    "  I3  every failure has a named exit code (0 ok, 1 general, 2 usage, 127 not-found)",
    "  I4  diagnostics go to stderr; stdout carries only results",
    "  I5  a documented sample's output equals the engine's output (this file)",
    "",
    "HOW TO DEBUG (the invariant debugger)",
    "  Every row below is executed against the real core by:",
    "      node tools/termkit_help_audit.mjs",
    "  The audit prints one line per fixture: id, cmd, expected, actual, PASS/FAIL.",
    "  A FAIL means the manual and the engine disagree — fix one, not neither.",
    "",
    "BUILTINS"
  ];

  var DEV_FIXTURE_HEADER = [
    "  id              cmd                                        => expected            ($?)"
  ];

  /* ---- comparison: TermKit vs Termux / Linux ----------------------------- */
  var COMPARE = [
    { what: "pipes  |",            tk: "byte-faithful",       tx: "same",            note: "trailing newline preserved via outNL" },
    { what: "arithmetic  $(( ))",  tk: "int + ** power",      tx: "same",            note: "no float drift; ^ is not xor here" },
    { what: "glob  * ? [a-z]",     tk: "yes (after cd)",      tx: "same",            note: "expanded against the VFS, sorted" },
    { what: "cd / export",         tk: "in-session VFS",      tx: "real filesystem", note: "no device writes until a bridge command asks" },
    { what: "which CMD",           tk: "reports 'shell builtin'", tx: "path lookup",  note: "66 builtins resolve without PATH" },
    { what: "find",                tk: "-name -type -maxdepth", tx: "full find",     note: "the useful subset, exact" },
    { what: "awk",                 tk: "NOT implemented",     tx: "real awk",        note: "absent (127) beats approximate; use cut/grep/sed" },
    { what: "sed",                 tk: "s/// with g and i",   tx: "full sed",        note: "small, exact subset" },
    { what: "sleep N",             tk: "no-op (status 0)",    tx: "real sleep",      note: "a tab must never freeze on sleep" },
    { what: "df",                  tk: "synthetic 1 MiB VFS", tx: "real mounts",     note: "honest about what it is" },
    { what: "heredoc  <<EOF",      tk: "not offered",         tx: "yes",             note: "use printf ... | tee instead" },
    { what: "network",             tk: "none (offline)",      tx: "yes",             note: "by design; nothing leaves the device" },
    { what: "job control  &",      tk: "jobs list",           tx: "real pids",       note: "no signals to real processes" },
    { what: "sha256sum / md5sum",  tk: "yes",                 tx: "same",            note: "hashes match coreutils for the same bytes" }
  ];

  /* ---- fracture closures: why the logic is implemented this way ---------- */
  var CLOSURE = [
    { id: "C1", claim: "A VFS, not the device filesystem",
      because: "closes the fracture 'commands that lie about a filesystem the app cannot safely write'. It keeps every run deterministic and offline; the SD card is reached only through an explicit bridge command." },
    { id: "C2", claim: "Byte-faithful pipelines (outNL)",
      because: "closes the fracture where printf/tr/tail disagree across a pipe because a trailing newline is dropped or invented. The producer records newline-termination per line; the consumer reconstructs bytes." },
    { id: "C3", claim: "awk is absent, not approximated",
      because: "closes the fracture 'a plausible-but-wrong result that no test can falsify'. A 127 is a named, testable outcome; an almost-awk is not." },
    { id: "C4", claim: "sleep is a no-op",
      because: "closes the fracture 'a browser tab frozen by a command that blocks the event loop'. Determinism over simulation." },
    { id: "C5", claim: "Named exit codes (0/1/2/127)",
      because: "closes the fracture 'unfalsifiable success'. Every failure path returns a code a script can branch on, and the audit asserts them." },
    { id: "C6", claim: "Two help registers",
      because: "closes the fracture 'one manual that serves neither novice nor machine'. Beginner optimises for the first successful command; dev exposes the model, the grammar and the fixtures." },
    { id: "C7", claim: "Fixtures are executed, not described",
      because: "closes the fracture 'documentation drift'. The output shown to you is the engine's output, re-derived by tools/termkit_help_audit.mjs on every CI run." }
  ];

  function byId(id) {
    for (var i = 0; i < FIXTURES.length; i++) if (FIXTURES[i].id === id) return FIXTURES[i];
    return null;
  }

  function expectLines(f) {
    if (f.expect === "") return ["(no output)"];
    return f.expect.split("\n");
  }

  /* Render a register to an array of lines. The in-page `help` builtin
     prints each line; the audit re-derives the fixture lines and compares. */
  function render(register) {
    var out = [];
    function push(a) { for (var i = 0; i < a.length; i++) out.push(a[i]); }

    if (register === "beginner") {
      push(["Darkith Forge Terminal — beginner guide", ""]);
      for (var s = 0; s < BEGINNER.length; s++) {
        var sec = BEGINNER[s];
        push([sec.title]);
        if (sec.lines) push(sec.lines);
        if (sec.fixtureIds) {
          for (var k = 0; k < sec.fixtureIds.length; k++) {
            var f = byId(sec.fixtureIds[k]);
            if (!f) continue;
            out.push("  $ " + f.cmd);
            var el = expectLines(f);
            for (var j = 0; j < el.length; j++) out.push("  " + el[j]);
          }
        }
        out.push("");
      }
      return out;
    }

    if (register === "dev") {
      push(["Darkith Forge Terminal — developer / AI register", ""]);
      push(DEV_INTRO);
      out.push("  " + Object.keys(BUILTINS_NAMES).sort().join(" "));
      out.push("");
      push(["FIXTURES (the invariant debugger executes each of these)", ""]);
      push(DEV_FIXTURE_HEADER);
      for (var i = 0; i < FIXTURES.length; i++) {
        var fx = FIXTURES[i];
        var exp = fx.expect === "" ? "(none)" : fx.expect.replace(/\n/g, "\\n");
        var row = "  " + pad(fx.id, 15) + " " + pad("$ " + fx.cmd, 42) + " => " + pad(exp, 19) + " (" + fx.status + ")";
        out.push(row);
        out.push("      why: " + fx.why);
      }
      out.push("");
      push(["COMPARED WITH TERMUX / LINUX", ""]);
      out.push("  " + pad("feature", 20) + " | " + pad("TermKit", 22) + " | " + pad("Termux/Linux", 15) + " | note");
      for (var c = 0; c < COMPARE.length; c++) {
        var r = COMPARE[c];
        out.push("  " + pad(r.what, 20) + " | " + pad(r.tk, 22) + " | " + pad(r.tx, 15) + " | " + r.note);
      }
      out.push("");
      push(["WHY THE LOGIC IS IMPLEMENTED THIS WAY (fracture closures)", ""]);
      for (var z = 0; z < CLOSURE.length; z++) {
        out.push("  " + CLOSURE[z].id + "  " + CLOSURE[z].claim);
        out.push("      " + CLOSURE[z].because);
      }
      return out;
    }

    return null;
  }

  function pad(s, n) {
    s = String(s);
    while (s.length < n) s += " ";
    return s;
  }

  /* The builtin names, injected by the build so the register can list them
     without importing the whole shell. Kept here so the file is standalone. */
  var BUILTINS_NAMES = {
    ".": 1, ":": 1, "[": 1, "aegis": 1, "alias": 1, "base64": 1, "basename": 1, "bc": 1,
    "cat": 1, "cd": 1, "cp": 1, "cut": 1, "date": 1, "df": 1, "dirname": 1, "du": 1,
    "echo": 1, "env": 1, "exit": 1, "export": 1, "expr": 1, "factor": 1, "false": 1,
    "find": 1, "forge": 1, "grep": 1, "head": 1, "help": 1, "history": 1, "ln": 1,
    "ls": 1, "mapfile": 1, "md5sum": 1, "mkdir": 1, "mv": 1, "nl": 1, "printf": 1,
    "pwd": 1, "read": 1, "readlink": 1, "rev": 1, "rm": 1, "rmdir": 1, "savf": 1,
    "sed": 1, "seq": 1, "set": 1, "sha256sum": 1, "sleep": 1, "sort": 1, "source": 1,
    "stat": 1, "tac": 1, "tail": 1, "tee": 1, "test": 1, "touch": 1, "tr": 1,
    "true": 1, "type": 1, "unalias": 1, "uniq": 1, "unset": 1, "wc": 1, "which": 1,
    "xargs": 1
  };

  global.__TermKitHelp = {
    version: "1.0.0",
    fixtures: FIXTURES,
    beginner: BEGINNER,
    dev: DEV_INTRO,
    compare: COMPARE,
    closure: CLOSURE,
    builtins: Object.keys(BUILTINS_NAMES).sort(),
    render: render,
    fixtureById: byId
  };
})(typeof window !== "undefined" ? window : globalThis);
