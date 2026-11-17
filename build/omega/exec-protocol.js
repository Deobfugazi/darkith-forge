/* =====================================================================
   Ω EXEC PROTOCOL — one contract, three execution tiers.

   The webapp never talks to a process directly. It talks to a backend that
   satisfies this interface. Backends:

     native  — a binary shipped as lib*.so, run from nativeLibraryDir
               (Android 10+ forbids execve from app-writable storage, so
                this is the only place a shipped binary may live).
     wasm    — a wasm32-wasi module run in-process (Chicory/WAMR/WASI).
               No exec at all, so W^X never applies.
     proot   — a full Linux guest, for toolchains.

   Every method is honest: a missing capability reports unavailable rather
   than a fabricated success string. Output is streamed, never discarded.

   This file is dependency-free and runs both in the browser (attached to
   window.OmegaExec) and in Node (module.exports), so the same contract is
   exercised by the test harness and by the shipped shell.
   ===================================================================== */
(function (root, factory) {
  var mod = factory();
  if (typeof module === "object" && module.exports) module.exports = mod;
  root.OmegaExec = mod;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var STATES = { PENDING: "pending", RUNNING: "running", EXITED: "exited", ERROR: "error" };

  /* A ring buffer keeps memory bounded on a 4 GB device: a runaway process
     cannot grow the scrollback without limit. Oldest bytes are dropped and
     the loss is recorded, never hidden. */
  function Ring(cap) {
    this.cap = cap || 262144;
    this.buf = [];
    this.len = 0;
    this.dropped = 0;
  }
  Ring.prototype.push = function (s) {
    s = String(s);
    this.buf.push(s);
    this.len += s.length;
    while (this.len > this.cap && this.buf.length > 1) {
      this.dropped += this.buf[0].length;
      this.len -= this.buf[0].length;
      this.buf.shift();
    }
  };
  Ring.prototype.drain = function () {
    var s = this.buf.join("");
    this.buf = [];
    this.len = 0;
    return s;
  };

  /* ---- Capability probe -------------------------------------------------
     Returns what this device can actually do. The UI uses this to enable or
     grey out commands; the assistant uses it to choose a backend. */
  function caps(host) {
    var native = [], wasm = [], proot = false, assistant = false, models = [];
    if (host) {
      if (typeof host.execCaps === "function") {
        try {
          var j = JSON.parse(host.execCaps() || "{}");
          native = j.native || [];
          wasm = j.wasm || [];
          proot = !!j.proot;
        } catch (e) { /* host said something unparseable: report nothing */ }
      }
      if (typeof host.assistantCaps === "function") {
        try {
          var a = JSON.parse(host.assistantCaps() || "{}");
          assistant = !!a.available;
          models = a.models || [];
        } catch (e) {}
      }
    }
    return { native: native, wasm: wasm, proot: proot, assistant: assistant, models: models };
  }

  /* ---- Backend: the JS-side supervisor ---------------------------------
     It speaks to a host object (the Android bridge, or a Node child_process
     adapter in tests). If no host is present it degrades to the in-page
     TermKit shell, which is why the offline webapp still works with zero
     native code. */
  function Backend(host, opts) {
    opts = opts || {};
    this.host = host || null;
    this.jobs = Object.create(null);
    this.next = 1;
    this.onEvent = opts.onEvent || function () {};
    this.maxJobs = opts.maxJobs || 8;
  }

  Backend.prototype.available = function () {
    return !!(this.host && (typeof this.host.execBegin === "function"));
  };

  /* Start a job. Returns {id, backend} or throws with a reason. */
  Backend.prototype.begin = function (cmd, o) {
    o = o || {};
    if (!this.available()) throw new Error("no native exec backend on this device");
    var live = 0;
    for (var k in this.jobs) if (this.jobs[k].state === STATES.RUNNING) live++;
    if (live >= this.maxJobs) throw new Error("too many running jobs (" + this.maxJobs + ")");
    var id = "j" + (this.next++);
    var spec = {
      cmd: String(cmd),
      /* argv wins when present: whitespace-splitting a shell string mangles
         quoting, so callers that care about argument boundaries pass an
         array and the host execs it directly. */
      argv: o.argv || null,
      cwd: o.cwd || "/",
      env: o.env || {},
      cols: o.cols || 80,
      rows: o.rows || 24,
      backend: o.backend || "native"
    };
    var res;
    try {
      res = this.host.execBegin(JSON.stringify(spec));
    } catch (e) {
      throw new Error("execBegin failed: " + (e && e.message ? e.message : e));
    }
    var parsed;
    try { parsed = JSON.parse(res || "{}"); } catch (e) { parsed = {}; }
    if (parsed.error) throw new Error(parsed.error);
    var jid = parsed.id || id;
    this.jobs[jid] = {
      id: jid, spec: spec, state: STATES.RUNNING,
      out: new Ring(), err: new Ring(), status: null
    };
    this.onEvent({ type: "begin", id: jid, spec: spec });
    return { id: jid, backend: spec.backend };
  };

  /* Pull whatever output is ready. Drains the ring so bytes are delivered
     exactly once. Returns {out, err, status, done, dropped}. */
  Backend.prototype.read = function (id) {
    var j = this.jobs[id];
    if (!j) throw new Error("unknown job " + id);
    if (j.state === STATES.RUNNING && typeof this.host.execRead === "function") {
      var raw;
      try { raw = this.host.execRead(id); } catch (e) { raw = null; }
      var msg;
      try { msg = JSON.parse(raw || "{}"); } catch (e) { msg = {}; }
      if (msg.out) { j.out.push(msg.out); this.onEvent({ type: "out", id: id, chunk: msg.out }); }
      if (msg.err) { j.err.push(msg.err); this.onEvent({ type: "err", id: id, chunk: msg.err }); }
      if (msg.done) {
        j.state = STATES.EXITED;
        j.status = typeof msg.status === "number" ? msg.status : 0;
        this.onEvent({ type: "exit", id: id, status: j.status });
      }
    }
    var out = j.out.drain(), err = j.err.drain();
    var dropped = j.out.dropped + j.err.dropped;
    j.out.dropped = j.err.dropped = 0;
    return { out: out, err: err, status: j.status, done: j.state !== STATES.RUNNING, dropped: dropped };
  };

  Backend.prototype.write = function (id, data) {
    if (typeof this.host.execWrite !== "function") throw new Error("stdin not supported");
    return this.host.execWrite(id, String(data));
  };

  Backend.prototype.signal = function (id, sig) {
    if (typeof this.host.execSignal !== "function") throw new Error("signals not supported");
    var j = this.jobs[id];
    if (j) j.state = STATES.EXITED;
    return this.host.execSignal(id, sig || "TERM");
  };

  /* Convenience for one-shot commands: run to completion with a byte cap and
     a deadline, so a hung command can never wedge the UI. */
  Backend.prototype.run = function (cmd, o) {
    o = o || {};
    var self = this;
    var started = self.begin(cmd, o);
    var deadline = Date.now() + (o.timeoutMs || 30000);
    var maxBytes = o.maxBytes || 1048576;
    return new Promise(function (resolve, reject) {
      var acc = { out: "", err: "" };
      (function pump() {
        var r;
        try { r = self.read(started.id); } catch (e) { return reject(e); }
        acc.out += r.out; acc.err += r.err;
        if (acc.out.length + acc.err.length > maxBytes) {
          try { self.signal(started.id, "TERM"); } catch (e) {}
          acc.err += "\n[omega] output cap reached; job terminated\n";
          return resolve({ status: 124, out: acc.out, err: acc.err, capped: true });
        }
        if (r.done) return resolve({ status: r.status, out: acc.out, err: acc.err });
        if (Date.now() > deadline) {
          try { self.signal(started.id, "TERM"); } catch (e) {}
          acc.err += "\n[omega] timeout; job terminated\n";
          return resolve({ status: 124, out: acc.out, err: acc.err, timeout: true });
        }
        setTimeout(pump, o.pollMs || 20);
      })();
    });
  };

  return { STATES: STATES, Ring: Ring, Backend: Backend, caps: caps };
});
