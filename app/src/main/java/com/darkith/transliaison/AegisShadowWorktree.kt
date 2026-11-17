package com.darkith.transliaison
import java.io.File

object AegisShadowWorktree {
    // Apps cannot write to /dev/shm or /data/local/tmp. java.io.tmpdir is the app cache dir on Android.
    private fun shadowBase(): File =
        File(System.getProperty("java.io.tmpdir") ?: throw IllegalStateException("no java.io.tmpdir"), "aegis_shadow")

    fun create(donorPath: String, payloadPath: String): File {
        val shadowDir = File(shadowBase(), "session_${System.currentTimeMillis()}")
        shadowDir.mkdirs()
        File(donorPath).copyTo(File(shadowDir, "donor.apk"), overwrite = true)
        File(payloadPath).copyTo(File(shadowDir, "payload.dex"), overwrite = true)
        return shadowDir
    }

    fun destroy(shadowDir: File) {
        shadowDir.deleteRecursively()
    }
}
