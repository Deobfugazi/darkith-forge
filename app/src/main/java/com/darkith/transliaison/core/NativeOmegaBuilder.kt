package com.darkith.transliaison.core

import android.content.Context
import android.os.Handler
import android.os.Looper
import java.io.File

/**
 * Feeds live CPU load to the renderer's control law and reports its verdict.
 *
 * This class does NOT tick the allocator and does NOT own a governor. OmegaRenderer runs
 * the whole law at the frame boundary, on the GL thread, and its contract says callers must
 * not tick it themselves. A second allocator here ran on a different clock (16 ms handler
 * vs frame), which corrupted the integral term's dt and drove a stale Allocation into
 * apply() behind the frame's own decision. One control law, one clock, one actuator.
 */
class NativeOmegaBuilder(private val renderer: OmegaRenderer, private val context: Context) {
    private val handler = Handler(Looper.getMainLooper())

    private var lastCpuTotal = 0L
    private var lastCpuIdle = 0L
    private var isRunning = false
    @Volatile private var lastStatus = "omega: initializing"

    private val ticker = object : Runnable {
        override fun run() {
            if (!isRunning) return

            // Measure CPU from /proc/stat. Memory is measured by the renderer's own
            // providers, which the frame-boundary law reads directly — one source per input.
            val cpuLoad = try {
                val parts = File("/proc/stat").readLines()
                    .first { it.startsWith("cpu ") }
                    .split(Regex("\\s+")).filter { it.isNotEmpty() }.drop(1).map { it.toLong() }
                val idle = parts.getOrElse(3) { 0L } + parts.getOrElse(4) { 0L }
                val total = parts.sum()
                val dT = total - lastCpuTotal
                val dI = idle - lastCpuIdle
                lastCpuTotal = total; lastCpuIdle = idle
                if (dT > 0) (1.0 - dI.toDouble() / dT).coerceIn(0.0, 1.0) else 0.0
            } catch (e: Exception) { 0.5 }

            // Hand the measurement to the one control law, which runs at the frame boundary.
            renderer.cpuProvider = { cpuLoad }

            // Report what that law actually decided this frame, not a second opinion.
            val alloc = renderer.lastAlloc
            val coupling = renderer.lastCoupling
            lastStatus = "vB=" + (alloc?.vertexBudget ?: 0L) +
                " cpu=" + (cpuLoad * 100).toInt() + "%" +
                " oomSafe=" + (coupling?.selfOomSafe ?: true) +
                " pressure=" + String.format("%.3f", coupling?.systemPressure ?: 0.0)

            handler.postDelayed(this, 16L)
        }
    }

    fun start() {
        if (isRunning) return
        isRunning = true
        handler.post(ticker)
    }

    fun status(): String = lastStatus

    fun stop() {
        isRunning = false
        handler.removeCallbacks(ticker)
    }
}
