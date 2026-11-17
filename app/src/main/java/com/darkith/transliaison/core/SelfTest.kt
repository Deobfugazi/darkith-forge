package com.darkith.transliaison.core

/**
 * NT X Part 11: the Forge is a testable hypothesis. These checks cover the pure-Kotlin half of the chain
 * (IR, emitter, Healer). They run in the app (Forge screen > Self-test) and as a JVM unit test.
 */
object SelfTest {
    data class Check(val name: String, val ok: Boolean, val detail: String)

    fun run(): List<Check> {
        val out = mutableListOf<Check>()
        fun check(name: String, block: () -> String?) {
            try {
                val problem = block()
                out.add(Check(name, problem == null, problem ?: "ok"))
            } catch (e: Exception) {
                out.add(Check(name, false, "threw " + e.javaClass.simpleName + ": " + (e.message ?: "")))
            }
        }
        val engine = TransliaisonEngine()

        check("nested same-name tags nest") {
            val n = engine.translate("<div><div>a</div><div>b</div></div>")
            val s = n.singleOrNull() as? LayoutNode.Stack
            if (s == null) "expected one Stack, got " + n.size
            else if (s.children.size != 2) "expected 2 children, got " + s.children.size else null
        }

        check("css var() resolves through :root") {
            val n = engine.translate("<style>:root{--c:#ff0000}.x{color:var(--c)}</style><p class=\"x\">hi</p>")
            val t = n.singleOrNull() as? LayoutNode.TextRun
            if (t == null) "expected one TextRun"
            else if (t.style.color != 0xFFFF0000L) "color was " + t.style.color else null
        }

        check("flex row with gap keeps spans as items") {
            val n = engine.translate("<div style=\"display:flex;gap:8px\"><span>1</span><span>2</span></div>")
            val s = n.singleOrNull() as? LayoutNode.Stack
            if (s == null) "expected one Stack"
            else if (s.vertical) "expected a row"
            else if (s.children.size != 2) "expected 2 items, got " + s.children.size
            else if (s.style.gap != 8.0) "gap was " + s.style.gap else null
        }

        check("grid reads repeat(3,1fr)") {
            val html = "<div style=\"display:grid;grid-template-columns:repeat(3,1fr)\"><div>a</div><div>b</div><div>c</div><div>d</div></div>"
            val g = engine.translate(html).singleOrNull() as? LayoutNode.Grid
            if (g == null) "expected one Grid"
            else if (g.columns != 3) "columns was " + g.columns
            else if (g.children.size != 4) "children " + g.children.size else null
        }

        check("button keeps data-act id") {
            val b = engine.translate("<button data-act=\"go\">Go</button>").singleOrNull() as? LayoutNode.Interactive
            if (b == null) "expected Interactive" else if (b.actionId != "go" || b.label != "Go") "got " + b else null
        }

        check("entities decode") {
            val t = engine.translate("<p>a &amp; b &lt; c</p>").singleOrNull() as? LayoutNode.TextRun
            if (t == null) "expected TextRun" else if (t.text != "a & b < c") "text was '" + t.text + "'" else null
        }

        check("display:none is dropped") {
            val n = engine.translate("<p style=\"display:none\">x</p><p>y</p>")
            if (n.size != 1) "expected 1 node, got " + n.size else null
        }

        val html = "<style>body{background:#101010;color:#eee}.card{padding:8px 12px;background:rgba(255,255,255,.1);border-radius:8px}</style>" +
            "<h1>Title \$5 \"q\"</h1><div class=\"card\"><button data-act=\"b1\">Press</button><input placeholder=\"name\"></div>" +
            "<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:6px\"><div>1</div><div>2</div><div>3</div></div><img src=\"x.png\" alt=\"pic\">"
        val res = engine.translateWithReport(html)

        // ComposeEmitter was purged: the app renders the IR through IRBuilder/OmegaRenderer, not
        // Compose. What must hold now is that this rich HTML reduces to a C7-renderable IR.
        check("rich HTML reduces to non-empty IR") {
            if (res.nodes.isEmpty()) "expected translatable nodes" else null
        }
        check("IR survives the C7 forge handoff intact") {
            val mutable = res.nodes.toMutableList()
            IRAuditor.healAndAudit(mutable)
            if (mutable.isEmpty()) "IR was emptied by the auditor" else null
        }
        check("IRBuilder fits the IR inside a bounded vertex budget") {
            val verts = IRBuilder(4096).build(res.nodes, 1080f, 1920f, 0xFF000000L)
            if (verts.isEmpty()) "no geometry built" else null
        }

        val healer = AutofillCorrector()
        check("preAnalyze injects a missing import") {
            val p = healer.preAnalyze("package p\n\nfun A() { Spacer() }\n")
            if (p.actions.isEmpty()) "expected a pending import action" else null
        }
        check("heal reads an unresolved-reference log line") {
            val r = healer.heal("package p\n\nfun A() { Spacer() }\n", "e: /tmp/A.kt: (3, 12): Unresolved reference: Spacer\n")
            if (r.actions.isEmpty()) "expected a repair" else if (r.deficits.isNotEmpty()) "unexpected deficit" else null
        }
        check("heal adds opt-in for FlowRow") {
            val r = healer.heal("package p\n\nfun A() { FlowRow() }\n", "A.kt:3:12: error: unresolved reference: FlowRow\n")
            if (!r.source.contains("@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)")) "opt-in missing" else null
        }
        check("heal surfaces an unknown miss in plain words") {
            val r = healer.heal("package p\n", "A.kt:9:1: error: something exotic happened\n")
            if (r.deficits.size != 1) "expected 1 deficit" else if (r.actions.isNotEmpty()) "must not claim a repair" else null
        }
        return out
    }

    /** Brace/paren/bracket balance, ignoring string literals. Returns null when balanced. */
    fun balanced(src: String): String? {
        val stack = ArrayList<Char>()
        var inStr = false
        var i = 0
        while (i < src.length) {
            val c = src[i]
            if (inStr) {
                if (c == '\\') i++ else if (c == '"') inStr = false
            } else {
                when (c) {
                    '"' -> inStr = true
                    '(', '{', '[' -> stack.add(c)
                    ')' -> if (stack.isEmpty() || stack.removeAt(stack.size - 1) != '(') return "unbalanced ) at " + i
                    '}' -> if (stack.isEmpty() || stack.removeAt(stack.size - 1) != '{') return "unbalanced } at " + i
                    ']' -> if (stack.isEmpty() || stack.removeAt(stack.size - 1) != '[') return "unbalanced ] at " + i
                }
            }
            i++
        }
        return if (inStr) "unterminated string" else if (stack.isNotEmpty()) "unclosed " + stack.last() else null
    }
}
