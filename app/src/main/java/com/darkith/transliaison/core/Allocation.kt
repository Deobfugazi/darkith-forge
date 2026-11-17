package com.darkith.transliaison.core

/** Plain data carrier between a resource allocator and whatever consumes its output. */
data class Allocation(
    val vertexBudget: Long,
    val gpuConcurrency: Int,
    val resolutionScale: Double,
    val memoryResidual: Double,
    val budgetCeiling: Double
)
