package com.darkith.transliaison

import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object AuditWriter {
    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }
    private val proj: File get() = File("/sdcard/Darkith/out/packaged-src")
    private val src: File get() = File(proj, "app/src/main/assets")
    private val kot: File get() = File(proj, "app/src/main/java/com/darkith/transliaison")
    private val out: File get() = File(ProgressDirectory.ledger, "AUDIT.md")
    private val humanOut: File get() = File(ProgressDirectory.docs, "PROGRESS.md")
    private val apk: File get() = File("/sdcard/Download/DarkithForge.apk")

    fun write() {
        try {
            ProgressDirectory.ensure()
            val now = iso.format(Date())
            val apkSha = ProgressDirectory.sha256(apk)
            val apkSize = if (apk.exists()) apk.length() else 0L

            val bridge = File(kot, "DarkithBridge.kt")
            val bridgeText = if (bridge.exists()) bridge.readText() else ""
            val gaps = mutableListOf<String>()
            listOf("appendFile","deviceShell","deviceZip","deviceUnzipList",
                   "deviceUnzipExtract","getAuditMarkdown","laborTodaySeconds",
                   "laborCumulativeHours","emitProgressEvent").forEach { m ->
                if (!bridgeText.contains("fun $m")) gaps.add("DarkithBridge.$m")
            }
            if (!File(kot, "KotlinShellExec.kt").exists()) gaps.add("KotlinShellExec.kt")
            if (!File(src, "sigil.svg").exists()) gaps.add("sigil.svg")

            val done = 3.0
            val total = 24.0
            val pct = "%.1f".format(100.0 * done / total)

            val sb = StringBuilder()
            sb.appendLine("# DARKITH · AUDIT · LIVE")
            sb.appendLine()
            sb.appendLine("utc:      $now")
            sb.appendLine("device:   ${android.os.Build.MODEL} · android ${android.os.Build.VERSION.RELEASE} · ${android.os.Build.SUPPORTED_ABIS.firstOrNull() ?: "?"}")
            sb.appendLine("heap:     ${Runtime.getRuntime().maxMemory() / (1024 * 1024)} MB")
            sb.appendLine()
            sb.appendLine("## 1. PROGRESS")
            sb.appendLine()
            sb.appendLine("distinct orders: $total")
            sb.appendLine("done (weighted): $done")
            sb.appendLine("progress:        $pct%")
            sb.appendLine()
            sb.appendLine("## 2. LABOR")
            sb.appendLine()
            sb.appendLine("today_s:       ${LaborClock.todaySeconds()}")
            sb.appendLine("today_h:       %.2f".format(LaborClock.todaySeconds() / 3600.0))
            sb.appendLine("session_h:     %.4f".format(LaborClock.sessionHours()))
            sb.appendLine("cumulative_h:  %.4f".format(LaborClock.cumulativeHours()))
            sb.appendLine("session_start: ${LaborClock.sessionStartIso()}")
            sb.appendLine()
            sb.appendLine("## 3. ASSETS")
            sb.appendLine()
            listOf("darkith_ui.html","donor_graft.js","files_module.js",
                   "runtime_splash.js","runtime_transitions.js","runtime_autophagic.js",
                   "vendor/darkith-rt.js","vendor/shell-quote.js").forEach { rel ->
                val f = File(src, rel)
                if (f.exists()) sb.appendLine("  [x] $rel  ${f.length()} B  sha ${ProgressDirectory.sha256(f).take(16)}…")
                else sb.appendLine("  [ ] $rel  MISSING")
            }
            sb.appendLine()
            sb.appendLine("## 4. KOTLIN")
            sb.appendLine()
            kot.listFiles { f -> f.extension == "kt" }?.sortedBy { it.name }?.forEach { f ->
                sb.appendLine("  [x] ${f.name}  ${f.length()} B  sha ${ProgressDirectory.sha256(f).take(16)}…")
            }
            sb.appendLine()
            sb.appendLine("## 5. GAPS")
            sb.appendLine()
            if (gaps.isEmpty()) sb.appendLine("  (none)")
            else gaps.forEach { sb.appendLine("  [ ] $it") }
            sb.appendLine()
            sb.appendLine("## 6. DEPLOYED APK")
            sb.appendLine()
            if (apk.exists()) {
                sb.appendLine("  path:   ${apk.absolutePath}")
                sb.appendLine("  size:   $apkSize B")
                sb.appendLine("  sha256: $apkSha")
            } else sb.appendLine("  MISSING")
            sb.appendLine()
            sb.appendLine("## 7. LAST 20 EVENTS")
            sb.appendLine()
            val events = File(ProgressDirectory.ledger, "events.jsonl")
            if (events.exists()) events.readLines().takeLast(20).forEach { sb.appendLine("    $it") }
            else sb.appendLine("    (none)")
            sb.appendLine()
            sb.appendLine("## 8. LEDGER TAIL")
            sb.appendLine()
            val ledger = File(ProgressDirectory.ledger, "ledger.jsonl")
            if (ledger.exists()) {
                val lines = ledger.readLines()
                sb.appendLine("- lines: ${lines.size}")
                lines.takeLast(10).forEach { sb.appendLine("    $it") }
            } else sb.appendLine("    (none)")
            sb.appendLine()
            sb.appendLine("## 9. BUILD LOG TAIL")
            sb.appendLine()
            val blog = File(ProgressDirectory.logs, "build.log")
            if (blog.exists()) {
                val lines = blog.readLines()
                sb.appendLine("- lines: ${lines.size}")
                lines.takeLast(50).forEach { sb.appendLine("    $it") }
            } else sb.appendLine("    (none)")
            sb.appendLine()
            sb.appendLine("## 10. AUTOPHAGIC POOL")
            sb.appendLine()
            val plog = File(ProgressDirectory.logs, "darkith.log")
            if (plog.exists()) {
                val lines = plog.readLines()
                val auto = lines.filter { it.contains("AUTOPHAGIC") }
                sb.appendLine("- log lines: ${lines.size}")
                sb.appendLine("- AUTOPHAGIC tagged: ${auto.size}")
                auto.takeLast(3).forEach { sb.appendLine("    $it") }
            } else sb.appendLine("    (none)")
            sb.appendLine()
            sb.appendLine("═══════════════════════════════════════════════════════════════")
            sb.appendLine("  A + (−A) = S ≠ 0")
            sb.appendLine("═══════════════════════════════════════════════════════════════")

            out.writeText(sb.toString())

            val pb = StringBuilder()
            pb.appendLine("# DARKITH · PROGRESS")
            pb.appendLine()
            pb.appendLine("| field | value |")
            pb.appendLine("|---|---|")
            pb.appendLine("| utc | $now |")
            pb.appendLine("| progress | $pct % |")
            pb.appendLine("| done | $done / $total |")
            pb.appendLine("| today (h) | %.2f |".format(LaborClock.todaySeconds() / 3600.0))
            pb.appendLine("| session (h) | %.4f |".format(LaborClock.sessionHours()))
            pb.appendLine("| cumulative (h) | %.4f |".format(LaborClock.cumulativeHours()))
            pb.appendLine()
            pb.appendLine("## APK")
            pb.appendLine("- path: `${apk.absolutePath}`")
            pb.appendLine("- sha256: `$apkSha`")
            pb.appendLine("- size: $apkSize B")
            pb.appendLine()
            pb.appendLine("## Gaps")
            gaps.forEach { pb.appendLine("- $it") }
            humanOut.writeText(pb.toString())

            val row = "{\"ts\":\"$now\",\"class\":\"audit.cycle\",\"pct\":$pct,\"today_s\":${LaborClock.todaySeconds()},\"cum_h\":${"%.4f".format(LaborClock.cumulativeHours())}}"
            File(ProgressDirectory.ledger, "progress.jsonl").appendText(row + "\n")
        } catch (_: Throwable) {}
    }
}
