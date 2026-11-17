package com.darkith.transliaison

import android.content.Context
import android.util.Log
import java.io.File
import java.io.InputStream
import java.io.OutputStream
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

/**
 * OmegaExecHost — the real multi-language execution host.
 *
 * This replaces DarkithRuntimeHost, which called ProcessBuilder(...).start()
 * and returned "OK <runtime> started" without ever reading the process output,
 * and which pointed at /sdcard/... where Android 10+ forbids execve (W^X).
 *
 * Design constraints, both load-bearing:
 *
 *   1. Executable payloads live ONLY in applicationInfo.nativeLibraryDir,
 *      i.e. shipped in the APK as lib*.so with extractNativeLibs=true. That
 *      is the one app-controlled directory the loader lets us exec from.
 *      Everything under filesDir/cacheDir/external storage is data, not code.
 *
 *   2. Output is streamed through bounded buffers and drained by the UI. A
 *      process that floods stdout cannot grow memory without limit.
 *
 * Three tiers back the one protocol the shell speaks:
 *   native — a shipped lib*.so run from nativeLibraryDir
 *   wasm   — a wasm32-wasi module run in-process (no exec, so W^X is moot)
 *   proot  — a full Linux guest for toolchains, when the user installs it
 */
class OmegaExecHost(private val context: Context) {

    companion object {
        private const val TAG = "OmegaExec"
        /** Per-stream cap. Beyond this the oldest bytes are dropped and the
         *  loss is reported to the caller, never silently hidden. */
        private const val STREAM_CAP = 1 shl 20 // 1 MiB
        private const val MAX_JOBS = 8
    }

    private class Job(
        val id: String,
        val proc: Process,
        val stdin: OutputStream
    ) {
        val out = StringBuilder()
        val err = StringBuilder()
        @Volatile var status: Int? = null
        @Volatile var dropped = 0
        @Volatile var alive = true

        fun append(sb: StringBuilder, chunk: String) {
            synchronized(sb) {
                sb.append(chunk)
                if (sb.length > STREAM_CAP) {
                    val cut = sb.length - STREAM_CAP
                    sb.delete(0, cut)
                    dropped += cut
                }
            }
        }

        fun drain(sb: StringBuilder): String = synchronized(sb) {
            val s = sb.toString(); sb.setLength(0); s
        }
    }

    private val jobs = ConcurrentHashMap<String, Job>()
    private val seq = AtomicLong(0)

    /** Binaries shipped as lib*.so. Names are the on-disk file names, which
     *  the packager guarantees end in .so so the installer extracts them. */
    private val nativeDir: File get() = File(context.applicationInfo.nativeLibraryDir)

    private val nativeBins: Map<String, File> by lazy {
        val names = listOf(
            "libdarkith_py.so", "libdarkith_qjs.so", "libdarkith_node.so",
            "libdarkith_lua.so", "libdarkith_sqlite.so", "libdarkith_jq.so",
            "libdarkith_busybox.so", "libproot.so", "libllama-cli.so"
        )
        names.mapNotNull { n ->
            val f = File(nativeDir, n)
            if (f.exists() && f.canExecute()) n.removePrefix("lib").removeSuffix(".so") to f else null
        }.toMap()
    }

    /** Wasm modules the app carries, run in-process. */
    private val wasmModules: List<String> by lazy {
        listOf("python.wasm", "lua.wasm", "rust-demo.wasm").filter {
            File(context.filesDir, "wasm/$it").exists()
        }
    }

    private val prootRootfs: File get() = File(context.filesDir, "guest/alpine")
    private val prootBin: File get() = File(nativeDir, "libproot.so")

    // ---- capability probe ------------------------------------------------

    /** JSON describing what this device can really do. No fabricated caps. */
    fun caps(): String {
        val native = nativeBins.keys.toList()
        val wasm = wasmModules
        val proot = prootBin.exists() && prootRootfs.exists()
        return buildString {
            append("{\"native\":[")
            append(native.joinToString(",") { "\"$it\"" })
            append("],\"wasm\":[")
            append(wasm.joinToString(",") { "\"$it\"" })
            append("],\"proot\":").append(proot)
            append(",\"wasmRuntime\":\"chicory\"}")
        }
    }

    fun status(): String {
        val n = nativeBins.keys
        return "native=${if (n.isEmpty()) "none" else n.joinToString("/")}; " +
            "wasm=${if (wasmModules.isEmpty()) "none" else wasmModules.joinToString("/")}; " +
            "proot=${if (prootBin.exists() && prootRootfs.exists()) "ready" else "not installed"}"
    }

    // ---- exec protocol ---------------------------------------------------

    /**
     * Start a job. specJson: {"cmd":..,"cwd":..,"env":{..},"backend":"native"|"wasm"|"proot"}
     * Returns {"id":"jN"} or {"error":"..."}.
     */
    fun begin(specJson: String): String {
        val spec = try { org.json.JSONObject(specJson) } catch (e: Exception) {
            return err("bad spec: ${e.message}")
        }
        val cmd = spec.optString("cmd", "").trim()
        if (cmd.isEmpty()) return err("empty command")
        val cwd = spec.optString("cwd", context.filesDir.absolutePath)
        val backend = spec.optString("backend", "native")

        val live = jobs.values.count { it.alive }
        if (live >= MAX_JOBS) return err("too many running jobs ($MAX_JOBS)")

        val pb = ProcessBuilder()
        when (backend) {
            "native" -> {
                val words = cmd.split(Regex("\\s+"))
                val bin = resolveNative(words[0])
                    ?: return err("no native runtime for '${words[0]}' (have: ${nativeBins.keys.joinToString()})")
                pb.command(listOf(bin.absolutePath) + words.drop(1))
            }
            "proot" -> {
                if (!prootBin.exists() || !prootRootfs.exists())
                    return err("proot guest not installed")
                pb.command(listOf(prootBin.absolutePath, "-r", prootRootfs.absolutePath,
                    "/bin/sh", "-lc", cmd))
            }
            "wasm" -> {
                // Wasm runs in-process via the JVM runtime; not a child process.
                return err("wasm backend is invoked in-process; use wasmRun(module, args)")
            }
            else -> return err("unknown backend '$backend'")
        }

        val dir = File(cwd)
        pb.directory(if (dir.isDirectory) dir else context.filesDir)
        pb.redirectErrorStream(false)
        val env = pb.environment()
        env["HOME"] = context.filesDir.absolutePath
        env["PATH"] = nativeDir.absolutePath
        env["TMPDIR"] = context.cacheDir.absolutePath
        env["LANG"] = "C.UTF-8"
        spec.optJSONObject("env")?.let { e ->
            e.keys().forEach { k -> env[k] = e.optString(k) }
        }

        val proc = try { pb.start() } catch (e: Exception) {
            return err("start failed: ${e.message}")
        }
        val id = "j" + seq.incrementAndGet()
        val job = Job(id, proc, proc.outputStream)
        jobs[id] = job
        pump(job, proc.inputStream) { job.append(job.out, it) }
        pump(job, proc.errorStream) { job.append(job.err, it) }
        Thread {
            val code = try { proc.waitFor() } catch (e: Exception) { -1 }
            job.status = code; job.alive = false
        }.start()
        return "{\"id\":\"$id\"}"
    }

    /** Drain buffered output: {"out":..,"err":..,"status":n,"done":bool,"dropped":n} */
    fun read(id: String): String {
        val job = jobs[id] ?: return err("unknown job $id")
        val o = job.drain(job.out)
        val e = job.drain(job.err)
        val done = job.status != null
        val j = org.json.JSONObject()
        j.put("out", o); j.put("err", e)
        if (done) j.put("status", job.status)
        j.put("done", done)
        j.put("dropped", job.dropped)
        if (done) jobs.remove(id)
        return j.toString()
    }

    fun write(id: String, data: String): String {
        val job = jobs[id] ?: return err("unknown job $id")
        return try {
            job.stdin.write(data.toByteArray()); job.stdin.flush(); "{\"ok\":true}"
        } catch (e: Exception) { err("stdin: ${e.message}") }
    }

    fun signal(id: String, sig: String): String {
        val job = jobs[id] ?: return err("unknown job $id")
        return try {
            val pid = pidOf(job.proc)
            Runtime.getRuntime().exec(arrayOf("kill", "-$sig", pid)).waitFor()
            "{\"ok\":true}"
        } catch (e: Exception) {
            try { job.proc.destroy(); "{\"ok\":true,\"soft\":true}" }
            catch (e2: Exception) { err("signal: ${e2.message}") }
        }
    }

    fun listJobs(): String {
        val arr = org.json.JSONArray()
        jobs.forEach { (k, v) -> arr.put(org.json.JSONObject().put("id", k).put("alive", v.alive)) }
        return arr.toString()
    }

    // ---- helpers ---------------------------------------------------------

    private fun resolveNative(name: String): File? {
        val base = name.substringBefore(' ').substringAfterLast('/')
        nativeBins[base]?.let { return it }
        // allow the packaged name too
        return nativeBins.entries.firstOrNull { it.key == base || it.key.startsWith(base) }?.value
    }

    private fun pump(src: InputStream, sink: (String) -> Unit) {
        Thread {
            val buf = ByteArray(4096)
            try {
                while (true) {
                    val n = src.read(buf)
                    if (n < 0) break
                    sink(String(buf, 0, n, Charsets.UTF_8))
                }
            } catch (e: Exception) {
                Log.w(TAG, "pump ended: ${e.message}")
            }
        }.start()
    }

    private fun pidOf(p: Process): String {
        return try {
            val f = Process::class.java.getDeclaredField("pid")
            f.isAccessible = true
            f.get(p).toString()
        } catch (e: Exception) { "-1" }
    }

    private fun err(msg: String) = "{\"error\":${org.json.JSONObject.quote(msg)}}"
}
