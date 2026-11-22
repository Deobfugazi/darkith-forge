import com.darkith.transliaison.core.DecisionProtocol
import com.darkith.transliaison.core.DecisionProtocol.Outcome
import com.darkith.transliaison.core.DecisionProtocol.Risk

fun main() {
    var pass = 0; var fail = 0
    fun check(n: String, c: Boolean) { if (c) { pass++; println("  PASS  $n") } else { fail++; println("  FAIL  $n") } }

    println("=== the invariant: destructive never auto-completes ===")
    for (cls in listOf("pr.label_security", "pr.label_critical", "pr.close", "branch.delete")) {
        check("$cls cannot auto-complete", !DecisionProtocol.canAutoComplete(cls))
        check("$cls escalates at any elapsed time",
            DecisionProtocol.onTimeout(cls, Long.MAX_VALUE) is Outcome.Escalate)
        check("$cls risk is DESTRUCTIVE", DecisionProtocol.riskOf(cls) == Risk.DESTRUCTIVE)
    }

    println("\n=== safe classes do clear themselves ===")
    check("checks_green can auto-complete", DecisionProtocol.canAutoComplete("pr.checks_green"))
    val green = DecisionProtocol.onTimeout("pr.checks_green", 16 * 60_000L)
    check("checks_green auto-completes after 15m", green is Outcome.AutoComplete)
    check("checks_green chooses MERGE", (green as? Outcome.AutoComplete)?.choice == "MERGE")

    val review = DecisionProtocol.onTimeout("pr.review_requested", 31 * 60_000L)
    check("review auto-completes after 30m", review is Outcome.AutoComplete)
    check("review chooses APPROVE", (review as? Outcome.AutoComplete)?.choice == "APPROVE")

    println("\n=== the timer actually gates ===")
    check("not due at 14m", DecisionProtocol.onTimeout("pr.checks_green", 14 * 60_000L) is Outcome.Escalate)
    check("due at exactly 15m", DecisionProtocol.onTimeout("pr.checks_green", 15 * 60_000L) is Outcome.AutoComplete)
    check("not due at 0", DecisionProtocol.onTimeout("pr.checks_green", 0L) is Outcome.Escalate)

    println("\n=== veto: state changed while waiting ===")
    check("stillValid=false vetoes",
        DecisionProtocol.onTimeout("pr.checks_green", 20 * 60_000L, stillValid = false) is Outcome.Escalate)

    println("\n=== unknown class is not guessed ===")
    check("unknown cannot auto-complete", !DecisionProtocol.canAutoComplete("pr.made_up"))
    check("unknown escalates", DecisionProtocol.onTimeout("pr.made_up", Long.MAX_VALUE) is Outcome.Escalate)

    println("\n=== failed checks escalate, not auto-fix ===")
    check("checks_failed cannot auto-complete", !DecisionProtocol.canAutoComplete("pr.checks_failed"))
    check("checks_failed escalates", DecisionProtocol.onTimeout("pr.checks_failed", Long.MAX_VALUE) is Outcome.Escalate)

    println("\n=== table is complete and ordered ===")
    check("table has 8 rules", DecisionProtocol.table().size == 8)
    check("every SAFE rule has a timeout > 0",
        DecisionProtocol.table().filter { it.third == Risk.SAFE }.all { it.second > 0 })

    println("\nRESULT: $pass passed, $fail failed")
    if (fail > 0) kotlin.system.exitProcess(1)
}
