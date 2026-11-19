package com.darkith.transliaison

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import java.io.File

class ApkInstaller(private val context: Context) {

    companion object {
        const val ACTION = "com.darkith.INSTALL_STATUS"
        private const val TAG = "ApkInstaller"
    }

    fun install(apkFile: File): String {
        if (!apkFile.isFile) return "ERROR: apk not found: ${apkFile.absolutePath}"
        if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls()) {
            try {
                val i = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + context.packageName))
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(i)
            } catch (e: Exception) { Log.w(TAG, "settings intent failed: ${e.message}") }
            return "ERROR: allow 'Install unknown apps' for Darkith (settings opened), then run it again"
        }

        val pi = context.packageManager.packageInstaller
        var sessionId = -1
        var receiver: BroadcastReceiver? = null
        try {
            val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
            sessionId = pi.createSession(params)
            val session = pi.openSession(sessionId)
            try {
                session.openWrite("apk", 0, apkFile.length()).use { out ->
                    apkFile.inputStream().use { it.copyTo(out) }
                    session.fsync(out)
                }

                val rcv = object : BroadcastReceiver() {
                    override fun onReceive(c: Context, intent: Intent) {
                        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -999)
                        val msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)
                        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
                            val confirm: Intent? = if (Build.VERSION.SDK_INT >= 33)
                                intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                            else @Suppress("DEPRECATION") intent.getParcelableExtra(Intent.EXTRA_INTENT)
                            if (confirm != null) {
                                confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                try { c.startActivity(confirm) } catch (e: Exception) { Log.e(TAG, "confirm start failed: ${e.message}") }
                            } else Log.e(TAG, "pending user action without intent")
                            return
                        }
                        Log.i(TAG, "install finished: status=$status message=$msg")
                        try { context.unregisterReceiver(this) } catch (_: Exception) {}
                    }
                }
                receiver = rcv
                val filter = IntentFilter(ACTION)
                if (Build.VERSION.SDK_INT >= 33) context.registerReceiver(rcv, filter, Context.RECEIVER_NOT_EXPORTED)
                else context.registerReceiver(rcv, filter)

                val intent = Intent(ACTION).setPackage(context.packageName)
                val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                val pending = PendingIntent.getBroadcast(context, sessionId, intent, flags)
                session.commit(pending.intentSender)
            } finally {
                session.close()
            }
            return "OK: confirm prompt requested"
        } catch (e: Throwable) {
            try { receiver?.let { context.unregisterReceiver(it) } } catch (_: Exception) {}
            try { if (sessionId >= 0) pi.abandonSession(sessionId) } catch (_: Exception) {}
            return "ERROR: install failed: ${e.javaClass.simpleName}: ${e.message}"
        }
    }
}
