package com.darkith.transliaison.core

/**
 * Couples an alert to a timer so a decision the operator never saw still resolves.
 *
 * The gap this closes: [DecisionProtocol] is a table, and a table with no caller decides
 * nothing. Before this, an alert could be raised, missed, and sit open forever — the
 * backlog the protocol exists to prevent. This object holds the live decisions, and a
 * caller ticks it; each expiry goes through [DecisionProtocol.onTimeout].
 *
 * Pure Kotlin: no Android imports, no clock of its own. [sweep] takes `now` and the ledger
 * is an injected sink, so the whole thing is provable on a plain JVM.
 * `PendingPump.kt` supplies the Handler and the SD-card file.
 *
 * On every expiry two things happen, in this order:
 *  1. the outcome is written to the ledger, so a missed alert leaves a record even if the
 *     process dies immediately afterwards;
 *  2. only then is the outcome applied.
 *
 * A DESTRUCTIVE class never reaches step 2: [DecisionProtocol] returns Escalate, which is
 * logged and counted as backlog, never applied. That ordering is the invariant — the log
 * must not depend on the action succeeding.
 */
object Pending {

    /** One unresolved decision. [expiresAt] is absolute, so a restart can resume it. */
    data class Decision(
        val id: String,
        val cls: String,
        val title: String,
        val raisedAt: Long,
        val expiresAt: Long,
        val payload: Map<String, String> = emptyMap(),
    )

    /** Where receipts go. The Android shell points this at the SD card. */
    fun interface Ledger { fun write(line: String) }

    private val lock = Any()
    private val live = LinkedHashMap<String, Decision>()
    private val escalated = HashSet<String>()
    private var seq = 0

    /** Applied when a decision auto-completes. */
    var onAutoComplete: ((Decision, String) -> Unit)? = null

    /** Called when a decision escalates. It stays live. */
    var onEscalate: ((Decision, String) -> Unit)? = null

    var ledger: Ledger? = null

    /** Register a decision. Returns it so the caller can resolve it by id. */
    fun raise(cls: String, title: String, payload: Map<String, String> = emptyMap()): Decision {
        val now = System.currentTimeMillis()
        val timeout = DecisionProtocol.timeoutMs(cls)
        val d = Decision(
            id = "d" + (++seq) + "-" + now,
            cls = cls,
            title = title,
            raisedAt = now,
            // A class with no timeout is due immediately: it cannot auto-complete, but it
            // must still reach sweep so it escalates. Long.MAX_VALUE would make it invisible
            // to the timer and it would sit silently forever — the defect this file fixes.
            expiresAt = if (timeout > 0L) now + timeout else now,
            payload = payload,
        )
        synchronized(lock) { live[d.id] = d }
        log("raised", d, DecisionProtocol.riskOf(cls).name)
        return d
    }

    /** The operator answered. Removes it so the timer can never fire on it. */
    fun resolve(id: String, choice: String) {
        val d = synchronized(lock) { live.remove(id) } ?: return
        log("resolved", d, choice)
    }

    /** Everything still open, oldest first. This is the backlog. */
    fun open(): List<Decision> = synchronized(lock) {
        live.values.sortedBy { it.raisedAt }
    }

    fun backlogSize(): Int = synchronized(lock) { live.size }

    /** One pass over the live set. [now] is injectable so tests need no clock. */
    fun sweep(now: Long = System.currentTimeMillis()) {
        val due = synchronized(lock) {
            live.values.filter { it.expiresAt <= now }.map { it.id }
        }
        for (id in due) {
            val d = synchronized(lock) { live[id] } ?: continue
            val elapsed = now - d.raisedAt
            when (val out = DecisionProtocol.onTimeout(d.cls, elapsed)) {
                is DecisionProtocol.Outcome.AutoComplete -> {
                    // Log BEFORE applying: a crash between the two must not lose the record.
                    log("auto-complete", d, out.choice)
                    synchronized(lock) { live.remove(id) }
                    onAutoComplete?.invoke(d, out.choice)
                }
                is DecisionProtocol.Outcome.Escalate -> {
                    // Log once. The decision stays live (it is backlog and keeps counting),
                    // but re-logging it every tick would bury the first escalation.
                    if (synchronized(lock) { escalated.add(d.id) }) {
                        log("escalate", d, out.reason)
                        onEscalate?.invoke(d, out.reason)
                    }
                }
            }
        }
    }

    /** For tests: drop all state so cases do not leak into each other. */
    fun reset() {
        synchronized(lock) { live.clear(); escalated.clear(); seq = 0 }
        ledger = null
        onAutoComplete = null
        onEscalate = null
    }

    private fun log(event: String, d: Decision, detail: String) {
        val sink = ledger ?: return
        val parts = mutableListOf(
            "\"event\":" + q(event),
            "\"id\":" + q(d.id),
            "\"cls\":" + q(d.cls),
            "\"title\":" + q(d.title),
            "\"detail\":" + q(detail),
            "\"risk\":" + q(DecisionProtocol.riskOf(d.cls).name),
        )
        d.payload.forEach { (k, v) -> parts.add(q(k) + ":" + q(v)) }
        sink.write("{" + parts.joinToString(",") + "}")
    }

    private fun q(s: String): String =
        "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"")
            .replace("\n", "\\n") + "\""
}
