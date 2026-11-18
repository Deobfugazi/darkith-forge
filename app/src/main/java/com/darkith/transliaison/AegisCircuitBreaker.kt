package com.darkith.transliaison
import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.os.Build
import java.io.File

object AegisCircuitBreaker {
    fun checkAndRollback(context: Context) {
        // getHistoricalProcessExitReasons is API 30+. Calling it unguarded on Android 7-10
        // (minSdk 24) throws NoSuchMethodError inside onCreate BEFORE setContentView, so the
        // launcher Activity dies before the UI paints. Guard it and fall back to the
        // always-available exit marker check.
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val crashed = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val exitInfo = am.getHistoricalProcessExitReasons(context.packageName, 0, 1)
            exitInfo.isNotEmpty() && exitInfo[0].reason == ApplicationExitInfo.REASON_CRASH
        } else {
            false
        }
        if (crashed) {
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
