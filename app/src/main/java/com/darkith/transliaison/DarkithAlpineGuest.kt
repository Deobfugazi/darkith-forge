package com.darkith.transliaison

import java.io.File

/**
 * DarkithAlpineGuest — proot Alpine Linux guest.
 * Informed by the Acode proot Alpine integration.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithAlpineGuest(private val context: android.content.Context) {

    private val base = File("/sdcard/Darkith/donors/alpine-guest")
    private val proot = File(base, "proot")
    private val rootfs = File(base, "alpine")

    fun isAvailable(): Boolean = proot.exists() && rootfs.exists()

    fun status(): String = if (isAvailable()) "alpine ready" else "not installed"

    fun apkAdd(pkg: String): String {
        if (!isAvailable()) return "ERROR: alpine guest not installed"
        if (pkg.isBlank()) return "ERROR: package name required"
        return try {
            ProcessBuilder(proot.absolutePath,
                "-r", rootfs.absolutePath,
                "/bin/sh", "-c", "apk add --no-cache $pkg")
                .redirectErrorStream(true).start()
            "OK apk add $pkg started"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }
}
