import com.darkith.transliaison.core.DecisionProtocol
import com.darkith.transliaison.core.Pending

/**
 * Proves the coupler actually fires the table. DecisionProtocolTest proves the table is
 * correct; this proves something calls it, which is the defect this file exists for.
 *
 * The clock is injected (sweep(now)) so nothing here sleeps.
 */

private var pass = 0
private var fail = 0

private fun ok(name: String, cond: Boolean, detail: String = "") {
    if (cond) { pass++; println("  ok   $name") }
    else { fail++; println("  FAIL $name ${if (detail.isNotEmpty()) "- $detail" else ""}") }
}

fun main() {
    println("PendingTest — the timer that fires DecisionProtocol")

    // ── a SAFE class auto-completes once its timeout elapses ────────────────
    run {
        Pending.reset()
        val applied = mutableListOf<String>()
        Pending.onAutoComplete = { _, choice -> applied.add(choice) }
        Pending.onEscalate = { _, _ -> }

        val d = Pending.raise("pr.checks_green", "CI green on #42")
        val t = DecisionProtocol.timeoutMs("pr.checks_green")
        ok("raised decision is live", Pending.backlogSize() == 1)

        Pending.sweep(d.raisedAt + t - 1)
        ok("does not fire before its timeout", applied.isEmpty() && Pending.backlogSize() == 1)

        Pending.sweep(d.raisedAt + t)
        ok("fires exactly at its timeout", applied.size == 1, "applied=$applied")
        ok("applies the protocol default", applied.firstOrNull() == "MERGE", "got=$applied")
        ok("leaves the backlog", Pending.backlogSize() == 0)
    }

    // ── a DESTRUCTIVE class never auto-completes, however long it waits ─────
    run {
        Pending.reset()
        val applied = mutableListOf<String>()
        val escalated = mutableListOf<String>()
        Pending.onAutoComplete = { _, choice -> applied.add(choice) }
        Pending.onEscalate = { _, reason -> escalated.add(reason) }

        val d = Pending.raise("pr.close", "Close #7?")
        Pending.sweep(d.raisedAt + 30L * 24 * 60 * 60 * 1000)   // 30 days later

        ok("destructive never applies", applied.isEmpty(), "applied=$applied")
        ok("destructive escalates", escalated.size == 1, "escalated=$escalated")
        ok("destructive stays in the backlog", Pending.backlogSize() == 1)
    }

    // ── security and critical are destructive by policy ─────────────────────
    for (cls in listOf("pr.label_security", "pr.label_critical")) {
        Pending.reset()
        val applied = mutableListOf<String>()
        Pending.onAutoComplete = { _, c -> applied.add(c) }
        Pending.onEscalate = { _, _ -> }
        val d = Pending.raise(cls, "security item")
        Pending.sweep(d.raisedAt + 365L * 24 * 60 * 60 * 1000)
        ok("$cls never auto-completes", applied.isEmpty(), "applied=$applied")
    }

    // ── an answered decision cannot be fired later ──────────────────────────
    run {
        Pending.reset()
        val applied = mutableListOf<String>()
        Pending.onAutoComplete = { _, c -> applied.add(c) }
        Pending.onEscalate = { _, _ -> }

        val d = Pending.raise("pr.checks_green", "CI green on #43")
        Pending.resolve(d.id, "REJECT")
        Pending.sweep(d.raisedAt + DecisionProtocol.timeoutMs("pr.checks_green") + 1)

        ok("a resolved decision never fires", applied.isEmpty(), "applied=$applied")
        ok("resolving clears the backlog", Pending.backlogSize() == 0)
    }

    // ── an unknown class is never guessed at ────────────────────────────────
    run {
        Pending.reset()
        val applied = mutableListOf<String>()
        Pending.onAutoComplete = { _, c -> applied.add(c) }
        Pending.onEscalate = { _, _ -> }
        val d = Pending.raise("something.new", "unknown")
        Pending.sweep(d.raisedAt + 365L * 24 * 60 * 60 * 1000)
        ok("unknown class never auto-completes", applied.isEmpty(), "applied=$applied")
    }

    // ── regression: a zero-timeout class must still reach sweep ─────────────
    // The defect: expiresAt = Long.MAX_VALUE for no-timeout classes made them invisible to
    // the timer, so they neither auto-completed nor escalated. They sat silently, which is
    // the exact failure this whole layer exists to prevent.
    run {
        Pending.reset()
        val escalated = mutableListOf<String>()
        Pending.onAutoComplete = { _, _ -> }
        Pending.onEscalate = { _, reason -> escalated.add(reason) }
        val d = Pending.raise("pr.close", "zero-timeout class")
        ok("zero-timeout decision is due immediately", d.expiresAt == d.raisedAt)
        Pending.sweep(d.raisedAt + 1)
        ok("zero-timeout class escalates on the first sweep", escalated.size == 1)
        Pending.sweep(d.raisedAt + 2)
        Pending.sweep(d.raisedAt + 3)
        ok("escalation is logged once, not every tick", escalated.size == 1,
            "got ${escalated.size}")
        ok("escalated decision stays in the backlog", Pending.backlogSize() == 1)
    }

    // ── every destructive row in the table agrees with the coupler ──────────
    run {
        var checked = 0
        for ((cls, timeout, risk) in DecisionProtocol.table()) {
            if (risk != DecisionProtocol.Risk.DESTRUCTIVE) continue
            checked++
            ok("table row $cls is not auto-completable",
                !DecisionProtocol.canAutoComplete(cls))
            ok("table row $cls has no timeout", timeout == 0L)
        }
        ok("the table has destructive rows to check", checked > 0, "checked=$checked")
    }

    println()
    println("RESULT: $pass passed, $fail failed")
    if (fail > 0) kotlin.system.exitProcess(1)
}
