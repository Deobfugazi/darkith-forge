package com.darkith.transliaison.core

import android.content.Context
import android.util.Log
import java.io.File

/**
 * The IR handoff. Parses HTML intent, heals it with IRAuditor, and queues the IR into the LIVE
 * OmegaRenderer (the one on screen).
 *
 * C7: this class does NOT construct a renderer and does NOT tick the allocator. The control law
 * lives in OmegaRenderer.tickFrameBoundary, which runs first in onDrawFrame. If no live renderer
 * is attached, execute() refuses with "DEFICIT: C7" rather than forging into a phantom instance.
 */
class NativeForgeBuilder(private val context: Context) {

    private val engine = TransliaisonEngine()

    fun execute(html: String?, appName: String?, pkgName: String?): String {
        if (html.isNullOrBlank()) return "DEFICIT: HTML intent is empty."

        val renderer = OmegaRenderer.liveInstance
            ?: return "DEFICIT: C7 — no live OmegaRenderer attached"

        return try {
            val result = engine.translateWithReport(html)
            val mutableNodes = result.nodes.toMutableList()
            val healingLog = IRAuditor.healAndAudit(mutableNodes)

            if (healingLog.isNotEmpty()) {
                val ledger = File("/sdcard/Darkith/ledger/aegis.jsonl")
                ledger.parentFile?.mkdirs()
                ledger.appendText(healingLog.joinToString("\n") { "{\"event\": \"heal\", \"detail\": \"$it\"}" } + "\n")
                Log.w("NativeForge", "Autophagic Healer mutated IR:\n${healingLog.joinToString("\n")}")
            }

            // Queue the IR into the LIVE surface. Geometry is built in onDrawFrame within budget.
            renderer.applyLayoutNodes(mutableNodes)

            val budget = renderer.lastSafeVertexBudget
            val healStatus = if (healingLog.isNotEmpty()) "Healed ${healingLog.size} faults." else "Clean."
            "OK: Forged ${mutableNodes.size} nodes into live surface. $healStatus vB=$budget"
        } catch (e: Throwable) {
            Log.e("NativeForge", "Forge execution failed", e)
            "DEFICIT: ${e.javaClass.simpleName}: ${e.message}"
        }
    }
}
