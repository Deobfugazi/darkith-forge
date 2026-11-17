package com.darkith.transliaison

object AegisOracle {
    data class Collision(val descriptor: String, val classification: String, val reason: String)
    data class CollisionMap(val fatal: List<Collision>, val resolvable: List<Collision>, val benign: List<Collision>)

    fun predict(
        donorClasses: Set<String>,
        payloadClasses: Set<String>,
        donorReachable: Set<String>,
        methodShapeEqual: Set<String>
    ): CollisionMap {
        val intersection = donorClasses.intersect(payloadClasses)
        val fatal = mutableListOf<Collision>()
        val resolvable = mutableListOf<Collision>()
        val benign = mutableListOf<Collision>()

        for (c in intersection) {
            when {
                !donorReachable.contains(c) -> benign.add(Collision(c, "BENIGN", "not-reachable"))
                methodShapeEqual.contains(c) -> resolvable.add(Collision(c, "ABSORB", "byte-equal-method-shape"))
                else -> fatal.add(Collision(c, "FATAL", "overlap+reachable+shape-diff"))
            }
        }
        return CollisionMap(fatal, resolvable, benign)
    }
}
