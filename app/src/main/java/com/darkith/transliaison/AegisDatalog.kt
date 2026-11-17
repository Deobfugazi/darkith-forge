package com.darkith.transliaison
import java.io.File

object AegisDatalog {
    private val factFile = File("/sdcard/Darkith/ledger/negative_datalog.jsonl")

    fun assertFailed(cls: String, fate: String, reason: String) {
        val entry = """{"cls":"$cls","fate":"$fate","outcome":"failed","reason":"$reason","ts":${System.currentTimeMillis()}}"""
        factFile.appendText(entry + "\n")
    }

    fun isBlacklisted(cls: String): Boolean {
        if (!factFile.exists()) return false
        return factFile.readLines().any { it.contains("\"cls\":\"$cls\"") && it.contains("\"outcome\":\"failed\"") }
    }
}
