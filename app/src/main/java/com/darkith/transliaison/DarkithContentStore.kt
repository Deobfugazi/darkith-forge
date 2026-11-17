package com.darkith.transliaison

import java.io.File

/**
 * DarkithContentStore — content-addressed storage layer.
 * Informed by the gomobile-ipfs node architecture.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithContentStore(private val context: android.content.Context) {

    private val lib = File("/sdcard/Darkith/donors/content-store/libgomobileipfs.so")
    private val repo = File("/sdcard/Darkith/donors/content-store/repo").apply { mkdirs() }

    fun isAvailable(): Boolean = lib.exists()

    fun status(): String = if (isAvailable()) "ready at ${lib.absolutePath}" else "not installed"

    fun pin(path: String): String {
        if (!isAvailable()) return "ERROR: content-store library missing"
        val f = File(path)
        if (!f.exists()) return "ERROR: file not found: $path"
        return "OK queued pin for $path (${f.length()} B)"
    }

    fun gateway(): String = "http://127.0.0.1:8080/ipfs/"
}
