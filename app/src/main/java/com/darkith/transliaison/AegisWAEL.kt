package com.darkith.transliaison
import java.io.File
import java.security.MessageDigest

object AegisWAEL {
    private val waelFile = File("/sdcard/Darkith/wael/wael.jsonl")

    fun append(sessionId: String, seq: Int, donorHash: String, payloadHash: String, envelopeHash: String, fate: String) {
        val prevHash = if (waelFile.exists() && waelFile.length() > 0) {
            waelFile.readLines().lastOrNull()?.let {
                MessageDigest.getInstance("SHA-256")
                    .digest(it.toByteArray())
                    .joinToString("") { b -> "%02x".format(b) }
            } ?: "genesis"
        } else "genesis"

        val entry = """{"session":"$sessionId","seq":$seq,"donor":"$donorHash","payload":"$payloadHash","envelope":"$envelopeHash","fate":"$fate","prev":"$prevHash","ts":${System.currentTimeMillis()}}"""
        waelFile.appendText(entry + "\n")
    }
}
