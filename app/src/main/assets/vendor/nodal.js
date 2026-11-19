/* nodal.js — Auto-Nodal Co-ordina-Sync, as a runtime engine (the SAVF twin of nodal/*.py).
 *
 * Every law the Python package enforces on source bytes, this enforces at runtime, in the
 * WebView, offline, with no build step and no dependency. The Python is the authority; this
 * is its universally frontend webview html friendly accompaniment coupling, and
 * tools/nodal_gate.py proves the two agree on the same scenarios.
 *
 * The laws, unchanged:
 *   - No undefined pass. A DEGRADED verdict without a named class cannot be constructed, so
 *     "unknown" can never read as "allow".
 *   - No contradictory receipt. A non-DEGRADED verdict may not carry a degraded class.
 *   - Content addressing. A receipt's id is the sha256 of its own bytes.
 *   - Per-lane hash chain from a fixed GENESIS anchor; the ledger computes the witness, so a
 *     caller cannot forge ancestry, and truncation is detectable.
 *   - Upstream existence. A non-degraded receipt citing an absent upstream is refused; the
 *     honest answer is DEGRADED/UPSTREAM_MISSING.
 *   - Read barrier. readAsof(E) sees only epochs strictly below E, so every bot in epoch E
 *     sees one frozen view.
 *   - Append-only. update/delete are refused at the API, and the log is frozen per entry.
 *   - Total function. fire() always returns a result; a throwing decide() becomes
 *     DEGRADED/INTERNAL_ERROR, a missing upstream becomes DEGRADED/UPSTREAM_MISSING. Never a
 *     wait, never a throw to the caller.
 *   - Deterministic order. computeFireOrder() rejects cycles (Tarjan SCC) and breaks ties by
 *     sha256(engineId||epoch), so the same inputs always give the same order.
 *   - Coordination. reconcile() names both clauses when receipts disagree; propagateDegraded()
 *     marks receipts that consumed degraded input.
 *
 * UMD-ish: browser global `Nodal`; Node module.
 */
;(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.Nodal = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var GENESIS_SEED = 'DARKITH_NODAL_GENESIS_v1';
  var LAW = 'no undefined pass; every gate is a total function; order is precomputed, never negotiated';

  // ---------------------------------------------------------------- sha256 (sync, no deps)
  // A dependency-free SHA-256 so the engine runs in any WebView with no async crypto and no
  // polyfill. Byte-for-byte the same digest the Python hashlib produces.
  var K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  function utf8Bytes(str) {
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
      else if (c < 0xd800 || c >= 0xe000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
      else {
        i++;
        var cp = 0x10000 + (((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
        out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
      }
    }
    return out;
  }

  function sha256(str) {
    var bytes = utf8Bytes(str);
    var h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var l = bytes.length;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) bytes.push(0);
    var bits = l * 8;
    for (var i = 7; i >= 0; i--) bytes.push((bits / Math.pow(2, i * 8)) & 0xff);

    var w = new Array(64);
    for (var off = 0; off < bytes.length; off += 64) {
      for (var t = 0; t < 16; t++) {
        w[t] = (bytes[off + t * 4] << 24) | (bytes[off + t * 4 + 1] << 16) |
               (bytes[off + t * 4 + 2] << 8) | bytes[off + t * 4 + 3];
      }
      for (t = 16; t < 64; t++) {
        var s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3);
        var s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10);
        w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
      }
      var a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
      for (t = 0; t < 64; t++) {
        var S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        var ch = (e & f) ^ (~e & g);
        var t1 = (hh + S1 + ch + K[t] + w[t]) | 0;
        var S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + maj) | 0;
        hh = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0;
      h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
    }
    return h.map(function (x) { return ('00000000' + (x >>> 0).toString(16)).slice(-8); }).join('');
  }

  function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }

  var GENESIS_WITNESS = sha256(GENESIS_SEED);

  // ---------------------------------------------------------------- schema
  var Verdict = { ALLOW: 'allow', DENY: 'deny', ROUTE: 'route', OBSERVE: 'observe', DEGRADED: 'degraded' };
  var DegradedClass = {
    UPSTREAM_MISSING: 'upstream_missing',
    UPSTREAM_STALE: 'upstream_stale',
    STALE_EPOCH: 'stale_epoch',
    INTERNAL_ERROR: 'internal_error',
    POLICY_MISSING: 'policy_missing',
    DOWNSTREAM_OF_DEGRADED: 'downstream_of_degraded'
  };

  function SchemaViolation(msg) {
    var e = new Error(msg);
    e.name = 'SchemaViolation';
    return e;
  }

  var VERDICT_VALUES = Object.keys(Verdict).map(function (k) { return Verdict[k]; });
  var CLASS_VALUES = Object.keys(DegradedClass).map(function (k) { return DegradedClass[k]; });

  function receiptId(r) {
    return sha256(
      r.engineId + '|' + r.boundary + '|' + r.epoch + '|' + r.seq + '|' + r.lane + '|' +
      r.inputHash + '|' + r.verdict + '|' + r.clause + '|' +
      (r.degradedClass || '') + '|' +
      (r.upstreamIds || []).slice().sort().join(',') + '|' + (r.policyVersion || 'v0') + '|' +
      (r.witness || '') + '|' + (r.tWallNs || 0)
    );
  }

  function makeReceipt(spec) {
    var r = {
      engineId: spec.engineId,
      boundary: spec.boundary,
      epoch: spec.epoch,
      seq: spec.seq,
      lane: spec.lane,
      inputHash: spec.inputHash,
      verdict: spec.verdict,
      clause: spec.clause,
      degradedClass: spec.degradedClass || null,
      upstreamIds: (spec.upstreamIds || []).slice(),
      policyVersion: spec.policyVersion || 'v0',
      witness: spec.witness || '',
      tWallNs: spec.tWallNs || 0
    };

    if (!r.engineId || !r.boundary || !r.clause) throw SchemaViolation('engineId, boundary, and clause are required and non-empty');
    if (!r.lane) throw SchemaViolation('lane is required and non-empty');
    if (!(r.epoch >= 0)) throw SchemaViolation('epoch must be a non-negative int, got ' + r.epoch);
    if (!(r.seq >= 0)) throw SchemaViolation('seq must be a non-negative int, got ' + r.seq);
    if (VERDICT_VALUES.indexOf(r.verdict) < 0) throw SchemaViolation('verdict must be a known Verdict, got ' + r.verdict);
    if (r.verdict === Verdict.DEGRADED && !r.degradedClass) {
      throw SchemaViolation('DEGRADED verdict requires a non-null degradedClass -- a degraded receipt with no named class is exactly the undefined-pass failure this schema exists to prevent.');
    }
    if (r.verdict !== Verdict.DEGRADED && r.degradedClass) {
      throw SchemaViolation('verdict=' + r.verdict + ' must not carry a degradedClass (got ' + r.degradedClass + '); degradedClass is reserved for verdict=degraded.');
    }
    if (r.degradedClass && CLASS_VALUES.indexOf(r.degradedClass) < 0) {
      throw SchemaViolation('unknown degradedClass: ' + r.degradedClass);
    }

    Object.defineProperty(r, 'receiptId', { value: receiptId(r), enumerable: true });
    Object.freeze(r.upstreamIds);
    return Object.freeze(r);
  }

  // ---------------------------------------------------------------- ledger
  // In-memory, append-only. Entries are frozen; the API has no update or delete at all, so
  // the only way to change history is to stop using the ledger — which is visible.
  function Ledger() {
    if (!(this instanceof Ledger)) return new Ledger();
    this._rows = [];          // insertion order
    this._byId = {};          // receiptId -> row
    this._laneHead = {};      // lane -> last receiptId
    this._laneMaxEpoch = {};  // lane -> highest epoch seen
  }

  Ledger.prototype._exists = function (id) { return !!this._byId[id]; };

  Ledger.prototype.append = function (draft) {
    var head = this._laneHead[draft.lane];
    var realWitness = head !== undefined ? head : GENESIS_WITNESS;

    var maxEpoch = this._laneMaxEpoch[draft.lane];
    if (maxEpoch !== undefined && draft.epoch < maxEpoch && draft.verdict !== Verdict.DEGRADED) {
      return { accepted: false, receiptId: null, reason: 'stale epoch: ' + draft.epoch + ' < lane high-water ' + maxEpoch + ' on ' + draft.lane + '; a stale writer may only append a degraded receipt', receipt: null };
    }

    var final;
    try {
      final = makeReceipt({
        engineId: draft.engineId, boundary: draft.boundary, epoch: draft.epoch, seq: draft.seq,
        lane: draft.lane, inputHash: draft.inputHash, verdict: draft.verdict, clause: draft.clause,
        degradedClass: draft.degradedClass, upstreamIds: draft.upstreamIds,
        policyVersion: draft.policyVersion, witness: realWitness, tWallNs: draft.tWallNs
      });
    } catch (e) {
      return { accepted: false, receiptId: null, reason: String(e.message || e), receipt: null };
    }

    if (final.verdict !== Verdict.DEGRADED) {
      var missing = final.upstreamIds.filter(function (u) { return !this._byId[u]; }, this);
      if (missing.length) {
        return { accepted: false, receiptId: null, reason: 'upstream_ids not found in ledger: ' + JSON.stringify(missing) + '. Fire a DEGRADED/UPSTREAM_MISSING receipt instead of citing evidence that does not exist.', receipt: null };
      }
    }

    for (var i = 0; i < this._rows.length; i++) {
      if (this._rows[i].lane === final.lane && this._rows[i].seq === final.seq) {
        return { accepted: false, receiptId: null, reason: 'integrity error (duplicate seq in lane)', receipt: null };
      }
    }

    this._rows.push(final);
    this._byId[final.receiptId] = final;
    this._laneHead[final.lane] = final.receiptId;
    if (maxEpoch === undefined || final.epoch > maxEpoch) this._laneMaxEpoch[final.lane] = final.epoch;
    return { accepted: true, receiptId: final.receiptId, reason: null, receipt: final };
  };

  Ledger.prototype.readAsof = function (epoch, lane) {
    return this._rows.filter(function (r) {
      return r.epoch < epoch && (lane === undefined || r.lane === lane);
    }).slice();
  };

  Ledger.prototype.get = function (id) { return this._byId[id] || null; };
  Ledger.prototype.laneReceipts = function (lane) {
    return this._rows.filter(function (r) { return r.lane === lane; })
      .sort(function (a, b) { return a.seq - b.seq; });
  };
  Ledger.prototype.lanes = function () {
    var seen = {}, out = [];
    this._rows.forEach(function (r) { if (!seen[r.lane]) { seen[r.lane] = 1; out.push(r.lane); } });
    return out.sort();
  };
  Ledger.prototype.count = function () { return this._rows.length; };

  Ledger.prototype.verifyChain = function (lane) {
    var problems = [];
    var prevId = GENESIS_WITNESS;
    this.laneReceipts(lane).forEach(function (r) {
      var recomputed = receiptId({
        engineId: r.engineId, boundary: r.boundary, epoch: r.epoch, seq: r.seq, lane: r.lane,
        inputHash: r.inputHash, verdict: r.verdict, clause: r.clause, degradedClass: r.degradedClass,
        upstreamIds: r.upstreamIds, policyVersion: r.policyVersion, witness: prevId, tWallNs: r.tWallNs
      });
      if (r.witness !== prevId) problems.push('lane=' + lane + ' seq=' + r.seq + ': witness=' + r.witness + ' but expected ' + prevId);
      if (recomputed !== r.receiptId) problems.push('lane=' + lane + ' seq=' + r.seq + ': content hash mismatch (stored ' + r.receiptId.slice(0, 12) + ', recomputed ' + recomputed.slice(0, 12) + ')');
      prevId = r.receiptId;
    });
    return problems;
  };

  Ledger.prototype.verifyAll = function () {
    var self = this, problems = [];
    this.lanes().forEach(function (l) { problems = problems.concat(self.verifyChain(l)); });
    return problems;
  };

  // ---------------------------------------------------------------- bot
  function hashInput(obj) {
    var s;
    try { s = JSON.stringify(obj); } catch (e) { s = String(obj); }
    return sha256(s === undefined ? 'undefined' : s);
  }

  function NodalBot(ledger, opts) {
    if (!(this instanceof NodalBot)) return new NodalBot(ledger, opts);
    opts = opts || {};
    this.ledger = ledger;
    this.lane = opts.lane || this.engineId;
    this.upstreamEngineIds = opts.upstreamEngineIds || [];
    var rows = ledger.laneReceipts(this.lane);
    this._seq = rows.length ? rows[rows.length - 1].seq + 1 : 0;
  }

  NodalBot.prototype.engineId = 'unnamed';
  NodalBot.prototype.boundary = 'unnamed.boundary';
  NodalBot.prototype.policyVersion = 'v0';

  // Subclasses override decide(inputObj, upstreamRows) -> {verdict, clause, degradedClass}.
  NodalBot.prototype.decide = function () {
    throw new Error('decide() not implemented');
  };

  NodalBot.prototype.fire = function (inputObj, epoch, upstreamIds) {
    upstreamIds = upstreamIds || [];
    var visible = {};
    this.ledger.readAsof(epoch).forEach(function (r) { visible[r.receiptId] = r; });

    var upstreamRows = [], missing = [];
    upstreamIds.forEach(function (uid) {
      if (visible[uid]) upstreamRows.push(visible[uid]);
      else missing.push(uid);
    });

    var inputH = hashInput(inputObj);
    var seq = this._seq++;
    var base = {
      engineId: this.engineId, boundary: this.boundary, epoch: epoch, seq: seq, lane: this.lane,
      inputHash: inputH, upstreamIds: upstreamIds, policyVersion: this.policyVersion,
      tWallNs: Date.now() * 1e6
    };

    if (missing.length) {
      base.verdict = Verdict.DEGRADED;
      base.clause = this.engineId + '.missing_upstream';
      base.degradedClass = DegradedClass.UPSTREAM_MISSING;
      return this._commit(base, null, upstreamRows);
    }

    var out;
    try {
      out = this.decide(inputObj, upstreamRows) || {};
    } catch (err) {
      base.verdict = Verdict.DEGRADED;
      base.clause = this.engineId + '.internal_error';
      base.degradedClass = DegradedClass.INTERNAL_ERROR;
      return this._commit(base, String(err && err.stack || err), upstreamRows);
    }

    base.verdict = out.verdict;
    base.clause = out.clause;
    base.degradedClass = out.degradedClass || null;
    return this._commit(base, null, upstreamRows);
  };

  NodalBot.prototype._commit = function (spec, traceback, upstreamRows) {
    var draft;
    try {
      draft = makeReceipt(spec);
    } catch (e) {
      // The schema refused the verdict (e.g. a decide() that returned DEGRADED with no
      // class). That is still a decision, so it still becomes a receipt: never a throw.
      draft = makeReceipt({
        engineId: spec.engineId, boundary: spec.boundary, epoch: spec.epoch, seq: spec.seq,
        lane: spec.lane, inputHash: spec.inputHash, verdict: Verdict.DEGRADED,
        clause: spec.engineId + '.internal_error',
        degradedClass: DegradedClass.INTERNAL_ERROR, upstreamIds: spec.upstreamIds,
        policyVersion: spec.policyVersion, tWallNs: spec.tWallNs
      });
      traceback = traceback || String(e.message || e);
    }
    var res = this.ledger.append(draft);
    return {
      accepted: res.accepted,
      receiptId: res.receiptId,
      reason: res.reason,
      receipt: res.receipt || draft,
      traceback: traceback,
      upstreamRows: upstreamRows,
      get verdict() { return (res.receipt || draft).verdict; }
    };
  };

  // ---------------------------------------------------------------- Co-ordina-Sync
  function computeFireOrder(registrations, epochId) {
    var ids = {}, list = [];
    registrations.forEach(function (r) {
      if (ids[r.engineId]) throw new Error('FireOrderViolation: engine ' + r.engineId + ' registered twice');
      ids[r.engineId] = true;
      list.push(r.engineId);
    });
    list.sort();

    var graph = {};
    list.forEach(function (id) { graph[id] = []; });
    registrations.forEach(function (r) {
      (r.upstreamEngineIds || []).forEach(function (up) {
        if (!ids[up]) throw new Error('FireOrderViolation: engine ' + r.engineId + ' declares upstream ' + up + ' which is not registered');
        if (graph[up].indexOf(r.engineId) < 0) graph[up].push(r.engineId);
      });
    });

    // Tarjan SCC — cycles are rejected before runtime, not discovered mid-fire.
    var index = 0, stack = [], idx = {}, low = {}, onStack = {}, sccs = [];
    function strongconnect(v) {
      idx[v] = low[v] = index++;
      stack.push(v); onStack[v] = true;
      graph[v].slice().sort().forEach(function (w) {
        if (idx[w] === undefined) { strongconnect(w); low[v] = Math.min(low[v], low[w]); }
        else if (onStack[w]) { low[v] = Math.min(low[v], idx[w]); }
      });
      if (low[v] === idx[v]) {
        var scc = [];
        for (;;) {
          var w = stack.pop(); onStack[w] = false; scc.push(w);
          if (w === v) break;
        }
        sccs.push(scc);
      }
    }
    list.forEach(function (v) { if (idx[v] === undefined) strongconnect(v); });
    sccs.forEach(function (scc) {
      if (scc.length > 1) throw new Error('FireOrderViolation: dependency cycle detected: ' + JSON.stringify(scc.sort()));
    });

    var inDeg = {};
    list.forEach(function (id) { inDeg[id] = 0; });
    Object.keys(graph).forEach(function (u) { graph[u].forEach(function (d) { inDeg[d]++; }); });

    function tiebreak(id) { return sha256(id + '||' + epochId); }

    var ready = list.filter(function (id) { return inDeg[id] === 0; }).sort(function (a, b) { return tiebreak(a) < tiebreak(b) ? -1 : 1; });
    var order = [];
    while (ready.length) {
      var v = ready.shift();
      order.push(v);
      graph[v].slice().sort(function (a, b) { return tiebreak(a) < tiebreak(b) ? -1 : 1; }).forEach(function (w) {
        if (--inDeg[w] === 0) ready.push(w);
      });
      ready.sort(function (a, b) { return tiebreak(a) < tiebreak(b) ? -1 : 1; });
    }
    if (order.length !== list.length) throw new Error('FireOrderViolation: topological sort failed despite an acyclic SCC check');
    return order;
  }

  function reconcile(receipts, precedence) {
    if (!receipts.length) return { agreed: true, canonicalId: null, derivativeIds: [], clause: 'coordina.reconcile.empty', reason: 'no receipts to reconcile' };
    var rank = {};
    precedence.forEach(function (e, i) { rank[e] = i; });
    var unknown = receipts.filter(function (r) { return rank[r.engineId] === undefined; }).map(function (r) { return r.engineId; });
    if (unknown.length) {
      return {
        agreed: false, canonicalId: null,
        derivativeIds: receipts.map(function (r) { return r.receiptId; }),
        clause: 'coordina.reconcile.unranked',
        reason: 'engines ' + JSON.stringify(unknown.filter(function (v, i, a) { return a.indexOf(v) === i; }).sort()) + ' produced receipts but are not in the precomputed precedence; the order is not defined, so no receipt is canonical'
      };
    }
    var ordered = receipts.slice().sort(function (a, b) {
      return (rank[a.engineId] - rank[b.engineId]) || (a.epoch - b.epoch) || (a.seq - b.seq);
    });
    var canonical = ordered[0];
    var derivatives = ordered.slice(1).map(function (r) { return r.receiptId; });
    var disagreeing = ordered.slice(1).filter(function (r) { return r.verdict !== canonical.verdict; });
    if (disagreeing.length) {
      var named = disagreeing.map(function (r) { return r.engineId + ':' + r.clause + '=' + r.verdict; }).join(', ');
      return {
        agreed: false, canonicalId: canonical.receiptId, derivativeIds: derivatives,
        clause: 'coordina.reconcile.divergent',
        reason: 'canonical ' + canonical.engineId + ':' + canonical.clause + '=' + canonical.verdict + ' is contradicted by ' + named + '; canonical wins by precomputed precedence'
      };
    }
    return {
      agreed: true, canonicalId: canonical.receiptId, derivativeIds: derivatives,
      clause: 'coordina.reconcile.agreed',
      reason: ordered.length + ' receipts agree; ' + canonical.engineId + ' is canonical'
    };
  }

  function propagateDegraded(receipt, upstreamRows) {
    var tainted = (upstreamRows || []).filter(function (row) { return row.verdict === Verdict.DEGRADED; });
    if (tainted.length) {
      return { verdict: Verdict.DEGRADED, clause: receipt.engineId + '.downstream_of_degraded', degradedClass: DegradedClass.DOWNSTREAM_OF_DEGRADED };
    }
    return { verdict: receipt.verdict, clause: receipt.clause, degradedClass: receipt.degradedClass || null };
  }

  return {
    LAW: LAW,
    GENESIS_WITNESS: GENESIS_WITNESS,
    Verdict: Verdict,
    DegradedClass: DegradedClass,
    SchemaViolation: SchemaViolation,
    sha256: sha256,
    makeReceipt: makeReceipt,
    receiptId: receiptId,
    Ledger: Ledger,
    NodalBot: NodalBot,
    hashInput: hashInput,
    computeFireOrder: computeFireOrder,
    reconcile: reconcile,
    propagateDegraded: propagateDegraded
  };
});
