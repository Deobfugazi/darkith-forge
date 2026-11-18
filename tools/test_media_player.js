/* Unit tests for darkith-omega-media-player.html — the single-file agnostic player.
   Run: node tools/test_media_player.js

   Dependency-free: builds a minimal DOM/browser shim so the REAL script from the
   file is exercised (not a reimplementation). Proves the pure parsers/formatters
   (VTT, SRT, M3U, time, bytes, speed ladder, shuffle), the queue + playlist logic,
   the equaliser definition, and — critically — that a hostile filename is escaped
   before it reaches the queue's innerHTML (never injected). */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const file = path.join(__dirname, "..", "darkith-omega-media-player.html");
const html = fs.readFileSync(file, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("no <script> found"); process.exit(1); }
const src = m[1] + "\n;globalThis.__API = window.DarkithMedia;\n";

/* ------------------------------------------------------------- DOM shim */
function makeEl(id) {
  const node = {
    id, innerHTML: "", textContent: "", className: "", value: "", disabled: false,
    dataset: {}, style: {}, _attrs: {}, _listeners: {},
    classList: { _s: new Set(), add(c){this._s.add(c);}, remove(c){this._s.delete(c);}, contains(c){return this._s.has(c);} },
    setAttribute(k, v) { this._attrs[k] = String(v); },
    removeAttribute(k) { delete this._attrs[k]; },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener() {},
    appendChild() {}, focus() {}, click() {}, closest() { return null; },
    querySelector() { return makeEl("q"); },
    querySelectorAll() { return []; },
    getContext() { return { clearRect(){}, createLinearGradient(){return {addColorStop(){}};}, fillRect(){}, set fillStyle(v){} }; },
    getBoundingClientRect() { return { width: 800, height: 200, left: 0, top: 0 }; },
    requestFullscreen() { return Promise.resolve(); },
    requestPictureInPicture() { return Promise.resolve(); },
  };
  return node;
}

const nodes = {};
function getEl(id) { return (nodes[id] = nodes[id] || makeEl(id)); }

/* media element: the player binds events and reads/writes transport props */
const media = getEl("media");
media.play = () => Promise.resolve();
media.pause = () => {};
media.load = () => {};
media.currentTime = 0; media.duration = 100; media.volume = 1; media.muted = false;
media.paused = true; media.playbackRate = 1; media.videoWidth = 640; media.videoHeight = 360;

const store = {};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};

const documentListeners = {}, winListeners = {};
const documentShim = {
  getElementById: (id) => getEl(id),
  querySelector: (sel) => makeEl("sel:" + sel),
  querySelectorAll: () => [],
  createElement: () => makeEl("created"),
  addEventListener: (t, fn) => { (documentListeners[t] = documentListeners[t] || []).push(fn); },
  body: makeEl("body"),
  readyState: "complete",
  fullscreenElement: null,
  pictureInPictureElement: null,
  exitFullscreen() {}, exitPictureInPicture() {},
};

function FR() { this.result = null; this.onload = null; }
FR.prototype.readAsText = function (f) { this.result = f && f._text != null ? f._text : ""; if (this.onload) this.onload(); };
FR.prototype.readAsArrayBuffer = function () { this.result = new ArrayBuffer(8); if (this.onload) this.onload(); };

const navigatorShim = {
  mediaSession: { setActionHandler() {}, metadata: null, playbackState: "none" },
  wakeLock: { request: () => Promise.resolve({ addEventListener() {}, release() {} }) },
  share: () => Promise.resolve(),
};

const windowShim = {
  addEventListener: (t, fn) => { (winListeners[t] = winListeners[t] || []).push(fn); },
  requestAnimationFrame: () => 0,
  setInterval: () => 0,
  setTimeout: (fn) => { fn(); return 0; },
  clearTimeout: () => {},
  localStorage,
  navigator: navigatorShim,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  MediaMetadata: function (o) { Object.assign(this, o); },
  BroadcastChannel: function () { this.postMessage = () => {}; this.close = () => {}; },
  crypto: { subtle: { digest: () => Promise.resolve(new ArrayBuffer(32)) } },
  document: documentShim,
  Math, JSON, Date, Promise, Array, Object, String, Number, parseFloat, parseInt, isFinite, Uint8Array,
  FileReader: FR,
  console,
};
windowShim.window = windowShim;
windowShim.globalThis = windowShim;

/* ------------------------------------------------------------- run the real script */
const sandbox = Object.assign({}, windowShim);
sandbox.document = documentShim;
sandbox.window = windowShim;
sandbox.localStorage = localStorage;
sandbox.navigator = navigatorShim;
sandbox.FileReader = FR;
sandbox.URL = windowShim.URL;
sandbox.MediaMetadata = windowShim.MediaMetadata;
sandbox.BroadcastChannel = windowShim.BroadcastChannel;
sandbox.crypto = windowShim.crypto;
sandbox.requestAnimationFrame = () => 0;
sandbox.setInterval = () => 0;
sandbox.setTimeout = (fn) => { fn(); return 0; };
sandbox.clearTimeout = () => {};
sandbox.console = console;
sandbox.globalThis = sandbox;

const out = [];
const ok = (n, c, d) => out.push({ n, ok: !!c, d: d == null ? "" : String(d) });

let threw = null;
try { vm.createContext(sandbox); vm.runInContext(src, sandbox, { filename: "media-player.html" }); }
catch (e) { threw = e; }
ok("script evaluates without throwing", !threw, threw && threw.message);

const API = sandbox.__API;
ok("window.DarkithMedia is exported", !!API && typeof API === "object");

/* ------------------------------------------------------------- DOM contract
   The shim hands out an element for ANY id, so a control whose host element is
   missing from the markup would still "work" in the shim and fail in a browser.
   Assert the real file actually declares every id the script binds. */
["media", "stage", "qlist", "mlist", "eq", "queue", "marks", "play", "seek", "vol", "rate",
 "cc", "ccbox", "viz", "eqbtn", "queuebtn", "marksbtn", "ab", "repeat", "shuffle", "toast",
 "tcur", "tdur", "m-name", "m-sha", "m-state", "drop", "file", "dir", "urlin", "urladd"]
  .forEach((id) => ok('markup declares #' + id, html.includes('id="' + id + '"')));

/* ------------------------------------------------------------- formatters */
ok("fmtTime(0) = 0:00", API.fmtTime(0) === "0:00");
ok("fmtTime(65) = 1:05", API.fmtTime(65) === "1:05");
ok("fmtTime(3661) = 1:01:01", API.fmtTime(3661) === "1:01:01");
ok("fmtTime(NaN) = 0:00", API.fmtTime(NaN) === "0:00");
ok("parseTime('1:30') = 90", API.parseTime("1:30") === 90);
ok("parseTime('1.5') = 1.5", API.parseTime("1.5") === 1.5);
ok("parseTime('') is NaN", Number.isNaN(API.parseTime("")));
ok("fmtBytes(1536) = 1.50 KB", API.fmtBytes(1536) === "1.50 KB");
ok("fmtBytes(1048576) = 1.00 MB", API.fmtBytes(1048576) === "1.00 MB");
ok("fmtBytes(null) = —", API.fmtBytes(null) === "—");

/* ------------------------------------------------------------- timestamps */
ok("parseTimeStamp('00:00:01.000') = 1", API.parseTimeStamp("00:00:01.000") === 1);
ok("parseTimeStamp('00:01.000') = 1", API.parseTimeStamp("00:01.000") === 1);
ok("parseTimeStamp('90.5') = 90.5", API.parseTimeStamp("90.5") === 90.5);
ok("parseTimeStamp('01:02:03.500') = 3723.5", API.parseTimeStamp("01:02:03.500") === 3723.5);

/* ------------------------------------------------------------- VTT */
const vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\nworld\n\n00:00:04.000 --> 00:00:05.500\nSecond\n";
const cues = API.parseVTT(vtt);
ok("parseVTT finds 2 cues", cues.length === 2, cues.length);
ok("parseVTT first cue start/end", cues[0].start === 1 && cues[0].end === 3);
ok("parseVTT keeps multi-line body", cues[0].text === "Hello\nworld", JSON.stringify(cues[0].text));
ok("cueAt picks the active cue", API.cueAt(cues, 4.5) && API.cueAt(cues, 4.5).text === "Second");
ok("cueAt returns null between cues", API.cueAt(cues, 3.5) === null);

/* ------------------------------------------------------------- SRT (comma millis) */
const srt = "1\n00:00:01,000 --> 00:00:02,000\nHi\n\n2\n00:00:03,000 --> 00:00:04,000\nBye\n";
const scues = API.parseSRT(srt);
ok("parseSRT finds 2 cues", scues.length === 2, scues.length);
ok("parseSRT normalises comma-millis", scues[0].start === 1 && scues[1].start === 3);

/* ------------------------------------------------------------- M3U */
ok("parseM3U ignores #EXT and blanks",
  JSON.stringify(API.parseM3U("#EXTM3U\n#EXTINF:-1,a\n/sdcard/a.mp3\n\nhttp://x/b.mp4\n")) === JSON.stringify(["/sdcard/a.mp3", "http://x/b.mp4"]));

/* ------------------------------------------------------------- classification */
ok("kindOf .mp4 = video", API.kindOf("a.mp4") === "video");
ok("kindOf .mp3 = audio", API.kindOf("a.mp3") === "audio");
ok("kindOf .png = image", API.kindOf("a.png") === "image");
ok("kindOf .vtt = subtitle", API.kindOf("a.vtt") === "subtitle");
ok("kindOf .m3u = playlist", API.kindOf("a.m3u") === "playlist");
ok("mimeFor .webm = video/webm", API.mimeFor("a.webm") === "video/webm");
ok("mimeFor given type wins", API.mimeFor("a.bin", "video/mp4") === "video/mp4");
ok("isPlayable(video|audio|image)", API.isPlayable("video") && API.isPlayable("audio") && API.isPlayable("image"));
ok("!isPlayable(subtitle)", !API.isPlayable("subtitle"));

/* ------------------------------------------------------------- speed ladder */
ok("stepSpeed(1,+1) = 1.25", API.stepSpeed(1, 1) === 1.25);
ok("stepSpeed(1,-1) = 0.75", API.stepSpeed(1, -1) === 0.75);
ok("stepSpeed(3,+1) clamps at 3", API.stepSpeed(3, 1) === 3);
ok("stepSpeed(0.25,-1) clamps at 0.25", API.stepSpeed(0.25, -1) === 0.25);
ok("stepSpeed(1.1,+1) snaps to 1.25", API.stepSpeed(1.1, 1) === 1.25);

/* ------------------------------------------------------------- shuffle */
let seed = 42;
const rng = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const ord = API.shuffleOrder(8, rng);
ok("shuffleOrder is a permutation of 0..n-1",
  ord.length === 8 && ord.slice().sort((a, b) => a - b).join(",") === "0,1,2,3,4,5,6,7", ord.join(","));

/* ------------------------------------------------------------- equaliser */
ok("EQ_BANDS has 6 bands", API.EQ_BANDS.length === 6);
ok("EQ flat preset is all zeros", API.EQ_PRESETS.flat.every((v) => v === 0));
ok("every EQ preset matches band count", Object.keys(API.EQ_PRESETS).every((k) => API.EQ_PRESETS[k].length === API.EQ_BANDS.length));

/* ------------------------------------------------------------- queue + XSS */
function fakeFile(name, type, text) { return { name, type, size: 1234, _text: text, slice: () => ({}) }; }
API.addEntries([
  { name: "song.mp3", kind: "audio", type: "audio/mpeg", size: 100, file: fakeFile("song.mp3", "audio/mpeg") },
  { name: "clip.mp4", kind: "video", type: "video/mp4", size: 200, file: fakeFile("clip.mp4", "video/mp4") },
], false);
ok("queue holds both media entries", API.state.queue.length === 2, API.state.queue.length);
ok("subtitle/playlist entries are not queued as media",
  (API.addEntries([{ name: "sub.vtt", kind: "subtitle", file: fakeFile("sub.vtt", "text/vtt", "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nx\n") }], false), API.state.queue.length === 2));

const hostile = '<img src=x onerror=alert(1)>"&<script>alert(2)</script>';
API.addEntries([{ name: hostile, kind: "video", type: "video/mp4", size: 10, file: fakeFile(hostile, "video/mp4") }], false);
const qhtml = nodes.qlist.innerHTML;
ok("hostile filename is HTML-escaped in the queue (no injection)",
  qhtml.includes("&lt;img") && qhtml.includes("&amp;") && !/<img src=x/.test(qhtml) && !/<script>alert\(2\)/.test(qhtml),
  qhtml.slice(0, 120));

/* ------------------------------------------------------------- transport */
API.setVolume(0.5);
ok("setVolume clamps + stores", Math.abs(API.state.prefs.volume - 0.5) < 1e-9);
API.setRate(1.5);
ok("setRate applies to prefs", API.state.prefs.rate === 1.5);
API.seekBy(-5);
ok("seekBy clamps at 0", media.currentTime === 0, media.currentTime);

/* ------------------------------------------------------------- report */
let failed = 0;
for (const r of out) { if (!r.ok) failed++; console.log((r.ok ? "  ok   " : "  FAIL ") + r.n + (r.ok ? "" : "  -> " + r.d)); }
console.log(`\n  ${out.length - failed}/${out.length} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
