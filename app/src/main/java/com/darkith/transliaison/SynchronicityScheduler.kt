package com.darkith.transliaison
import kotlin.math.sqrt
object SynchronicityScheduler {
    /*
     * Two-phase gate (human presence + finished build). The presence proof (the nonce) must be
     * ARMED BEFORE the build is shipped: the WebView call that ships the build is synchronous, so
     * the JavaScript thread that would have to submit the nonce is the very thread the build is
     * blocking. The earlier design (reset(), then wait 10 s inside onBuildComplete for a nonce
     * that nothing could deliver) could never pass and froze the caller for the whole window.
     * Now: onBuildComplete never blocks. It consumes one fresh armed nonce or fails fast.
     */
    @Volatile private var armedAtMs: Long = 0L
    @Volatile private var armedDistance: Double = Double.NaN
    private const val BINDING_WINDOW_MS = 10_000L
    private const val MAX_DISTANCE = 2.5
    private val lock = Any()

    fun reset() { synchronized(lock) { armedAtMs = 0L; armedDistance = Double.NaN } }

    /** Present the human-presence distance D (<= 2.5). Valid for BINDING_WINDOW_MS. */
    fun submitNonce(distance: Double): String {
        if (distance.isNaN() || distance > MAX_DISTANCE) return "ERROR: NONCE_REJECTED"
        synchronized(lock) { armedAtMs = System.currentTimeMillis(); armedDistance = distance }
        return "OK: NONCE_ACCEPTED"
    }

    /** Called after a build. Consumes the armed nonce (one nonce, one build). Never blocks. */
    fun onBuildComplete(apkPath: String): String {
        val now = System.currentTimeMillis()
        synchronized(lock) {
            val at = armedAtMs
            armedAtMs = 0L; armedDistance = Double.NaN
            if (at == 0L) return "ERROR: NONCE_REQUIRED (call submitNonce before shipping a build)"
            if (now - at > BINDING_WINDOW_MS) return "ERROR: NONCE_STALE"
            return "OK: SYNCHRONIZED"
        }
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
