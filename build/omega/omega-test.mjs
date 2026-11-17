#!/usr/bin/env node
/* =====================================================================
   Ω engine harness — proves the contract on real processes, not mocks.

   Runs the exact client modules the webapp ships (exec-protocol.js,
   assistant.js) against a Node adapter that spawns real children, then
   optionally drives a real llama.cpp binary and a real GGUF file.

   Usage:
     node build/omega/omega-test.mjs
     node build/omega/omega-test.mjs --llama /path/to/llama-cli --model /path/to/m.gguf
   ===================================================================== */
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));

const OmegaExec = require(path.join(here, "exec-protocol.js"));
const OmegaAssistant = require(path.join(here, "assistant.js"));

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log(`  ok   ${name}`); }
  else { fail++; console.log(`  FAIL ${name}${detail ? "  -- " + detail : ""}`); }
}

/* ---- A host adapter that satisfies the bridge contract with real procs --- */
function makeNodeHost() {
  const procs = new Map();
  const bufs = new Map();
  let seq = 0;
  return {
    execBegin(specJson) {
      const spec = JSON.parse(specJson);
      const id = "n" + (++seq);
      const argv = Array.isArray(spec.argv) && spec.argv.length
        ? spec.argv
        : spec.cmd.split(/\s+/);
      const [bin, ...args] = argv;
      let child;
      try {
        child = spawn(bin, args, {
          cwd: fs.existsSync(spec.cwd) ? spec.cwd : process.cwd(),
          env: { ...process.env, ...spec.env }
        });
      } catch (e) { return JSON.stringify({ error: e.message }); }
      bufs.set(id, { out: "", err: "", status: null });
      child.stdout.on("data", d => bufs.get(id).out += d.toString());
      child.stderr.on("data", d => bufs.get(id).err += d.toString());
      child.on("close", code => { bufs.get(id).status = code ?? 0; });
      child.on("error", e => { bufs.get(id).err += "\n" + e.message; bufs.get(id).status = 127; });
      procs.set(id, child);
      return JSON.stringify({ id });
    },
    execRead(id) {
      const b = bufs.get(id);
      if (!b) return JSON.stringify({ error: "unknown " + id });
      const out = b.out, err = b.err;
      b.out = ""; b.err = "";
      const done = b.status !== null;
      return JSON.stringify({ out, err, done, status: b.status ?? 0 });
    },
    execWrite(id, data) { const c = procs.get(id); if (c) c.stdin.write(data); return '{"ok":true}'; },
    execSignal(id) { const c = procs.get(id); if (c) c.kill("SIGTERM"); return '{"ok":true}'; },
    execCaps() { return JSON.stringify({ native: ["sh", "node"], wasm: [], proot: false }); }
  };
}

const host = makeNodeHost();
const backend = new OmegaExec.Backend(host, { maxJobs: 4 });

/* ---- 1. real command, real output ------------------------------------- */
{
  const r = await backend.run("echo hello-omega");
  ok("exec: runs a real command and captures stdout", r.status === 0 && r.out.includes("hello-omega"),
     JSON.stringify(r));
}

/* ---- 2. stderr is separated, exit code preserved ----------------------- */
{
  const r = await backend.run("", { argv: ["sh", "-c", "echo to-err 1>&2; exit 3"] });
  ok("exec: separates stderr and preserves exit status", r.status === 3 && r.err.includes("to-err"),
     JSON.stringify(r));
}

/* ---- 3. a failure is a failure, never a fake 'started' ----------------- */
{
  const r = await backend.run("this-binary-does-not-exist-xyz");
  ok("exec: missing binary reports failure (no fabricated success)",
     r.status !== 0 && (r.err.length > 0 || r.out.length > 0), JSON.stringify(r));
}

/* ---- 4. streaming: chunks arrive across multiple reads ----------------- */
{
  const { id } = backend.begin("", { argv: ["sh", "-c", "for i in 1 2 3; do echo line$i; sleep 0.05; done"] });
  const seen = [];
  const t0 = Date.now();
  while (Date.now() - t0 < 5000) {
    const r = backend.read(id);
    if (r.out) seen.push(r.out);
    if (r.done) break;
    await new Promise(r => setTimeout(r, 20));
  }
  ok("exec: output streams incrementally (more than one read)", seen.length > 1, `reads=${seen.length}`);
  ok("exec: streamed text is complete", seen.join("").includes("line3"), seen.join(""));
}

/* ---- 5. job cap is enforced ------------------------------------------- */
{
  for (let i = 0; i < 4; i++) backend.begin("sleep 0.3");
  let threw = false;
  try { backend.begin("sleep 0.3"); } catch (e) { threw = true; }
  ok("exec: enforces the concurrent-job cap", threw);
}

/* ---- 6. ring buffer bounds memory and reports loss --------------------- */
{
  const ring = new OmegaExec.Ring(64);
  for (let i = 0; i < 100; i++) ring.push("x".repeat(10));
  const s = ring.drain();
  ok("ring: caps stored bytes", s.length <= 64, `len=${s.length}`);
  ok("ring: records dropped bytes", ring.dropped > 0, `dropped=${ring.dropped}`);
}

/* ---- 7. capability probe is honest ------------------------------------ */
{
  const c = OmegaExec.caps(host);
  ok("caps: reports native backends", Array.isArray(c.native) && c.native.length > 0, JSON.stringify(c));
  ok("caps: proot reported false when absent", c.proot === false);
}

/* ---- 8. assistant model selection against the 4 GB budget ------------- */
{
  const GB = 1024 * 1024 * 1024;
  const a = OmegaAssistant.chooseModel(2.0 * GB);   // ~2 GB free
  ok("assistant: picks a model that fits 2 GB free", a.model && a.model.id, JSON.stringify(a));
  const b = OmegaAssistant.chooseModel(0.4 * GB);   // too little for any
  ok("assistant: refuses when nothing fits", b.model === null && /no model fits/.test(b.reason),
     JSON.stringify(b));
  const c = OmegaAssistant.chooseModel(3.0 * GB);
  ok("assistant: picks the largest that fits when memory is plentiful",
     c.model && c.model.id === "qwen3-1.7b-iq3xs", JSON.stringify(c));
  ok("assistant: catalog sizes match published GGUF bytes",
     OmegaAssistant.CATALOG[0].bytes === 491400032 && OmegaAssistant.CATALOG[1].bytes === 807694368);
}

/* ---- 9. assistant streams tokens through the host --------------------- */
{
  const fakeHost = {
    assistantLoad: () => '{"ok":true}',
    assistantPrompt: () => '{"id":"g1"}',
    _n: 0,
    assistantRead() {
      const toks = ["Hel", "lo", " world"];
      if (this._n < toks.length) return JSON.stringify({ token: toks[this._n++] });
      return JSON.stringify({ token: "", done: true, tokens: 3 });
    },
    assistantUnload: () => '{"ok":true}'
  };
  const asst = new OmegaAssistant.Assistant(fakeHost);
  asst.load("qwen2.5-0.5b-q4km");
  const out = [];
  asst.onToken = t => out.push(t);
  const res = await asst.prompt("hi");
  ok("assistant: streams tokens incrementally", out.length === 3, JSON.stringify(out));
  ok("assistant: assembles the full text", res.text === "Hello world", res.text);
}

/* ---- 10. tier 2: a real wasm32-wasi module runs in-process -----------
   No exec, so Android's W^X rule never applies. This is how "any language"
   becomes literal: anything with a wasm32-wasi target runs here. We use
   Node's WASI as the reference runtime; on-device the same module runs under
   a JVM Wasm engine (Chicory) or WAMR. */
{
  const wasmPath = path.join(here, "wasm", "hello.wasm");
  if (fs.existsSync(wasmPath)) {
    const { WASI } = await import("node:wasi");
    const tmp = path.join("/tmp", "omega-wasi-" + Date.now() + ".txt");
    const fd = fs.openSync(tmp, "w");
    let exitCode = -1, captured = "";
    try {
      const wasi = new WASI({ version: "preview1", args: ["hello.wasm"], env: {}, stdout: fd, stderr: fd });
      const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
      const inst = await WebAssembly.instantiate(mod, wasi.getImportObject());
      exitCode = wasi.start(inst);
      fs.closeSync(fd);
      captured = fs.readFileSync(tmp, "utf8");
    } catch (e) {
      captured = "error: " + e.message;
    } finally { try { fs.unlinkSync(tmp); } catch (e) {} }
    ok("wasm: a real wasm32-wasi module runs in-process and exits 0", exitCode === 0, `exit=${exitCode}`);
    ok("wasm: captures the module's stdout", captured.includes("hello from wasm32-wasi"), JSON.stringify(captured));
  } else {
    ok("wasm: fixture present", false, "missing " + wasmPath);
  }
}

/* ---- 11. real llama.cpp + real GGUF (optional, when provided) ----------
   Note: llama-cli is tty-bound — it writes 0 bytes to a plain pipe even
   with stdout redirected, because it draws through its console layer. So we
   give it a pty via `script`. This is also the strongest argument for the
   production design: the app must use the in-process JNI binding, not an
   exec'd CLI, or it would have to carry a pty for every generation. */
const llamaIdx = process.argv.indexOf("--llama");
const modelIdx = process.argv.indexOf("--model");
if (llamaIdx > 0 && modelIdx > 0) {
  const llama = process.argv[llamaIdx + 1];
  const model = process.argv[modelIdx + 1];
  const t0 = Date.now();
  const llamaBackend = new OmegaExec.Backend(host, { maxJobs: 4 });

  // First, prove the pipe limitation is real and that a pty fixes it.
  const pipeRun = await llamaBackend.run("", {
    argv: [llama, "-m", model, "-c", "512", "-n", "4", "-p", "hi", "-co", "off", "-st"],
    timeoutMs: 180000, maxBytes: 1 << 20
  });
  const needsPty = (pipeRun.out + pipeRun.err).trim().length === 0;
  ok("llama: CLI is tty-bound (documents why the app uses JNI, not exec)", needsPty,
     `captured ${(pipeRun.out + pipeRun.err).length} bytes from a plain pipe`);

  const inner = `${llama} -m ${model} -c 2048 -n 24 -p "Reply with one word: capital of France?" -co off -st`;
  const r = await llamaBackend.run("", {
    argv: ["script", "-qec", inner, "/dev/null"],
    timeoutMs: 180000, maxBytes: 1 << 20
  });
  const text = (r.out || "").replace(/\r/g, "").replace(/\s+/g, " ").trim();
  ok("llama: real GGUF produced a real answer through a pty", /paris/i.test(text), text.slice(-200));
  const m = /Generation:\s*([\d.]+)\s*t\/s/.exec(r.out || "");
  console.log(`       model=${path.basename(model)} gen=${m ? m[1] : "?"} t/s elapsed=${((Date.now()-t0)/1000).toFixed(1)}s`);
}

console.log(`\nOMEGA: ${fail === 0 ? "PASS" : "FAIL"}  (${pass} passed, ${fail} failed)`);
process.exit(fail === 0 ? 0 : 1);
