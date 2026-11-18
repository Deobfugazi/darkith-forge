package com.darkith.transliaison

import android.content.Context
import android.os.Handler
import android.os.HandlerThread
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object ProgressLedger {
    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }
    private const val TICK_MS = 1_000L
    private const val AUDIT_MS = 30_000L
    @Volatile private var running = false
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var lastAuditAt = 0L

    fun start(ctx: Context) {
        if (running) return
        running = true
        ProgressDirectory.ensure()
        ProgressDirectory.writeMeta()
        LaborClock.start()
        thread = HandlerThread("darkith-progress").also { it.start() }
        val h = thread?.looper?.let { Handler(it) }
        handler = h
        h?.post(tickRunnable)
        onEvent("progress.ledger.start", "{\"pkg\":\"${ctx.packageName}\"}")
    }
    fun stop() {
        running = false
        LaborClock.persist()
        onEvent("progress.ledger.stop", "{}")
        handler?.removeCallbacksAndMessages(null)
        thread?.quitSafely()
        thread = null
        handler = null
    }
    fun onEvent(cls: String, detailsJson: String) {
        try {
            ProgressDirectory.ensure()
            LaborClock.onEvent()
            val safe = if (detailsJson.isBlank()) "{}" else detailsJson
            val row = "{\"ts\":\"${iso.format(Date())}\",\"class\":\"$cls\",\"details\":$safe}"
            File(ProgressDirectory.ledger, "events.jsonl").appendText(row + "\n")
            File(ProgressDirectory.ledger, "ledger.jsonl").appendText(row + "\n")
        } catch (_: Throwable) {}
    }
    private val tickRunnable = object : Runnable {
        override fun run() {
            if (!running) return
            try {
                LaborClock.tick()
                val now = System.currentTimeMillis()
                if (now - lastAuditAt >= AUDIT_MS) {
                    AuditWriter.write()
                    lastAuditAt = now
                }
                LaborClock.persist()
            } catch (_: Throwable) {}
            handler?.postDelayed(this, TICK_MS)
        }
    }
}
