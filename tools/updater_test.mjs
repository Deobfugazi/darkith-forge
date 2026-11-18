/* tools/updater_test.mjs — drives build/updater.js with real inputs.
   The alerting logic is pure (codeOf/cmp/decide) plus a thin I/O layer we
   exercise with a stubbed global.fetch; no part of the code under test is
   mocked. Run: node tools/updater_test.mjs */
import { readFileSync } from "node:fs";
import { runInThisContext } from "node:vm";

const code = readFileSync(new URL("../build/updater.js", import.meta.url), "utf8");
runInThisContext(code);
const U = globalThis.__dkUpdate;

let pass = 0, fail = 0;
function ok(name, cond) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name); }
}

console.log("codeOf");
ok("numeric code", U.codeOf({ versionCode: 7 }) === 7);
ok("string code", U.codeOf({ versionCode: "12" }) === 12);
ok("name-derived 1.2.0 -> 10200", U.codeOf({ versionName: "1.2.0-omega" }) === 10200);
ok("name-derived 5.3.1 -> 50301", U.codeOf({ surfaceVersion: "v5.3.1" }) === 50301);
ok("no version -> null", U.codeOf({}) === null);
ok("null -> null", U.codeOf(null) === null);

console.log("cmp");
ok("3 < 4", U.cmp({ versionCode: 3 }, { versionCode: 4 }) === -1);
ok("4 > 3", U.cmp({ versionCode: 4 }, { versionCode: 3 }) === 1);
ok("3 == 3", U.cmp({ versionCode: 3 }, { versionCode: 3 }) === 0);
ok("incomparable -> null", U.cmp({ versionCode: 3 }, {}) === null);

console.log("decide");
const local = { versionCode: 3, versionName: "1.2.0-omega" };
let d = U.decide(local, { versionCode: 4, versionName: "1.3.0-omega", notes: "x" }, true);
ok("newer remote -> update", d.state === "update" && d.actionable === true);
ok("update message names both", /1\.2\.0-omega/.test(d.message) && /1\.3\.0-omega/.test(d.message));
d = U.decide(local, { versionCode: 3, versionName: "1.2.0-omega" }, true);
ok("equal -> current", d.state === "current" && d.actionable === false);
d = U.decide(local, { versionCode: 2 }, true);
ok("older remote -> current (never a downgrade alert)", d.state === "current");
d = U.decide(local, null, false);
ok("offline -> unknown, not 'current'", d.state === "unknown" && d.actionable === false);
ok("offline message says neither confirmed nor denied", /confirmed nor denied/.test(d.message));
d = U.decide(local, { notes: "no version" }, true);
ok("no comparable version -> unknown", d.state === "unknown");

console.log("fetchManifest (stubbed global.fetch)");
const realFetch = globalThis.fetch;
globalThis.fetch = async (url, opts) => ({ ok: true, status: 200, json: async () => ({ versionCode: 9, versionName: "9.0.0" }) });
let r = await U.fetchManifest("http://x");
ok("200 -> ok+manifest", r.ok === true && r.manifest.versionCode === 9);
globalThis.fetch = async () => ({ ok: false, status: 404 });
r = await U.fetchManifest("http://x");
ok("404 -> not ok", r.ok === false && /http-404/.test(r.reason));
globalThis.fetch = async () => { throw Object.assign(new Error("nope"), { name: "TypeError" }); };
r = await U.fetchManifest("http://x");
ok("network throw -> not ok", r.ok === false && /error/.test(r.reason));

console.log("check() — alert fires once per new version");
let alerts = 0;
globalThis.UI = { dialog: async () => { alerts++; } };
globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ versionCode: 5, versionName: "5.0.0" }) });
await U.check({ alert: true });
await U.check({ alert: true });
ok("one alert for the same new code across two checks", alerts === 1);
globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ versionCode: 6, versionName: "6.0.0" }) });
await U.check({ alert: true });
ok("a newer code alerts again", alerts === 2);
globalThis.fetch = async () => { throw new Error("offline"); };
let before = alerts;
await U.check({ alert: true });
ok("offline does not raise an update alert", alerts === before);

console.log("probeLocal");
delete globalThis.darkith;
const pl = U.probeLocal();
ok("falls back to embedded stamp", pl.source === "embedded" && pl.versionCode === U.LOCAL.versionCode);
globalThis.darkith = { apkVersion: () => "bridge=hk-bridge-52 pkg=1.4.0-omega (7)" };
const pl2 = U.probeLocal();
ok("reads the real APK version via the bridge", pl2.source === "apk" && pl2.versionCode === 7 && pl2.versionName === "1.4.0-omega");

console.log("fetchFirst (mirror walk)");
let hits = [];
globalThis.fetch = async (u) => {
  hits.push(u);
  if (u === "http://c") return { ok: true, status: 200, json: async () => ({ versionCode: 9, versionName: "9.0.0" }) };
  return { ok: false, status: 404, json: async () => ({}) };
};
let fr = await U.fetchFirst(["http://a", "http://raw.githubusercontent.com/b", "http://c"]);
ok("skips dead mirrors and lands on the first live one", fr.ok === true && fr.url === "http://c");
ok("it actually tried the dead mirrors", hits.includes("http://a") && hits.includes("http://raw.githubusercontent.com/b"));
globalThis.fetch = async () => ({ ok: false, status: 404, json: async () => ({}) });
fr = await U.fetchFirst(["http://a", "http://b"]);
ok("all mirrors dead -> unreachable", fr.ok === false && fr.reason === "all-failed" && fr.tried.length === 2);
fr = await U.fetchFirst([]);
ok("no mirrors -> unreachable", fr.ok === false && fr.reason === "no-url");
// check() defaults to the mirror list
hits = [];
globalThis.fetch = async (u) => { hits.push(u); return { ok: true, status: 200, json: async () => ({ versionCode: 3, versionName: "1.2.0-omega" }) }; };
const dflt = await U.check({ alert: false });
ok("check() walks the configured mirrors by default", hits[0] === U.manifestUrls[0] && dflt.state === "current");
ok("default mirrors lead with the runtime host", /prod-runtime\.all-hands\.dev/.test(U.manifestUrls[0]));

console.log("presentation (overlay, host-agnostic)");
function mkNode(tag) {
  return {
    tagName: tag, style: {}, children: [], attrs: {}, textContent: "", id: "",
    href: "", target: "", rel: "", parentNode: null,
    setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); c.parentNode = this; return c; },
    removeChild(c) { this.children = this.children.filter((x) => x !== c); },
    addEventListener() {}, removeEventListener() {},
    _find(id) { if (this.id === id) return this; for (const c of this.children) { const r = c._find && c._find(id); if (r) return r; } return null; }
  };
}
const shimDoc = {
  body: mkNode("body"),
  createElement: (t) => mkNode(t),
  getElementById: (id) => shimDoc.body._find(id),
  addEventListener() {}, removeEventListener() {}
};
delete globalThis.UI; delete globalThis.document;
ok("overlay declines when there is no DOM", U.overlay("t", "m", {}) === false);
globalThis.document = shimDoc;
const evil = '<img src=x onerror="pwn()">';
ok("overlay draws with a DOM", U.overlay("Sovereign upliftment available", evil, { actionable: true, remote: { oneshot_url: "http://x/one.sh" } }) === true);
const modal = shimDoc.getElementById("dku-modal");
ok("modal element is present", !!modal);
const panel = modal.children[0];
ok("untrusted message is textContent, never markup", panel.children[1].textContent === evil && panel.children[1].innerHTML === undefined);
ok("actionable dialog offers the one-shot link", panel.children[2].children.some((c) => c.href === "http://x/one.sh"));
delete globalThis.document;
let alerted = 0; globalThis.alert = () => { alerted++; };
U.present("t", "m", {});
ok("present falls back to alert without a DOM", alerted === 1);
let dlg = 0; globalThis.UI = { dialog: async () => { dlg++; } };
U.present("t", "m", {});
ok("present prefers the host UI.dialog", dlg === 1);
delete globalThis.UI; delete globalThis.alert;

globalThis.fetch = realFetch;
console.log("\nUPDATER: " + pass + "/" + (pass + fail) + (fail === 0 ? " — all checks pass" : " — FAILURES"));
process.exit(fail === 0 ? 0 : 1);
