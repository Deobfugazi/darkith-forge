package com.darkith.transliaison

import java.io.File
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object ProgressDirectory {
    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }
    val root: File get() = File("/sdcard/Darkith")
    val meta: File get() = File(root, "_meta")
    val progress: File get() = File(root, "progress")
    val ledger: File get() = File(root, "ledger")
    val logs: File get() = File(root, "logs")
    val docs: File get() = File(root, "docs")
    val snapshots: File get() = File(root, "snapshots")
    val donors: File get() = File(root, "donors")
    val projects: File get() = File(root, "projects")
    val corpusIn: File get() = File(root, "corpus-in")
    val bootstrap: File get() = File(root, "bootstrap")
    val engine: File get() = File(root, "engine")
    val out: File get() = File(root, "out")
    val workspace: File get() = File(root, "workspace")

    fun ensure() {
        listOf(root, meta, progress, ledger, logs, docs, snapshots, donors,
               projects, corpusIn, bootstrap, engine, out, workspace).forEach { it.mkdirs() }
    }

    fun sha256(f: File): String {
        if (!f.exists()) return "missing"
        return try {
            val md = MessageDigest.getInstance("SHA-256")
            f.inputStream().use { ins ->
                val b = ByteArray(8192)
                while (true) {
                    val n = ins.read(b); if (n <= 0) break; md.update(b, 0, n)
                }
            }
            md.digest().joinToString("") { "%02x".format(it) }
        } catch (_: Throwable) { "error" }
    }

    fun writeMeta() {
        ensure()
        val now = iso.format(Date())
        val sessionId = "S-" + now.replace(":", "").replace("-", "")
        try {
            File(meta, "SESSION.json").writeText(
                "{\"session\":\"$sessionId\",\"start\":\"$now\"," +
                "\"device\":\"${android.os.Build.MODEL}\"," +
                "\"sdk\":${android.os.Build.VERSION.SDK_INT}}"
            )
        } catch (_: Throwable) {}

        val layout = "LOOSE FILES AT ROOT: NONE.\n" +
            "Audit (machine): ${File(ledger, "AUDIT.md").absolutePath}\n" +
            "Human:           ${File(docs, "PROGRESS.md").absolutePath}\n" +
            "Progress trail:  ${File(ledger, "progress.jsonl").absolutePath}\n" +
            "Ledger:          ${File(ledger, "ledger.jsonl").absolutePath}\n" +
            "Events:          ${File(ledger, "events.jsonl").absolutePath}\n" +
            "Labor trail:     ${File(ledger, "labor.jsonl").absolutePath}\n" +
            "Labor state:     ${File(ledger, "labor_state.json").absolutePath}\n" +
            "Runtime log:     ${File(logs, "darkith.log").absolutePath}\n" +
            "Build log:       ${File(logs, "build.log").absolutePath}\n" +
            "Merkle:          ${File(meta, "MERKLE.md").absolutePath}\n"
        try { File(meta, "LAYOUT.md").writeText(layout) } catch (_: Throwable) {}
        try { File(docs, "LAYOUT.md").writeText(layout) } catch (_: Throwable) {}

        val project = File("/data/data/com.termux/files/home/darkith-project")
        val merkle = StringBuilder()
        merkle.appendLine("# /sdcard/Darkith · MERKLE")
        merkle.appendLine()
        merkle.appendLine("Generated: $now")
        merkle.appendLine()
        merkle.appendLine("| path | sha256 |")
        merkle.appendLine("|---|---|")
        listOf(
            "app/src/main/assets/darkith_ui.html",
            "app/src/main/assets/donor_graft.js",
            "app/src/main/assets/files_module.js",
            "app/src/main/assets/runtime_splash.js",
            "app/src/main/assets/runtime_transitions.js",
            "app/src/main/assets/runtime_autophagic.js",
            "app/src/main/assets/vendor/shell-quote.js",
            "app/src/main/assets/vendor/darkith-rt.js",
            "app/src/main/java/com/darkith/transliaison/DarkithBridge.kt",
            "app/src/main/java/com/darkith/transliaison/MainActivity.kt",
            "app/src/main/java/com/darkith/transliaison/ProgressDirectory.kt",
            "app/src/main/java/com/darkith/transliaison/LaborClock.kt",
            "app/src/main/java/com/darkith/transliaison/AuditWriter.kt",
            "app/src/main/java/com/darkith/transliaison/ProgressLedger.kt"
        ).forEach { rel ->
            merkle.appendLine("| $rel | ${sha256(File(project, rel))} |")
        }
        try { File(meta, "MERKLE.md").writeText(merkle.toString()) } catch (_: Throwable) {}
    }
}
