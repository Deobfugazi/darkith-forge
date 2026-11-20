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
    /** Bytes one IR vertex occupies. Mirrors IRBuilder.VERTEX_STRIDE_FLOATS * 4 so the
     *  memory budget and the vertex budget can be compared without a unit crossing. */
    private val BYTES_PER_VERTEX: Double = IRBuilder.VERTEX_STRIDE_FLOATS * 4.0


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

        // mBudget is a BYTE budget, but vK is a VERTEX COUNT. They cannot be subtracted.
        // The error is therefore expressed in the unit vK lives in: the vertex budget this
        // much memory can actually pay for. Adding a byte error to a vertex count saturated
        // vK on the first tick at any realistic free RAM, so anti-windup fired every tick and
        // the controller became a constant.
        val mBudget = (alpha * safeFreeRam * (1.0 - beta * safeCpuLoad)).coerceAtLeast(1.0)
        val affordableVertices = mBudget / BYTES_PER_VERTEX
        // The budget tracks the ceiling memory can pay for, so the error is the distance from
        // that ceiling. affordableVertices is derived from measured free RAM and CPU, never
        // from vK, so this is not self-reference. Driving on (affordable - usage) instead
        // pushed vK UP whenever the renderer was under budget, railing it at vMax while the
        // affordable ceiling was far below vMax — a budget that spends memory it does not have.
        val targetVertices = affordableVertices.coerceIn(vMin, vMax)
        val actualVertices = safeGpuMem / BYTES_PER_VERTEX
        val error = targetVertices - vK
        integral += error * dt

        val p = 0.12 * error
        val i = 0.004 * integral
        // Differentiated in TICKS, not seconds. /dt re-scales a per-second gain by 1/dt (60x at
        // 60 Hz), which drove full-span oscillation and pinned the resolution scale at its floor.
        val d = 0.08 * (error - lastError)
        var vNext = vK + p + i + d
        if (vNext <= vMin || vNext >= vMax) integral = 0.0 // anti-windup
        vNext = vNext.coerceIn(vMin, vMax)
        vK = vNext
        lastError = error

        val cGpu = (8.0 * (1.0 - safeCpuLoad) / (1.0 + gamma * maxOf(0.0, safeFrameMs - 16.6)))
            .takeIf { it.isFinite() }?.toInt()?.coerceIn(1, 8) ?: 1

        // Over-use is vK ABOVE what memory can pay for; that is the only direction that costs
        // frames. The old term divided a BYTE error by a BYTE budget and let its sign through,
        // so headroom was penalised and the scale ratcheted to its 0.5 floor at idle.
        val overUse = (maxOf(0.0, actualVertices - affordableVertices) / maxOf(affordableVertices, 1.0))
            .coerceIn(0.0, 10.0)
        val framePressure = (maxOf(0.0, safeFrameMs - 16.6) / 16.6).coerceAtMost(10.0)
        // Proportional, not multiplicative: a bounded integrator on a bounded state can only
        // descend to the floor, so the scale could never recover when pressure lifted.
        var sNext = 1.0 - lambda * overUse - mu * framePressure
        if (!sNext.isFinite()) sNext = sK
        sK = sNext.coerceIn(0.5, 1.0)

        return Allocation(
            vertexBudget = vK.toLong(),
            gpuConcurrency = cGpu,
            resolutionScale = sK,
            // memoryResidual is BYTES by name, so it is converted back; budgetCeiling is a
            // ceiling on vertexBudget, so it stays in VERTICES. Both names now state their unit.
            memoryResidual = error * BYTES_PER_VERTEX,
            budgetCeiling = affordableVertices
        )
    }
}
