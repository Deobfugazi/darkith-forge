package com.darkith.transliaison.core

/**
 * Plain data carrier between a resource allocator and whatever consumes its output.
 *
 * Units are part of the contract (SPI-37). Every field names one and is only ever filled
 * with that one:
 *   vertexBudget    VERTICES
 *   gpuConcurrency  draw calls
 *   resolutionScale fraction of native resolution, [0.5, 1.0]
 *   memoryResidual  BYTES, the signed distance from the affordable ceiling
 *   budgetCeiling   VERTICES the measured free RAM can pay for
 */
data class Allocation(
    val vertexBudget: Long,
    val gpuConcurrency: Int,
    val resolutionScale: Double,
    val memoryResidual: Double,
    val budgetCeiling: Double
)
