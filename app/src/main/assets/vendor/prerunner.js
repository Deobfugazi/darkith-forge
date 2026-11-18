/* darkith · pre-runner v1
   Ephemeral "silent race before the race".
   One report contract, two engines:
     browser : sandboxed offscreen iframe (works inside the app/WebView, no deps)
     node    : real headless Chromium via Playwright OR Puppeteer (desktop/Termux/CI)
   Usage (browser):  DarkithPreRunner.run({files:{'a.js':src}, entry:'a.js', shots:4, interval:600, stress:25}).then(report)
   Usage (node):     node darkith-prerunner.js app.html --shots 5 --ms 800 --stress 40 --out ./pr
   Language support is an adapter registry: register(lang, fn) -> {html}|{js}. Nothing is "magic". */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(root);
  else root.DarkithPreRunner = factory(root);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  var esc = function (s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var NEEDS = function (l, w) { var e = new Error('NEEDS_ADAPTER: ' + l + ' needs ' + w); e.needs = true; return e; };


  /* ---------- ADAPTERS (virtual transpile, in memory only) ---------- */
  var AD = {
    html: function (s) { return { html: s }; },
    js: function (s) { return { js: s }; },
    mjs: function (s) { return { js: s, module: true }; },
    css: function (s) { return { html: '<style>' + s + '</style><div>css loaded</div>' }; },
    json: function (s) { JSON.parse(s); return { html: '<pre>' + esc(s) + '</pre>' }; },
    md: function (s) { return { html: '<pre style="white-space:pre-wrap">' + esc(s) + '</pre>' }; }
  };
  function viaCompiler(s, l) {
    if (root.Sucrase) return { js: root.Sucrase.transform(s, { transforms: ['typescript', 'jsx'] }).code };
    if (root.ts) return { js: root.ts.transpileModule(s, { compilerOptions: { jsx: 1, target: 7 } }).outputText };
    if (root.Babel) return { js: root.Babel.transform(s, { presets: ['typescript', 'react'], filename: 'x.' + l }).code };
    throw NEEDS(l, 'Sucrase, TypeScript or Babel on the page (load one first)');
  }
  ['ts', 'tsx', 'jsx'].forEach(function (l) { AD[l] = function (s) { return viaCompiler(s, l); }; });
  function register(lang, fn) { AD[lang] = fn; }
  function extOf(n) { var m = /\.([a-z0-9]+)$/i.exec(n || ''); return m ? m[1].toLowerCase() : 'js'; }


  async function transpile(files, entry) {
    var t0 = Date.now(), notes = [], pre = [], ent = null;
    for (var n in files) {
      var l = extOf(n), a = AD[l];
      if (!a) throw NEEDS(l, 'register("' + l + '", fn) adapter');
      var out = await a(files[n], l);
      notes.push(n + ' -> ' + (out.html ? 'html' : 'js'));
      if (n === entry) ent = out; else if (out.js) pre.push(out.js);
    }
    if (!ent) throw new Error('entry not found: ' + entry);
    return { ent: ent, pre: pre, notes: notes, ms: Date.now() - t0 };
  }


  /* ---------- PROBE (runs inside the page under test) ---------- */
  var PROBE = '(' + function (T) {
    var D = window.__dpr = { log: [], errs: [], lt: 0, ltMax: 0, frames: 0, t0: performance.now() };
    ['log', 'info', 'warn', 'error'].forEach(function (k) {
      var o = console[k]; console[k] = function () {
        var m = [].slice.call(arguments).map(function (a) { try { return typeof a === 'string' ? a : JSON.stringify(a); } catch (e) { return String(a); } }).join(' ');
        if (D.log.length < 500) D.log.push({ k: k, m: m }); try { o.apply(console, arguments); } catch (e) {}
      };
    });
    window.addEventListener('error', function (e) { D.errs.push((e.message || 'error') + (e.lineno ? ' @' + e.lineno + ':' + e.colno : '')); });
    window.addEventListener('unhandledrejection', function (e) { D.errs.push('rejection: ' + (e.reason && e.reason.message || e.reason)); });
    try { new PerformanceObserver(function (l) { l.getEntries().forEach(function (x) { D.lt++; D.ltMax = Math.max(D.ltMax, x.duration); }); }).observe({ entryTypes: ['longtask'] }); } catch (e) {}
    (function f() { D.frames++; requestAnimationFrame(f); })();
    window.__dprSnap = async function () {
      var w = innerWidth, h = innerHeight, s = new XMLSerializer().serializeToString(document.documentElement);
      var u = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><foreignObject width="100%" height="100%">' + s + '</foreignObject></svg>');
      try {
        var im = new Image(); await new Promise(function (r, j) { im.onload = r; im.onerror = j; im.src = u; });
        var c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').drawImage(im, 0, 0); return c.toDataURL('image/png');
      } catch (e) { return u; }
    };
    window.__dprFuzz = function (n, seed) {
      var keys = ['a', 'Enter', 'Tab', 'Backspace', 'ArrowDown', ' ', '{', '"'];
      /* mulberry32 — seeded so a run is reproducible: same seed -> same fuzz -> same report. */
      var s = (seed >>> 0) || 1;
      var rnd = function () { s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
      for (var i = 0; i < n; i++) {
        var els = [].slice.call(document.querySelectorAll('button,a,input,select,textarea,[onclick],[tabindex],canvas'));
        var e = els.length ? els[rnd() * els.length | 0] : document.body, r = e.getBoundingClientRect();
        var x = r.left + r.width / 2, y = r.top + r.height / 2;
        try {
          ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function (t) { e.dispatchEvent(new MouseEvent(t, { bubbles: true, clientX: x, clientY: y })); });
          if (/^(INPUT|TEXTAREA)$/.test(e.tagName)) {
            /* setting .value is OUR action: a file/color input may reject it. Swallow that —
               it is harness misuse, not a page fault, so it must not be reported as an error. */
            try { e.value = rnd().toString(36).slice(2); e.dispatchEvent(new Event('input', { bubbles: true })); } catch (_) {}
          }
          document.dispatchEvent(new KeyboardEvent('keydown', { key: keys[rnd() * keys.length | 0], bubbles: true }));
          if (i % 9 === 0) window.dispatchEvent(new Event('resize'));
        } catch (er) { D.errs.push('fuzz: ' + er.message); }
      }
    };
    window.__dprDump = function () {
      var s = (performance.now() - D.t0) / 1000;
      return { console: D.log, errors: D.errs, metrics: { fps: Math.round(D.frames / s), longTasks: D.lt, maxLongMs: Math.round(D.ltMax), nodes: document.getElementsByTagName('*').length, heapMB: performance.memory ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(1) : null } };
    };
    window.addEventListener('message', function (e) {
      if (e.source === window) return; /* ignore our own posts (top-level/node engine) — avoids a self-loop */
      var d = e.data; if (!d || d.t !== T) return;
      Promise.resolve(d.cmd === 'snap' ? window.__dprSnap() : d.cmd === 'fuzz' ? window.__dprFuzz(d.n, d.seed) : window.__dprDump())
        .then(function (v) { parent.postMessage({ t: T, id: d.id, v: v }, '*'); });
    });
    addEventListener('load', function () { parent.postMessage({ t: T, ready: 1 }, '*'); });
  }.toString() + ')(' + JSON.stringify('__TOKEN__') + ')';


  function buildHtml(tp, token) {
    var probe = '<script>' + PROBE.replace('__TOKEN__', token) + '<\/script>';
    var safe = function (s) { return String(s).replace(/<\/script/gi, '<\\/script'); };
    if (tp.ent.html) {
      var h = tp.ent.html;
      return /<head[^>]*>/i.test(h) ? h.replace(/<head[^>]*>/i, function (m) { return m + probe; }) : probe + h;
    }
    return '<!doctype html><meta charset="utf-8">' + probe + '<body>' +
      tp.pre.map(function (s) { return '<script>' + safe(s) + '<\/script>'; }).join('') +
      '<script' + (tp.ent.module ? ' type="module"' : '') + '>' + safe(tp.ent.js) + '<\/script></body>';
  }


  function verdict(r) {
    if (r.errors.length) return 'FAIL';
    var m = r.metrics;
    return (m.fps && m.fps < 20) || m.longTasks > 5 ? 'WARN' : 'PASS';
  }


  /* ---------- BROWSER ENGINE ---------- */
  async function runBrowser(o) {
    var tp = await transpile(o.files, o.entry), token = 'dpr' + Math.random().toString(36).slice(2);
    var fr = document.createElement('iframe'), w = o.width || 390, h = o.height || 780, pend = {}, ready, n = 0;
    var readyP = new Promise(function (r) { ready = r; });
    function onMsg(e) { var d = e.data; if (!d || d.t !== token) return; if (d.ready) ready(); else if (pend[d.id]) { pend[d.id](d.v); delete pend[d.id]; } }
    function rpc(cmd, extra) { return new Promise(function (res) { var id = ++n; pend[id] = res; fr.contentWindow.postMessage(Object.assign({ t: token, id: id, cmd: cmd }, extra || {}), '*'); setTimeout(function () { if (pend[id]) { delete pend[id]; res(null); } }, 5000); }); }
    window.addEventListener('message', onMsg);
    fr.setAttribute('sandbox', 'allow-scripts');
    fr.style.cssText = 'position:fixed;left:-9999px;top:0;border:0;width:' + w + 'px;height:' + h + 'px';
    fr.srcdoc = buildHtml(tp, token);
    document.body.appendChild(fr);
    var shots = [], t0 = Date.now();
    try {
      await Promise.race([readyP, sleep(o.timeout || 8000)]);
      for (var i = 0; i < (o.shots || 4); i++) {
        await sleep(o.interval || 600);
        if (o.stress) await rpc('fuzz', { n: o.stress, seed: (o.seed || 1) + i });
        shots.push({ t: Date.now() - t0, png: await rpc('snap') });
      }
      var d = await rpc('dump') || { console: [], errors: ['no response from page (hung?)'], metrics: {} };
      return finish('browser', o, tp, d, shots);
    } finally { window.removeEventListener('message', onMsg); fr.remove(); }
  }


  /* ---------- NODE ENGINE (real headless Chromium) ---------- */
  async function runNode(o) {
    var lib = o.lib || (function () { try { return require('playwright'); } catch (e) { try { return require('playwright-core'); } catch (e2) { return require('puppeteer-core'); } } })();
    var tp = await transpile(o.files, o.entry), html = buildHtml(tp, 'node');
    var launchOpts = { headless: true, args: ['--no-sandbox'] };
    /* A system Chromium (no browser download) may be supplied directly or by env,
       mirroring the python render gate's fallback so CI never needs a fetch. */
    var env = (root && root.process && root.process.env) || {};
    var exe = o.executablePath || env.PRERUNNER_CHROME || env.CHROME_PATH;
    if (exe) launchOpts.executablePath = exe;
    var br = await (lib.chromium || lib).launch(launchOpts);
    var shots = [], t0 = Date.now();
    try {
      var pg = await br.newPage(), vp = { width: o.width || 390, height: o.height || 780 };
      await (pg.setViewportSize ? pg.setViewportSize(vp) : pg.setViewport(vp));
      await pg.setContent(html);
      for (var i = 0; i < (o.shots || 4); i++) {
        await sleep(o.interval || 600);
        if (o.stress) await pg.evaluate('window.__dprFuzz(' + (o.stress | 0) + ',' + ((o.seed || 1) + i) + ')');
        shots.push({ t: Date.now() - t0, png: 'data:image/png;base64,' + Buffer.from(await pg.screenshot({ type: 'png' })).toString('base64') });
      }
      return finish('node', o, tp, await pg.evaluate('window.__dprDump()'), shots);
    } finally { await br.close(); }
  }


  function finish(engine, o, tp, d, shots) {
    var r = { engine: engine, entry: o.entry, ok: true, verdict: 'PASS',
              console: d.console, errors: d.errors, metrics: d.metrics, shots: shots,
              target: { width: o.width || 390, height: o.height || 780, shots: o.shots || 4,
                        interval: o.interval || 600, stress: o.stress || 0, seed: o.seed || 1 },
              transpile: { ms: tp.ms, notes: tp.notes } };
    r.verdict = verdict(r); r.ok = r.verdict !== 'FAIL'; return r;
  }


  async function run(o) {
    o = o || {};
    if (!o.files) throw new Error('files required: {name: source}');
    o.entry = o.entry || Object.keys(o.files)[0];
    try { return await (o.engine === 'node' || typeof document === 'undefined' ? runNode(o) : runBrowser(o)); }
    catch (e) {
      return { engine: o.engine === 'node' ? 'node' : 'browser', entry: o.entry, ok: false,
               verdict: e.needs ? 'NEEDS_ADAPTER' : 'ERROR', errors: [e.message],
               console: [], metrics: {}, shots: [], transpile: {} };
    }
  }


  /* ---------- CLI ---------- */
  if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
    var fs = require('fs'), path = require('path'), a = process.argv.slice(2), file = a[0];
    var opt = function (k, d) { var i = a.indexOf('--' + k); return i > -1 ? a[i + 1] : d; };
    var out = opt('out', './prerun-out');
    if (!file) { console.log('usage: node darkith-prerunner.js <file> [--shots 5 --ms 800 --stress 40 --out dir]'); process.exit(2); }
    var f = {}; f[path.basename(file)] = fs.readFileSync(file, 'utf8');
    run({ engine: 'node', files: f, shots: +opt('shots', 5), interval: +opt('ms', 800), stress: +opt('stress', 30) }).then(function (r) {
      fs.mkdirSync(out, { recursive: true });
      r.shots.forEach(function (s, i) { if (s.png) { fs.writeFileSync(path.join(out, 'shot' + (i + 1) + '.png'), Buffer.from(s.png.split(',')[1], 'base64')); s.png = 'shot' + (i + 1) + '.png'; } });
      fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(r, null, 2));
      console.log(r.verdict, JSON.stringify(r.metrics), r.errors.length + ' errors ->', out);
      process.exit(r.ok ? 0 : 1);
    });
  }


  return { run: run, register: register, transpile: transpile, adapters: AD };
});
