package com.darkith.transliaison

/**
 * DarkithEVMKit — native multi-chain EVM surface.
 * Informed by the horizontalsystems/ethereum-kit-android library.
 * Darkith-native surface. Donor is origin, not identity.
 */
class DarkithEVMKit(private val context: android.content.Context) {

    fun isAvailable(): Boolean = try {
        Class.forName("io.horizontalsystems.ethereumkit.core.EthereumKit")
        true
    } catch (_: Throwable) { false }

    fun status(): String = if (isAvailable()) "evm-kit loaded" else "library not in build.gradle"

    fun supportedChains(): String = listOf(
        "Ethereum", "Binance Smart Chain", "Avalanche",
        "Arbitrum", "Optimism", "Polygon"
    ).joinToString(",")
}
