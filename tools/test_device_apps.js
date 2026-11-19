/* Tests for the five Ω device apps — phone, messages, contacts, camera, clock.
   Run: node tools/test_device_apps.js

   Each page's REAL <script> is executed against a DOM + bridge shim. The point is not
   to re-test the bridge (that is Kotlin, proven by the compile), but to prove the JS
   contract: honest degradation when a permission is missing, bounded polling, correct
   formatting, and never injecting a value as HTML. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");

function extract(file) {
  const html = fs.readFileSync(path.join(ROOT, file), "utf8");
  const m = html.match(/<script>([\s\S]*)<\/script>/);
  if (!m) throw new Error("no <script> in " + file);
  return m[1];
}

/* ------------------------------------------------------------- DOM shim */
function makeEl(tag) {
  const node = {
    tagName: (tag || "div").toUpperCase(),
    children: [], _text: "", _html: undefined,
    className: "", dataset: {}, style: { cssText: "" },
    _attrs: {}, _listeners: {}, value: "", disabled: false, id: "",
    set textContent(v) { this._text = String(v); this.children = []; },
    get textContent() { return this._text; },
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html === undefined ? "" : this._html; },
    appendChild(c) { this.children.push(c); return c; },
    setAttribute(k, v) { this._attrs[k] = String(v); },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener() {},
    querySelectorAll() { return []; },
    focus() {}, click() { (this._listeners.click || []).forEach(f => fn0(f, this)); },
    get scrollHeight() { return 100; }, set scrollTop(v) { this._st = v; }, get scrollTop() { return this._st || 0; }
  };
  return node;
}
function fn0(fn, self) { fn.call(self, { target: self, preventDefault() {}, stopPropagation() {} }); }

function makeDoc() {
  const els = {};
  return {
    readyState: "complete",
    createElement: makeEl,
    createTextNode: (s) => { const n = makeEl("#text"); n._text = String(s); return n; },
    createDocumentFragment: () => makeEl("#fragment"),
    getElementById: (id) => {
      if (!els[id]) { els[id] = makeEl("div"); els[id].id = id; }
      return els[id];
    },
    querySelectorAll: () => [],
    addEventListener() {},
    _els: els
  };
}

/* ---------------------------------------------------------- bridge shim */
function makeBridge(over) {
  const b = {
    dialNumber: () => "OK",
    dialCall: () => "OK",
    dialTelephony: () => JSON.stringify({ simState: 5, canDial: false, phoneType: 1 }),
    smsInbox: () => "[]",
    smsSend: () => JSON.stringify({ sent: true, parts: 1 }),
    smsCompose: () => "OK",
    contactsList: () => "[]",
    contactsAdd: () => JSON.stringify({ added: true }),
    sysRequest: () => "OK",
    cameraList: () => "[]",
    cameraCapture: () => "PENDING:c1",
    cameraPickImage: () => "PENDING:i1",
    deviceResult: () => "",
    mediaList: () => "[]",
    clockSetAlarm: () => "OK",
    clockTimer: () => "OK",
    clockShowAlarms: () => "OK"
  };
  return Object.assign(b, over || {});
}

function run(file, globalName, bridgeOver, opts) {
  const doc = makeDoc();
  const timers = [];
  const win = {
    document: doc,
    darkith: makeBridge(bridgeOver),
    prompt: (opts && opts.prompt) || (() => null),
    confirm: (opts && opts.confirm) || (() => true),
    setTimeout: (fn) => { timers.push(fn); return timers.length; },
    clearTimeout: () => {},
    setInterval: () => 0,
    Date: Date,
    Math: Math,
    JSON: JSON
  };
  win.window = win;
  const ctx = vm.createContext(win);
  vm.runInContext(extract(file), ctx, { filename: file });
  return { api: ctx.window[globalName], win, doc, timers, bridge: win.darkith };
}

/* --------------------------------------------------------------- harness */
let pass = 0, fail = 0;
const failures = [];
function check(name, fn) {
  try {
    const r = fn();
    if (r === false) throw new Error("returned false");
    pass++;
  } catch (e) { fail++; failures.push(name + " :: " + (e && e.message ? e.message : String(e))); }
}
function eq(a, b, msg) {
  const sa = JSON.stringify(a), sb = JSON.stringify(b);
  if (sa !== sb) throw new Error((msg || "mismatch") + " — got " + sa + " want " + sb);
}

/* ================================================================= PHONE */
check("phone: sanitize keeps only dialable characters", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone");
  eq(api.sanitize("+1 (555) 010-9999"), "+15550109999");
  eq(api.sanitize("abc*#12"), "*#12");
});
check("phone: type accumulates digits", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone");
  api.type("5"); api.type("5"); api.type("5");
  eq(api.state.number, "555");
});
check("phone: type caps at 32 characters", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone");
  for (let i = 0; i < 40; i++) api.type("1");
  eq(api.state.number.length, 32);
});
check("phone: backspace and clear", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone");
  api.type("1"); api.type("2");
  api.backspace();
  eq(api.state.number, "1");
  api.clear();
  eq(api.state.number, "");
});
check("phone: dial refuses an empty number", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone");
  if (api.dial() !== false) throw new Error("expected false");
});
check("phone: dial passes the number to the bridge", () => {
  const seen = [];
  const { api } = run("darkith-omega-phone.html", "DarkithPhone",
    { dialNumber: (n) => { seen.push(n); return "OK"; } });
  api.type("9"); api.type("1"); api.type("1");
  api.dial();
  eq(seen, ["911"]);
});
check("phone: dial surfaces a bridge ERROR as failure, not success", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone",
    { dialNumber: () => "ERROR: permission not granted" });
  api.type("1");
  if (api.dial() !== false) throw new Error("expected false");
});
check("phone: sim badge reflects simState", () => {
  const { api } = run("darkith-omega-phone.html", "DarkithPhone",
    { dialTelephony: () => JSON.stringify({ simState: 1, canDial: false }) });
  eq(api.state.sim.simState, 1);
});
check("phone: works with no bridge at all", () => {
  const doc = makeDoc();
  const win = { document: doc, setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0 };
  win.window = win;
  const ctx = vm.createContext(win);
  vm.runInContext(extract("darkith-omega-phone.html"), ctx, { filename: "phone" });
  const api = ctx.window.DarkithPhone;
  api.type("5");
  eq(api.state.number, "5");
  if (api.dial() !== false) throw new Error("expected false without a bridge");
});

/* ============================================================== MESSAGES */
check("messages: isOut distinguishes sent (type 2)", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages");
  eq(api.isOut({ type: 2 }), true);
  eq(api.isOut({ type: 1 }), false);
  eq(api.isOut(null), false);
});
check("messages: load populates from the bridge", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages", {
    smsInbox: () => JSON.stringify([
      { id: 1, address: "+1555", body: "hi", date: 1700000000000, type: 1 }
    ])
  });
  const m = api.load();
  eq(m.length, 1);
  eq(api.state.granted, true);
});
check("messages: a denied inbox is reported, never faked", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages",
    { smsInbox: () => "ERROR: permission not granted: android.permission.READ_SMS" });
  const m = api.load();
  eq(m.length, 0);
  eq(api.state.granted, false);
});
check("messages: send refuses empty number or text", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages");
  if (api.send() !== false) throw new Error("expected false");
  api.state.number = "123";
  if (api.send() !== false) throw new Error("expected false with no text");
});
check("messages: send uses smsSend when it succeeds", () => {
  const seen = [];
  const { api } = run("darkith-omega-messages.html", "DarkithMessages",
    { smsSend: (n, t) => { seen.push([n, t]); return JSON.stringify({ sent: true }); } });
  api.state.number = "123"; api.state.text = "yo";
  const ok = api.send();
  eq(seen, [["123", "yo"]]);
  if (ok !== true) throw new Error("expected true");
  eq(api.state.text, "");
});
check("messages: send falls back to the composer when direct send fails", () => {
  const composed = [];
  const { api } = run("darkith-omega-messages.html", "DarkithMessages", {
    smsSend: () => "ERROR: permission not granted: android.permission.SEND_SMS",
    smsCompose: (n, t) => { composed.push([n, t]); return "OK"; }
  });
  api.state.number = "123"; api.state.text = "yo";
  api.send();
  eq(composed, [["123", "yo"]]);
});
check("messages: fmtTime formats a same-day timestamp as HH:MM", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages");
  const d = new Date(); d.setHours(9, 5, 0, 0);
  eq(api.fmtTime(d.getTime()), "09:05");
});
check("messages: fmtTime returns empty for 0", () => {
  const { api } = run("darkith-omega-messages.html", "DarkithMessages");
  eq(api.fmtTime(0), "");
});

/* ============================================================== CONTACTS */
check("contacts: initials handles one and many words", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts");
  eq(api.initials("Ada Lovelace"), "AL");
  eq(api.initials("Brandon"), "B");
  eq(api.initials(""), "?");
  eq(api.initials("  "), "?");
});
check("contacts: typeLabel maps phone type codes", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts");
  eq(api.typeLabel(2), "mobile");
  eq(api.typeLabel(1), "home");
  eq(api.typeLabel(3), "work");
  eq(api.typeLabel(99), "other");
});
check("contacts: filter matches name and number", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts");
  const list = [{ name: "Ada", number: "5550100" }, { name: "Bob", number: "5550199" }];
  eq(api.filter(list, "ada").length, 1);
  eq(api.filter(list, "0100").length, 1);
  eq(api.filter(list, "").length, 2);
});
check("contacts: load marks denied as not granted", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts",
    { contactsList: () => "ERROR: permission not granted: android.permission.READ_CONTACTS" });
  const r = api.load();
  eq(r.length, 0);
  eq(api.state.granted, false);
});
check("contacts: load populates when granted", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts",
    { contactsList: () => JSON.stringify([{ name: "Ada", number: "1", type: 2 }]) });
  const r = api.load();
  eq(r.length, 1);
  eq(api.state.granted, true);
});
check("contacts: add refuses an empty name", () => {
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts");
  if (api.add("", "1") !== false) throw new Error("expected false");
});
check("contacts: add calls the bridge with all three fields", () => {
  const seen = [];
  const { api } = run("darkith-omega-contacts.html", "DarkithContacts",
    { contactsAdd: (n, p, e) => { seen.push([n, p, e]); return JSON.stringify({ added: true }); } });
  api.add("Ada", "555", "a@b.c");
  eq(seen, [["Ada", "555", "a@b.c"]]);
});

/* ================================================================ CAMERA */
check("camera: capture returns a PENDING id and polls", () => {
  const { api, timers } = run("darkith-omega-camera.html", "DarkithCamera");
  const ok = api.capture();
  if (ok !== true) throw new Error("expected true");
  eq(api.state.pending, "c1");
  if (!timers.length) throw new Error("no poll scheduled");
});
check("camera: a delivered path becomes a shot", () => {
  const { api } = run("darkith-omega-camera.html", "DarkithCamera", {
    cameraCapture: () => "PENDING:c9",
    deviceResult: () => JSON.stringify({ path: "/sdcard/Pictures/a.jpg", bytes: 2048 })
  });
  api.capture();
  // poll ran synchronously via the shimmed setTimeout
  eq(api.state.shots.length, 1);
  eq(api.state.shots[0].path, "/sdcard/Pictures/a.jpg");
  eq(api.state.busy, false);
});
check("camera: a cancelled capture reports failure and clears busy", () => {
  const { api } = run("darkith-omega-camera.html", "DarkithCamera", {
    cameraCapture: () => "PENDING:c8",
    deviceResult: () => "ERROR: cancelled"
  });
  api.capture();
  eq(api.state.shots.length, 0);
  eq(api.state.busy, false);
});
check("camera: polling is bounded (never hangs forever)", () => {
  const { api, timers } = run("darkith-omega-camera.html", "DarkithCamera", {
    cameraCapture: () => "PENDING:never",
    deviceResult: () => ""
  });
  api.capture();
  let guard = 0;
  while (timers.length && guard++ < 400) {
    const fn = timers.shift();
    fn();
  }
  eq(api.state.busy, false, "busy must clear after the ceiling");
});
check("camera: fmtBytes is human-readable", () => {
  const { api } = run("darkith-omega-camera.html", "DarkithCamera");
  eq(api.fmtBytes(0), "0 B");
  eq(api.fmtBytes(2048), "2.0 KB");
  eq(api.fmtBytes(-1), "—");
});
check("camera: baseName extracts the file name", () => {
  const { api } = run("darkith-omega-camera.html", "DarkithCamera");
  eq(api.baseName("/a/b/c.jpg"), "c.jpg");
  eq(api.baseName(""), "");
});
check("camera: loadGallery maps MediaStore rows", () => {
  const { api } = run("darkith-omega-camera.html", "DarkithCamera", {
    mediaList: () => JSON.stringify([{ name: "p.jpg", path: "/sdcard/p.jpg", bytes: 9 }])
  });
  const g = api.loadGallery();
  eq(g.length, 1);
  eq(g[0].name, "p.jpg");
});

/* ================================================================= CLOCK */
check("clock: pad2 zero-pads", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  eq(api.pad2(7), "07");
  eq(api.pad2(12), "12");
});
check("clock: fmtDur formats mm:ss and h:mm:ss", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  eq(api.fmtDur(0), "00:00");
  eq(api.fmtDur(65000), "01:05");
  eq(api.fmtDur(3661000), "1:01:01");
  eq(api.fmtDur(-5), "00:00");
});
check("clock: setAlarm validates the hour range", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  api.state.alarm.hour = 25;
  if (api.setAlarm() !== false) throw new Error("expected false for hour 25");
  api.state.alarm.hour = 7;
  api.state.alarm.minute = 61;
  if (api.setAlarm() !== false) throw new Error("expected false for minute 61");
});
check("clock: setAlarm passes valid values to the bridge", () => {
  const seen = [];
  const { api } = run("darkith-omega-clock.html", "DarkithClock",
    { clockSetAlarm: (h, m, l, s) => { seen.push([h, m, l, s]); return "OK"; } });
  api.state.alarm = { hour: 6, minute: 30, label: "Wake" };
  api.setAlarm();
  eq(seen, [[6, 30, "Wake", true]]);
});
check("clock: startTimer validates the range", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  api.state.timer.seconds = 0;
  if (api.startTimer() !== false) throw new Error("expected false for 0s");
  api.state.timer.seconds = 90000;
  if (api.startTimer() !== false) throw new Error("expected false for 90000s");
});
check("clock: stopwatch toggle, lap and reset", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  eq(api.swToggle(), true);
  api.swLap();
  eq(api.state.sw.laps.length, 1);
  eq(api.swToggle(), false);
  api.swReset();
  eq(api.state.sw.laps.length, 0);
  eq(api.state.sw.elapsed, 0);
});
check("clock: lap without starting is refused", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  if (api.swLap() !== false) throw new Error("expected false");
});
check("clock: selectTab switches the view", () => {
  const { api } = run("darkith-omega-clock.html", "DarkithClock");
  eq(api.selectTab("timer"), "timer");
  eq(api.state.tab, "timer");
});

/* ------------------------------------------------------------ cross-cutting */
check("no page injects a bridge value via innerHTML", () => {
  const evil = '<img src=x onerror=alert(1)>';
  const files = [
    ["darkith-omega-phone.html", "DarkithPhone", { dialTelephony: () => JSON.stringify({ simState: 5 }) }],
    ["darkith-omega-messages.html", "DarkithMessages",
      { smsInbox: () => JSON.stringify([{ address: evil, body: evil, type: 1, date: 1 }]) }],
    ["darkith-omega-contacts.html", "DarkithContacts",
      { contactsList: () => JSON.stringify([{ name: evil, number: evil, type: 2 }]) }],
    ["darkith-omega-camera.html", "DarkithCamera",
      { mediaList: () => JSON.stringify([{ name: evil, path: "/x", bytes: 1 }]) }]
  ];
  files.forEach(([f, g, b]) => {
    const { api, doc } = run(f, g, b);
    if (api.load) api.load();
    if (api.loadGallery) api.loadGallery();
    Object.keys(doc._els).forEach(id => {
      const el = doc._els[id];
      if (el._html && el._html.indexOf("onerror") >= 0) throw new Error(f + " injected into #" + id);
      el.children.forEach(c => {
        if (c._html && c._html.indexOf("onerror") >= 0) throw new Error(f + " injected a child in #" + id);
      });
    });
  });
});

/* ---------------------------------------------------------------- report */
const total = pass + fail;
if (fail) { console.error("  FAILURES:"); failures.forEach(f => console.error("    ✗ " + f)); }
console.log("  device apps: " + pass + "/" + total + " passed" + (fail ? ", " + fail + " FAILED" : ""));
process.exit(fail ? 1 : 0);
