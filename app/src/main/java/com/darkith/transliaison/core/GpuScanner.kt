package com.darkith.transliaison.core

import android.opengl.GLES20
import android.util.Log

/**
 * Queries the live GL context for its real limits and derives a hard byte ceiling for the
 * renderer's own allocations.
 *
 * GLES only. This device is a TECNO KM4k / MT6768 / Mali-G52 MC2, where Vulkan is the crash
 * path (verified device-lost) and GLES 3.2 is the stable path, so nothing here touches Vulkan.
 *
 * safetyCap() is deliberately conservative and total: it never returns 0, so a failed query
 * degrades to a small-but-usable cap instead of stalling the renderer.
 */
object GpuScanner {
    private const val TAG = "GpuScanner"
    private const val FLOOR_BYTES = 8L * 1024L * 1024L
    private const val RAM_FRACTION = 0.25
    private const val TEXTURE_FRACTION = 0.5

    @Volatile var lastMaxTextureSize: Int = 0; private set
    @Volatile var lastMaxTextureBytes: Long = 0L; private set
    @Volatile var lastCap: Long = 0L; private set

    /** Must run on the GL thread (needs a current context). Safe to call repeatedly. */
    fun scan(maxTextureSizeFromGl: Int = 0) {
        val size = if (maxTextureSizeFromGl > 0) maxTextureSizeFromGl else queryMaxTextureSize()
        lastMaxTextureSize = size
        lastMaxTextureBytes = size.toLong() * size.toLong() * 4L
        Log.d(TAG, "gpu scan: maxTextureSize=$size unit=${lastMaxTextureBytes / 1048576L}MB")
    }

    fun queryMaxTextureSize(): Int = try {
        val a = IntArray(1)
        GLES20.glGetIntegerv(GLES20.GL_MAX_TEXTURE_SIZE, a, 0)
        if (a[0] > 0) a[0] else 0
    } catch (e: Throwable) {
        0
    }

    /** freeRamBytes <= 0 means "unknown"; the cap then falls back to the texture budget. */
    fun safetyCap(freeRamBytes: Long, maxTextureSizeFromGl: Int = 0): Long {
        if (lastMaxTextureBytes == 0L) scan(maxTextureSizeFromGl)
        val texBudget = if (lastMaxTextureBytes > 0L) (lastMaxTextureBytes * TEXTURE_FRACTION).toLong() else 0L
        val ramBudget = if (freeRamBytes > 0L) (freeRamBytes * RAM_FRACTION).toLong() else 0L
        val cap = when {
            texBudget > 0L && ramBudget > 0L -> if (texBudget < ramBudget) texBudget else ramBudget
            texBudget > 0L -> texBudget
            ramBudget > 0L -> ramBudget
            else -> FLOOR_BYTES
        }.coerceAtLeast(FLOOR_BYTES)
        lastCap = cap
        return cap
    }
}
