package com.darkith.transliaison

import java.io.File

/**
 * DarkithRuntimeHost — on-device multi-language runtime host.
 * Informed by the WebToApp runtime orchestration layer.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithRuntimeHost(private val context: android.content.Context) {

    private val base = File("/sdcard/Darkith/donors/runtime-host")
    private val runtimes = mapOf(
        "node"   to File(base, "node/bin/node"),
        "php"    to File(base, "php/bin/php"),
        "python" to File(base, "python/bin/python3"),
        "go"     to File(base, "go/bin/go")
    )

    fun isAvailable(): Boolean = runtimes.values.any { it.exists() && it.canExecute() }

    fun list(): String = runtimes.map { (k, f) ->
        "$k=${if (f.exists()) "ok" else "missing"}"
    }.joinToString(";")

    fun run(runtime: String, scriptPath: String): String {
        val bin = runtimes[runtime] ?: return "ERROR: unknown runtime $runtime"
        if (!bin.exists() || !bin.canExecute()) return "ERROR: $runtime not installed"
        val script = File(scriptPath)
        if (!script.exists()) return "ERROR: script not found: $scriptPath"
        return try {
            ProcessBuilder(bin.absolutePath, script.absolutePath)
                .redirectErrorStream(true).start()
            "OK $runtime started"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }
}
