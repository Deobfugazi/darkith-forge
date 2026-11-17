package com.darkith.transliaison.core

/** One thing the Healer could not repair, in words the Operator can act on (NT X Part 9, right 3). */
data class Deficit(
    val code: String,
    val line: Int?,
    val symbol: String?,
    val plain: String
)

data class HealOutcome(
    val source: String,
    /** What was changed, one line each. Empty means nothing was repaired. */
    val actions: List<String>,
    val deficits: List<Deficit>
)

/**
 * NT X Part 5: the fixed dictionary of miss signatures. This is deliberately NOT a general repair engine.
 * symbol -> fully qualified name to import; optIn lists the opt-in marker a symbol drags in.
 */
object HealerDictionary {
    val imports: Map<String, String> = mapOf(
        "Composable" to "androidx.compose.runtime.Composable",
        "remember" to "androidx.compose.runtime.remember",
        "mutableStateOf" to "androidx.compose.runtime.mutableStateOf",
        "getValue" to "androidx.compose.runtime.getValue",
        "setValue" to "androidx.compose.runtime.setValue",
        "Text" to "androidx.compose.material3.Text",
        "Modifier" to "androidx.compose.ui.Modifier",
        "Alignment" to "androidx.compose.ui.Alignment",
        "Color" to "androidx.compose.ui.graphics.Color",
        "RectangleShape" to "androidx.compose.ui.graphics.RectangleShape",
        "SolidColor" to "androidx.compose.ui.graphics.SolidColor",
        "clip" to "androidx.compose.ui.draw.clip",
        "TextStyle" to "androidx.compose.ui.text.TextStyle",
        "FontWeight" to "androidx.compose.ui.text.font.FontWeight",
        "FontStyle" to "androidx.compose.ui.text.font.FontStyle",
        "TextAlign" to "androidx.compose.ui.text.style.TextAlign",
        "dp" to "androidx.compose.ui.unit.dp",
        "sp" to "androidx.compose.ui.unit.sp",
        "Column" to "androidx.compose.foundation.layout.Column",
        "Row" to "androidx.compose.foundation.layout.Row",
        "Box" to "androidx.compose.foundation.layout.Box",
        "Spacer" to "androidx.compose.foundation.layout.Spacer",
        "Arrangement" to "androidx.compose.foundation.layout.Arrangement",
        "fillMaxSize" to "androidx.compose.foundation.layout.fillMaxSize",
        "fillMaxWidth" to "androidx.compose.foundation.layout.fillMaxWidth",
        "fillMaxHeight" to "androidx.compose.foundation.layout.fillMaxHeight",
        "padding" to "androidx.compose.foundation.layout.padding",
        "width" to "androidx.compose.foundation.layout.width",
        "height" to "androidx.compose.foundation.layout.height",
        "size" to "androidx.compose.foundation.layout.size",
        "background" to "androidx.compose.foundation.background",
        "border" to "androidx.compose.foundation.border",
        "clickable" to "androidx.compose.foundation.clickable",
        "rememberScrollState" to "androidx.compose.foundation.rememberScrollState",
        "verticalScroll" to "androidx.compose.foundation.verticalScroll",
        "horizontalScroll" to "androidx.compose.foundation.horizontalScroll",
        "CircleShape" to "androidx.compose.foundation.shape.CircleShape",
        "RoundedCornerShape" to "androidx.compose.foundation.shape.RoundedCornerShape",
        "BasicTextField" to "androidx.compose.foundation.text.BasicTextField",
        "FlowRow" to "androidx.compose.foundation.layout.FlowRow",
        "FlowColumn" to "androidx.compose.foundation.layout.FlowColumn"
    )

    /** Symbols whose use requires an opt-in marker; the Healer adds @file:OptIn(marker::class). */
    val optIn: Map<String, String> = mapOf(
        "FlowRow" to "androidx.compose.foundation.layout.ExperimentalLayoutApi",
        "FlowColumn" to "androidx.compose.foundation.layout.ExperimentalLayoutApi"
    )
}

/**
 * NT X Part 4.3 - The Healer. Reads the compiler's named miss, patches the source in place.
 * preAnalyze() pre-empts misses before the first compile; heal() consumes a real compiler log.
 */
class AutofillCorrector(private val dictionary: Map<String, String> = HealerDictionary.imports) {

    fun preAnalyze(source: String): HealOutcome {
        val missing = mutableListOf<String>()
        val bodyOnly = source.lines().filterNot { it.trimStart().startsWith("import ") || it.trimStart().startsWith("package ") }.joinToString("\n")
        for ((sym, fqn) in dictionary) {
            if (hasImport(source, fqn)) continue
            val used = Regex("(?<![A-Za-z0-9_\"])" + Regex.escape(sym) + "(?![A-Za-z0-9_])").containsMatchIn(bodyOnly)
            if (used) missing.add(sym)
        }
        return applyMissing(source, missing)
    }

    fun heal(source: String, compilerLog: String): HealOutcome {
        val missing = mutableListOf<String>()
        val deficits = mutableListOf<Deficit>()
        val optIns = mutableListOf<String>()
        for (raw in compilerLog.lines()) {
            val line = raw.trim()
            if (line.isEmpty()) continue
            val isError = line.contains("error:") || line.startsWith("e: ") || line.contains(": error")
            if (!isError) continue
            val lineNo = LINE_NO.find(line)?.let { m -> m.groupValues[1].ifEmpty { m.groupValues[2] } }?.toIntOrNull()
            val unresolved = UNRESOLVED.find(line)
            val opt = OPT_IN.find(line)
            if (unresolved != null) {
                val sym = unresolved.groupValues[1]
                if (dictionary.containsKey(sym)) {
                    if (!missing.contains(sym)) missing.add(sym)
                } else {
                    deficits.add(Deficit("unresolved", lineNo, sym,
                        "The compiler does not know the name '" + sym + "'" + at(lineNo) +
                            ". The Healer has no import for it. Paste the correct import or replace the name in the Source box."))
                }
            } else if (opt != null) {
                val marker = opt.groupValues[1]
                if (!optIns.contains(marker)) optIns.add(marker)
            } else if (line.contains("@Composable invocations can only happen")) {
                deficits.add(Deficit("composable-context", lineNo, null,
                    "A screen element was used outside a Compose function" + at(lineNo) + ". This needs a manual fix in the source."))
            } else if (line.contains("Type mismatch") || line.contains("type mismatch")) {
                deficits.add(Deficit("type-mismatch", lineNo, null,
                    "The compiler found two values that do not fit together" + at(lineNo) + ": " + cleanMessage(line)))
            } else {
                deficits.add(Deficit("unknown", lineNo, null,
                    "The compiler refused" + at(lineNo) + ": " + cleanMessage(line) +
                        ". The Healer cannot repair this kind of miss; it needs a manual correction."))
            }
        }
        val base = applyMissing(source, missing)
        var out = base.source
        val actions = base.actions.toMutableList()
        for (marker in optIns) {
            val ann = "@file:OptIn(" + marker + "::class)"
            if (!out.contains(ann)) {
                out = ann + "\n" + out
                actions.add("Added opt-in " + marker.substringAfterLast('.'))
            }
        }
        return HealOutcome(out, actions, deficits)
    }

    private fun at(line: Int?): String = if (line == null) "" else " (line " + line + ")"

    private fun cleanMessage(line: String): String {
        val i = line.indexOf("error:")
        val msg = if (i >= 0) line.substring(i + 6).trim() else line.removePrefix("e: ").trim()
        return msg.take(200)
    }

    private fun hasImport(source: String, fqn: String): Boolean {
        if (Regex("(?m)^\\s*import\\s+" + Regex.escape(fqn) + "\\s*$").containsMatchIn(source)) return true
        val pkg = fqn.substringBeforeLast('.')
        return Regex("(?m)^\\s*import\\s+" + Regex.escape(pkg) + "\\.\\*\\s*$").containsMatchIn(source)
    }

    private fun applyMissing(source: String, missing: List<String>): HealOutcome {
        if (missing.isEmpty()) return HealOutcome(source, emptyList(), emptyList())
        val lines = source.lines().toMutableList()
        var insertAt = -1
        for ((i, l) in lines.withIndex()) if (l.trimStart().startsWith("import ")) insertAt = i + 1
        if (insertAt < 0) {
            val pkgIdx = lines.indexOfFirst { it.trimStart().startsWith("package ") }
            insertAt = if (pkgIdx >= 0) pkgIdx + 1 else 0
        }
        val actions = mutableListOf<String>()
        val newLines = mutableListOf<String>()
        val optMarkers = mutableListOf<String>()
        for (sym in missing) {
            val fqn = dictionary[sym] ?: continue
            if (hasImport(source, fqn)) continue
            newLines.add("import " + fqn)
            actions.add("Injected import " + fqn)
            val marker = HealerDictionary.optIn[sym]
            if (marker != null && !optMarkers.contains(marker)) optMarkers.add(marker)
        }
        lines.addAll(insertAt, newLines)
        var out = lines.joinToString("\n")
        for (m in optMarkers) {
            val ann = "@file:OptIn(" + m + "::class)"
            if (!out.contains(ann)) {
                out = ann + "\n" + out
                actions.add("Added opt-in " + m.substringAfterLast('.'))
            }
        }
        return HealOutcome(out, actions, emptyList())
    }

    private companion object {
        val UNRESOLVED = Regex("(?i)unresolved reference:?\\s*'?([A-Za-z_][A-Za-z0-9_]*)'?")
        val OPT_IN = Regex("@OptIn\\(([A-Za-z0-9_.]+)::class\\)")
        val LINE_NO = Regex("\\.kt:(\\d+)(?::\\d+)?|\\((\\d+),\\s*\\d+\\)")
    }
}
