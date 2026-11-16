/* ============================================================================
   SAVF host integration  --  binds a host UI to the one truth function.

   The studio (code manager) ships its own claims-math engine under window.SAVF.
   That engine is right for the claims language and wrong for code: it answers
   "does this line state a true claim?", not "does this source contain stubs,
   phantom imports, vacuous tests or swallowed exceptions?".  Code auditing must
   therefore run on the real SAVF core, or the in-app verdict is a weaker,
   different verdict than `savf.py` gives for the same bytes.

   This file is appended to the studio (and reused by the forge and terminal
   hosts).  It does three things, and nothing else:

     1. routes Python audits through the real core (SavfTruth.auditSource);
     2. maps real findings onto the studio's row/gate/witness shape so the
        existing panel renders them, swapping the gate labels for code mode so
        the chips do not mislabel phi1 ("stubs/markers") as "syntax";
     3. leaves the claims engine untouched for every other language.

   It is additive and fail-safe: if the core or the studio object is absent it
   returns immediately and the host keeps working exactly as before.
   ============================================================================ */
(function (global) {
  "use strict";

  var T = global.SavfTruth || global.SAVF;
  if (!T || typeof T.auditSource !== "function") return;      /* no core: leave host alone */

  var S = global.SAVF;
  if (!S || typeof S.runAudit !== "function") return;         /* no host engine: nothing to bind */

  var REAL_LABELS = {};
  Object.keys(T.gateInfo).forEach(function (k) { REAL_LABELS[k] = T.gateInfo[k]; });
  REAL_LABELS.phi11 = "code scan (SAVF core)";
  var REAL_GATES = T.gates.slice();                            /* phi0..phi10 */
  var REAL_HARD = {};
  T.hardGates.forEach(function (g) { REAL_HARD[g] = 1; });
  /* Capture the studio's own scheme so claims mode can be restored exactly. */
  var STUDIO_LABELS = global.GATE_LABELS || null;
  var STUDIO_GATES = S.gates ? S.gates.slice() : null;
  var STUDIO_HARD = S.hardGates ? Object.assign({}, S.hardGates) : null;

  var RATIONALE = {
    STUB: "Replace the placeholder body with the real implementation, or delete the function.",
    MARKER: "Resolve the TODO/FIXME/XXX marker, or remove it if the work is done.",
    PHANTOM_IMPORT: "Import a module that exists: stdlib, an installed package, or a local file.",
    PHANTOM_ATTR: "The attribute is not a known member of that stdlib module; check the name.",
    VACUOUS_TEST: "Make the test assert something that can fail; a bare assert True proves nothing.",
    TAUTOLOGY: "The comparison is true by construction and cannot detect a defect.",
    SWALLOWED: "Do not swallow the exception: log it, re-raise it, or handle it meaningfully.",
    FAKE_DATA: "Mock-style data reached production code; inject it in tests instead."
  };

  function applyRealScheme() {
    if (STUDIO_LABELS) global.GATE_LABELS = REAL_LABELS;
    S.gates = REAL_GATES.concat(["phi11"]);
    S.hardGates = Object.assign({ phi11: 1 }, REAL_HARD);
  }
  function restoreStudioScheme() {
    if (STUDIO_LABELS) global.GATE_LABELS = STUDIO_LABELS;
    if (STUDIO_GATES) S.gates = STUDIO_GATES;
    if (STUDIO_HARD) S.hardGates = STUDIO_HARD;
  }

  function lineAt(lines, n) {
    return (n >= 1 && n <= lines.length) ? lines[n - 1].trim() : "";
  }

  /* Run the real core over Python source and shape the result for the studio. */
  function pythonAudit(text) {
    var res = T.auditSource("input.py", text == null ? "" : String(text));
    var lines = String(text == null ? "" : text).split(/\r\n|\r|\n/);

    var results = res.findings.map(function (f) {
      var ln = f.line || 1;
      return {
        line: lineAt(lines, ln),
        lineNo: ln,
        kind: "SCAN_CODE",
        status: "failed",
        badge: f.sev === "high" ? "FAIL" : "INVALID",
        note: f.rule + " \u00b7 " + f.msg,
        interp: "phi" + f.phi + " \u00b7 " + f.rule + " \u00b7 " + f.sev,
        interpNotes: [],
        fix: null,
        rationale: RATIONALE[f.rule] || "",
        claim: { line: lineAt(lines, ln), idx: ln - 1, kind: "SCAN_CODE" }
      };
    });

    if (!results.length) {
      results.push({
        line: "Structural scan complete \u2014 no findings",
        lineNo: 1,
        kind: "SCAN_CODE",
        status: "verified",
        badge: "PASS",
        note: "no phi1/phi2/phi3/phi6 findings",
        interp: "savf-core " + res.version,
        interpNotes: [],
        fix: null,
        rationale: "",
        claim: { line: "Structural scan complete \u2014 no findings", idx: 0, kind: "SCAN_CODE" }
      });
    }

    var gates = {};
    S.gates.forEach(function (g) { gates[g] = "n/a"; });
    REAL_GATES.forEach(function (g) { gates[g] = res.states[g]; });
    if ("phi11" in gates) gates.phi11 = res.findings.length ? "fail" : "pass";

    var verdict = res.verdict;                       /* identical to `savf.py verdict` */
    var witness = null;
    if (verdict === "LIED" || verdict === "BLOCKED") {
      var pick = null;
      for (var i = 0; i < res.findings.length; i++) {
        var f = res.findings[i];
        var isHigh = f.sev === "high";
        if (verdict === "LIED" && !isHigh) continue;
        pick = f; break;
      }
      if (!pick) pick = res.findings[0];
      if (pick) {
        witness = {
          gate: "phi" + pick.phi,
          lineNo: pick.line,
          claimLine: lineAt(lines, pick.line),
          note: pick.msg,
          hardness: REAL_HARD["phi" + pick.phi] ? "HARD" : "SOFT"
        };
      }
    }

    var counts = { pass: 0, fail: 0, invalid: 0, unparseable: 0 };
    results.forEach(function (r) {
      if (r.badge === "PASS") counts.pass++;
      else if (r.badge === "FAIL") counts.fail++;
      else if (r.badge === "UNPARSEABLE") counts.unparseable++;
      else counts.invalid++;
    });

    return {
      version: S.version || "3.0.0",
      engine: "savf-core/" + res.version,
      verdict: verdict,
      witness: witness,
      gates: gates,
      results: results,
      counts: counts,
      payload: (typeof S.payloadSummary === "function") ? S.payloadSummary() : null
    };
  }

  /* Only Python has a real SAVF core.  Every other language keeps the studio's
     structural scanner, so this never degrades a language it cannot improve. */
  function isCoreLang() {
    return !!(global.STATE && global.STATE.auditLang === "python");
  }

  var prevRun = S.runAudit;
  S.runAudit = function (text, payloadOverride, runCodeScan) {
    if (isCoreLang()) {
      applyRealScheme();
      try {
        return pythonAudit(text);
      } catch (e) {
        restoreStudioScheme();
        throw e;
      }
    }
    restoreStudioScheme();
    return prevRun.apply(this, arguments);
  };

  /* Python needs no grammar download; present it as always ready so the studio's
     "Load Grammar" gate never blocks a real audit. */
  var prevHas = S.hasParser, prevLang = S.parserLang;
  S.hasParser = function () { return isCoreLang() ? true : prevHas.apply(this, arguments); };
  S.parserLang = function () { return isCoreLang() ? "python" : prevLang.apply(this, arguments); };

  /* Surface the binding so a host (shell/terminal) can prove the core is live. */
  S.coreEngine = function () { return T; };
  S.auditSource = T.auditSource;
  S.auditFiles = T.auditFiles;
})(typeof window !== "undefined" ? window : globalThis);
