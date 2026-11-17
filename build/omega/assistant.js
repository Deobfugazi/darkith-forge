/* =====================================================================
   Ω ASSISTANT — local GGUF assistant, tiered for a 4 GB device.

   Backed by llama.cpp's Android binding over JNI (in-process, so W^X and
   execve never enter the picture). This module is the policy layer: it
   picks the largest model that actually fits, streams tokens, and exposes
   tool-calls that reach back into the Ω terminal and SAVF.

   Model sizes below are the real published GGUF byte sizes, not guesses:
     Qwen2.5-0.5B-Instruct Q4_K_M   491,400,032 B
     Llama-3.2-1B-Instruct Q4_K_M   807,694,368 B
     Qwen3-1.7B IQ3_XS              ~888,100,000 B

   Dependency-free; runs in the browser and in Node so the harness can
   exercise the exact selection logic the phone runs.
   ===================================================================== */
(function (root, factory) {
  var mod = factory();
  if (typeof module === "object" && module.exports) module.exports = mod;
  root.OmegaAssistant = mod;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var MB = 1048576;

  /* KV cache grows with context. These are conservative per-1k-token
     estimates for the shipped quants; used only to keep the budget honest. */
  var KV_PER_1K_MB = 48;

  var CATALOG = [
    {
      id: "qwen2.5-0.5b-q4km",
      label: "Qwen2.5 0.5B Instruct",
      quant: "Q4_K_M",
      bytes: 491400032,
      ctx: 4096,
      tier: "T0",
      url: "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
      sha256: null
    },
    {
      id: "llama32-1b-q4km",
      label: "Llama 3.2 1B Instruct",
      quant: "Q4_K_M",
      bytes: 807694368,
      ctx: 4096,
      tier: "T1",
      url: "https://huggingface.co/unsloth/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
      sha256: null
    },
    {
      id: "qwen3-1.7b-iq3xs",
      label: "Qwen3 1.7B",
      quant: "IQ3_XS",
      bytes: 888100000,
      ctx: 4096,
      tier: "T2",
      url: "https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen_Qwen3-1.7B-IQ3_XS.gguf",
      sha256: null
    }
  ];

  /* ---- Budgeting -------------------------------------------------------
     Given free bytes, choose the largest model whose weights + a working
     KV/context reserve fit under the ceiling. The reserve keeps us from
     OOM-killing the foreground app on a 4 GB device. */
  function chooseModel(freeBytes, opts) {
    opts = opts || {};
    var ctx = opts.ctx || 2048;
    var reserveMB = opts.reserveMB != null ? opts.reserveMB : 320;
    var kvMB = (ctx / 1024) * KV_PER_1K_MB;
    var need = reserveMB + kvMB;
    var freeMB = freeBytes / MB;
    var pick = null;
    for (var i = 0; i < CATALOG.length; i++) {
      var m = CATALOG[i];
      if (m.bytes / MB + need <= freeMB) pick = m;
    }
    var wantMB = freeMB - need;
    return {
      model: pick,
      freeMB: Math.round(freeMB),
      reserveMB: Math.round(need),
      budgetMB: Math.round(wantMB),
      /* If even T0 does not fit, say so plainly. */
      reason: pick ? "fits" : "no model fits in " + Math.round(freeMB) + " MB free"
    };
  }

  /* ---- Streaming client ------------------------------------------------
     Speaks to a host (the JNI bridge, or the test adapter). Tokens arrive
     incrementally so the UI can paint them as they come. */
  function Assistant(host, opts) {
    opts = opts || {};
    this.host = host || null;
    this.modelId = null;
    this.onToken = opts.onToken || function () {};
    this.onState = opts.onState || function () {};
  }

  Assistant.prototype.available = function () {
    return !!(this.host && typeof this.host.assistantLoad === "function");
  };

  Assistant.prototype.load = function (modelId, path) {
    if (!this.available()) throw new Error("local assistant backend unavailable on this device");
    var res = this.host.assistantLoad(modelId, path || "");
    var j; try { j = JSON.parse(res || "{}"); } catch (e) { j = {}; }
    if (j.error) throw new Error(j.error);
    this.modelId = modelId;
    this.onState({ state: "loaded", model: modelId });
    return j;
  };

  Assistant.prototype.unload = function () {
    if (this.host && typeof this.host.assistantUnload === "function") this.host.assistantUnload();
    this.modelId = null;
    this.onState({ state: "unloaded" });
  };

  /* Send a prompt; returns the full text and streams each piece. */
  Assistant.prototype.prompt = function (message, o) {
    o = o || {};
    var self = this;
    if (!this.available()) return Promise.reject(new Error("assistant unavailable"));
    if (!this.modelId) return Promise.reject(new Error("no model loaded"));
    var id;
    try {
      id = this.host.assistantPrompt(JSON.stringify({
        message: String(message),
        system: o.system || "",
        predict: o.predict || 512,
        temperature: o.temperature != null ? o.temperature : 0.7
      }));
    } catch (e) {
      return Promise.reject(e);
    }
    return new Promise(function (resolve, reject) {
      var text = "";
      var deadline = Date.now() + (o.timeoutMs || 120000);
      (function pump() {
        var raw;
        try { raw = self.host.assistantRead(id); } catch (e) { return reject(e); }
        var msg; try { msg = JSON.parse(raw || "{}"); } catch (e) { msg = {}; }
        if (msg.token) { text += msg.token; self.onToken(msg.token); }
        if (msg.error) return reject(new Error(msg.error));
        if (msg.done) return resolve({ text: text, tokens: msg.tokens || null });
        if (Date.now() > deadline) return reject(new Error("generation timeout"));
        setTimeout(pump, o.pollMs || 25);
      })();
    });
  };

  /* Tool-calls let the model act on the device through the Ω terminal and
     the existing bridge. Kept explicit: no implicit shell from model text. */
  var TOOLS = [
    { name: "exec", args: ["cmd"], desc: "run a command in the Ω terminal" },
    { name: "read_file", args: ["path"], desc: "read a text file" },
    { name: "write_file", args: ["path", "content"], desc: "write a text file" },
    { name: "savf_audit", args: ["path"], desc: "audit a source file with SAVF" },
    { name: "forge_apk", args: ["html", "appName", "pkgName"], desc: "build an APK" }
  ];

  function systemPrompt() {
    return [
      "You are DARKITH, an offline assistant running on the user's own phone.",
      "Be terse and concrete. You have tools: " + TOOLS.map(function (t) { return t.name; }).join(", ") + ".",
      "To call a tool, emit exactly one line: TOOL <name> <json-args>",
      "Never invent tool output. If unsure, say so."
    ].join(" ");
  }

  return {
    CATALOG: CATALOG,
    MB: MB,
    KV_PER_1K_MB: KV_PER_1K_MB,
    chooseModel: chooseModel,
    Assistant: Assistant,
    TOOLS: TOOLS,
    systemPrompt: systemPrompt
  };
});
