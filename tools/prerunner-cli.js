#!/usr/bin/env node
/* darkith · pre-runner CLI  (savf-grade node driver for Playwright / Puppeteer)
 *
 * The node half of the pre-runner: it drives a REAL headless Chromium, loads the
 * page under test with an injected probe, then reports console/errors/metrics plus
 * screenshots — the same report contract the browser engine emits, so the two agree.
 *
 * One contract, two engines (see app/src/main/assets/vendor/prerunner.js):
 *   browser : sandboxed offscreen iframe  (in-app / WebView, zero deps)
 *   node    : this file — real Chromium via Playwright or Puppeteer
 *
 * Verdicts are honest and total (SAVF discipline):
 *   PASS          clean run, frame budget held            exit 0
 *   WARN          ran, but janky (low fps / many longtasks) exit 0
 *   FAIL          a page error or uncaught rejection       exit 1
 *   NEEDS_ADAPTER no adapter for a file extension          exit 2
 *   ERROR         the harness itself failed (no browser…)  exit 2
 *
 * Determinism: fuzz input is seeded (mulberry32), so --seed N reproduces a run
 * exactly — same seed, same report (screenshots and timings aside).
 *
 * Usage:
 *   node tools/prerunner-cli.js <file...> [--entry NAME] [--shots 5] [--ms 800]
 *        [--stress 40] [--seed 1] [--width 390] [--height 780]
 *        [--lib playwright|puppeteer] [--out ./prerun-out] [--quiet]
 *   node tools/prerunner-cli.js --selftest [--lib playwright]
 */
'use strict';

const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const MODULE = path.join(HERE, '..', 'app', 'src', 'main', 'assets', 'vendor', 'prerunner.js');

const EXIT = { PASS: 0, WARN: 0, FAIL: 1, NEEDS_ADAPTER: 2, ERROR: 2 };

function usage(code) {
  process.stdout.write([
    'darkith · pre-runner CLI — real headless Chromium via Playwright or Puppeteer.',
    '',
    'Usage:',
    '  node tools/prerunner-cli.js <file...> [options]',
    '  node tools/prerunner-cli.js --selftest [--lib playwright]',
    '',
    'Options:',
    '  --entry NAME     entry file (default: first file)',
    '  --shots N        screenshot rounds (default 4)',
    '  --ms N           ms between rounds (default 600)',
    '  --stress N       fuzz events per round (default 0 = off)',
    '  --seed N         fuzz seed, reproducible (default 1)',
    '  --width/--height viewport (default 390x780)',
    '  --lib NAME       force playwright | puppeteer',
    '  --out DIR        report dir (default ./prerun-out)',
    '  --quiet          only write the report',
    '',
    'Verdicts: PASS/WARN exit 0 · FAIL exit 1 · NEEDS_ADAPTER/ERROR exit 2.',
  ].join('\n') + '\n');
  process.exit(code);
}

function parseArgs(argv) {
  const o = { files: [], shots: 4, interval: 600, stress: 0, seed: 1, width: 390, height: 780,
              out: './prerun-out', quiet: false, selftest: false, entry: null, lib: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const val = () => argv[++i];
    if (a === '--help' || a === '-h') usage(0);
    else if (a === '--selftest') o.selftest = true;
    else if (a === '--quiet' || a === '-q') o.quiet = true;
    else if (a === '--entry') o.entry = val();
    else if (a === '--shots') o.shots = +val();
    else if (a === '--ms' || a === '--interval') o.interval = +val();
    else if (a === '--stress') o.stress = +val();
    else if (a === '--seed') o.seed = +val();
    else if (a === '--width') o.width = +val();
    else if (a === '--height') o.height = +val();
    else if (a === '--lib') o.lib = val();
    else if (a === '--chrome') o.chrome = val();
    else if (a === '--expect') o.expect = val().split(',').filter(Boolean);
    else if (a === '--out') o.out = val();
    else if (a.startsWith('--')) { console.error('unknown flag: ' + a); usage(2); }
    else o.files.push(a);
  }
  return o;
}

function loadFiles(list) {
  const files = {};
  for (const f of list) {
    if (!fs.existsSync(f)) { console.error('no such file: ' + f); process.exit(2); }
    files[path.basename(f)] = fs.readFileSync(f, 'utf8');
  }
  return files;
}

function libFor(name) {
  if (name) return require(name);
  try { return require('playwright'); } catch (e) {}
  try { return require('playwright-core'); } catch (e) {}
  try { return require('puppeteer'); } catch (e) {}
  try { return require('puppeteer-core'); } catch (e) {}
  return null;
}

function findChrome(explicit) {
  if (explicit) return explicit;
  if (process.env.PRERUNNER_CHROME) return process.env.PRERUNNER_CHROME;
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  for (const p of ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
                   '/usr/bin/google-chrome-stable', '/snap/bin/chromium']) {
    try { if (fs.existsSync(p)) return p; } catch (e) {}
  }
  return null;
}

function writeReport(o, r) {
  fs.mkdirSync(o.out, { recursive: true });
  r.shots.forEach((s, i) => {
    if (s.png && s.png.startsWith('data:')) {
      const name = 'shot' + (i + 1) + '.png';
      fs.writeFileSync(path.join(o.out, name), Buffer.from(s.png.split(',')[1], 'base64'));
      s.png = name;
    }
  });
  fs.writeFileSync(path.join(o.out, 'report.json'), JSON.stringify(r, null, 2));
}

function summarize(r) {
  const m = r.metrics || {};
  return [r.verdict, 'fps=' + (m.fps ?? '?'), 'long=' + (m.longTasks ?? '?'),
          'nodes=' + (m.nodes ?? '?'), r.errors.length + ' error(s)'].join(' ');
}

async function main() {
  const o = parseArgs(process.argv.slice(2));

  if (!fs.existsSync(MODULE)) { console.error('engine module missing: ' + MODULE); process.exit(2); }
  const PR = require(MODULE);

  if (o.selftest) return selftest(PR, o);

  if (!o.files.length) usage(2);
  o.files = loadFiles(o.files);
  o.entry = o.entry || Object.keys(o.files)[0];
  o.engine = 'node';
  const lib = libFor(o.lib);
  if (lib) o.lib = lib;
  const chrome = findChrome(o.chrome);
  if (chrome) o.executablePath = chrome;

  const r = await PR.run(o);
  writeReport(o, r);
  if (!o.quiet) {
    console.log(summarize(r));
    if (r.errors.length) r.errors.slice(0, 8).forEach((e) => console.log('  ! ' + e));
    console.log('-> ' + path.resolve(o.out));
  }
  process.exit(EXIT[r.verdict] ?? 2);
}

async function selftest(PR, o) {
  const out = [];
  const ok = (n, c, d) => out.push({ n, ok: c === null || c === undefined ? null : !!c, d: d || '' });

  /* --- pure parts: always runnable, no browser needed --- */
  const tp = await PR.transpile({ 'a.js': 'globalThis.__x = 1;' }, 'a.js');
  ok('transpile js -> js', tp.ent && typeof tp.ent.js === 'string' && !tp.ent.html);
  const tpMd = await PR.transpile({ 'r.md': '# hi' }, 'r.md');
  ok('transpile md -> html', tpMd.ent && /<pre/.test(tpMd.ent.html));
  let needs = false;
  try { await PR.transpile({ 'x.zzz': 'q' }, 'x.zzz'); } catch (e) { needs = !!e.needs; }
  ok('unknown extension raises NEEDS_ADAPTER', needs);
  ok('register() adds an adapter', (() => { PR.register('zzz', (s) => ({ js: '/*' + s + '*/' })); return !!PR.adapters.zzz; })());

  /* --- engine parts: only if a real browser library is present --- */
  const lib = libFor(o.lib);
  const chrome = findChrome(o.chrome);
  const runOpts = (extra) => Object.assign({ engine: 'node', lib, executablePath: chrome || undefined }, extra);
  if (!lib) {
    ok('node engine (needs playwright/puppeteer)', null, 'SKIPPED — npm i playwright (or puppeteer)');
  } else {
    const clean = await PR.run(runOpts({ files: { 'clean.html': '<!doctype html><body><h1>ok</h1><script>document.title="ok"</script></body>' }, shots: 2, interval: 120, seed: 7 }));
    ok('clean page -> PASS', clean.verdict === 'PASS', clean.verdict + ' ' + JSON.stringify(clean.errors));
    const broken = await PR.run(runOpts({ files: { 'broken.html': '<!doctype html><body><script>throw new Error("boom")</script></body>' }, shots: 1, interval: 120, seed: 7 }));
    ok('throwing page -> FAIL', broken.verdict === 'FAIL', broken.verdict);
    const page = '<!doctype html><body><button id=b>x</button><script>document.getElementById("b").onclick=function(){}</script></body>';
    const a = await PR.run(runOpts({ files: { 'f.html': page }, shots: 2, interval: 80, stress: 20, seed: 42 }));
    const b = await PR.run(runOpts({ files: { 'f.html': page }, shots: 2, interval: 80, stress: 20, seed: 42 }));
    ok('deterministic: same seed -> same errors', JSON.stringify(a.errors) === JSON.stringify(b.errors));
    ok('deterministic: same seed -> same verdict', a.verdict === b.verdict);
  }

  const failed = out.filter((r) => r.ok === false);
  out.forEach((r) => console.log('  ' + (r.ok === null ? 'SKIP' : r.ok ? 'ok  ' : 'FAIL') + '  ' + r.n + (r.d ? '  (' + r.d + ')' : '')));
  console.log('prerunner selftest: ' + (failed.length ? 'FAIL ' + failed.length + '/' + out.length : 'ok ' + out.length + '/' + out.length));
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => { console.error('prerunner: ' + (e && e.stack || e)); process.exit(2); });
