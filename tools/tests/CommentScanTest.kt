import com.darkith.transliaison.core.*

fun main() {
    var pass = 0; var fail = 0
    fun check(name: String, cond: Boolean) {
        if (cond) { pass++; println("  PASS  $name") }
        else { fail++; println("  FAIL  $name") }
    }

    println("=== CommentScan ===")
    check("clean KDoc", CommentScan.scan("/** hi */\nval a = 1\n") == null)
    check("nested block", CommentScan.scan("/* a /* b */ c */\n") == null)
    check("line comment", CommentScan.scan("// /* not a comment\nval a=1\n") == null)
    check("delimiter in string", CommentScan.scan("val s = \"/*\"\n") == null)
    check("delimiter in raw string", CommentScan.scan("val s = \"\"\"/*\"\"\"\n") == null)

    val unclosed = CommentScan.scan("/**\n * doc\nval a = 1\n")
    check("UNCLOSED detected", unclosed?.kind == "UNCLOSED")
    check("UNCLOSED line 1", unclosed?.line == 1)

    val orphan = CommentScan.scan("val a = 1\n * doc\n */\nval b = 2\n")
    check("ORPHAN detected", orphan?.kind == "ORPHAN")
    check("ORPHAN line 3", orphan?.line == 3)

    println("\n=== Formulary ===")
    check("CRITICAL allowed", Formulary.judge(Severity.CRITICAL, "x", "t", "b") == Verdict.ALLOW)
    check("DECISION allowed", Formulary.judge(Severity.DECISION, "x", "t", "b") == Verdict.ALLOW)
    check("ledger tick denied", Formulary.judge(Severity.INFO, "progress.ledger.start", "t", "b") == Verdict.DENY)
    check("labor clock denied", Formulary.judge(Severity.INFO, "labor.clock.tick", "t", "b") == Verdict.DENY)
    check("empty denied", Formulary.judge(Severity.INFO, "x", "", "") == Verdict.DENY)
    check("notice allowed", Formulary.judge(Severity.NOTICE, "watchdog.unpushed", "t", "b") == Verdict.ALLOW)
    check("rule order stable", Formulary.ruleNames() == listOf("critical-always","decision-always","empty-body","ledger-tick","default-notice"))

    println("\n=== regression: false positives (found on the real tree) ===")
    check("content:// in KDoc",
        CommentScan.scan("/** Resolve a content:// MediaStore uri. */\nval a = 1\n") == null)
    check("http:// in KDoc",
        CommentScan.scan("/**\n * See http://example.com for details.\n */\nval a = 1\n") == null)
    check("quote inside block",
        CommentScan.scan("/* say \"hello\" */\nval a = 1\n") == null)
    check("star-slash in string",
        CommentScan.scan("val s = \"*\" + \"/\"\n") == null)

    println("\n=== replay the blind sed (the real defect) ===")
    val original = "/**\n * Header doc for the file.\n */\npackage p\n"
    check("original is clean", CommentScan.scan(original) == null)
    // strip the opener, which is what the blind sed did
    val damaged = original.replaceFirst("/**", " *")
    val d = CommentScan.scan(damaged)
    check("damage detected", d != null)
    check("damage is ORPHAN", d?.kind == "ORPHAN")
    println("  detail: $d")

    println("\nRESULT: $pass passed, $fail failed")
    if (fail > 0) kotlin.system.exitProcess(1)
}
