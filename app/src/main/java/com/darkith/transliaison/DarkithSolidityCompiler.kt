package com.darkith.transliaison

import java.io.File

/**
 * DarkithSolidityCompiler — on-device Solidity compiler.
 * Informed by the SmartIDE Solidity toolchain integration.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithSolidityCompiler(private val context: android.content.Context) {

    private val base = File("/sdcard/Darkith/donors/solidity-compiler")
    private val solc = File(base, "bin/solc")

    fun isAvailable(): Boolean = solc.exists() && solc.canExecute()

    fun status(): String = if (isAvailable()) "solidity ready" else "not installed"

    fun compile(solPath: String, outDir: String): String {
        if (!isAvailable()) return "ERROR: solc not installed"
        val src = File(solPath)
        if (!src.exists()) return "ERROR: solidity file not found: $solPath"
        val out = File(outDir).apply { mkdirs() }
        return try {
            ProcessBuilder(solc.absolutePath,
                "--bin", "--abi",
                "-o", out.absolutePath,
                src.absolutePath)
                .redirectErrorStream(true).start()
            "OK solc started"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }
}
