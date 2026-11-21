package com.darkith.transliaison.core

import android.content.Context
import android.webkit.JavascriptInterface

/**
 * Bridge that lets the hand-rolled web layer raise alerts on the physical device.
 *
 * Registered as "alert" next to the existing "darkith" bridge. Everything it accepts is
 * judged by [Formulary] before a window appears, so the web layer cannot bypass the gate.
 */
class AlertBridge(private val ctx: Context) {

    @JavascriptInterface
    fun raise(severity: String, cls: String, title: String, body: String, optionsCsv: String): String {
        val sev = runCatching {
            Severity.valueOf(severity.uppercase())
        }.getOrElse { Severity.NOTICE }
        val options = if (optionsCsv.isBlank()) emptyList() else optionsCsv.split(",")
        val verdict = AlertBus.raise(sev, cls, title, body, options, origin = "web")
        return verdict.name
    }

    @JavascriptInterface
    fun decide(id: String, choice: String): Boolean {
        AlertBus.acknowledge(id, choice)
        return true
    }

    @JavascriptInterface
    fun replay(): Int = AlertBus.replayHeld()

    @JavascriptInterface
    fun pending(): Int = AlertBus.pendingCount()

    @JavascriptInterface
    fun rules(): String = Formulary.ruleNames().joinToString(",")

    @JavascriptInterface
    fun version(): String = "alert-bridge-1"
}
