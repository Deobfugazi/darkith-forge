package com.darkith.transliaison.core

import android.content.Context
import android.os.Debug
import android.os.Handler
import android.os.Looper
import java.io.File

class NativeOmegaBuilder(private val renderer: OmegaRenderer, private val context: Context) {
    private val allocator = AutophagicAllocator()
    private val governor = MemoryGovernor()
    private val handler = Handler(Looper.getMainLooper())
    
    private var lastCpuTotal = 0L
    private var lastCpuIdle = 0L
    private var isRunning = false
    @Volatile private var lastStatus = "omega: initializing"

    private val ticker = object : Runnable {
        override fun run() {
            if (!isRunning) return
            
            // Measure memory
            val freeRam = Debug.getNativeHeapFreeSize()
            val usedRam = Debug.getNativeHeapAllocatedSize()
            
            // Measure CPU from /proc/stat
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

            // 1. Autophagic Allocator derives the frame budget
            val allocation = allocator.tick(freeRam, usedRam, cpuLoad, renderer.lastFrameMs.toDouble())
            
            // 2. Governor asserts internal heap safety and reciprocally throttles memory
            val coupling = governor.reciprocate(usedRam, allocation.vertexBudget)
            lastStatus = "vB=" + allocation.vertexBudget + " cpu=" + (cpuLoad * 100).toInt() + "% oomSafe=" + coupling.selfOomSafe
            if (!coupling.selfOomSafe) {
                // Structurally bypassed: the governor has clamped the budgets. 
                // In a real LLM runtime, this is where the model's KV cache trim is enforced.
            }

            // 3. Renderer consumes the invariantly mapped Allocation
            renderer.apply(allocation)
            
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
