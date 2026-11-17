package com.darkith.transliaison.core

import java.io.File

/**
 * A bounded PID-style controller mapping measured free RAM, measured GPU-side memory use,
 * CPU load, and frame time to a vertex budget / GPU concurrency / resolution scale.
 *
 * Structural guarantees: V_k never leaves [vMin, vMax] regardless of input, the
 * integral term is reset (anti-windup) whenever a step would leave those bounds, and no
 * division by zero or NaN can escape tick() for any finite, non-negative input.
 * Reads actual device RAM from /proc/meminfo at construction time instead of hardcoding a guess.
 */
class AutophagicAllocator(
    totalRamBytesOverride: Long? = null,
    private val vMin: Double = 65_536.0,
    private val vMax: Double = 524_288.0,
    private val alpha: Double = 0.45,
    private val beta: Double = 0.08,
    private val gamma: Double = 0.15,
    private val lambda: Double = 0.25,
    private val mu: Double = 0.40
) {
    val totalRamBytes: Long = totalRamBytesOverride ?: readTotalRamBytes() ?: 3_925_000_000L

    private var vK = (vMin + vMax) / 2.0
    private var sK = 1.0
    private var integral = 0.0
    private var lastError = 0.0
    private var lastTs = System.nanoTime()

    private fun readTotalRamBytes(): Long? = try {
        File("/proc/meminfo").useLines { lines ->
            lines.firstOrNull { it.startsWith("MemTotal:") }
                ?.let { Regex("(\\d+)").find(it)?.groupValues?.get(1)?.toLongOrNull()?.times(1024L) }
        }
    } catch (e: Exception) {
        null
    }

    fun tick(freeRamBytes: Long, gpuMemBytes: Long, cpuLoad: Double, frameMs: Double): Allocation {
        val now = System.nanoTime()
        val dt = ((now - lastTs) / 1e9).coerceAtLeast(1e-3) // floor dt so a stalled clock can't divide by ~0
        lastTs = now

        val safeFreeRam = freeRamBytes.coerceAtLeast(0L).toDouble()
        val safeGpuMem = gpuMemBytes.coerceAtLeast(0L).toDouble()
        val safeCpuLoad = cpuLoad.coerceIn(0.0, 1.0)
        val safeFrameMs = if (frameMs.isFinite() && frameMs > 0.0) frameMs else 16.6

        val mBudget = (alpha * safeFreeRam * (1.0 - beta * safeCpuLoad)).coerceAtLeast(1.0)
        val error = mBudget - safeGpuMem
        integral += error * dt

        val p = 0.12 * error
        val i = 0.004 * integral
        val d = 0.08 * (error - lastError) / dt
        var vNext = vK + p + i + d
        if (vNext <= vMin || vNext >= vMax) integral = 0.0 // anti-windup
        vNext = vNext.coerceIn(vMin, vMax)
        vK = vNext
        lastError = error

        val cGpu = (8.0 * (1.0 - safeCpuLoad) / (1.0 + gamma * maxOf(0.0, safeFrameMs - 16.6)))
            .takeIf { it.isFinite() }?.toInt()?.coerceIn(1, 8) ?: 1

        val memPressure = (error / mBudget).coerceIn(-10.0, 10.0) // bounded even if mBudget is tiny
        val framePressure = (maxOf(0.0, safeFrameMs - 16.6) / 16.6).coerceAtMost(10.0)
        var sNext = sK * (1.0 - lambda * memPressure - mu * framePressure)
        if (!sNext.isFinite()) sNext = sK
        sK = sNext.coerceIn(0.5, 1.0)

        return Allocation(
            vertexBudget = vK.toLong(),
            gpuConcurrency = cGpu,
            resolutionScale = sK,
            memoryResidual = error,
            budgetCeiling = mBudget
        )
    }
}
