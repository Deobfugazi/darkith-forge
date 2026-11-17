package com.darkith.transliaison
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.math.sqrt
object SynchronicityScheduler {
    @Volatile private var forgeLatch: CountDownLatch = CountDownLatch(2)
    @Volatile private var nonceVerified: Boolean = false
    @Volatile private var buildTimestamp: Long = 0L
    private const val BINDING_WINDOW_MS = 10_000L
    fun reset() { forgeLatch = CountDownLatch(2); nonceVerified = false; buildTimestamp = 0L }
    fun onBuildComplete(apkPath: String): String {
        buildTimestamp = System.currentTimeMillis()
        forgeLatch.countDown()
        val nonceArrived = try { forgeLatch.await(BINDING_WINDOW_MS, TimeUnit.MILLISECONDS) && nonceVerified } catch (_: InterruptedException) { false }
        return if (nonceArrived) "OK: SYNCHRONIZED" else "ERROR: TIMEOUT"
    }
    fun submitNonce(distance: Double): String {
        if (distance > 2.5) return "ERROR: NONCE_REJECTED"
        if (buildTimestamp == 0L) return "ERROR: NO_BUILD_PENDING"
        if (System.currentTimeMillis() - buildTimestamp > BINDING_WINDOW_MS) return "ERROR: NONCE_STALE"
        nonceVerified = true; forgeLatch.countDown(); return "OK: NONCE_ACCEPTED"
    }
    fun calculateBurnRate(c: DoubleArray, t: DoubleArray): Double {
        var sum = 0.0
        for (i in 0 until 7) { val n = c[i] / t[i]; sum += n * n }
        return sqrt(sum)
    }
    fun mintToken(c: DoubleArray, t: DoubleArray, d: Double, deltaZ: Double, apkHash: String): String? {
        if (deltaZ > 2.5) return null
        val b = calculateBurnRate(c, t)
        val vt = b * d
        return """{"event":"token_minted","value":$vt,"apk_hash":"$apkHash","delta_z":$deltaZ}"""
    }
}
