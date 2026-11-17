package com.darkith.transliaison

import java.io.File

/**
 * DarkithChainReader — trustless Ethereum read layer.
 * Informed by the a16z/helios light client architecture.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithChainReader(private val context: android.content.Context) {

    private val bin = File("/sdcard/Darkith/donors/chain-reader/helios")
    private val dataDir = File("/sdcard/Darkith/donors/chain-reader/data").apply { mkdirs() }

    fun isAvailable(): Boolean = bin.exists() && bin.canExecute()

    fun start(executionRpc: String, network: String = "mainnet"): String {
        if (!isAvailable()) return "ERROR: chain-reader binary not at ${bin.absolutePath}"
        if (executionRpc.isBlank()) return "ERROR: executionRpc required"
        return try {
            val cmd = listOf(bin.absolutePath, "ethereum",
                "--execution-rpc", executionRpc,
                "--network", network,
                "--data-dir", dataDir.absolutePath,
                "--rpc-port", "8545")
            ProcessBuilder(cmd).redirectErrorStream(true).start()
            "OK chain-reader starting on 127.0.0.1:8545"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun localEndpoint(): String = "http://127.0.0.1:8545"
    fun status(): String = if (isAvailable()) "ready" else "not installed"
}
