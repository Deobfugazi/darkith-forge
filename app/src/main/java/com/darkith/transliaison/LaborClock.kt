package com.darkith.transliaison

import android.os.SystemClock
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object LaborClock {
    private const val ACTIVE_WINDOW_MS = 5L * 60L * 1000L
    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }
    private val trail: File get() = File(ProgressDirectory.ledger, "labor.jsonl")
    private val state: File get() = File(ProgressDirectory.ledger, "labor_state.json")
    private var lastTick = 0L
    private var cumulativeSeconds = 0L
    private var sessionStart = 0L
    @Volatile private var lastEventAt = 0L

    fun start() {
        lastTick = SystemClock.elapsedRealtime()
        sessionStart = System.currentTimeMillis()
        try {
            if (state.exists()) {
                val j = JSONObject(state.readText())
                cumulativeSeconds = j.optLong("cumulative_seconds", 0L)
            }
        } catch (_: Throwable) {}
    }
    fun onEvent() { lastEventAt = SystemClock.elapsedRealtime() }
    fun tick() {
        val now = SystemClock.elapsedRealtime()
        val delta = now - lastTick
        lastTick = now
        if (delta <= 0L || delta > 10_000L) return
        if (lastEventAt == 0L || (now - lastEventAt) >= ACTIVE_WINDOW_MS) return
        val sec = delta / 1000L
        if (sec <= 0L) return
        cumulativeSeconds += sec
        try {
            ProgressDirectory.ensure()
            val nowStr = iso.format(Date())
            val row = JSONObject()
                .put("ts", nowStr)
                .put("day", nowStr.substring(0, 10))
                .put("seconds", sec)
                .put("cumulative", cumulativeSeconds)
            trail.appendText(row.toString() + "\n")
        } catch (_: Throwable) {}
    }
    fun todaySeconds(): Long {
        val day = iso.format(Date()).substring(0, 10)
        if (!trail.exists()) return 0L
        var sum = 0L
        try {
            trail.forEachLine { line ->
                try {
                    val j = JSONObject(line)
                    if (j.optString("day") == day) sum += j.optLong("seconds", 0L)
                } catch (_: Throwable) {}
            }
        } catch (_: Throwable) {}
        return sum
    }
    fun cumulativeHours(): Double = cumulativeSeconds / 3600.0
    fun sessionHours(): Double =
        if (sessionStart == 0L) 0.0 else (System.currentTimeMillis() - sessionStart) / 3_600_000.0
    fun sessionStartIso(): String =
        if (sessionStart == 0L) "" else iso.format(Date(sessionStart))
    fun persist() {
        try {
            ProgressDirectory.ensure()
            state.writeText(
                JSONObject()
                    .put("cumulative_seconds", cumulativeSeconds)
                    .put("saved_at", iso.format(Date()))
                    .toString()
            )
        } catch (_: Throwable) {}
    }
}
