#!/usr/bin/env node
/*
 * Tests for the `savf axis` CLI surface.
 *
 * The axis is the one function the whole formulary rests on, and the CLI is how
 * a shell user reaches it. Two things broke here in practice:
 *
 *   1. The pole arguments were undocumented, so a 3D axis looked impossible to
 *      pass even though the core supports it.
 *   2. `nargs="+"` silently stopped consuming at a negative number, so
 *      `--p1 -1.5 8` failed with "unrecognized arguments". Negative coordinates
 *      are the common case in a coordinate frame.
 *
 * Both are covered below, along with the arithmetic itself and its error paths.
 *
 * Run: node tools/test_savf_axis_cli.js
 */
"use strict";

const { execFileSync } = require("child_process");
const path = require("path");

const CLI = path.resolve(__dirname, "..", "savf.py");

let pass = 0;
let fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (detail ? "  -> " + detail : "")); }
}

function axis(p0, p1, s, tau) {
  const args = [CLI, "axis", "--p0", p0, "--p1", p1, "--s", String(s), "--tau", String(tau)];
  try {
    const out = execFileSync("python3", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    return { code: 0, json: JSON.parse(out) };
  } catch (e) {
    return { code: e.status === undefined ? -1 : e.status, err: (e.stderr || "") + (e.stdout || "") };
  }
}

/* --- the arithmetic ----------------------------------------------------- */
const half = axis("0", "10", 0.5, 1);
ok("1D midpoint is 5", half.json && half.json.point[0] === 5, JSON.stringify(half.json));
ok("start is the tau pole", half.json && half.json.start[0] === 0);
ok("end is the far pole", half.json && half.json.end[0] === 10);

const rev = axis("0", "10", 0.5, -1);
ok("tau=-1 swaps the poles", rev.json && rev.json.start[0] === 10 && rev.json.end[0] === 0);

const q = axis("0", "10", 0.25, 1);
ok("s=0.25 is a quarter along", q.json && q.json.point[0] === 2.5, JSON.stringify(q.json));

/* --- higher dimensions, both documented forms --------------------------- */
const comma = axis("0,0,0", "2,4,6", 0.5, 1);
ok("a 3D axis is accepted in comma form",
   comma.json && JSON.stringify(comma.json.point) === JSON.stringify([1, 2, 3]),
   JSON.stringify(comma.json));

const spaced = axis("0 0 0", "2 4 6", 0.5, 1);
ok("a 3D axis is accepted in space form",
   spaced.json && JSON.stringify(spaced.json.point) === JSON.stringify([1, 2, 3]),
   JSON.stringify(spaced.json));

const d2 = axis("0,0", "100,0", 0.5, 1);
ok("a 2D axis is accepted",
   d2.json && JSON.stringify(d2.json.point) === JSON.stringify([50, 0]), JSON.stringify(d2.json));

/* --- negative coordinates must not be eaten by the option parser -------- */
const neg = axis("-5,-5,-5", "-1,3,7", 0.5, 1);
ok("negative coordinates parse",
   neg.json && JSON.stringify(neg.json.point) === JSON.stringify([-3, -1, 1]),
   neg.json ? JSON.stringify(neg.json) : (neg.err || "").trim().slice(-120));

const negSpaced = axis("-5 -5 -5", "-1 3 7", 0.5, 1);
ok("negative coordinates parse in space form",
   negSpaced.json && JSON.stringify(negSpaced.json.point) === JSON.stringify([-3, -1, 1]),
   negSpaced.json ? JSON.stringify(negSpaced.json) : (negSpaced.err || "").trim().slice(-120));

/* --- the reflection law, on a case where a wrong law would differ ------- */
const r = axis("0,0", "100,0", 0.3, 1);
const rBack = axis("0,0", "100,0", 0.7, -1);
ok("at(s,+1) equals at(1-s,-1)",
   r.json && rBack.json &&
   JSON.stringify(r.json.point) === JSON.stringify(rBack.json.point),
   `${JSON.stringify(r.json && r.json.point)} vs ${JSON.stringify(rBack.json && rBack.json.point)}`);

/* --- error paths must be clean exits, never tracebacks ------------------ */
const badNum = axis("a,b", "1,2", 0.5, 1);
ok("a non-numeric pole is refused", badNum.code === 1 && !/Traceback/.test(badNum.err || ""),
   (badNum.err || "").trim().slice(0, 100));

const dimMismatch = axis("0,0", "1,1,1", 0.5, 1);
ok("mismatched dimensions are refused", dimMismatch.code === 1 && !/Traceback/.test(dimMismatch.err || ""),
   (dimMismatch.err || "").trim().slice(0, 100));

const samePole = axis("5,5", "5,5", 0.5, 1);
ok("identical poles are refused", samePole.code === 1 && !/Traceback/.test(samePole.err || ""),
   (samePole.err || "").trim().slice(0, 100));

const badS = axis("0", "10", 1.5, 1);
ok("s outside [0,1] is refused", badS.code === 1, "exit " + badS.code);

const badTau = axis("0", "10", 0.5, 2);
ok("tau other than +-1 is refused", badTau.code === 2, "exit " + badTau.code);

/* --- an unsupported form must fail loudly, never compute silently ------- */
/* `--p0 1 2 3` (three bare tokens) is not a supported form. It must exit
   non-zero rather than pick up "1" and quietly ignore "2 3" -- a silent
   wrong answer is the worst possible outcome for an audit tool. */
let bareTokens;
try {
  execFileSync("python3", [CLI, "axis", "--p0", "1", "2", "3", "--p1", "4", "5", "6",
                           "--s", "0.5", "--tau", "1"],
               { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  bareTokens = { code: 0 };
} catch (e) {
  bareTokens = { code: e.status, out: (e.stdout || "") };
}
ok("three bare pole tokens are refused, not silently truncated",
   bareTokens.code !== 0, "exit " + bareTokens.code + " out=" + JSON.stringify(bareTokens.out || ""));

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
