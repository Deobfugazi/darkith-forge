package com.darkith.omega

import android.content.Context
import android.os.Build
import android.util.Log
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * OmegaBridge — the JS surface for the Darkith Ω standalone app.
 *
 * The studio is the userspace; this is the only door to the device. Every
 * method returns a JSON string, never throws, and reports ABSENCE as a named
 * state ("model not found") rather than a silent failure — the invariant the
 * specialist apps are held to.
 */
class OmegaBridge(private val context: Context) {

    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    private val home: File get() = File("/sdcard/Darkith")
    private val modelsDir: File get() = File(home, "models")
    private val logsDir: File get() = File(home, "logs")

    @JavascriptInterface
    fun version(): String = JSONObject()
        .put("bridge", "omega-bridge-1")
        .put("app", "2.0.0-omega")
        .put("pkg", context.packageName)
        .put("sdk", Build.VERSION.SDK_INT)
        .put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
        .put("abi", Build.SUPPORTED_ABIS.joinToString(","))
        .toString()

    /**
     * GGUF status. Honest by construction: `models` lists what is actually on
     * disk, parsed from the real bytes; `inference` names whether a native
     * backend is present. A model present with no backend is reported as
     * "present, backend-missing" — never as working.
     */
    @JavascriptInterface
    fun ggufStatus(): String {
        val models = GgufReader.scan(modelsDir)
        val arr = JSONArray()
        for (m in models) {
            arr.put(JSONObject()
                .put("path", m.path)
                .put("name", m.name ?: m.path.substringAfterLast('/'))
                .put("arch", m.architecture ?: "unknown")
                .put("quant", m.quant)
                .put("bytes", m.sizeBytes)
                .put("contextLength", m.contextLength ?: JSONObject.NULL)
                .put("embeddingLength", m.embeddingLength ?: JSONObject.NULL)
                .put("tensors", m.tensorCount)
                .put("runtimeBytes", m.estimatedRuntimeBytes())
                .put("version", m.version))
        }
        val backend = nativeBackendPresent()
        return JSONObject()
            .put("modelsDir", modelsDir.absolutePath)
            .put("modelCount", models.size)
            .put("models", arr)
            .put("inference", if (backend) "available" else "backend-missing")
            .put("backend", "llama.cpp-android (JNI)")
            .put("readable", true)
            .toString()
    }

    private fun nativeBackendPresent(): Boolean = try {
        System.loadLibrary("llama")
        true
    } catch (_: Throwable) {
        false
    }

    @JavascriptInterface
    fun fileWrite(relPath: String, contents: String): String = runCatching {
        val target = File(home, relPath.replace(Regex("\\.\\./"), ""))
        target.parentFile?.mkdirs()
        target.writeText(contents)
        JSONObject().put("ok", true).put("path", target.absolutePath).toString()
    }.getOrElse { JSONObject().put("ok", false).put("error", it.message).toString() }

    @JavascriptInterface
    fun fileRead(relPath: String): String = runCatching {
        val target = File(home, relPath.replace(Regex("\\.\\./"), ""))
        if (!target.exists()) JSONObject().put("ok", false).put("state", "absent").toString()
        else JSONObject().put("ok", true).put("path", target.absolutePath).put("data", target.readText()).toString()
    }.getOrElse { JSONObject().put("ok", false).put("error", it.message).toString() }

    @JavascriptInterface
    fun log(line: String): String = runCatching {
        logsDir.mkdirs()
        File(logsDir, "omega-studio.log").appendText("${iso.format(Date())}  $line\n")
        JSONObject().put("ok", true).toString()
    }.getOrElse { JSONObject().put("ok", false).put("error", it.message).toString() }

    @JavascriptInterface
    fun lastCrash(): String = runCatching {
        val f = File(File(context.filesDir, "crashes"), "last_crash.txt")
        if (f.exists()) f.readText() else ""
    }.getOrDefault("")

    fun captureCrash(t: Thread, e: Throwable) {
        runCatching {
            val sw = StringWriter(); e.printStackTrace(PrintWriter(sw))
            val stamp = iso.format(Date())
            val body = "DARKITH OMEGA CRASH\nwhen: $stamp\nthread: ${t.name}\n" +
                "sdk: ${Build.VERSION.SDK_INT}\n\n$sw"
            val priv = File(context.filesDir, "crashes").apply { mkdirs() }
            File(priv, "last_crash.txt").writeText(body)
            File(priv, "crash-${stamp.replace(":", "")}.txt").writeText(body)
            runCatching { logsDir.mkdirs(); File(logsDir, "crash-${stamp.replace(":", "")}.txt").writeText(body) }
            Log.e("DarkithOmega", body)
        }
    }
}
