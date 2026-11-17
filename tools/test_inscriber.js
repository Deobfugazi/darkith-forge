const fs = require("fs");
const { JSDOM, VirtualConsole } = require("jsdom");
const html = fs.readFileSync(__dirname + "/../darkith-inscriber.html", "utf8");
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => errors.push("jsdomError: " + e.message));
vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));
const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc, url: "http://localhost/darkith-inscriber.html" });
const w = dom.window;
const out = [];
const ok = (n, c, d) => out.push({ n, ok: !!c, d: d || "" });
setTimeout(() => {
  try {
  ok("no load errors", errors.length === 0, errors.join(" | "));
  ok("DarkTerm present", !!w.DarkTerm);
  ok("DarkTools present", !!w.DarkTools);
  ok("SAVF present", !!w.SAVF);
  const term = w.document.querySelector("#term-cmd");
  const host = w.document.querySelector("#term");
  function run(line) { term.value = line; term.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true })); }
  run("task list");
  ok("terminal shows seeded tasks", /wire task manager/.test(host.textContent), host.textContent.slice(-100));
  run("task add prove it works +darkith !5");
  ok("task add via terminal", /added t5/.test(host.textContent));
  run("standup");
  ok("handcoded toolkit runs in-app", /== next ==/.test(host.textContent));
  run("sync weights");
  ok("sync engine responds", /high/.test(host.textContent.slice(-200)));
  run("sync omega");
  ok("omega ladder renders in-app", /omega ladder — \d+\/\d+/.test(host.textContent));
  run("sync deficits");
  ok("deficit ledger renders in-app", /\[rung\]|\[attribution\]|\[coverage\]|no open deficits/.test(host.textContent));
  run("task add learn the parser +parser !4");
  run("cd /home/inscriber/projects/parser");
  run("sync signals");
  ok("passive observer learns in-app", /observed: [1-9]/.test(host.textContent.slice(-400)));
  run("tk list");
  ok("tk lists toolkits", /standup/.test(host.textContent.slice(-300)));
  const ws = w.localStorage.getItem("darkith.workspace");
  ok("workspace autosaved to localStorage", !!ws && /wire task manager/.test(ws));
  ok("sync state autosaved to localStorage", !!w.localStorage.getItem("darkith.sync"));
  let fails = 0;
  console.log("== inscriber app functional test ==");
  out.forEach(r => { if (!r.ok) fails++; console.log((r.ok ? "  PASS  " : "  FAIL  ") + r.n + (r.d ? "  [" + r.d + "]" : "")); });
  console.log("\n" + (out.length - fails) + "/" + out.length + " checks passed");
  process.exit(fails ? 1 : 0);
  } catch (e) { console.log("THREW:", e && e.message, "\n", e && e.stack && e.stack.split("\n").slice(0,6).join("\n")); process.exit(2); }
}, 700);
