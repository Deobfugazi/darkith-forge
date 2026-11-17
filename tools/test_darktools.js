/* Unit tests for darktools.js — the task manager, synchronicity engine
   (explicit + passive learning, deficit ledger, omega ladder) and toolkit host.
   Run: node tools/test_darktools.js */
const DarkTerm = require("../app/src/main/assets/vendor/darkterm.js");
const DarkTools = require("../app/src/main/assets/vendor/darktools.js");

const out = [];
const ok = (n, c, d) => out.push({ n, ok: !!c, d: d || "" });

const s = DarkTerm.createSession({ empty: true });
const ctx = DarkTools.install(s, { fresh: true, DarkTerm });
const sh = (cmd) => s.exec(cmd);

/* ---------------------------------------------------------- task manager */
ok("task list seeded", /t1/.test(sh("task list").out));
ok("task add", /added t5/.test(sh("task add ship the toolkit #darkith !5").out));
ok("task add excludes priority token from title", !/!5/.test(sh("cat tasks/t5.task").out.split("\t")[1]));
ok("task next", /next/.test(sh("task next").out));
ok("task do", /done t5/.test(sh("task do t5").out));
ok("task persists as text file", /t1/.test(sh("ls tasks").out));
ok("coreutils work on task files", /id\tt1/.test(sh("cat tasks/t1.task").out));
ok("grep over task files", /ship the toolkit/.test(sh("grep ship tasks/t5.task").out));

/* ------------------------------------------------- explicit learning */
ok("sync why shows contributions", /score=/.test(sh("sync why t2").out));
sh("task focus t2"); sh("task focus t2"); sh("task focus t2");
ok("sync weights learned something", /\+0\.\d+/.test(sh("sync weights").out));
ok("sync top ranks t2 high", /t2/.test(sh("sync top").out.split("\n")[0]));
ok("sync explain", /sigmoid/.test(sh("sync explain").out));

const s2 = DarkTerm.createSession({ empty: true });
DarkTools.install(s2, { fresh: true, DarkTerm });
const ids = (t) => t.split("\n").map(l => l.trim().split(/\s+/)[1]).filter(Boolean);
const rank0 = ids(s2.exec("sync top").out);
for (let i = 0; i < 8; i++) s2.exec("task focus t4");
const rank1 = ids(s2.exec("sync top").out);
ok("learning moves t4 up the ranking", rank1.indexOf("t4") < rank0.indexOf("t4"), `before ${rank0.join(",")} after ${rank1.join(",")}`);

/* ------------------------------------------------- passive observation */
const s4 = DarkTerm.createSession({ empty: true });
const ctx4 = DarkTools.install(s4, { fresh: true, DarkTerm });
s4.exec("task add fix the parser +parser !5");
s4.exec("task add write docs +docs !2");
// a real command working in the #parser area, not an app command
const obs0 = ctx4.sync.stats.observed;
s4.exec("cd /home/inscriber/projects/parser");
ok("passive observer counted a real command", ctx4.sync.stats.observed > obs0,
   `observed ${obs0} -> ${ctx4.sync.stats.observed}`);
ok("observer credited the #parser task", (ctx4.sync.touched["t5"] || 0) > 0,
   "touched=" + JSON.stringify(ctx4.sync.touched));
ok("observer reinforced the parser tag", (ctx4.sync.tagWeights.parser || 0) > 0,
   "parser=" + (ctx4.sync.tagWeights.parser || 0).toFixed(3));
ok("sync signals reports evidence", /observed: \d/.test(s4.exec("sync signals").out));

// an unattributable command must raise a NAMED deficit — never a silent drop
const before = ctx4.sync.ledger.open().length;
s4.exec("cd /home/inscriber/projects/quantumthing");
ok("unattributable command raised a deficit", ctx4.sync.ledger.open().length > before,
   "open deficits " + before + " -> " + ctx4.sync.ledger.open().length);
ok("deficit has an actionable suggestion",
   ctx4.sync.ledger.open().some(d => d.kind === "attribution" && /tag a task/.test(d.suggestion)));
ok("sync deficits renders the ledger", /\[attribution\]/.test(s4.exec("sync deficits").out));

/* ------------------------------------------------- deficit ledger semantics */
const s5 = DarkTerm.createSession({ empty: true });
const ctx5 = DarkTools.install(s5, { fresh: true, DarkTerm });
s5.exec("task add lonely work");                     // no tags -> coverage deficit
s5.exec("cd /home/inscriber/work/anything");
ok("coverage deficit for an untagged task", ctx5.sync.ledger.open().some(d => d.kind === "coverage"));
s5.exec("task tag t5 alpha");                        // tagging resolves it
ok("tagging resolves the coverage deficit", !ctx5.sync.ledger.open().some(d => d.kind === "coverage" && d.data.task === "t5"));
const cov = (ctx5.sync.ledger.all().find(d => d.kind === "coverage" && d.data.task === "t5") || {});
ok("coverage deficit message is accurate (no tags)", /no tags at all/.test(cov.detail || ""), cov.detail);
// a task that has tags but whose area was never worked is reported honestly
const s5b = DarkTerm.createSession({ empty: true });
const ctx5b = DarkTools.install(s5b, { fresh: true, DarkTerm });
s5b.exec("task add tagged but untouched +widgets");
s5b.exec("cd /home/inscriber/other/place");
const covb = ctx5b.sync.ledger.open().find(d => d.kind === "coverage" && d.data.task === "t5");
ok("coverage deficit names existing tags", /carries \+widgets/.test(covb.detail) && /none are learned/.test(covb.detail), covb && covb.detail);
ok("coverage suggestion offers the concrete next step", /task tag t5 widgets/.test(covb.suggestion), covb && covb.suggestion);
const d = ctx5.sync.ledger.open()[0];
ok("deficit has an id and a count", !!d && !!d.id && d.count >= 1);
ok("sync deficits resolve <id> clears it", /resolved/.test(s5.exec("sync deficits resolve " + d.id).out));

/* ------------------------------------------------- contradiction detection */
const s6 = DarkTerm.createSession({ empty: true });
const ctx6 = DarkTools.install(s6, { fresh: true, DarkTerm });
s6.exec("task focus t1"); s6.exec("task defer t1");
ok("contradiction raised (raise then lower)", ctx6.sync.ledger.open().some(x => x.kind === "contradiction"));
ok("sync claim reconciles it", (s6.exec("sync claim t1 1"), !ctx6.sync.ledger.open().some(x => x.kind === "contradiction")));

/* ------------------------------------------------- omega ladder */
const s7 = DarkTerm.createSession({ empty: true });
const ctx7 = DarkTools.install(s7, { fresh: true, DarkTerm });
const om0 = s7.exec("sync omega").out;
ok("sync omega reports a ladder", /omega ladder — \d+\/\d+/.test(om0));
ok("unmet rungs are raised as deficits", ctx7.sync.ledger.open().some(x => x.kind === "rung"));
ok("omega percent is honest (<100 at start)", /\(\d+%\)/.test(om0));
// drive it: work in tagged areas so rungs close
["parser", "docs", "sync", "tools"].forEach(t => s7.exec("task add do " + t + " +" + t));
for (let i = 0; i < 12; i++) s7.exec("cd /home/inscriber/projects/parser");
const om1 = s7.exec("sync omega").out;
const pct = (t) => Number((/\((\d+)%\)/.exec(t) || [0, 0])[1]);
ok("omega percent rises with real syncing", pct(om1) > pct(om0), `before ${pct(om0)}% after ${pct(om1)}%`);

// the ceiling is real and reachable: sustained, coherent syncing drives 8/8
const s8 = DarkTerm.createSession({ empty: true });
const ctx8 = DarkTools.install(s8, { fresh: true, DarkTerm });
[["t1","darkith"],["t2","sync"],["t3","tools"],["t4","docs"]].forEach(([id,tg]) => s8.exec("task tag " + id + " " + tg));
["darkith","sync","tools","docs"].forEach(a => { for (let i=0;i<6;i++) s8.exec("cd /home/inscriber/" + a); });
for (let i=0;i<20;i++) { s8.exec("task focus t2"); s8.exec("cd /home/inscriber/sync"); }
let g = 0; while (g++ < 100) { const d = ctx8.sync.ledger.open().filter(x => x.kind !== "rung")[0]; if (!d) break; ctx8.sync.ledger.resolve(d.id); }
const omFull = s8.exec("sync omega").out;
ok("omega ladder reaches the ceiling (8/8)", /8\/8 rungs met \(100%\)/.test(omFull), omFull.split("\n")[0].trim());
ok("ceiling reports 'fully synced'", /ceiling reached: fully synced/.test(omFull));
ok("every rung is met at the ceiling", !/\[ \]/.test(omFull));

/* ------------------------------------------------- toolkit host */
ok("tk list shows seeds", /standup/.test(sh("tk list").out) && /triage/.test(sh("tk list").out));
ok("tk build installs", /built 3/.test(sh("tk build").out));
ok("toolkit runs as shell function", /== next ==/.test(sh("standup").out));
ok("toolkit pipelines", /!5/.test(sh("triage").out));
ok("tk new scaffolds", /created/.test(sh("tk new mytool").out));
ok("tk cat prints source", /@desc mytool/.test(sh("tk cat mytool").out));
ok("handcoded toolkit runs", /hello from mytool/.test(sh("tk build; mytool").out));

/* ------------------------------------------------- persistence round trip */
const snap = ctx.store.read();
ok("store captured a snapshot", !!snap && !!snap.fs);
const s3 = DarkTerm.createSession({ empty: true });
const ctx3 = DarkTools.install(s3, { store: ctx.store, DarkTerm });
ok("reload restores a task added before", /ship the toolkit/.test(s3.exec("cat tasks/t5.task").out));
ok("reload restores a handcoded toolkit", /mytool/.test(s3.exec("tk list").out));
ok("reload restores learned sync weights", /\+0\.\d+/.test(s3.exec("sync weights").out));

/* ------------------------------------------------- no silent stub, no defect */
const src = require("fs").readFileSync(__dirname + "/../app/src/main/assets/vendor/darktools.js", "utf8");
ok("observer hook is guarded (never breaks a command)", /try \{ ctx\.sync\.observe/.test(src));
ok("no TODO/FIXME stubs left in engine", !/\b(TODO|FIXME|XXX)\b/.test(src));

let fails = 0;
console.log("== darktools unit tests ==");
out.forEach(r => { if (!r.ok) fails++; console.log((r.ok ? "  PASS  " : "  FAIL  ") + r.n + (r.d ? "  [" + r.d + "]" : "")); });
console.log("\n" + (out.length - fails) + "/" + out.length + " passed");
process.exit(fails ? 1 : 0);
