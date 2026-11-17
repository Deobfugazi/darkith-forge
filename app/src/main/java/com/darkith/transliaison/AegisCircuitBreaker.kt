package com.darkith.transliaison
import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import java.io.File

object AegisCircuitBreaker {
    fun checkAndRollback(context: Context) {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val exitInfo = am.getHistoricalProcessExitReasons(context.packageName, 0, 1)
        if (exitInfo.isNotEmpty() && exitInfo[0].reason == ApplicationExitInfo.REASON_CRASH) {
            val marker = File(context.cacheDir, "aegis_last_patch.applied")
            if (marker.exists()) {
                marker.delete()
                AegisDatalog.assertFailed("__last_patch__", "APPLIED", "crash")
                android.util.Log.e("AEGIS", "CIRCUIT_BREAKER: prior boot crashed. Patch blacklisted.")
            }
        }
    }

    fun arm(context: Context) {
        File(context.cacheDir, "aegis_last_patch.applied").writeText(System.currentTimeMillis().toString())
    }
}
