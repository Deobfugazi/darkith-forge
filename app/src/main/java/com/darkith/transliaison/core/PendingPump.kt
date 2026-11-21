package com.darkith.transliaison.core

import android.os.Handler
import android.os.Looper
import java.io.File

/**
 * The Android side of [Pending]: a Handler for the tick and a file for the receipts.
 *
 * Kept apart from [Pending] so the decision logic stays pure and testable on a plain JVM —
 * `tools/tests/run.sh` compiles [Pending] with no android.jar on the classpath.
 */
object PendingPump {

    private var handler: Handler? = null
    private var tick: Runnable? = null

    /** Start the sweep. Safe to call twice; the second call is a no-op. */
    fun start(ledgerFile: File = File("/sdcard/Darkith/ledger/decisions.jsonl")) {
        if (tick != null) return
        Pending.ledger = Pending.Ledger { line ->
            try {
                ledgerFile.parentFile?.mkdirs()
                ledgerFile.appendText(line + "\n")
            } catch (_: Throwable) {
                // A full or unmounted card must not take the process down. The decision
                // still resolves; it only loses its receipt.
            }
        }
        val h = Handler(Looper.getMainLooper())
        handler = h
        val r = object : Runnable {
            override fun run() {
                Pending.sweep()
                h.postDelayed(this, TICK_MS)
            }
        }
        tick = r
        h.postDelayed(r, TICK_MS)
    }

    fun stop() {
        tick?.let { handler?.removeCallbacks(it) }
        tick = null
        handler = null
    }

    private const val TICK_MS = 30_000L
}
