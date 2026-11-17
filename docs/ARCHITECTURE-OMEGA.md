# DARKITH Ω — local-assistant + polyglot terminal architecture

Status: design, grounded in verified upstream facts (see Sources at the end).
Target: TECNO KM4k, Termux, arm64-v8a, 4 GB RAM, 360×800 CSS viewport.

## 0. What is actually wrong today

Two classes in the shipped host are stubs that can never work on the target:

- `DarkithRuntimeHost.run()` calls `ProcessBuilder(...).start()` and returns
  `"OK <runtime> started"` **without ever reading the process output**. The
  caller sees a success string and no result. Same pattern in
  `DarkithAlpineGuest.apkAdd()`.
- Both point at `/sdcard/Darkith/donors/...`, i.e. **app-writable storage**.
  Android 10+ (the host targets SDK 34) forbids `execve()` on any file in a
  writable directory — a W^X violation. So even with output plumbed in, the
  exec would fail with `EACCES`.

Any real engine has to fix both: put executable payloads where the loader allows
them, and stream their output back.

## 1. The one hard Android constraint

> Untrusted apps that target Android 10 cannot invoke `execve()` directly on
> files within the app's home directory. (Android 10 behavior changes, W^X)

Consequences, and the escape hatches that actually work:

| Where the bytes live | Executable? | Use for |
| --- | --- | --- |
| `filesDir/`, `cacheDir`, `/sdcard/...` | **no** | data, models, scripts-as-input |
| `applicationInfo.nativeLibraryDir` (`lib/*.so` in the APK, `extractNativeLibs=true`) | **yes** | interpreters, PRoot, llama.cpp CLI |
| `/data/local/tmp` | yes (via `sh` on some builds) | dev only, not shipped |
| Termux's own `$PREFIX/bin` | yes (Termux targets a legacy SDK) | optional external path |

So the engine ships every executable **as a `lib*.so`** inside the APK and runs
it from `nativeLibraryDir`. That is the whole trick behind a root-free, in-app
polyglot terminal.

## 2. Two engines, one surface

```
            ┌──────────────────────── webapp (file://, zero deps) ─────────────┐
            │  Ω terminal  •  Ω assistant  •  Ω IR viewer                        │
            └───────────────▲───────────────────────────────▲───────────────────┘
                            │ window.darkith.*               │ streaming events
            ┌───────────────┴───────────────┐   ┌───────────┴───────────────────┐
            │  ShellBridge (exec + streams) │   │  AssistantBridge (tokens)     │
            └───────────────▲───────────────┘   └───────────▲───────────────────┘
        ┌───────────────────┴───────────┐     ┌─────────────┴───────────────────┐
        │  Ω TERMINAL: ExecHost          │     │  Ω ASSISTANT: GgufHost          │
        │  nativeLibraryDir binaries     │     │  llama.cpp in-process (JNI)     │
        │  + Wasm tier (Chicory/WAMR)    │     │  GGUF model tiers, KV budget    │
        │  + PRoot tier (full Linux)     │     │  tool-calls back into ExecHost  │
        └────────────────────────────────┘     └─────────────────────────────────┘
```

Both tiers are honest about state: a capability probe returns
`available | needs-download | unavailable`, never a fake "started".

### 2a. Ω TERMINAL — three execution tiers, one protocol

**Tier 1 — native (shipped in the APK, `lib*.so`).** The bulk of "all
languages" without shipping a distro: interpreters cross-compiled for
arm64-v8a and run straight from `nativeLibraryDir`.

| Language | Artifact | Approx size |
| --- | --- | --- |
| Python 3.12 | `libpy.cpython-312.so` + `libpython3.12.so` + stdlib zip | ~12 MB |
| QuickJS / Node-lite | `libqjs.so` / `libnode.so` | 1–15 MB |
| Lua | `liblua.so` | ~300 KB |
| SQLite | `libsqlite3.so` | ~1.5 MB |
| jq / sed / grep / awk / busybox | `lib*.so` | ~2 MB total |
| C/C++/Rust/Go **toolchains** | too large to ship | → Tier 3 |

**Tier 2 — Wasm/WASI (in-process, no exec at all).** Anything compiled to
`wasm32-wasi` runs inside a JVM Wasm runtime (Chicory — pure JVM, zero native
deps; or WAMR AOT for speed). This is how "every language" becomes literal:
`wasm32-wasi` targets exist for Rust, C, C++, Zig, Go, and even CPython (WASI is
a tier-2 CPython platform). A language is "supported" when a prebuilt module is
present, and modules are ~1–5 MB each, sandboxed, and safe.

**Tier 3 — PRoot (full Linux, optional, on demand).** For toolchains and the
long tail, ship a static `libproot.so` + a compressed Alpine/Ubuntu rootfs that
the user installs on first use. This is what `DarkithAlpineGuest` was reaching
for; done properly it runs `gcc`, `pip`, `npm`, `git` inside the app.

**Exec protocol** (streams, not a return string):

```
darkith.execBegin(cmd, {cwd, env, stdin, cols, rows, backend}) -> {id}
darkith.execRead(id)   -> {out, err, status, done}     // poll, or…
events:  ExecOutput{id, stream, chunk}  ExecExit{id, status}
darkith.execWrite(id, data)                            // stdin
darkith.execSignal(id, sig)                            // Ctrl-C / kill
darkith.execCaps() -> {native:[…], wasm:[…], proot:bool}
```

The terminal UI (`TermKit 2.0`, already ANSI-aware) binds to this. Local
builtins (`savf`, `cd`, `ls`) stay in JS; anything else routes to the host.

### 2b. Ω ASSISTANT — local GGUF, tiered for 4 GB

Runtime: llama.cpp's **Android binding** (Arm's `AiChat`/`InferenceEngine`,
`GgufMetadataReader`) with `GGML_CPU_KLEIDIAI=ON` for arm64-v8a, built into the
APK. It runs **in-process over JNI** — no exec, no W^X issue, no separate app.

Memory budget on a 4 GB device (OS + app baseline ≈ 1.2–1.6 GB; safe working
ceiling for the model ≈ 1.5–2.0 GB):

| Tier | Model (quant) | Weights | + KV/ctx | Fits 4 GB? |
| --- | --- | --- | --- | --- |
| **T0 default** | Qwen2.5-0.5B-Instruct **Q4_K_M** | ~0.49 GB | ~0.1 GB @2k | yes, comfortable |
| **T1** | Llama-3.2-1B-Instruct **Q4_K_M** | ~0.81 GB | ~0.15 GB @2k | yes |
| **T2** | Qwen3-1.7B **IQ3_XS / Q3_K_S** | ~0.89–0.97 GB | ~0.2 GB @2k | yes, tight |
| ✗ | anything ≥ 2 B at Q4 | ≥ 1.2 GB+ | — | no, OOM risk |

Numbers are the real published file sizes (verified below), not estimates. The
engine picks the **largest model that fits the live free-RAM probe**, and
degrades gracefully: mmap the weights, cap context (`-c 2048`), keep the KV
cache quantized (q8_0), and unload on `onTrimMemory`.

**Why this beats cloud assistants on this device:** zero network, zero per-token
cost, no data leaves the phone, and it works offline on a 4 GB handset. What it
does *not* claim: a 0.5–1.7 B model is not GPT-4-class. The honest positioning is
"a capable, private, always-available local assistant," with the option to route
hard prompts to a remote model when online.

### 2c. The fusion: assistant that drives the terminal

The assistant exposes tool-calls that map onto the Ω terminal and the existing
bridge — `exec`, `read_file`, `write_file`, `savf_audit`, `forge_apk`. So the
local model can audit code with SAVF, run it, read the result, and iterate, all
on-device. That is the "better than other assistants on *this* device" claim:
it is the only one wired into the forge.

## 3. Ω IR viewer

`forgeRenderNative` already posts HTML to an "Omega surface". Formalize it: the
assistant emits a small JSON IR (blocks: prose/code/diff/tree/diagram), the shell
renders it. Keeps model output structured and safe (no raw HTML from the model).

## 4. Build & verification plan

1. `lib/` module from llama.cpp's Android binding, `abiFilters = arm64-v8a`,
   `GGML_CPU_KLEIDIAI=ON`. Ship no model; download T0 on first run.
2. `exec-host/` — interpreters cross-compiled for arm64-v8a, packaged as
   `jniLibs/arm64-v8a/lib*.so` (`extractNativeLibs=true`).
3. Bridge: replace the two stubs with real streaming implementations; add
   `execCaps`, `execBegin/Read/Write/Signal`, and the assistant token stream.
4. Prove it: this repo's harness runs a real GGUF through llama.cpp and a real
   interpreter exec; the webapp battery already proves the shell from `file://`.

## 5. Non-goals / honest limits

- Not shipping a 7 B model on a 4 GB device — it will not fit.
- Tier 3 (PRoot) needs a one-time rootfs download; without it, "all languages"
  means Tier 1 + Tier 2, which is still broad (Python, JS, Lua, SQL, C/Rust/Go
  via Wasm).
- GPU/NPU offload on the KM4k's Mali is not assumed; CPU + KleidiAI is the
  portable baseline.

## Sources (verified during design)

- llama.cpp Android binding + `docs/android.md` (Arm AI Chat, KleidiAI, arm64-v8a).
- Android 10 behavior changes — "Removed execute permission for app home
  directory" (W^X / `execve`).
- `applicationInfo.nativeLibraryDir` / `android:extractNativeLibs`.
- CPython `Platforms/WASI` (WASI is a tier-2 platform); wasi-sdk releases.
- Chicory (pure-JVM Wasm) and WAMR (AOT on Android).
- Hugging Face file sizes for Qwen2.5-0.5B, Llama-3.2-1B, Qwen3-1.7B GGUFs.
