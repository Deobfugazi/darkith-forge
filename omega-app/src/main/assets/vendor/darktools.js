/* ============================================================================
   darktools.js — handcoded dev toolkits for DarkTerm
   ----------------------------------------------------------------------------
   Ships four things:
     1. persistence  — snapshot the VFS + session to a store (localStorage, or
                       the filesystem under node), so state survives a reload
     2. tk           — a toolkit host: handcode tools in the VFS, `tk build` to
                       install them, `tk list`/`tk help`/`tk run` to drive them
     3. task         — a real task manager (data in tab files, real shell verbs)
     4. sync         — a synchronicity engine: a transparent weighted scorer that
                       LEARNS your priorities online from BOTH explicit intent
                       (task do|focus|defer) and passive evidence (every real
                       command you type), plus an honest deficit ledger and a
                       measurable capability ladder (`sync omega`). It never
                       stubs and never injects a defect: anything it cannot sync
                       becomes a named, actionable deficit to work on.
   Everything is plain data in the VFS, so `cat`, `grep`, `awk`, pipes all work
   on it. No build step, no Gradle, no dependencies.
   ============================================================================ */
(function (root, factory) {
  var api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.DarkTools = api;
})(typeof window !== "undefined" ? window : this, function (root) {

  var VERSION = "2.0.0";
  var HOME = "/home/inscriber";
  var TASKDIR = HOME + "/tasks";
  var TOOLDIR = HOME + "/tools";

  function nowMs() { return Date.now(); }
  function day() { var d = new Date(); return d.getFullYear() + "-" + p2(d.getMonth() + 1) + "-" + p2(d.getDate()); }
  function p2(n) { return (n < 10 ? "0" : "") + n; }
  function clamp(x, a, b) { return x < a ? a : (x > b ? b : x); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]; }); }

  /* ------------------------------------------------------------------ store */
  function makeStore(kind, name) {
    try {
      if (kind === "fs" && root.require) {
        var fs = root.require("fs");
        return {
          read: function () { try { return JSON.parse(fs.readFileSync(name, "utf8")); } catch (e) { return null; } },
          write: function (obj) { fs.writeFileSync(name, JSON.stringify(obj)); }
        };
      }
      if (kind === "local" && root.localStorage) {
        return {
          read: function () { try { return JSON.parse(root.localStorage.getItem(name)); } catch (e) { return null; } },
          write: function (obj) { root.localStorage.setItem(name, JSON.stringify(obj)); }
        };
      }
    } catch (e) { /* fall through to memory */ }
    var mem = null;
    return { read: function () { return mem; }, write: function (o) { mem = o; } };
  }

  /* ------------------------------------------------------- serialise the VFS */
  function dumpNode(n) {
    if (n.t === "f") return { t: "f", d: n.d, m: n.m };
    var c = {}; Object.keys(n.c).forEach(function (k) { c[k] = dumpNode(n.c[k]); });
    return { t: "d", c: c, m: n.m };
  }
  function loadNode(o) {
    if (o.t === "f") return { t: "f", d: o.d, m: o.m, ts: 0 };
    var c = {}; Object.keys(o.c || {}).forEach(function (k) { c[k] = loadNode(o.c[k]); });
    return { t: "d", c: c, m: o.m, ts: 0 };
  }

  function persist(fs, sh) {
    return { v: 1, fs: dumpNode(fs.root), cwd: sh.cwd, vars: sh.vars, aliases: sh.aliases };
  }
  function restore(fs, sh, snap) {
    if (!snap || !snap.fs) return false;
    fs.root = loadNode(snap.fs);
    if (snap.cwd) sh.cwd = snap.cwd;
    if (snap.vars) sh.vars = snap.vars;
    if (snap.aliases) sh.aliases = snap.aliases;
    return true;
  }

  /* =============================================================== TASK MANAGER
     Storage: one file per task under ~/tasks/<id>.task — a tiny tab-separated
     record. Because it is plain text in the VFS, every coreutil works on it. */
  var FIELDS = ["id", "title", "status", "prio", "tags", "created", "done"];

  function encTask(t) {
    return "id\t" + t.id + "\n" +
           "title\t" + t.title + "\n" +
           "status\t" + t.status + "\n" +
           "prio\t" + t.prio + "\n" +
           "tags\t" + (t.tags || []).join(",") + "\n" +
           "created\t" + t.created + "\n" +
           "done\t" + (t.done || "") + "\n";
  }
  function decTask(text) {
    var t = { tags: [] };
    String(text).split("\n").forEach(function (line) {
      var i = line.indexOf("\t"); if (i < 0) return;
      var k = line.slice(0, i), v = line.slice(i + 1);
      if (k === "tags") t.tags = v ? v.split(",") : [];
      else if (FIELDS.indexOf(k) >= 0) t[k] = v;
    });
    t.prio = Number(t.prio) || 3;
    return t;
  }
  function taskPath(id) { return TASKDIR + "/" + id + ".task"; }

  function TaskManager(sh) {
    this.sh = sh;
    sh.fs.mkdirp(TASKDIR);
    this.seq = 0;
  }
  TaskManager.prototype._nextId = function () {
    var self = this, max = 0;
    this.list().forEach(function (t) { var n = parseInt(String(t.id).replace(/\D/g, ""), 10) || 0; if (n > max) max = n; });
    return "t" + (max + 1);
  };
  TaskManager.prototype.list = function (filter) {
    var fs = this.sh.fs, names = fs.list(TASKDIR) || [], out = [];
    names.forEach(function (n) {
      if (!/\.task$/.test(n)) return;
      var node = fs.get(TASKDIR + "/" + n);
      if (node && node.t === "f") out.push(decTask(node.d));
    });
    if (filter) out = out.filter(function (t) {
      if (filter.status && t.status !== filter.status) return false;
      if (filter.tag && (t.tags || []).indexOf(filter.tag) < 0) return false;
      if (filter.text) { var hay = (t.title + " " + (t.tags || []).join(" ")).toLowerCase(); if (hay.indexOf(filter.text.toLowerCase()) < 0) return false; }
      return true;
    });
    out.sort(function (a, b) { return (b.prio - a.prio) || (a.id < b.id ? -1 : 1); });
    return out;
  };
  TaskManager.prototype.get = function (id) {
    var node = this.sh.fs.get(taskPath(id));
    return node && node.t === "f" ? decTask(node.d) : null;
  };
  TaskManager.prototype.add = function (title, opts) {
    opts = opts || {};
    var id = this._nextId();
    var t = { id: id, title: title, status: opts.status || "todo", prio: opts.prio == null ? 3 : Number(opts.prio), tags: opts.tags || [], created: day(), done: "" };
    this.sh.fs.writeFile(taskPath(id), encTask(t));
    return t;
  };
  TaskManager.prototype.update = function (id, patch) {
    var t = this.get(id); if (!t) return null;
    Object.keys(patch).forEach(function (k) { t[k] = patch[k]; });
    this.sh.fs.writeFile(taskPath(id), encTask(t));
    return t;
  };
  TaskManager.prototype.done = function (id) { return this.update(id, { status: "done", done: day() }); };
  TaskManager.prototype.rm = function (id) { return this.sh.fs.unlink(taskPath(id)); };

  /* =========================================================== SYNC ENGINE
     A transparent, learnable priority scorer — and an honest deficit ledger.

     score = sigmoid(w . x). It learns from two sources:
       * explicit intent  — `task do|focus|defer`  (label 1 / 0)
       * passive evidence — every real command you type. Working in a tagged
         area credits that task; it also reinforces the tag and tracks
         momentum (an EMA of recent intent).

     The rule this engine obeys: it NEVER silently stubs and NEVER injects a
     defect. When it cannot sync something — a command it cannot attribute, a
     task with no tags, an unmet capability rung — it RAISES A NAMED DEFICIT
     with an actionable suggestion. `sync omega` shows the capability ladder;
     every unmet rung is itself a deficit to work on. That is the path to the
     ceiling: measure the gap, name it, close it. */
  var FEATURES = ["overdue", "high", "age", "tag", "recent_focus", "momentum",
                  "blocking", "quick", "shared", "title_hit", "in_cwd", "tool_link", "stale"];

  function zeroWeights() { var w = {}; FEATURES.forEach(function (f) { w[f] = 0; }); return w; }
  function sigmoid(z) { return 1 / (1 + Math.exp(-z)); }
  function uniqA(a) { var o = {}, r = []; a.forEach(function (x) { if (x && !o[x]) { o[x] = 1; r.push(x); } }); return r; }
  function countNonZero(o) { var n = 0; Object.keys(o).forEach(function (k) { if (Math.abs(o[k]) > 1e-6) n++; }); return n; }

  function featureVec(t, ctx) {
    ctx = ctx || {};
    var ageDays = 0;
    if (t.created) { var d = new Date(t.created + "T00:00:00"); ageDays = Math.max(0, (nowMs() - d.getTime()) / 86400000); }
    var tagAffinity = 0;
    (t.tags || []).forEach(function (tg) { tagAffinity += (ctx.tagWeights && ctx.tagWeights[tg]) || 0; });
    var lastTouch = (ctx.touched && ctx.touched[t.id]) || 0;
    var daysSince = lastTouch ? (nowMs() - lastTouch) / 86400000 : 30;
    var cwdTags = ctx.cwdTags || [], toolTags = ctx.toolTags || [];
    function shares(set) { return (t.tags || []).some(function (tg) { return set.indexOf(tg) >= 0; }) ? 1 : 0; }
    return {
      overdue: (t.status === "todo" && ctx.overdue && ctx.overdue[t.id]) ? 1 : 0,
      high: (Number(t.prio) >= 4) ? 1 : 0,
      age: clamp(ageDays / 30, 0, 1),
      tag: clamp(tagAffinity, 0, 1),
      recent_focus: clamp(1 - daysSince / 14, 0, 1),
      momentum: clamp((ctx.momentum && ctx.momentum[t.id]) || 0, -1, 1),
      blocking: (ctx.blocking && ctx.blocking[t.id]) ? 1 : 0,
      quick: (ctx.quick && ctx.quick[t.id]) ? 1 : 0,
      shared: (ctx.shared && ctx.shared[t.id]) ? 1 : 0,
      title_hit: (ctx.titleHit && ctx.titleHit[t.id]) ? 1 : 0,
      in_cwd: shares(cwdTags),
      tool_link: shares(toolTags),
      stale: clamp(daysSince / 30, 0, 1)
    };
  }
  function dot(w, x) { var z = 0; Object.keys(x).forEach(function (k) { z += (w[k] || 0) * x[k]; }); return z; }

  /* ----------------------------------------------------- DEFICIT LEDGER
     The honest ledger. Every unsyncable thing becomes a named, deduped,
     actionable work item — never a stub, never a silent drop. */
  function DeficitLedger() { this.byId = {}; this.byKey = {}; this.seq = 0; }
  DeficitLedger.prototype.raise = function (kind, detail, opts) {
    opts = opts || {};
    var key = kind + "::" + (opts.key != null ? opts.key : detail);
    if (this.byKey[key]) { var e = this.byId[this.byKey[key]]; e.count++; e.last = nowMs(); return e; }
    var id = "d" + (++this.seq);
    var item = { id: id, kind: kind, detail: detail, count: 1, first: nowMs(), last: nowMs(),
                 status: "open", suggestion: suggestDeficit(kind, detail, opts), data: opts };
    this.byId[id] = item; this.byKey[key] = id;
    return item;
  };
  DeficitLedger.prototype.resolveKey = function (kind, key) {
    var id = this.byKey[kind + "::" + key];
    if (id && this.byId[id]) { this.byId[id].status = "resolved"; this.byId[id].resolved = nowMs(); }
  };
  DeficitLedger.prototype.resolve = function (id) {
    if (this.byId[id]) { this.byId[id].status = "resolved"; this.byId[id].resolved = nowMs(); return true; }
    return false;
  };
  DeficitLedger.prototype.open = function () {
    var self = this;
    return Object.keys(this.byId).map(function (k) { return self.byId[k]; })
      .filter(function (d) { return d.status === "open"; })
      .sort(function (a, b) { return (b.count - a.count) || (a.id < b.id ? -1 : 1); });
  };
  DeficitLedger.prototype.all = function () { var self = this; return Object.keys(this.byId).map(function (k) { return self.byId[k]; }); };
  DeficitLedger.prototype.dump = function () { return { byId: this.byId, byKey: this.byKey, seq: this.seq }; };
  DeficitLedger.prototype.load = function (o) { if (o) { this.byId = o.byId || {}; this.byKey = o.byKey || {}; this.seq = o.seq || 0; } };

  function suggestDeficit(kind, detail, opts) {
    if (kind === "attribution") { var tg = (opts.tags || []).slice(-1)[0] || "area"; return "tag a task with +" + tg + " — e.g. task add \"<title>\" +" + tg + " — so work here is credited to it"; }
    if (kind === "coverage") return (opts.tags && opts.tags.length)
      ? "task " + opts.task + " has tags (+" + opts.tags.join(" +") + ") but none are learned; work in that area (e.g. cd ~/" + opts.tags[0] + ") or run: task tag " + opts.task + " " + opts.tags[0]
      : "task " + opts.task + " has no tags; add one: task tag " + opts.task + " <tag>";
    if (kind === "dangling") return "a command named task " + opts.id + " but no such task exists; it may have been removed";
    if (kind === "contradiction") return "task " + opts.task + " was both raised and lowered; state the intent: sync claim " + opts.task + " 1";
    if (kind === "rung") return opts.desc || "close this capability gap";
    return "resolve: " + detail;
  }

  /* -------------------------------------------------------- OMEGA LADDER
     The measurable capability ceiling. Each rung is a predicate over the
     engine's live state. Unmet rungs become deficits automatically, so the
     engine is always working an explicit list toward the top. */
  var RUNGS = [
    { id: "r1", name: "observer-wired", desc: "learn from real typed commands, not only explicit focus",
      met: function (e) { return e.stats.observed > 0; } },
    { id: "r2", name: "attribution-closed", desc: "every observed command is credited to a task (0 unattributed)",
      met: function (e) { return e.stats.observed > 0 && e.stats.observed_unattributed === 0; } },
    { id: "r3", name: "tag-model", desc: "at least 3 tags carry learned weight",
      met: function (e) { return countNonZero(e.tagWeights) >= 3; } },
    { id: "r4", name: "weights-settled", desc: "feature weights stable (max |delta| < 0.05 over last 20 updates)",
      met: function (e) { return e.stats.updates >= 20 && e.stats.maxRecentDelta < 0.05; } },
    { id: "r5", name: "predictive", desc: "predicts your next focus >= 70% over last 10 observations",
      met: function (e) { var w = e.stats.predWindow || []; return w.length >= 10 && (w.reduce(function (a, b) { return a + b; }, 0) / w.length) >= 0.7; } },
    { id: "r6", name: "coherent", desc: "no unresolved contradiction (a task both raised and lowered)",
      met: function (e) { return e.stats.contradictions === 0; } },
    { id: "r7", name: "deficits-clear", desc: "zero open operational deficits (capability gaps excluded)",
      met: function (e) { return e.ledger.open().filter(function (d) { return d.kind !== "rung"; }).length === 0; } },
    { id: "r8", name: "fully-covered", desc: "every open task carries at least one learned tag",
      met: function (e, tasks) { return tasks.filter(function (t) { return t.status !== "done"; })
        .every(function (t) { return (t.tags || []).some(function (tg) { return Math.abs(e.tagWeights[tg] || 0) > 1e-6; }); }); } }
  ];

  function SyncEngine(store) {
    this.store = store || makeStore("memory", "darkith.sync");
    var s = this.store.read() || {};
    this.weights = s.weights || zeroWeights();
    this.tagWeights = s.tagWeights || {};
    this.events = s.events || [];
    this.touched = s.touched || {};
    this.momentum = s.momentum || {};
    this.lastLabel = s.lastLabel || {};
    this.rate = s.rate == null ? 0.35 : s.rate;
    this.stats = s.stats || { observed: 0, observed_unattributed: 0, updates: 0, predSamples: 0, predHits: 0,
                              contradictions: 0, maxRecentDelta: 0, recentDeltas: [], predWindow: [] };
    if (!this.stats.predWindow) this.stats.predWindow = [];
    this.ledger = new DeficitLedger();
    this.ledger.load(s.ledger);
    this.cwdTags = s.cwdTags || [];
    this.toolTags = s.toolTags || [];
    this.toolNames = s.toolNames || [];
  }
  SyncEngine.prototype.save = function () {
    this.store.write({ weights: this.weights, tagWeights: this.tagWeights, events: this.events.slice(-500),
      touched: this.touched, momentum: this.momentum, lastLabel: this.lastLabel, rate: this.rate,
      stats: this.stats, ledger: this.ledger.dump(), cwdTags: this.cwdTags, toolTags: this.toolTags, toolNames: this.toolNames });
  };
  SyncEngine.prototype.buildContext = function (tasks, query) {
    var self = this, ctx = { touched: this.touched, tagWeights: this.tagWeights, momentum: this.momentum,
      cwdTags: this.cwdTags, toolTags: this.toolTags, overdue: {}, blocking: {}, quick: {}, shared: {}, titleHit: {} };
    tasks.forEach(function (t) {
      (t.tags || []).forEach(function (tg) { if (self.tagWeights[tg] > 0.5) ctx.overdue[t.id] = 1; });
      if (query) ctx.titleHit[t.id] = (t.title.toLowerCase().indexOf(String(query).toLowerCase()) >= 0) ? 1 : 0;
    });
    return ctx;
  };
  SyncEngine.prototype.rank = function (tasks, opts) {
    var self = this, ctx = this.buildContext(tasks, opts && opts.query);
    var rows = tasks.map(function (t) {
      var x = featureVec(t, ctx);
      return { task: t, features: x, score: sigmoid(dot(self.weights, x)) };
    });
    rows.sort(function (a, b) { return b.score - a.score; });
    return rows;
  };
  SyncEngine.prototype.predictTop = function (tasks) {
    var open = tasks.filter(function (t) { return t.status !== "done"; });
    if (!open.length) return null;
    var rows = this.rank(open);
    return rows[0].task.id;
  };
  SyncEngine.prototype.why = function (t, tasks, opts) {
    var ctx = this.buildContext(tasks, opts && opts.query);
    var x = featureVec(t, ctx), self = this;
    var contrib = Object.keys(x).map(function (k) { return { feature: k, x: x[k], w: self.weights[k], c: x[k] * (self.weights[k] || 0) }; })
      .filter(function (r) { return Math.abs(r.c) > 1e-9; })
      .sort(function (a, b) { return Math.abs(b.c) - Math.abs(a.c); });
    return { score: sigmoid(dot(this.weights, x)), features: x, contrib: contrib };
  };
  SyncEngine.prototype._nudge = function (x, err) {
    var self = this, maxD = 0;
    Object.keys(x).forEach(function (k) {
      var d = self.rate * err * x[k];
      self.weights[k] = (self.weights[k] || 0) + d;
      if (Math.abs(d) > maxD) maxD = Math.abs(d);
    });
    this.stats.updates++;
    this.stats.recentDeltas.push(maxD);
    if (this.stats.recentDeltas.length > 20) this.stats.recentDeltas.shift();
    this.stats.maxRecentDelta = this.stats.recentDeltas.reduce(function (a, b) { return Math.max(a, b); }, 0);
  };
  SyncEngine.prototype.learn = function (t, tasks, label, opts) {
    opts = opts || {};
    var ctx = this.buildContext(tasks, opts.query);
    var x = featureVec(t, ctx);
    var p = sigmoid(dot(this.weights, x));
    var err = label - p;
    this._nudge(x, err);
    var self = this;
    (t.tags || []).forEach(function (tg) { self.tagWeights[tg] = clamp((self.tagWeights[tg] || 0) + self.rate * err, -2, 2); });
    this.touched[t.id] = nowMs();
    this.momentum[t.id] = 0.6 * ((label === 1) ? 1 : -1) + 0.4 * (this.momentum[t.id] || 0);
    // contradiction: a task that is both raised and lowered without reconciliation
    if (this.lastLabel[t.id] != null && this.lastLabel[t.id] !== label && !opts.reconcile) {
      this.stats.contradictions++;
      this.ledger.raise("contradiction", "task " + t.id + " raised then lowered", { task: t.id, key: t.id });
    } else {
      this.stats.contradictions = Math.max(0, this.stats.contradictions - (opts.reconcile ? 1 : 0));
      if (opts.reconcile) this.ledger.resolveKey("contradiction", t.id);
    }
    this.lastLabel[t.id] = label;
    this.events.push({ at: nowMs(), id: t.id, label: label, via: opts.via || "explicit" });
    if (this.events.length > 500) this.events = this.events.slice(-500);
    this.save();
    return { before: p, after: sigmoid(dot(this.weights, x)), err: err };
  };
  SyncEngine.prototype.learnById = function (id, tasks, label, opts) {
    var t = null;
    tasks.forEach(function (x) { if (x.id === id) t = x; });
    if (!t) { this.ledger.raise("dangling", "learn target " + id + " does not exist", { id: id, key: id }); return null; }
    return this.learn(t, tasks, label, opts);
  };

  /* ------------------------------------------------- PASSIVE OBSERVATION
     Turn a real command into evidence. Meaningful tokens (paths, tags, tool
     names, task ids) become a signal. The signal is attributed to a task; if
     it cannot be, that is an explicit deficit — not a silent drop. */
  var STOP = { "": 1, ".": 1, "..": 1, "home": 1, "inscriber": 1, "sdcard": 1, "tmp": 1, "bin": 1, "usr": 1,
               "local": 1, "var": 1, "etc": 1, "root": 1, "mnt": 1, "storage": 1, "emulated": 1, "0": 1,
               "download": 1, "downloads": 1, "documents": 1, "dcim": 1, "darkith": 0 };
  var APP_CMDS = { task: 1, sync: 1, tk: 1, store: 1 };

  function signalsFromCommand(cmd, argv, sh) {
    var tags = [], ids = [], paths = [];
    function eat(token) {
      if (/^[#+].+/.test(token)) { tags.push(token.slice(1).toLowerCase()); return; }
      if (/^t\d+$/.test(token)) { ids.push(token); return; }
      if (token.indexOf("/") >= 0 || /^[~.]/.test(token)) {
        paths.push(token);
        token.replace(/^~/, "").split("/").forEach(function (c) {
          c = c.replace(/\.[a-z0-9]+$/i, "").toLowerCase();
          if (!STOP[c] && !/^\d+$/.test(c) && c) tags.push(c);
        });
      }
    }
    (argv || []).forEach(eat);
    return { cmd: cmd, tags: uniqA(tags), ids: uniqA(ids), paths: paths };
  }

  SyncEngine.prototype.attribute = function (sig, tasks) {
    var open = tasks.filter(function (t) { return t.status !== "done"; });
    var i, t;
    for (i = 0; i < open.length; i++) { if (sig.ids.indexOf(open[i].id) >= 0) return { id: open[i].id, overlap: 99 }; }
    var best = null;
    open.forEach(function (t) {
      var ov = (t.tags || []).filter(function (tg) { return sig.tags.indexOf(tg) >= 0; }).length;
      if (ov > 0 && (!best || ov > best.overlap || (ov === best.overlap && t.id < best.id))) best = { id: t.id, overlap: ov };
    });
    return best;
  };

  SyncEngine.prototype.observe = function (cmd, argv, sh, tasks) {
    if (APP_CMDS[cmd]) return { skipped: true };
    var sig = signalsFromCommand(cmd, argv, sh);
    var S = sig.tags;
    if (!S.length && !sig.ids.length) return { signals: sig, silent: true };

    // decay all tag affinities slightly (recency-weighted), then reinforce observed tags
    var self = this;
    Object.keys(this.tagWeights).forEach(function (k) { self.tagWeights[k] = clamp(self.tagWeights[k] * 0.99, -2, 2); });
    S.forEach(function (tg) { self.tagWeights[tg] = clamp((self.tagWeights[tg] || 0) + 0.15, -2, 2); });

    // every open task must carry a learned tag, else it is a coverage deficit
    tasks.filter(function (t) { return t.status !== "done"; }).forEach(function (t) {
      var tags = t.tags || [];
      var covered = tags.some(function (tg) { return Math.abs(self.tagWeights[tg] || 0) > 1e-6; });
      if (!covered) {
        var detail = tags.length
          ? "open task " + t.id + " carries +" + tags.join(" +") + " but none are learned yet"
          : "open task " + t.id + " has no tags at all";
        self.ledger.raise("coverage", detail, { task: t.id, key: t.id, tags: tags });
      } else self.ledger.resolveKey("coverage", t.id);
    });

    var hit = this.attribute(sig, tasks);
    if (hit) {
      var predicted = this.predictTop(tasks);
      this.stats.predSamples++;
      var pHit = (predicted === hit.id) ? 1 : 0;
      this.stats.predHits += pHit;
      this.stats.predWindow.push(pHit);
      if (this.stats.predWindow.length > 10) this.stats.predWindow.shift();
      this.learnById(hit.id, tasks, 1, { via: "observed:" + cmd });
      this.stats.observed++;
      this.ledger.resolveKey("attribution", S.join("|") || "none");
      this.save();
      return { signals: sig, hit: hit, predicted: predicted === hit.id };
    }
    this.stats.observed_unattributed++;
    this.ledger.raise("attribution", "command in " + (S.join(",") || "an unknown area") + " credited no task",
      { tags: S, command: cmd, key: S.join("|") || cmd });
    this.save();
    return { signals: sig, hit: null };
  };

  SyncEngine.prototype.omega = function (tasks) {
    var self = this, rows = [];
    RUNGS.forEach(function (r) {
      var met = false;
      try { met = !!r.met(self, tasks); } catch (e) { met = false; }
      rows.push({ id: r.id, name: r.name, desc: r.desc, met: met });
      if (!met) self.ledger.raise("rung", "capability gap: " + r.name + " — " + r.desc, { rung: r.id, key: r.id, desc: r.desc });
      else self.ledger.resolveKey("rung", r.id);
    });
    var level = rows.filter(function (r) { return r.met; }).length;
    return { rungs: rows, level: level, max: rows.length, percent: Math.round(100 * level / rows.length) };
  };

  SyncEngine.prototype.reset = function () {
    this.weights = zeroWeights(); this.tagWeights = {}; this.events = []; this.touched = {};
    this.momentum = {}; this.lastLabel = {}; this.ledger = new DeficitLedger();
    this.stats = { observed: 0, observed_unattributed: 0, updates: 0, predSamples: 0, predHits: 0, contradictions: 0, maxRecentDelta: 0, recentDeltas: [], predWindow: [] };
    this.save();
  };

  /* ================================================================= TK HOST
     Handcode a toolkit as a shell script under ~/tools/<name>.tk and run
     `tk build` to install it. A tool is a function you write in DarkTerm's own
     shell; `tk` discovers it, gives it help, and can run it. */
  function TkHost(sh, session) {
    this.sh = sh;
    this.session = session;
    sh.fs.mkdirp(TOOLDIR);
  }
  TkHost.prototype.tools = function () {
    var fs = this.sh.fs, names = fs.list(TOOLDIR) || [];
    return names.filter(function (n) { return /\.tk$/.test(n); }).map(function (n) {
      var node = fs.get(TOOLDIR + "/" + n);
      var src = node.d, m = /^#\s*@desc\s+(.*)$/m.exec(src);
      return { name: n.replace(/\.tk$/, ""), file: TOOLDIR + "/" + n, desc: m ? m[1] : "(no @desc)", src: src };
    });
  };
  TkHost.prototype.build = function () {
    var self = this, built = [];
    this.tools().forEach(function (tool) {
      var lines = tool.src.split("\n").filter(function (l) { return !/^#/.test(l); }).join("\n");
      // wrap the body as a shell function named after the tool
      var fn = tool.name + "() {\n" + lines + "\n}";
      self.sh.runString(fn);
      built.push(tool.name);
    });
    return built;
  };
  TkHost.prototype.run = function (name, args) {
    return this.session.exec(name + " " + (args || []).join(" "));
  };

  /* ------------------------------------------------------------- app command
     `tk` — the toolkit host, wired as a shell builtin. */
  function ctxOf(sh, fallback) { return (sh && sh._dtctx) ? sh._dtctx : fallback; }

  function tkCommand(fallback) {
    return function (sh, args) {
      var ctx = ctxOf(sh, fallback);
      var sub = args[0] || "list", host = ctx.tk;
      if (sub === "list") {
        var ts = host.tools();
        if (!ts.length) return { out: "no toolkits installed. handcode one in " + TOOLDIR + "/<name>.tk, then: tk build\n" };
        return { out: ts.map(function (t) { return "  " + t.name + "  " + t.desc + "\n"; }).join("") };
      }
      if (sub === "build") {
        var built = host.build();
        return { out: "built " + built.length + " toolkit(s): " + (built.join(", ") || "(none)") + "\n" };
      }
      if (sub === "cat") {
        var tool = host.tools().filter(function (t) { return t.name === args[1]; })[0];
        if (!tool) return { out: "", err: "tk: no toolkit '" + args[1] + "'\n", code: 1 };
        return { out: tool.src };
      }
      if (sub === "new") {
        var name = args[1]; if (!name) return { out: "", err: "usage: tk new <name>\n", code: 2 };
        var path = TOOLDIR + "/" + name + ".tk";
        if (sh.fs.get(path)) return { out: "", err: "tk: " + path + " already exists\n", code: 1 };
        sh.fs.writeFile(path, "# @desc " + name + " — describe me\n# handcoded toolkit; runs in DarkTerm's shell\necho \"hello from " + name + "\"\n");
        return { out: "created " + path + " (edit it, then: tk build)\n" };
      }
      if (sub === "run") {
        var nm = args[1]; if (!nm) return { out: "", err: "usage: tk run <name> [args...]\n", code: 2 };
        return host.run(nm, args.slice(2));
      }
      if (sub === "help") {
        return { out: "tk — handcoded toolkit host\n" +
          "  tk list             list installed toolkits\n" +
          "  tk new <name>       scaffold ~/tools/<name>.tk\n" +
          "  tk cat <name>       print a toolkit's source\n" +
          "  tk build            install every *.tk as a shell function\n" +
          "  tk run <name> [a..] run a toolkit\n" };
      }
      return { out: "", err: "tk: unknown subcommand '" + sub + "' (try: tk help)\n", code: 2 };
    };
  }

  /* ------------------------------------------------------------ task command */
  function taskCommand(fallback) {
    return function (sh, args) {
      var ctx = ctxOf(sh, fallback);
      var tm = ctx.tasks, sync = ctx.sync, sub = args[0] || "list";
      function tagsOf(a) { return a.filter(function (x) { return /^[#+]\w/.test(x); }).map(function (x) { return x.slice(1); }); }
      if (sub === "add") {
        var title = args.slice(1).filter(function (x) { return !/^[#+]\w/.test(x) && !/^!\d$/.test(x); }).join(" ");
        var pr = 3; args.forEach(function (x) { if (/^!\d$/.test(x)) pr = Number(x.slice(1)); });
        if (!title) return { out: "", err: "usage: task add <title> [+tag] [!prio]\n", code: 2 };
        var t = tm.add(title, { prio: pr, tags: tagsOf(args.slice(1)) });
        return { out: "added " + t.id + ": " + t.title + "\n" };
      }
      if (sub === "list" || sub === "ls") {
        var f = {}, tag = tagsOf(args); if (tag[0]) f.tag = tag[0];
        if (args.indexOf("--done") >= 0) f.status = "done";
        var rows = sync.rank(tm.list(f));
        if (!rows.length) return { out: "  (no tasks)\n" };
        return { out: rows.map(function (r) {
          var mark = r.task.status === "done" ? "x" : " ";
          return "  [" + mark + "] " + r.task.id + "  " + r.task.title +
            "  #" + (r.task.tags.join(" #") || "") + "  !" + r.task.prio + "  sync=" + r.score.toFixed(2) + "\n";
        }).join("") };
      }
      if (sub === "do") { var t1 = tm.done(args[1]); if (!t1) return { out: "", err: "task: no such id " + args[1] + "\n", code: 1 }; sync.learn(t1, tm.list(), 1); return { out: "done " + t1.id + ": " + t1.title + "\n" }; }
      if (sub === "focus") { var t2 = tm.get(args[1]); if (!t2) return { out: "", err: "task: no such id " + args[1] + "\n", code: 1 }; sync.learn(t2, tm.list(), 1); return { out: "focus " + t2.id + "\n" }; }
      if (sub === "defer") { var t3 = tm.get(args[1]); if (!t3) return { out: "", err: "task: no such id " + args[1] + "\n", code: 1 }; sync.learn(t3, tm.list(), 0); return { out: "defer " + t3.id + "\n" }; }
      if (sub === "tag") {
        var t4 = tm.get(args[1]); if (!t4) return { out: "", err: "task: no such id " + args[1] + "\n", code: 1 };
        var add = args.slice(2).map(function (x) { return x.replace(/^#/, ""); }).filter(Boolean);
        if (!add.length) return { out: "", err: "usage: task tag <id> <tag...>\n", code: 2 };
        t4.tags = uniqA((t4.tags || []).concat(add));
        tm.update(t4.id, { tags: t4.tags });
        add.forEach(function (tg) { sync.tagWeights[tg] = clamp((sync.tagWeights[tg] || 0) + 0.05, -2, 2); });
        sync.ledger.resolveKey("coverage", t4.id);
        return { out: "tagged " + t4.id + ": #" + t4.tags.join(" #") + "\n" };
      }
      if (sub === "rm") { return tm.rm(args[1]) ? { out: "removed " + args[1] + "\n" } : { out: "", err: "task: no such id\n", code: 1 }; }
      if (sub === "next") {
        var open = tm.list({ status: "todo" }), rows2 = sync.rank(open);
        if (!rows2.length) return { out: "nothing open\n" };
        var top = rows2[0];
        return { out: "next → " + top.task.id + "  " + top.task.title + "  (sync " + top.score.toFixed(2) + ")\n" };
      }
      return { out: "", err: "task: unknown subcommand '" + sub + "' (try: task add|list|do|focus|defer|next|rm)\n", code: 2 };
    };
  }

  /* ------------------------------------------------------------ sync command */
  function syncCommand(fallback) {
    return function (sh, args) {
      var ctx = ctxOf(sh, fallback);
      var sync = ctx.sync, tm = ctx.tasks, sub = args[0] || "top";
      if (sub === "weights") {
        var w = sync.weights;
        return { out: Object.keys(w).sort(function (a, b) { return Math.abs(w[b]) - Math.abs(w[a]); }).map(function (k) {
          return "  " + (w[k] >= 0 ? "+" : "") + w[k].toFixed(3) + "  " + k + "\n";
        }).join("") };
      }
      if (sub === "why") {
        var t = tm.get(args[1]); if (!t) return { out: "", err: "sync: no such id " + args[1] + "\n", code: 1 };
        var r = sync.why(t, tm.list());
        var head = "  " + t.id + "  " + t.title + "  score=" + r.score.toFixed(3) + "\n";
        var body = r.contrib.map(function (c) { return "    " + (c.c >= 0 ? "+" : "") + c.c.toFixed(3) + "  " + c.feature + " (x=" + c.x.toFixed(2) + " × w=" + c.w.toFixed(3) + ")\n"; }).join("");
        return { out: head + (body || "    (no features fired)\n") };
      }
      if (sub === "explain") {
        return { out: "sync engine — a transparent weighted scorer: score = sigmoid(w · x).\n" +
          "It learns from your actions, and carries an honest deficit ledger. It never stubs\n" +
          "and never injects defects: anything it cannot sync becomes a named, actionable deficit.\n" +
          "  features: " + FEATURES.join(", ") + "\n" +
          "  sources: explicit (task do|focus|defer) + passive (every real command you type)\n" +
          "  sync top           open tasks ranked by learned priority\n" +
          "  sync weights       the learned feature weights\n" +
          "  sync why <id>      one task's feature contributions\n" +
          "  sync signals       what the observer extracts from your commands\n" +
          "  sync deficits      the open deficit ledger (what to work on)\n" +
          "  sync omega         the capability ladder toward the ceiling\n" +
          "  sync claim <id> <0|1>  reconcile a contradictory task\n" +
          "  sync reset         forget everything learned\n" };
      }
      if (sub === "signals") {
        var recent = sync.events.slice(-10).map(function (e) { return "  " + (e.via || "explicit") + "  →  " + e.id + "  label=" + e.label + "\n"; }).join("");
        return { out: "  observed: " + sync.stats.observed + "  unattributed: " + sync.stats.observed_unattributed +
          "  updates: " + sync.stats.updates + "\n" +
          "  prediction: " + sync.stats.predHits + "/" + sync.stats.predSamples + " recent hits\n" +
          "  learned tags: " + Object.keys(sync.tagWeights).sort().map(function (k) { return k + "=" + sync.tagWeights[k].toFixed(2); }).join(" ") + "\n" +
          "  recent evidence:\n" + (recent || "    (none yet — run some real commands)\n") };
      }
      if (sub === "deficits") {
        var open = sync.ledger.open();
        if (args[1] === "resolve") { var okr = sync.ledger.resolve(args[2]); return okr ? { out: "resolved " + args[2] + "\n" } : { out: "", err: "sync: no deficit " + args[2] + "\n", code: 1 }; }
        if (!open.length) return { out: "  no open deficits — the ledger is clear.\n" };
        return { out: open.map(function (d) {
          return "  " + d.id + "  [" + d.kind + "]  " + d.detail + "  (x" + d.count + ")\n      → " + d.suggestion + "\n";
        }).join("") };
      }
      if (sub === "omega") {
        var o = sync.omega(tm.list());
        return { out: "  omega ladder — " + o.level + "/" + o.max + " rungs met (" + o.percent + "%)\n" +
          o.rungs.map(function (r) { return "  " + (r.met ? "[x]" : "[ ]") + " " + r.name + " — " + r.desc + "\n"; }).join("") +
          (o.level < o.max ? "  unmet rungs are raised as deficits: see `sync deficits`\n" : "  ceiling reached: fully synced.\n") };
      }
      if (sub === "claim") {
        var t = tm.get(args[1]); if (!t) return { out: "", err: "sync: no such id " + args[1] + "\n", code: 1 };
        var label = args[2] === "0" ? 0 : 1;
        sync.learn(t, tm.list(), label, { reconcile: true, via: "claim" });
        return { out: "claimed " + t.id + " = " + label + " (contradiction reconciled)\n" };
      }
      if (sub === "reset") { sync.reset(); return { out: "sync: weights reset\n" }; }
      if (sub === "top") {
        var rows = sync.rank(tm.list({ status: "todo" }));
        if (!rows.length) return { out: "nothing open\n" };
        return { out: rows.slice(0, 10).map(function (r) {
          return "  " + r.score.toFixed(2) + "  " + r.task.id + "  " + r.task.title + "\n";
        }).join("") };
      }
      return { out: "", err: "sync: unknown subcommand '" + sub + "' (try: sync explain)\n", code: 2 };
    };
  }

  /* --------------------------------------------------------- store command */
  function storeCommand(fallback) {
    return function (sh, args) {
      var ctx = ctxOf(sh, fallback);
      var sub = args[0] || "status";
      if (sub === "status") return { out: "  home: " + HOME + "\n  tasks: " + (ctx.tasks.list().length) + "\n  toolkits: " + (ctx.tk.tools().length) + "\n  sync events: " + ctx.sync.events.length + "\n" };
      if (sub === "save") { ctx.save(); return { out: "snapshot saved\n" }; }
      if (sub === "reset") { ctx.reset(); return { out: "workspace reset to seed\n" }; }
      if (sub === "export") return { out: JSON.stringify(persist(ctx.fs, sh), null, 1) + "\n" };
      return { out: "", err: "store: unknown subcommand (status|save|reset|export)\n", code: 2 };
    };
  }

  /* -------------------------------------------------------------- installer
     Wire every toolkit into a live DarkTerm session. */
  function install(session, opts) {
    opts = opts || {};
    var sh = session.shell, fs = session.fs;
    var store = opts.store || makeStore("memory", "darkith.workspace");
    var syncStore = opts.syncStore || makeStore("memory", "darkith.sync");

    var snap = store.read();
    if (snap && !opts.fresh) restore(fs, sh, snap);
    else seedToolkits(fs);

    var ctx = { fs: fs, sh: sh, session: session, store: store };
    ctx.tasks = new TaskManager(sh);
    ctx.sync = new SyncEngine(syncStore);
    if (opts.fresh) ctx.sync.reset();
    ctx.tk = new TkHost(sh, session);
    ctx.save = function () { store.write(persist(fs, sh)); };
    ctx.reset = function () { seedToolkits(fs); store.write(persist(fs, sh)); };

    // every shell (and fork of it) resolves app commands against this context
    sh._dtctx = ctx;

    var DT = opts.DarkTerm || (root && root.DarkTerm) || (typeof module !== "undefined" && module.exports && null);
    if (DT && DT.registerCommand) {
      var wrapSave = function (fn) { return function (sh2, args, io) { var r = fn(sh2, args, io); try { ctxOf(sh2, ctx).save(); } catch (e) { /* persistence is best-effort */ } return r; }; };
      DT.registerCommand("task", wrapSave(taskCommand(ctx)));
      DT.registerCommand("sync", wrapSave(syncCommand(ctx)));
      DT.registerCommand("tk", wrapSave(tkCommand(ctx)));
      DT.registerCommand("store", storeCommand(ctx));
    }
    ctx.save();

    // build the seed toolkits so they are immediately runnable
    ctx.tk.build();

    // observe real command usage so the engine learns priorities passively.
    // the hook resolves the context per-shell (forks inherit _dtctx) and feeds
    // the sync engine; it must never break a command, so it is fully guarded.
    sh.onCommand = function (cmd, argv) {
      if (opts.onCommand) { try { opts.onCommand(cmd, argv); } catch (e) { /* observer must not throw */ } }
      try { ctx.sync.observe(cmd, argv, sh, ctx.tasks.list()); } catch (e) { /* never break a command */ }
    };

    // surface the capability ladder once at install, so unmet rungs are
    // already in the ledger for the operator to work.
    ctx.sync.omega(ctx.tasks.list());
    ctx.save();

    ctx.install = install;
    return ctx;
  }

  /* ------------------------------------------------------- seed toolkits
     Two handcoded tools demonstrate the model, written in DarkTerm's shell. */
  function seedToolkits(fs) {
    fs.mkdirp(TOOLDIR);
    fs.writeFile(TOOLDIR + "/standup.tk",
      "# @desc standup — one-screen status: open tasks ranked by synchronicity\n" +
      "echo '== now =='\n" +
      "date +%Y-%m-%d\n" +
      "echo '== next =='\n" +
      "task next\n" +
      "echo '== open =='\n" +
      "task list\n");
    fs.writeFile(TOOLDIR + "/triage.tk",
      "# @desc triage — list high-priority open work\n" +
      "task list | grep '!5' || echo 'nothing at !5'\n");
    fs.writeFile(TOOLDIR + "/overview.tk",
      "# @desc overview — task/toolkit/sync counters\n" +
      "store status\n");
    fs.mkdirp(TASKDIR);
    if (!fs.get(TASKDIR + "/t1.task")) {
      var tm = new TaskManager({ fs: fs });
      tm.add("wire task manager into inscriber", { prio: 5, tags: ["darkith", "shell"] });
      tm.add("teach the synchronicity engine my priorities", { prio: 4, tags: ["sync"] });
      tm.add("write a standup toolkit", { prio: 3, tags: ["tools"] });
      tm.add("tidy the toolkit host docs", { prio: 2, tags: ["docs"] });
    }
  }

  return {
    version: VERSION,
    install: install,
    makeStore: makeStore,
    persist: persist,
    restore: restore,
    TaskManager: TaskManager,
    SyncEngine: SyncEngine,
    TkHost: TkHost,
    FEATURES: FEATURES,
    TASKDIR: TASKDIR,
    TOOLDIR: TOOLDIR
  };
});
