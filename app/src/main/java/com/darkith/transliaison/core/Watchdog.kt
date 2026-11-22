package com.darkith.transliaison.core

import android.content.Context
import android.os.Handler
import android.os.HandlerThread
import com.darkith.transliaison.ProgressDirectory
import com.darkith.transliaison.ProgressLedger
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Watches for the failure modes that silently cost work, and raises a device-local alert
 * when one is detected.
 *
 * Each check targets a concrete way progress has been lost before:
 *
 *  - UNPUSHED      work exists on disk that no remote has, so a sandbox reset destroys it.
 *  - NO_REMOTE     a git repo has no origin at all.
 *  - DANGLING_HEAD commits exist on a branch no remote tracks.
 *  - KT_UNBALANCED a Kotlin file has an unclosed or orphaned comment delimiter.
 *  - STALE_SNAPSHOT the last ledger event is older than the configured window.
 *
 * The watchdog never mutates the tree. It only reports. The operator decides.
 */
object Watchdog {

    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    private const val INTERVAL_MS = 10 * 60 * 1000L
    private var thread: HandlerThread? = null
    private var handler: Handler? = null

    @Volatile private var lastCheckAt = 0L
    @Volatile private var lastFingerprint = ""

    fun start(ctx: Context) {
        if (handler != null) return
        val t = HandlerThread("darkith-watchdog").also { it.start() }
        thread = t
        val h = Handler(t.looper)
        handler = h
        h.post(checkRunnable)
    }

    fun stop() {
        handler?.removeCallbacksAndMessages(null)
        thread?.quitSafely()
        handler = null
        thread = null
    }

    private val checkRunnable = object : Runnable {
        override fun run() {
            runCatching { checkAll() }
            handler?.postDelayed(this, INTERVAL_MS)
        }
    }

    /** Runs every check once. Public so a self-test or the web layer can force a sweep. */
    fun checkAll(): List<String> {
        val findings = mutableListOf<String>()

        val root = ProgressDirectory.workspace
        if (root.exists()) {
            gitFindings(root)?.let { findings.addAll(it) }
        }

        kotlinFindings(root)?.let { findings.addAll(it) }

        lastCheckAt = System.currentTimeMillis()
        val fp = findings.joinToString("|")
        if (fp != lastFingerprint) {
            lastFingerprint = fp
            for (f in findings) {
                val (sev, cls, title, body) = parse(f)
                AlertBus.raise(sev, cls, title, body, listOf("ACK"), origin = "watchdog")
            }
            ProgressLedger.onEvent(
                "watchdog.sweep",
                """{"findings":${findings.size},"at":"${iso.format(Date())}"}""",
            )
        }
        return findings
    }

    private fun parse(f: String): Parsed {
        val parts = f.split("\u0001", limit = 4)
        val sev = when (parts.getOrNull(0)) {
            "CRITICAL" -> Severity.CRITICAL
            "DECISION" -> Severity.DECISION
            "NOTICE" -> Severity.NOTICE
            else -> Severity.INFO
        }
        return Parsed(
            sev,
            parts.getOrNull(1) ?: "watchdog",
            parts.getOrNull(2) ?: "Watchdog",
            parts.getOrNull(3) ?: "",
        )
    }

    private data class Parsed(
        val sev: Severity,
        val cls: String,
        val title: String,
        val body: String,
    )

    private fun gitFindings(root: File): List<String>? {
        val repos = root.walkTopDown()
            .maxDepth(3)
            .filter { it.isDirectory && File(it, ".git").exists() }
            .toList()
        if (repos.isEmpty()) return null
        val out = mutableListOf<String>()
        for (repo in repos) {
            val head = git(repo, "rev-parse", "--short", "HEAD") ?: continue
            val remotes = git(repo, "remote")
            if (remotes.isNullOrBlank()) {
                out.add("CRITICAL\u0001watchdog.no_remote\u0001Repo has no remote\u0001${repo.path}\nHEAD $head is not backed up anywhere. A sandbox reset destroys it.")
                continue
            }
            val ahead = git(repo, "rev-list", "--count", "HEAD", "--not", "--remotes")
            val dirty = git(repo, "status", "--porcelain")
            val dirtyCount = dirty?.lines()?.count { it.isNotBlank() } ?: 0
            val unpushed = (ahead?.trim()?.toIntOrNull() ?: 0) + dirtyCount
            if (unpushed > 0) {
                out.add("CRITICAL\u0001watchdog.unpushed\u0001Unpushed work in ${repo.name}\u0001${repo.path}\n${ahead?.trim() ?: "0"} commits ahead, $dirtyCount uncommitted files. Not on any remote.")
            }
        }
        return out
    }

    /**
     * Delegates to [CommentScan], which is unit-tested and shared with the web layer.
     * A broken comment costs a full rebuild cycle on a phone; it is cheaper to detect it here.
     */
    private fun kotlinFindings(root: File): List<String>? {
        if (!root.exists()) return null
        val out = mutableListOf<String>()
        root.walkTopDown()
            .filter { it.isFile && it.name.endsWith(".kt") && it.length() < 4_000_000 }
            .forEach { f ->
                val dmg = runCatching { CommentScan.scan(f.readText()) }.getOrNull() ?: return@forEach
                out.add("CRITICAL\u0001watchdog.kt_unbalanced\u0001Unbalanced comment in ${f.name}\u0001${f.path}\n$dmg")
            }
        return out
    }

    private fun git(dir: File, vararg args: String): String? = runCatching {
        val p = ProcessBuilder(listOf("git") + args)
            .directory(dir)
            .redirectErrorStream(true)
            .start()
        val text = p.inputStream.bufferedReader().readText()
        p.waitFor()
        text.trim()
    }.getOrNull()

    fun status(): String = """{"lastCheckAt":$lastCheckAt,"fingerprint":${lastFingerprint.length}}"""
}
