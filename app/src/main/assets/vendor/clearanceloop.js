/* ClearanceLoop — the Homeokinetic Debt Ratchet, as a runtime engine.
 *
 * One law, the same one tools/source_inspector.py proves on source bytes: health
 * is a RATE of clearance, not a static tolerance. Debt (friction) is measured per
 * class; the per-class high-water mark (HWM) may only ever move DOWN; any class
 * above its HWM is a net addition of debt = a regression = FAIL; debt that does
 * not flux downward over a delivery window is FORCE-DEGRADED to a blocker; a rise
 * is permitted only by a recorded, reasoned, time-boxed waiver.
 *
 * This is the runtime half of the pair: the pre-runner produces diagnostic truth
 * (errors, long tasks), ClearanceLoop turns that truth into a clearance verdict and
 * refuses to let the number settle. `absorb(report)` closes the loop between them.
 *
 * Offline, dependency-free, OS-agnostic: it runs in any browser or WebView, and in
 * Node it degrades to a pure function (no DOM, no storage).
 *
 * UMD-ish: browser global `ClearanceLoop`; Node module.
 */
;(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(root);
  else root.ClearanceLoop = factory(root);
})(typeof self !== 'undefined' ? self : this, function (root) {
  'use strict';

  var CLASSES = ['switching', 'waiting', 'searching', 'correcting', 'review'];
  var WINDOW = 5;                 // deliveries of non-clearance before force-degradation
  var WAIVER = 5;                 // a waiver's budget: it expires after this many deliveries
  var KEY = 'darkith.clearanceloop.v1';
  var LAW = 'homeokinesis: debt may only flux downward; stasis is force-degraded';

  /* Resolve the actual global. `root` is the UMD receiver, which is `module.exports`
     under CommonJS — it carries no localStorage. Using it directly would make storage
     silently dead everywhere except a browser, so the ratchet would reset on every
     reload and the law could never hold across sessions. */
  var G = (typeof globalThis !== 'undefined') ? globalThis : root;
  var store = function () { try { return G && G.localStorage; } catch (e) { return null; } };
  /* A waiver is {reason, at, expires}. Older builds stored a bare reason string, which
     carried no expiry and so granted permanent immunity. Such a record is normalised to
     an ALREADY-EXPIRED waiver: the operator must re-justify. Failing closed here is the
     only safe direction — a stale waiver must never silently keep hiding a regression. */
  function normWaiver(w) {
    if (!w) return null;
    if (typeof w === 'string') return { reason: w, at: 0, expires: 0 };
    if (typeof w === 'object') return { reason: String(w.reason || 'waiver'), at: w.at || 0, expires: w.expires || 0 };
    return null;
  }
  /* Any state that reaches us from storage, a file or another build is untrusted:
     it may be truncated, hand-edited or written by an older schema. Every field is
     rebuilt from scratch so a missing or hostile value can only ever cost history,
     never throw. A ratchet that cannot read its own file must still run. */
  function normState(st) {
    var out = { hwm: {}, justified: {}, since: {}, delivery: 0, history: [] }, k, v;
    if (!st || typeof st !== 'object' || Array.isArray(st)) return out;
    if (st.state && typeof st.state === 'object') st = st.state;   // wrapped {state, report}
    for (k in (st.hwm || {})) {
      if (!Object.prototype.hasOwnProperty.call(st.hwm, k)) continue;
      v = Number(st.hwm[k]);
      if (isFinite(v) && v >= 0) out.hwm[k] = Math.floor(v);
    }
    for (k in (st.since || {})) {
      if (!Object.prototype.hasOwnProperty.call(st.since, k)) continue;
      v = Number(st.since[k]);
      if (isFinite(v) && v >= 0) out.since[k] = Math.floor(v);
    }
    for (k in (st.justified || {})) {
      if (!Object.prototype.hasOwnProperty.call(st.justified, k)) continue;
      var nw = normWaiver(st.justified[k]);
      if (nw) out.justified[k] = nw;
    }
    v = Number(st.delivery);
    out.delivery = isFinite(v) && v > 0 ? Math.floor(v) : 0;
    if (Array.isArray(st.history)) {
      out.history = st.history.filter(function (h) {
        return h && typeof h === 'object' && isFinite(Number(h.score));
      }).map(function (h) {
        return { delivery: Number(h.delivery) || 0, now: h.now && typeof h.now === 'object' ? h.now : {}, score: Number(h.score) };
      }).slice(-40);
    }
    return out;
  }
  function load() {
    try {
      var j = store() && store().getItem(KEY); if (!j) return null;
      var st = JSON.parse(j);
      if (!st || typeof st !== 'object') return null;
      return normState(st);
    } catch (e) { return null; }
  }
  var persist = function (st) { try { var s = store(); if (s) s.setItem(KEY, JSON.stringify(st)); } catch (e) { /* file:// may deny storage; memory still holds */ } };
  var cp = function (o) { var r = {}; for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) r[k] = o[k]; return r; };

  var state = load() || { hwm: {}, justified: {}, since: {}, delivery: 0, history: [] };
  var acc = {};                    // friction accrued since the last delivery
  var hooks = false;

  function bump(cls, n) { acc[cls] = (acc[cls] || 0) + (n == null ? 1 : n); }

  /* Real, offline signals — no self-report. Every hook is guarded: a missing API
     costs a signal, never an exception. */
  function install() {
    if (hooks || typeof window === 'undefined' || !window.addEventListener) return;
    hooks = true;
    var d = window.document;
    window.addEventListener('blur', function () { bump('switching'); });
    window.addEventListener('focus', function () { bump('switching'); });
    if (d && d.addEventListener) d.addEventListener('visibilitychange', function () { bump('switching'); });
    window.addEventListener('hashchange', function () { bump('searching'); });
    window.addEventListener('error', function () { bump('correcting'); });
    window.addEventListener('unhandledrejection', function () { bump('correcting'); });
    try {
      if (window.PerformanceObserver) {
        new window.PerformanceObserver(function (l) {
          var e = l.getEntries(); for (var i = 0; i < e.length; i++) bump('waiting');
        }).observe({ entryTypes: ['longtask'] });
      }
    } catch (e) { /* not all engines expose longtask */ }
  }

  function sample() { var o = {}; for (var i = 0; i < CLASSES.length; i++) o[CLASSES[i]] = acc[CLASSES[i]] || 0; return o; }
  function score(now) { var s = 0; for (var i = 0; i < CLASSES.length; i++) s += now[CLASSES[i]] || 0; return s; }

  /* Absorb a pre-runner report: its errors and long tasks are friction debt. */
  function absorb(report) {
    if (!report) return acc;
    var m = report.metrics || {};
    bump('waiting', m.longTasks || 0);
    bump('correcting', (report.errors || []).length);
    return acc;
  }

  function observe(partial) {
    if (partial) for (var k in partial) if (Object.prototype.hasOwnProperty.call(partial, k) && CLASSES.indexOf(k) >= 0) acc[k] = partial[k];
    return acc;
  }

  /* One delivery: apply the law, advance the HWM, report events + degradations. */
  function advance(justify) {
    install();
    var now = sample();
    var hwm = cp(state.hwm), since = cp(state.since), justified = cp(state.justified);
    var events = [], expired = [], i, cls, n, prev, w;

    /* Expire first: a waiver's budget is a fixed number of deliveries, never forever. */
    for (cls in justified) {
      if (!Object.prototype.hasOwnProperty.call(justified, cls)) continue;
      if ((state.delivery || 0) >= justified[cls].expires) {
        events.push('EXPIRED waiver ' + cls + ' (' + justified[cls].reason + '): the apoptotic exception ended');
        expired.push(cls);
        delete justified[cls];
      }
    }

    for (i = 0; i < CLASSES.length; i++) {
      cls = CLASSES[i]; n = now[cls] || 0;
      if (!(cls in hwm)) { hwm[cls] = n; since[cls] = 0; events.push('seeded ' + cls + ': HWM ' + n); continue; }
      prev = hwm[cls];
      if (n < prev) { events.push('cleared ' + cls + ': ' + prev + ' -> ' + n + ' (flux down)'); hwm[cls] = n; since[cls] = 0; }
      else if (n === prev) { since[cls] = (since[cls] || 0) + 1; }
      else if (justify) {
        /* A waiver permits the debt to EXIST for a bounded window; it never raises the
           HWM. Raising it would loosen the gate permanently, and the ratchet only ever
           tightens. The class keeps reporting above its HWM, so the moment the waiver
           expires the debt is a plain regression again — nothing was ever forgiven. */
        justified[cls] = { reason: String(justify), at: (state.delivery || 0), expires: (state.delivery || 0) + WAIVER };
        events.push('JUSTIFIED waiver ' + cls + ': ' + prev + ' -> ' + n + ' for ' + WAIVER + ' deliveries (' + justify + '); HWM stays ' + prev);
        since[cls] = 0;
      }
      /* else: net addition left in place; the HWM is NOT raised and the verdict fails. */
    }
    for (cls in hwm) {
      if (Object.prototype.hasOwnProperty.call(hwm, cls) && (now[cls] || 0) === 0 && hwm[cls] !== 0) {
        events.push('cleared ' + cls + ': ' + hwm[cls] + ' -> 0 (flux down)'); hwm[cls] = 0; since[cls] = 0;
      }
    }
    var degraded = [];
    for (cls in since) {
      if (Object.prototype.hasOwnProperty.call(since, cls) && (now[cls] || 0) > 0 && since[cls] >= WINDOW && !justified[cls]) degraded.push(cls);
    }

    var delivery = (state.delivery || 0) + 1;
    state = {
      hwm: hwm, justified: justified, since: since, delivery: delivery,
      history: (state.history || []).concat([{ delivery: delivery, now: now, score: score(now) }]).slice(-40)
    };
    acc = {}; persist(state);
    return { events: events, degraded: degraded, expired: expired, now: now, delivery: delivery };
  }

  function last() { var h = state.history || []; return h.length ? h[h.length - 1] : null; }
  function flux() { var h = state.history || []; if (h.length < 2) return 0; return h[h.length - 1].score - h[h.length - 2].score; }

  function report() {
    var now = (last() && last().now) || sample();
    var classes = [], outstanding = 0, i, cls, n, h, since, status, w, left;
    for (i = 0; i < CLASSES.length; i++) {
      cls = CLASSES[i]; n = now[cls] || 0; h = (state.hwm || {})[cls] == null ? n : state.hwm[cls]; since = (state.since || {})[cls] || 0;
      w = (state.justified || {})[cls] || null;
      /* A waiver that has outlived its budget is dead even before the next advance()
         sweeps it, so the report can never show a live waiver past its expiry. */
      if (w && (state.delivery || 0) >= w.expires) w = null;
      left = w ? Math.max(0, w.expires - (state.delivery || 0)) : 0;
      status = 'clear';
      if (n > h && !w) status = 'regression';
      else if (n > 0 && since >= WINDOW && !w) status = 'stale';
      else if (n > 0) status = w ? 'waived' : 'tracked';
      if (n > 0) outstanding += n;
      classes.push({ cls: cls, now: n, hwm: h, since: since, waived: !!w,
                     reason: w ? w.reason : null, expires: w ? w.expires : null, remaining: left, status: status });
    }
    var regress = [], stale = [];
    for (i = 0; i < classes.length; i++) { if (classes[i].status === 'regression') regress.push(classes[i].cls); if (classes[i].status === 'stale') stale.push(classes[i].cls); }
    var v, reason;
    if (regress.length) { v = 'FAIL'; reason = 'net addition of debt: ' + regress.join(', '); }
    else if (stale.length) { v = 'FAIL'; reason = 'stasis force-degraded to blocker: ' + stale.join(', '); }
    else if (outstanding > 0 && flux() === 0) { v = 'WARN'; reason = 'stasis: debt outstanding and not clearing'; }
    else { v = 'PASS'; reason = outstanding ? 'debt fluxing down' : 'no friction debt'; }
    return { law: LAW, verdict: v, reason: reason, flux: flux(), delivery: state.delivery || 0, outstanding: outstanding, window: WINDOW, classes: classes };
  }

  function reset() { state = { hwm: {}, justified: {}, since: {}, delivery: 0, history: [] }; acc = {}; persist(state); return state; }

  /* Adopt a previously exported state. This is how a ratchet travels between machines
     and how the in-app self-test exercises the law without destroying live history.
     Unknown/legacy waiver shapes normalise through the same fail-closed path as load(). */
  function restore(st) {
    if (typeof st === 'string') { try { st = JSON.parse(st); } catch (e) { return false; } }
    if (!st || typeof st !== 'object') return false;
    state = normState(st);
    acc = {}; persist(state);
    return true;
  }

  /* ---------- UI: a self-contained, sleek ratchet report ---------- */
  var VC = { PASS: '#3fb950', WARN: '#d29922', FAIL: '#f85149' };
  function el(tag, css, txt) { var e = document.createElement(tag); if (css) e.style.cssText = css; if (txt != null) e.textContent = txt; return e; }
  function ui() {
    if (typeof document === 'undefined') return report();
    var r = report();
    var host = el('div', 'position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:14px;background:rgba(3,4,7,.82);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#e8edf3');
    var card = el('div', 'width:min(600px,96vw);max-height:92vh;overflow:auto;background:#0b0c0e;border:1px solid #262a31;border-radius:14px;box-shadow:0 24px 60px rgba(0,0,0,.6)');
    host.appendChild(card); document.body.appendChild(host);
    var close = function () { if (host.parentNode) host.remove(); };
    host.addEventListener('click', function (e) { if (e.target === host) close(); });
    var head = el('div', 'display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid #1b1f25;position:sticky;top:0;background:#0b0c0e');
    head.appendChild(el('span', 'color:#7ee787;font-weight:700', '\u25c9 ClearanceLoop'));
    head.appendChild(el('span', 'padding:2px 9px;border-radius:999px;font-weight:700;font-size:12px;color:#05070a;background:' + (VC[r.verdict] || '#8b949e'), r.verdict));
    var x = el('button', 'margin-left:auto;background:transparent;border:0;color:#8b949e;font-size:16px;cursor:pointer', '\u2715');
    x.addEventListener('click', close); head.appendChild(x); card.appendChild(head);
    var body = el('div', 'padding:12px 14px'); card.appendChild(body);
    body.appendChild(el('div', 'color:#8b949e;margin-bottom:10px', r.reason + ' \u00b7 flux ' + r.flux + ' \u00b7 delivery ' + r.delivery));
    var tbl = el('div', 'display:grid;grid-template-columns:1.3fr .7fr .7fr .7fr;gap:4px 8px;font-size:12px');
    ['class', 'now', 'hwm', 'stasis'].forEach(function (h) { tbl.appendChild(el('div', 'color:#8b949e', h)); });
    r.classes.forEach(function (c) {
      var col = c.status === 'regression' ? '#ffb4ad' : c.status === 'stale' ? '#ffd28a' : '#c9d1d9';
      tbl.appendChild(el('div', 'color:' + col, c.cls + (c.waived ? ' (waived)' : '')));
      tbl.appendChild(el('div', 'color:' + col, String(c.now)));
      tbl.appendChild(el('div', 'color:#8b949e', String(c.hwm)));
      tbl.appendChild(el('div', 'color:#8b949e', c.since + '/' + r.window));
    });
    body.appendChild(tbl);
    var foot = el('div', 'display:flex;align-items:center;gap:8px;margin-top:12px');
    var adv = el('button', 'background:#161a20;border:1px solid #262a31;color:#e8edf3;border-radius:8px;padding:6px 12px;cursor:pointer', 'Advance delivery');
    adv.addEventListener('click', function () { advance(); close(); ui(); });
    var jst = el('button', 'background:#161a20;border:1px solid #262a31;color:#e8edf3;border-radius:8px;padding:6px 12px;cursor:pointer', 'Waive (justify)');
    jst.addEventListener('click', function () {
      var w = (root.prompt && root.prompt('Reason for the waiver (an apoptotic exception):')) || 'manual waiver';
      advance(w); close(); ui();
    });
    var rst = el('button', 'margin-left:auto;background:transparent;border:1px solid #262a31;color:#8b949e;border-radius:8px;padding:6px 12px;cursor:pointer', 'Reset');
    rst.addEventListener('click', function () { reset(); close(); ui(); });
    foot.appendChild(adv); foot.appendChild(jst); foot.appendChild(rst); body.appendChild(foot);
    return host;
  }

  return {
    LAW: LAW, CLASSES: CLASSES, WINDOW: WINDOW, WAIVER: WAIVER,
    install: install, observe: observe, absorb: absorb, advance: advance,
    flux: flux, report: report, verdict: function () { return report().verdict; },
    state: function () { return state; }, reset: reset, restore: restore, ui: ui
  };
});
