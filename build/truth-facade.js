/* ============================================================================
   SAVF truth facade  --  the one function every surface calls.

   SAVF is a truth function, not an application.  This facade gives every host
   -- the standalone page, the code manager, the forge, the terminal -- a single
   entry point with identical semantics:

       SAVF.auditSource(name, text)        -> { verdict, gates, findings, ... }
       SAVF.auditFiles([{path, text}])     -> { verdict, gates, findings, ... }

   The verdict is computed by the real engine (SavfScan + SavfCore.verdict) over
   the same phi0..phi10 gate scheme the CLI uses, so a browser verdict and a
   `savf.py` verdict for the same input are the same verdict.

   Appended to build/savf-core.js by the pipeline.  Depends only on the globals
   that core defines (SavfScan, SavfCore, SAVF_STDLIB, SAVF_STDATTRIB).
   ============================================================================ */
(function (global) {
  "use strict";

  var SC = global.SavfScan, C = global.SavfCore;
  if (!SC || !C) {
    throw new Error("SAVF core missing: SavfScan/SavfCore not loaded before the facade");
  }

  /* Gate metadata, verbatim from savf.html's UI so labels never drift. */
  var GATE_INFO = {
    phi0: "freeze: contract hashed and unchanged",
    phi1: "stubs, markers, mock identifiers",
    phi2: "phantom imports and phantom attributes",
    phi3: "tests that assert nothing or assert tautologies",
    phi4: "functions the tests never enter",
    phi5: "held-out data was really sealed away",
    phi6: "exceptions swallowed with pass",
    phi7: "mutation score against the threshold",
    phi8: "the dependency is real, not assumed",
    phi9: "a named human signed off",
    phi10: "artifacts match the signed manifest"
  };
  var ALL_PHI = [];
  for (var i = 0; i < 11; i++) ALL_PHI.push("phi" + i);

  function stdlibDict() {
    var d = Object.create(null);
    var list = global.SAVF_STDLIB || [];
    for (var i = 0; i < list.length; i++) d[list[i]] = 1;
    return d;
  }

  /* A file name is Python iff it ends .py; the engine only parses Python. */
  function isPy(name) { return /\.py$/i.test(String(name || "")); }

  function shouldSkip(path) {
    var parts = String(path || "").split("/");
    for (var i = 0; i < parts.length - 1; i++) if (SC.SKIP_DIRS[parts[i]]) return true;
    return false;
  }

  /* Build the local-name set the scanner uses to tell a local module from a
     phantom one: every ancestor directory and every sibling module stem. */
  function localDict(entries) {
    var local = Object.create(null);
    entries.forEach(function (e) {
      var base = String(e.path).split("/").pop().replace(/\.py$/i, "");
      if (base) local[base] = 1;
      var parts = String(e.path).split("/");
      for (var i = 0; i < parts.length - 1; i++) if (parts[i]) local[parts[i]] = 1;
    });
    return local;
  }

  /* phi4 (reachability), phi5 (held-out data), phi7 (mutation), phi8 (dependency)
     and phi9 (sign-off) cannot be established by a static browser pass.  They
     are reported marginal with an explicit note -- an honest boundary, never a
     silent pass.  phi0 is marginal when no freeze lock has been loaded. */
  var UNATTESTED = {
    phi4: "unattested: a browser cannot run your tests; use the CLI `savf.py reach`",
    phi5: "unattested: no sealed held-out data loaded",
    phi7: "unattested: a browser cannot count mutants; use the CLI `savf.py mutate`",
    phi8: "unattested: no recorded dependency evidence loaded",
    phi9: "unattested: no named human sign-off loaded",
    phi10: "unattested: no manifest loaded"
  };

  /* Scan one file to findings.  Never throws: an engine fault becomes a single
     high-severity finding so the verdict degrades to LIED rather than a silent
     pass.  This mirrors savf.html's runAudit exactly. */
  function scanOne(path, text, opts) {
    try {
      return SC.scanSource(path, text, opts);
    } catch (err) {
      return [{ rule: "ENGINE", phi: 1, file: path, line: 0,
                msg: String((err && err.message) || err), sev: "high" }];
    }
  }

  function auditFiles(entries, options) {
    options = options || {};
    entries = (entries || []).filter(function (e) {
      return e && isPy(e.path) && !shouldSkip(e.path);
    });

    var opts = {
      stdlib: stdlibDict(),
      stdattrs: global.SAVF_STDATTRIB || {},
      local: localDict(entries),
      /* mirrors the CLI's --installed: third-party roots the caller vouches for */
      installed: options.installed
    };

    var findings = [], parsed = 0, skipped = 0;
    entries.forEach(function (e) {
      var found = scanOne(e.path, e.text, opts);
      if (found.some(function (f) { return f.rule === "ENGINE"; })) skipped++;
      else if (!found.some(function (f) { return f.rule === "PARSE"; })) parsed++;
      findings = findings.concat(found);
    });

    var states = {}, notes = {};
    [1, 2, 3, 6].forEach(function (p) {
      var key = "phi" + p;
      var xs = findings.filter(function (f) { return f.phi === p; });
      states[key] = SC.phiFromFindings(findings, p);
      notes[key] = xs.length ? xs.length + " finding(s)" : "no finding";
    });
    states.phi0 = options.freezeOk === true ? "pass"
                : options.freezeOk === false ? "fail" : "marginal";
    notes.phi0 = options.freezeNote || "no lock loaded: contract not frozen";
    ["phi4", "phi5", "phi7", "phi8", "phi9", "phi10"].forEach(function (p) {
      states[p] = "marginal";
      notes[p] = UNATTESTED[p];
    });

    var verdict = C.verdict(states);
    return {
      version: "SAVF-1",
      engine: "savf-core",
      verdict: verdict,
      states: states,
      notes: notes,
      findings: findings,
      files: entries.length,
      parsed: parsed,
      skipped: skipped,
      counts: {
        high: findings.filter(function (f) { return f.sev === "high"; }).length,
        medium: findings.filter(function (f) { return f.sev === "medium"; }).length,
        total: findings.length
      }
    };
  }

  function auditSource(name, text, options) {
    return auditFiles([{ path: name || "input.py", text: text == null ? "" : String(text) }], options);
  }

  /* One-line human summary, for the terminal and any host that wants text. */
  function summarize(result) {
    if (!result) return "no result";
    var lines = [result.verdict + "  (" + result.counts.total + " finding(s) over "
                 + result.files + " file(s))"];
    var order = ["phi0", "phi1", "phi2", "phi3", "phi4", "phi5", "phi6",
                 "phi7", "phi8", "phi9", "phi10"];
    order.forEach(function (g) {
      lines.push("  " + g + "  " + result.states[g] + "  " + (result.notes[g] || ""));
    });
    result.findings.forEach(function (f) {
      lines.push("  phi" + f.phi + " " + f.rule + "  line " + f.line + "  " + f.msg);
    });
    return lines.join("\n");
  }

  var facade = {
    /* identity */
    version: "SAVF-1",
    /* the real engine, reachable by name from any host */
    scan: SC,
    core: C,
    /* the one function */
    auditSource: auditSource,
    auditFiles: auditFiles,
    summarize: summarize,
    /* gate metadata + scheme */
    gates: ALL_PHI,
    gateInfo: GATE_INFO,
    hardGates: C.HARD,
    softGates: C.SOFT,
    /* byte hashing for freeze/manifest, from the core */
    hash: global.SavfHash,
    audit: global.SavfAudit
  };

  /* Attach without clobbering a host that already published a richer SAVF.
     A host such as the code studio owns its own SAVF with its own gate scheme
     (`hardGates` is a map there, an array here), so merging the core's fields
     into it would either shadow the core or corrupt the host.  The core
     therefore keeps its own authoritative object and merges in additively. */
  var existing = global.SAVF;
  if (existing && typeof existing === "object" && existing !== facade) {
    Object.keys(facade).forEach(function (k) {
      if (!(k in existing)) existing[k] = facade[k];
    });
  } else {
    global.SAVF = facade;
  }
  /* SavfTruth is always the core surface, never a host's object, so a caller
     that asks the core a question always gets the core's answer. */
  global.SavfTruth = facade;
})(typeof window !== "undefined" ? window : globalThis);
