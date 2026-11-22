package com.darkith.transliaison.core

/**
 * What happens to an alert the operator never saw.
 *
 * The failure this prevents: an alert fires, the phone is face-down, the notification is
 * missed, and the decision sits unresolved until the queue is a backlog. This object decides,
 * deterministically, which unresolved decisions may complete themselves and which must
 * escalate.
 *
 * The invariant: a decision may auto-complete ONLY if its class is allow-listed AND every
 * option it could take is reversible. Anything destructive escalates, always, no timeout.
 * A backlog of safe decisions is worse than a backlog of risky ones, so the safe ones clear
 * themselves and the risky ones stay loud.
 *
 * Pure Kotlin: no Android imports, so the whole table is unit-testable on a plain JVM.
 */
object DecisionProtocol {

    /** How much a choice can hurt if it is taken without the operator looking. */
    enum class Risk { SAFE, REVIEW, DESTRUCTIVE }

    /** The outcome of a timeout. */
    sealed class Outcome {
        /** Take [choice] on the operator's behalf, and say so in the ledger. */
        data class AutoComplete(val choice: String, val reason: String) : Outcome()
        /** Leave it open, escalate it, and count it as backlog. */
        data class Escalate(val reason: String) : Outcome()
    }

    private class Rule(
        val cls: String,
        val timeoutMs: Long,
        val risk: Risk,
        /** The option taken on timeout. Null means escalate; never guess a destructive one. */
        val defaultChoice: String?,
    )

    /**
     * Timeouts are per class, not global, because the cost of waiting differs.
     * A green CI check needs no human; a security label does.
     */
    private val RULES: List<Rule> = listOf(
        // Checks finished green on a non-draft, non-security PR. Reversible: a merge can be
        // reverted, and nothing is destroyed. This is the one class that clears itself.
        Rule("pr.checks_green", 15 * 60_000L, Risk.SAFE, "MERGE"),
        // A review request with no blocking findings. Approving is reversible and public.
        Rule("pr.review_requested", 30 * 60_000L, Risk.SAFE, "APPROVE"),
        // Routine maintenance the operator has pre-authorised by protocol.
        Rule("pr.label_routine", 60 * 60_000L, Risk.SAFE, "MERGE"),

        // Anything security-labelled is never auto-merged. Escalate and stay loud.
        Rule("pr.label_security", 0L, Risk.DESTRUCTIVE, null),
        // Critical severity, same reasoning: a human must look.
        Rule("pr.label_critical", 0L, Risk.DESTRUCTIVE, null),
        // Closing a PR or deleting a branch loses work. Never on a timer.
        Rule("pr.close", 0L, Risk.DESTRUCTIVE, null),
        Rule("branch.delete", 0L, Risk.DESTRUCTIVE, null),
        // A failed check needs a fix, not a decision. Escalate.
        Rule("pr.checks_failed", 0L, Risk.REVIEW, null),
    )

    private val byClass: Map<String, Rule> = RULES.associateBy { it.cls }

    /** The timeout for a class. Zero means "never auto-complete". */
    fun timeoutMs(cls: String): Long = byClass[cls]?.timeoutMs ?: 0L

    fun riskOf(cls: String): Risk = byClass[cls]?.risk ?: Risk.REVIEW

    /** True only when this class may resolve itself without the operator. */
    fun canAutoComplete(cls: String): Boolean {
        val r = byClass[cls] ?: return false
        return r.risk == Risk.SAFE && r.defaultChoice != null && r.timeoutMs > 0L
    }

    /**
     * Decide what a timeout means. [elapsedMs] is how long the alert has been unresolved;
     * [stillValid] lets a caller veto (for example, CI went red while the alert waited).
     */
    fun onTimeout(cls: String, elapsedMs: Long, stillValid: Boolean = true): Outcome {
        val r = byClass[cls] ?: return Outcome.Escalate("unknown class: $cls")
        if (r.risk != Risk.SAFE) {
            return Outcome.Escalate("${r.risk.name} class cannot auto-complete: $cls")
        }
        if (r.defaultChoice == null) {
            return Outcome.Escalate("no default choice for $cls")
        }
        if (r.timeoutMs <= 0L) {
            return Outcome.Escalate("no timeout for $cls")
        }
        if (elapsedMs < r.timeoutMs) {
            return Outcome.Escalate("not yet due: ${elapsedMs}ms of ${r.timeoutMs}ms")
        }
        if (!stillValid) {
            return Outcome.Escalate("precondition failed at timeout for $cls")
        }
        return Outcome.AutoComplete(
            r.defaultChoice,
            "pre-authorised by protocol after ${r.timeoutMs}ms",
        )
    }

    /** For the studio and for tests: the full table, so nothing is hidden. */
    fun table(): List<Triple<String, Long, Risk>> =
        RULES.map { Triple(it.cls, it.timeoutMs, it.risk) }
}
