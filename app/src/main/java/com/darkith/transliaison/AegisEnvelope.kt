package com.darkith.transliaison
import java.security.MessageDigest

object AegisEnvelope {
    data class Envelope(val hash: String, val allowedFates: Set<String>, val allowedClasses: Set<String>)

    fun create(donorHash: String, payloadHash: String, fates: Set<String>, classes: Set<String>): Envelope {
        val canonical = "$donorHash|$payloadHash|${fates.sorted().joinToString(",")}|${classes.sorted().joinToString(",")}"
        val hash = MessageDigest.getInstance("SHA-256")
            .digest(canonical.toByteArray())
            .joinToString("") { "%02x".format(it) }
        return Envelope(hash, fates, classes)
    }
}
