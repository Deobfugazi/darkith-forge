package com.darkith.transliaison.core

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.darkith.transliaison.ProgressDirectory
import com.darkith.transliaison.ProgressLedger
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.CopyOnWriteArrayList

/**
 * The single alert channel for Darkith.
 *
 * Every alert is written to the SD-card ledger BEFORE it is shown, so an alert that
 * cannot be delivered is still recorded and can be replayed. Nothing leaves the device:
 * no FCM, no Play Services, no notification provider. The only transport is a popup
 * window raised by [attach] on whichever Activity is currently on screen.
 *
 * The decision gate is [Formulary]: a pure function that maps an alert to ALLOW, HOLD,
 * or DENY. DENY is silent by construction and never reaches the UI.
 */
object AlertBus {

    /** A surface that can raise a popup. Registered by the live Activity. */
    interface Surface {
        fun showAlert(alert: Alert, onChoose: (String) -> Unit)
        fun dismissAlert(id: String)
    }

    private val iso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    private val main = Handler(Looper.getMainLooper())
    private val surfaces = CopyOnWriteArrayList<Surface>()
    private val pending = LinkedHashMap<String, Alert>()
    private val listeners = CopyOnWriteArrayList<(Alert) -> Unit>()

    private var seq = 0

    val ledgerFile: File
        get() {
            ProgressDirectory.ensure()
            return File(ProgressDirectory.ledger, "alerts.jsonl")
        }

    fun attach(surface: Surface) {
        surfaces.addIfAbsent(surface)
        main.post { drainTo(surface) }
    }

    fun detach(surface: Surface) {
        surfaces.remove(surface)
    }

    fun onAlert(listener: (Alert) -> Unit) {
        listeners.add(listener)
    }

    /** How many alerts are waiting for a surface. Surfaced to the web layer for diagnostics. */
    fun pendingCount(): Int = pending.size

    /**
     * Raise an alert. Returns the verdict so a caller can tell "denied" from "queued".
     * Delivery happens on the main thread; this is safe to call from any thread.
     */
    fun raise(
        severity: Severity,
        cls: String,
        title: String,
        body: String,
        options: List<String> = emptyList(),
        origin: String = "native",
    ): Verdict {
        val verdict = Formulary.judge(severity, cls, title, body)
        if (verdict == Verdict.DENY) {
            // Denied alerts are recorded as denied, never displayed.
            record(null, severity, cls, title, body, options, origin, verdict)
            return verdict
        }
        val alert = Alert(
            id = nextId(),
            ts = iso.format(Date()),
            severity = severity,
            cls = cls,
            title = title,
            body = body,
            options = options,
            origin = origin,
        )
        record(alert, severity, cls, title, body, options, origin, verdict)
        ProgressLedger.onEvent("alert.raise", """{"id":"${alert.id}","cls":"$cls","sev":"$severity"}""")
        main.post { deliver(alert) }
        return verdict
    }

    /** Re-raise anything that was HOLDed and never delivered (e.g. after a restart). */
    fun replayHeld(): Int {
        val f = ledgerFile
        if (!f.exists()) return 0
        var n = 0
        f.useLines { lines ->
            lines.filter { it.contains("\"verdict\":\"HOLD\"") }.forEach { row ->
                runCatching {
                    val o = JSONObject(row)
                    if (o.optString("delivered") == "false") {
                        val a = Alert(
                            id = o.optString("id"),
                            ts = o.optString("ts"),
                            severity = Severity.valueOf(o.optString("sev", "NOTICE")),
                            cls = o.optString("cls"),
                            title = o.optString("title"),
                            body = o.optString("body"),
                            options = o.optJSONArray("options")?.let { arr ->
                                (0 until arr.length()).map { arr.optString(it) }
                            } ?: emptyList(),
                            origin = o.optString("origin"),
                        )
                        pending[a.id] = a
                        n++
                    }
                }
            }
        }
        if (n > 0) main.post { surfaces.forEach { drainTo(it) } }
        return n
    }

    private fun nextId(): String {
        seq += 1
        return "A" + System.currentTimeMillis().toString(36) + "-" + seq.toString(36)
    }

    private fun deliver(alert: Alert) {
        val target = surfaces.lastOrNull()
        if (target == null) {
            // No window on screen: HOLD until a surface attaches.
            pending[alert.id] = alert
            return
        }
        target.showAlert(alert) { choice ->
            acknowledge(alert.id, choice)
        }
        listeners.forEach { runCatching { it(alert) } }
    }

    private fun drainTo(surface: Surface) {
        if (pending.isEmpty()) return
        val queued = pending.values.toList()
        pending.clear()
        queued.forEach { a -> surface.showAlert(a) { choice -> acknowledge(a.id, choice) } }
    }

    /** Record the operator's choice. A decision with no choice is a dismissal. */
    fun acknowledge(id: String, choice: String) {
        ProgressLedger.onEvent("alert.decide", """{"id":"$id","choice":${JSONObject.quote(choice)}}""")
        surfaces.forEach { runCatching { it.dismissAlert(id) } }
    }

    private fun record(
        alert: Alert?,
        severity: Severity,
        cls: String,
        title: String,
        body: String,
        options: List<String>,
        origin: String,
        verdict: Verdict,
    ) {
        runCatching {
            val o = JSONObject().apply {
                put("id", alert?.id ?: "-")
                put("ts", alert?.ts ?: iso.format(Date()))
                put("sev", severity.name)
                put("cls", cls)
                put("title", title)
                put("body", body)
                put("options", JSONArray(options))
                put("origin", origin)
                put("verdict", verdict.name)
                put("delivered", alert != null && verdict == Verdict.ALLOW)
            }
            val f = ledgerFile
            f.parentFile?.mkdirs()
            f.appendText(o.toString() + "\n")
        }
    }
}
