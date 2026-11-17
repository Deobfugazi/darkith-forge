package com.darkith.transliaison

import android.content.Context
import com.arm.aichat.AiChat
import com.arm.aichat.InferenceEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

/**
 * OmegaGgufHost — local GGUF assistant, in-process.
 *
 * Backed by llama.cpp's Android binding (Arm's AiChat / InferenceEngine),
 * which runs the model over JNI inside this app. That matters on the target
 * device: because nothing is exec'd, Android's W^X restriction never applies,
 * and the assistant works with the app fully offline.
 *
 * Memory policy for a 4 GB handset: pick the largest catalog model whose
 * weights plus a KV/context reserve fit under a ceiling derived from the
 * live free-memory probe; mmap the weights; cap the context; unload on
 * onTrimMemory so a backgrounded forge does not get OOM-killed.
 *
 * The token stream is exposed as {token} events the webapp paints live.
 */
class OmegaGgufHost(private val context: Context) {

    companion object {
        private const val TAG = "OmegaGguf"
        /** Never let the model claim more than this much, even if free RAM lies. */
        private const val HARD_CEILING_MB = 1900
        private const val DEFAULT_CTX = 2048
    }

    data class ModelSpec(
        val id: String, val label: String, val quant: String,
        val bytes: Long, val ctx: Int, val url: String
    )

    /** Real published GGUF sizes, mirrored from the JS catalog so both sides
     *  agree on what "fits". */
    private val catalog = listOf(
        ModelSpec("qwen2.5-0.5b-q4km", "Qwen2.5 0.5B Instruct", "Q4_K_M", 491_400_032L, 4096,
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"),
        ModelSpec("llama32-1b-q4km", "Llama 3.2 1B Instruct", "Q4_K_M", 807_694_368L, 4096,
            "https://huggingface.co/unsloth/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
        ModelSpec("qwen3-1.7b-iq3xs", "Qwen3 1.7B", "IQ3_XS", 888_100_000L, 4096,
            "https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen_Qwen3-1.7B-IQ3_XS.gguf")
    )

    private val modelsDir: File get() = File(context.filesDir, "models")
    private val engine: InferenceEngine by lazy { AiChat.getInferenceEngine(context) }
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val streams = ConcurrentHashMap<String, StringBuilder>()
    private val doneFlag = ConcurrentHashMap<String, Boolean>()
    private val seq = AtomicLong(0)
    private var loadedId: String? = null
    private var genJob: Job? = null

    fun available(): Boolean = try {
        // Touch the engine; if the native lib is absent this throws.
        engine != null
    } catch (e: Throwable) { false }

    fun caps(): String {
        val installed = catalog.filter { File(modelsDir, "${it.id}.gguf").exists() }
        val arr = installed.joinToString(",") { "\"${it.id}\"" }
        val freeMB = freeMemMB()
        return "{\"available\":${available()}," +
            "\"models\":[$arr],\"freeMB\":$freeMB," +
            "\"default\":\"${pickDefault()?.id ?: ""}\"}"
    }

    fun listModels(): String = org.json.JSONArray().apply {
        catalog.forEach { put(org.json.JSONObject().put("id", it.id).put("label", it.label)
            .put("quant", it.quant).put("bytes", it.bytes)
            .put("installed", File(modelsDir, "${it.id}.gguf").exists())) }
    }.toString()

    fun defaultModelId(): String = pickDefault()?.id ?: ""

    /** Largest installed model that fits the live budget. Null if none fit. */
    private fun pickDefault(): ModelSpec? {
        val free = freeMemMB()
        val ceiling = minOf(free - 320, HARD_CEILING_MB)
        return catalog
            .filter { File(modelsDir, "${it.id}.gguf").exists() }
            .filter { it.bytes / 1048576 + kvMB(DEFAULT_CTX) <= ceiling }
            .maxByOrNull { it.bytes }
    }

    private fun kvMB(ctx: Int) = (ctx / 1024) * 48

    private fun freeMemMB(): Int = try {
        val mi = android.app.ActivityManager.MemoryInfo()
        (context.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager).getMemoryInfo(mi)
        (mi.availMem / 1048576L).toInt()
    } catch (e: Exception) { 1024 }

    /** Load a model by id (or the default). Returns {"ok":true,...} or error. */
    fun load(modelId: String, path: String): String {
        if (!available()) return err("local assistant backend unavailable")
        val spec = catalog.firstOrNull { it.id == modelId }
            ?: return err("unknown model '$modelId'")
        val file = if (path.isNotBlank()) File(path) else File(modelsDir, "${spec.id}.gguf")
        if (!file.exists()) return err("model not installed: ${file.name} (download ${spec.url})")
        return try {
            // Blocking load is fine here; the bridge call runs off the UI thread.
            kotlinx.coroutines.runBlocking { engine.loadModel(file.absolutePath) }
            kotlinx.coroutines.runBlocking { engine.setSystemPrompt(SYSTEM_PROMPT) }
            loadedId = spec.id
            "{\"ok\":true,\"model\":\"${spec.id}\",\"ctx\":$DEFAULT_CTX}"
        } catch (e: Throwable) {
            err("load failed: ${e.message}")
        }
    }

    fun unload(): String {
        genJob?.cancel(); genJob = null
        return try { engine.cleanUp(); loadedId = null; "{\"ok\":true}" }
        catch (e: Throwable) { err("unload: ${e.message}") }
    }

    /** Begin a prompt. Returns a job id; tokens are drained via read(id). */
    fun prompt(reqJson: String): String {
        if (!available()) return err("assistant unavailable")
        if (loadedId == null) return err("no model loaded")
        val req = try { org.json.JSONObject(reqJson) } catch (e: Exception) { return err("bad request") }
        val msg = req.optString("message", "").trim()
        if (msg.isEmpty()) return err("empty prompt")
        val predict = req.optInt("predict", 512)
        val id = "g" + seq.incrementAndGet()
        streams[id] = StringBuilder()
        doneFlag[id] = false
        genJob = scope.launch {
            try {
                engine.sendUserPrompt(msg, predict).collect { tok ->
                    streams[id]?.append(tok)
                }
            } catch (e: Throwable) {
                streams[id]?.append("\u0000ERR:${e.message}")
            } finally {
                doneFlag[id] = true
            }
        }
        return "{\"id\":\"$id\"}"
    }

    /** Drain generated tokens: {"token":..,"done":bool} */
    fun read(id: String): String {
        val sb = streams[id] ?: return err("unknown generation $id")
        val chunk = synchronized(sb) { val s = sb.toString(); sb.setLength(0); s }
        val done = doneFlag[id] == true
        val j = org.json.JSONObject()
        j.put("token", chunk)
        j.put("done", done)
        if (done) { streams.remove(id); doneFlag.remove(id) }
        return j.toString()
    }

    fun trim() {
        // Called from Activity.onTrimMemory: give memory back before the OOM killer does.
        if (loadedId != null) unload()
    }

    private fun err(msg: String) = "{\"error\":${org.json.JSONObject.quote(msg)}}"

    private val SYSTEM_PROMPT = listOf(
        "You are DARKITH, an offline assistant running on the user's own phone.",
        "Be terse and concrete. You can run commands and audit code on this device.",
        "Never claim an action succeeded unless you were given its output."
    ).joinToString(" ")
}
