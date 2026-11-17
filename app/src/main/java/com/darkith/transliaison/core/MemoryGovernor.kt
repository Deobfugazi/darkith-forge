package com.darkith.transliaison.core

import java.util.concurrent.atomic.AtomicLong

/**
 * Prevents the app from throwing its own java.lang.OutOfMemoryError by keeping tracked
 * allocations under a safety fraction of Runtime.maxMemory(). 
 * 
 * It does NOT prevent Android's lmkd from killing the process (lmkd evaluates system-wide
 * pressure and oom_adj_score, not app-internal bookkeeping). It only keeps the app's own
 * internal heap pristine.
 */
class MemoryGovernor(
    private val maxAppHeapBytes: Long = Runtime.getRuntime().maxMemory(),
    private val selfOomThreshold: Double = 0.80,
    private val warnMargin: Double = 0.05,
    private val relaxBelow: Double = 0.50,
    private val relaxCeiling: Double = 0.60,
    private val couplingRatio: Double = 0.40,
    private val minBudgetBytes: Long = 4L * 1024 * 1024
) {
    private val rendererBudget = AtomicLong(maxAppHeapBytes / 3)
    private val modelBudget = AtomicLong(maxAppHeapBytes / 2)

    init {
        require(maxAppHeapBytes > 0) { "maxAppHeapBytes must be positive" }
        require(selfOomThreshold in 0.0..1.0) { "selfOomThreshold must be in [0,1]" }
        require(minBudgetBytes in 1..maxAppHeapBytes) { "minBudgetBytes must be in [1, maxAppHeapBytes]" }
    }

    private val maxBudgetEach = (maxAppHeapBytes * selfOomThreshold).toLong().coerceAtLeast(minBudgetBytes)

    fun reciprocate(rendererAllocatedBytes: Long, modelAllocatedBytes: Long): CouplingAllocation {
        val r = rendererAllocatedBytes.coerceAtLeast(0L)
        val m = modelAllocatedBytes.coerceAtLeast(0L)
        val totalAllocated = r + m
        val currentPressure = totalAllocated.toDouble() / maxAppHeapBytes.toDouble()
        val warnLine = selfOomThreshold - warnMargin

        if (currentPressure > warnLine) {
            // Overshoot measured against WARNING line, so it's >= 0 throughout this branch.
            // totalAllocated > 0 is guaranteed here because currentPressure > warnLine > 0.
            val overshoot = (totalAllocated - (maxAppHeapBytes * warnLine).toLong()).coerceAtLeast(0L)
            val rendererShare = r.toDouble() / totalAllocated.toDouble()
            if (rendererShare > couplingRatio) {
                rendererBudget.updateAndGet { (it - overshoot).coerceAtLeast(minBudgetBytes) }
            } else {
                modelBudget.updateAndGet { (it - overshoot).coerceAtLeast(minBudgetBytes) }
            }
        } else if (currentPressure < relaxBelow) {
            val headroom = ((maxAppHeapBytes * relaxCeiling).toLong() - totalAllocated).coerceAtLeast(0L)
            val grow = headroom / 4
            rendererBudget.updateAndGet { (it + grow).coerceAtMost(maxBudgetEach) }
            modelBudget.updateAndGet { (it + grow).coerceAtMost(maxBudgetEach) }
        }

        return CouplingAllocation(
            rendererMaxBytes = rendererBudget.get(),
            modelMaxBytes = modelBudget.get(),
            systemPressure = currentPressure,
            selfOomSafe = currentPressure < selfOomThreshold
        )
    }
}

data class CouplingAllocation(
    val rendererMaxBytes: Long,
    val modelMaxBytes: Long,
    val systemPressure: Double,
    /** True if this process's OWN heap usage is under its own OOM threshold. */
    val selfOomSafe: Boolean
)
