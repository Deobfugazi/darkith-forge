package com.darkith.transliaison.core

/**
 * Alert vocabulary. Kept free of Android imports so the gate and the ledger format can be
 * exercised on a plain JVM, without a device or an emulator.
 */
enum class Verdict { ALLOW, HOLD, DENY }

enum class Severity { INFO, NOTICE, DECISION, CRITICAL }

data class Alert(
    val id: String,
    val ts: String,
    val severity: Severity,
    val cls: String,
    val title: String,
    val body: String,
    val options: List<String>,
    val origin: String,
)
