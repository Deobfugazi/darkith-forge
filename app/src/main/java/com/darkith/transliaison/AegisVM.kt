package com.darkith.transliaison

import android.content.Context
import java.io.File

object AegisVM {

    // Not implemented: reports that honestly instead of fabricating "OK: ABSOLVED".
    fun executeAbsolution(context: Context, donorPath: String, payloadPath: String, nonceZ: Double): String {
        if (!File(donorPath).exists()) return "ERROR: Donor missing"
        if (!File(payloadPath).exists()) return "ERROR: Payload missing"
        if (nonceZ > 2.5) return "ERROR: AEGIS_FAULT — biological presence lost"
        return "ERROR: NOT_IMPLEMENTED"
    }

    fun executeCommand(context: Context, command: String): String {
        return try {
            val envelope = AegisEnvelope.create("terminal", command, setOf("ABSORB"), emptySet())
            AegisWAEL.append(
                sessionId = "session_" + System.currentTimeMillis(),
                seq = 1, donorHash = "terminal", payloadHash = command,
                envelopeHash = envelope.hash, fate = "PENDING"
            )
            if (AegisDatalog.isBlacklisted(command)) {
                return "ERROR: AEGIS_BLACKLISTED — command previously failed"
            }
            AegisCircuitBreaker.arm(context)
            runBash(context, command)
        } catch (e: Exception) {
            "ERROR: AEGIS_FAILURE: ${e.message}"
        }
    }

    private fun runBash(context: Context, command: String): String {
        val nativeDir = File(context.applicationInfo.nativeLibraryDir)
        val bash = File(nativeDir, "libbash.so")
        if (!bash.isFile) return "ERROR: libbash.so missing in ${nativeDir.absolutePath}"
        val pb = ProcessBuilder(bash.absolutePath, "-c", command)
            .directory(context.filesDir).redirectErrorStream(true)
        val env = pb.environment()
        env["PATH"] = nativeDir.absolutePath + ":/system/bin"
        env["LD_LIBRARY_PATH"] = nativeDir.absolutePath
        env["HOME"] = context.filesDir.absolutePath
        env["TMPDIR"] = context.cacheDir.absolutePath
        val p = pb.start()
        val sb = StringBuilder()
        val reader = Thread {
            try {
                p.inputStream.bufferedReader().use { r ->
                    val buf = CharArray(4096)
                    while (true) {
                        val n = r.read(buf)
                        if (n < 0) break
                        synchronized(sb) { if (sb.length < 100000) sb.append(buf, 0, n) }
                    }
                }
            } catch (e: Exception) { }
        }
        reader.start()
        if (!p.waitFor(60, java.util.concurrent.TimeUnit.SECONDS)) {
            p.destroyForcibly(); reader.join(2000)
            return "ERROR: timeout after 60s\n" + synchronized(sb) { sb.toString() }
        }
        reader.join(2000)
        val out = synchronized(sb) { sb.toString().trimEnd() }
        val code = p.exitValue()
        return if (code == 0) "OK: $out" else "ERROR: exit $code: $out"
    }
}
