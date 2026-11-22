package com.darkith.transliaison.core

/**
 * The gatekeeping formulary: the single decision source for whether an alert may interrupt.
 *
 * This file decides. Callers cannot bypass it, because [AlertBus.raise] runs every alert
 * through [judge] before any window exists. Changing alert behaviour means changing [RULES]
 * and nothing else. No Android imports: this is testable on a plain JVM.
 */
object Formulary {

    private class Rule(
        val name: String,
        val verdict: Verdict,
        val match: (Severity, String, String, String) -> Boolean,
    )

    /** Ordered; first match wins. */
    private val RULES: List<Rule> = listOf(
        // An unrecoverable condition must be seen: a corrupted tree or a failed build.
        Rule("critical-always", Verdict.ALLOW) { sev, _, _, _ ->
            sev == Severity.CRITICAL
        },
        // A decision the operator must make cannot be auto-dismissed.
        Rule("decision-always", Verdict.ALLOW) { sev, _, _, _ ->
            sev == Severity.DECISION
        },
        // Nothing to say is noise. Suppress silently.
        Rule("empty-body", Verdict.DENY) { _, _, title, body ->
            body.isBlank() && title.isBlank()
        },
        // Ledger ticks are already durable; surfacing them would flood the screen.
        Rule("ledger-tick", Verdict.DENY) { _, cls, _, _ ->
            cls.startsWith("progress.ledger.") || cls.startsWith("labor.clock.")
        },
        // Everything else is informational and shown once.
        Rule("default-notice", Verdict.ALLOW) { _, _, _, _ -> true },
    )

    fun judge(severity: Severity, cls: String, title: String, body: String): Verdict {
        for (rule in RULES) {
            if (rule.match(severity, cls, title, body)) return rule.verdict
        }
        return Verdict.HOLD
    }

    fun ruleNames(): List<String> = RULES.map { it.name }
}
