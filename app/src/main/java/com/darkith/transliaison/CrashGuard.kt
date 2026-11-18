package com.darkith.transliaison

import android.content.Context
import android.os.Build
import android.util.Log
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * CrashGuard — the app must never die silently.
 *
 * A launcher that throws during onCreate leaves the Operator with "it just
 * closes" and no evidence. This installs an uncaught-exception handler that
 * writes the full stack trace to a location that survives the crash and can be
 * read on the next boot, then re-raises so the platform still reports it.
 *
 * Two destinations on purpose: the app-private dir is always writable without
 * any runtime permission (so the first-ever boot is captured), and the device
 * home /sdcard/Darkith/logs is the durable one the Operator can pull (SPI-8).
 */
object CrashGuard {
    private const val TAG = "DarkithCrash"

    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    fun install(context: Context) {
        val app = context.applicationContext
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try { write(app, t, e) } catch (_: Throwable) {}
            prev?.uncaughtException(t, e)
        }
    }

    private fun write(context: Context, t: Thread, e: Throwable) {
        val sw = StringWriter()
        e.printStackTrace(PrintWriter(sw))
        val stamp = iso.format(Date())
        val body = buildString {
            appendLine("DARKITH CRASH")
            appendLine("when:   $stamp")
            appendLine("thread: ${t.name}")
            appendLine("pkg:    ${context.packageName}")
            appendLine("device: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("sdk:    ${Build.VERSION.SDK_INT} (${Build.VERSION.RELEASE})")
            appendLine("abi:    ${Build.SUPPORTED_ABIS.joinToString(",")}")
            appendLine()
            appendLine(sw.toString())
        }
        val name = "crash-" + stamp.replace(":", "") + ".txt"
        val priv = File(context.filesDir, "crashes").apply { mkdirs() }
        File(priv, name).writeText(body)
        File(priv, "last_crash.txt").writeText(body)
        try {
            val home = File("/sdcard/Darkith/logs").apply { mkdirs() }
            File(home, name).writeText(body)
        } catch (_: Throwable) {}
        Log.e(TAG, body)
    }

    /** The most recent captured crash, or null. Read by the UI to show a trace. */
    fun lastCrash(context: Context): String? =
        File(File(context.filesDir, "crashes"), "last_crash.txt")
            .takeIf { it.exists() }?.readText()

    fun clear(context: Context) {
        File(File(context.filesDir, "crashes"), "last_crash.txt").takeIf { it.exists() }?.delete()
    }
}
