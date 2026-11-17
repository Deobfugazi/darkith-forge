package com.darkith.transliaison.core

/*
 * Small CSS cascade. Supports: tag, .class, #id and compounds of them (a.b, div.x#y), comma lists,
 * :root custom properties with var() and fallbacks, inline style="...", specificity + source order.
 * NOT supported (recorded in [skipped], never silently dropped): combinators, pseudo-classes,
 * attribute selectors, @media and other at-rules.
 */
class CssLite(styleTexts: List<String>) {

    private class Sel(val tag: String?, val id: String?, val classes: List<String>) {
        val specificity: Int
            get() = (if (id != null) 100 else 0) + classes.size * 10 + (if (tag != null) 1 else 0)
    }

    private class Rule(val sel: Sel, val decls: Map<String, String>, val order: Int)

    private val rules = mutableListOf<Rule>()
    val vars = LinkedHashMap<String, String>()
    val skipped = mutableListOf<String>()

    init {
        var order = 0
        for (t in styleTexts) order = parseSheet(t, order)
    }

    private fun parseSheet(raw: String, startOrder: Int): Int {
        var order = startOrder
        val css = raw.replace(COMMENT, "")
        var i = 0
        val n = css.length
        while (i < n) {
            val open = css.indexOf('{', i)
            if (open < 0) break
            val semi = css.indexOf(';', i)
            if (semi in 0 until open) {
                val pre = css.substring(i, semi).trim()
                if (pre.isNotEmpty()) skipped.add(pre.take(60))
                i = semi + 1
                continue
            }
            val prelude = css.substring(i, open).trim()
            var depth = 1
            var j = open + 1
            while (j < n && depth > 0) {
                if (css[j] == '{') depth++ else if (css[j] == '}') depth--
                j++
            }
            val bodyEnd = if (depth == 0) j - 1 else j
            val body = css.substring(open + 1, maxOf(open + 1, bodyEnd))
            i = j
            if (prelude.startsWith("@")) {
                skipped.add(prelude.take(60))
                continue
            }
            val decls = parseDecls(body)
            for (rawSel in prelude.split(',')) {
                val s = rawSel.trim()
                if (s.isEmpty()) continue
                if (s == ":root" || s == "html" || s == "body" || s == "*") {
                    for ((k, v) in decls) if (k.startsWith("--")) vars[k] = v
                }
                if (s == ":root") continue
                val sel = parseSel(s)
                if (sel == null) {
                    skipped.add(s.take(60))
                    continue
                }
                rules.add(Rule(sel, decls, order++))
            }
        }
        return order
    }

    private fun parseSel(s: String): Sel? {
        val m = SIMPLE.matchEntire(s) ?: return null
        val tag = m.groupValues[1]
        val rest = m.groupValues[2]
        var id: String? = null
        val cls = mutableListOf<String>()
        for (part in PART.findAll(rest)) {
            if (part.groupValues[1] == "#") id = part.groupValues[2] else cls.add(part.groupValues[2])
        }
        val t = if (tag.isEmpty() || tag == "*") null else tag.lowercase()
        return Sel(t, id, cls)
    }

    private fun parseDecls(body: String): Map<String, String> {
        val out = LinkedHashMap<String, String>()
        val parts = mutableListOf<String>()
        var depth = 0
        val sb = StringBuilder()
        for (ch in body) {
            if (ch == '(') depth++ else if (ch == ')') depth = maxOf(0, depth - 1)
            if (ch == ';' && depth == 0) {
                parts.add(sb.toString())
                sb.setLength(0)
            } else {
                sb.append(ch)
            }
        }
        parts.add(sb.toString())
        for (p in parts) {
            val k = p.indexOf(':')
            if (k <= 0) continue
            val name = p.substring(0, k).trim().lowercase()
            val value = p.substring(k + 1).replace("!important", "").trim()
            if (name.isNotEmpty() && value.isNotEmpty()) out[name] = value
        }
        return out
    }

    // * Declared properties for [node] after cascade, inline style and var() substitution. // 
    fun resolve(node: DomNode): Map<String, String> {
        val matched = rules.filter { matches(it.sel, node) }
            .sortedWith(compareBy<Rule>({ it.sel.specificity }, { it.order }))
        val out = LinkedHashMap<String, String>()
        for (r in matched) out.putAll(r.decls)
        out.putAll(parseDecls(node.attr("style")))
        val keys = out.keys.toList()
        for (k in keys) {
            if (k.startsWith("--")) {
                out.remove(k)
            } else {
                out[k] = substituteVars(out[k] ?: "")
            }
        }
        return out
    }

    private fun matches(s: Sel, n: DomNode): Boolean {
        val t = s.tag
        if (t != null && t != n.tag) return false
        val id = s.id
        if (id != null && id != n.attr("id")) return false
        if (s.classes.isNotEmpty() && !n.classes().containsAll(s.classes)) return false
        return true
    }

    private fun substituteVars(v: String): String {
        var cur = v
        var guard = 0
        while (guard < 6 && cur.contains("var(")) {
            cur = VAR.replace(cur) { m -> vars[m.groupValues[1]] ?: m.groupValues[2].trim() }
            guard++
        }
        return cur
    }

    private companion object {
        val COMMENT = Regex("/\\*.*?\\// ", RegexOption.DOT_MATCHES_ALL)
        val SIMPLE = Regex("^(\\*|[A-Za-z][A-Za-z0-9-]*)?((?:[.#][A-Za-z_-][\\w-]*)*)$")
        val PART = Regex("([.#])([A-Za-z_-][\\w-]*)")
        val VAR = Regex("var\\(\\s*(--[A-Za-z0-9_-]+)\\s*(?:,\\s*([^)]*))?\\)")
    }
}

// * CSS property map -> StyleSpec. // 
object CssMap {
    private val INHERITED = setOf("color", "font-size", "font-weight", "font-style", "text-align")
    private val NUM = Regex("^(-?\\d+(?:\\.\\d+)?)(px|rem|em)?$")
    private val RGB = Regex("^rgba?\\(([^)]*)\\)$")

    private val NAMED = mapOf(
        "white" to 0xFFFFFFFFL, "black" to 0xFF000000L, "transparent" to 0x00000000L,
        "red" to 0xFFFF0000L, "green" to 0xFF008000L, "blue" to 0xFF0000FFL,
        "yellow" to 0xFFFFFF00L, "orange" to 0xFFFFA500L, "gray" to 0xFF808080L,
        "grey" to 0xFF808080L, "cyan" to 0xFF00FFFFL, "magenta" to 0xFFFF00FFL
    )

    fun inheritFrom(props: Map<String, String>): Map<String, String> = props.filterKeys { it in INHERITED }

    fun px(v: String): Double? {
        val m = NUM.matchEntire(v.trim().lowercase()) ?: return null
        val num = m.groupValues[1].toDouble()
        return if (m.groupValues[2] == "rem" || m.groupValues[2] == "em") num * 16.0 else num
    }

    private fun argb(a: Int, r: Int, g: Int, b: Int): Long =
        (a.toLong() shl 24) or (r.toLong() shl 16) or (g.toLong() shl 8) or b.toLong()

    private fun hex(s: String, from: Int, len: Int): Int {
        val part = s.substring(from, from + len)
        return (if (len == 1) part + part else part).toInt(16)
    }

    fun color(v: String): Long? {
        val t = v.trim().lowercase()
        val named = NAMED[t]
        if (named != null) return named
        if (t.startsWith("#")) {
            val h = t.substring(1)
            if (h.isEmpty() || !h.all { it in '0'..'9' || it in 'a'..'f' }) return null
            return when (h.length) {
                3 -> argb(255, hex(h, 0, 1), hex(h, 1, 1), hex(h, 2, 1))
                4 -> argb(hex(h, 3, 1), hex(h, 0, 1), hex(h, 1, 1), hex(h, 2, 1))
                6 -> argb(255, hex(h, 0, 2), hex(h, 2, 2), hex(h, 4, 2))
                8 -> argb(hex(h, 6, 2), hex(h, 0, 2), hex(h, 2, 2), hex(h, 4, 2))
                else -> null
            }
        }
        val m = RGB.matchEntire(t) ?: return null
        val parts = m.groupValues[1].split(Regex("[,\\s/]+")).filter { it.isNotEmpty() }
        if (parts.size < 3) return null
        fun channel(p: String): Int? {
            val x = if (p.endsWith("%")) p.dropLast(1).toDoubleOrNull()?.let { it * 2.55 } else p.toDoubleOrNull()
            return x?.let { it.toInt().coerceIn(0, 255) }
        }
        val r = channel(parts[0]) ?: return null
        val g = channel(parts[1]) ?: return null
        val b = channel(parts[2]) ?: return null
        var a = 255
        if (parts.size >= 4) {
            val p = parts[3]
            val av = if (p.endsWith("%")) p.dropLast(1).toDoubleOrNull()?.let { it / 100.0 } else p.toDoubleOrNull()
            if (av == null) return null
            a = (av.coerceIn(0.0, 1.0) * 255).toInt()
        }
        return argb(a, r, g, b)
    }

    // * Split on whitespace that is not inside parentheses. // 
    fun splitTop(v: String): List<String> {
        val out = mutableListOf<String>()
        val sb = StringBuilder()
        var depth = 0
        for (ch in v) {
            if (ch == '(') depth++ else if (ch == ')') depth = maxOf(0, depth - 1)
            if (ch.isWhitespace() && depth == 0) {
                if (sb.isNotEmpty()) {
                    out.add(sb.toString())
                    sb.setLength(0)
                }
            } else {
                sb.append(ch)
            }
        }
        if (sb.isNotEmpty()) out.add(sb.toString())
        return out
    }

    // * CSS box shorthand -> top, right, bottom, left. // 
    fun box(v: String): List<Double>? {
        val vals = splitTop(v).map { px(it) ?: return null }
        return when (vals.size) {
            1 -> listOf(vals[0], vals[0], vals[0], vals[0])
            2 -> listOf(vals[0], vals[1], vals[0], vals[1])
            3 -> listOf(vals[0], vals[1], vals[2], vals[1])
            4 -> listOf(vals[0], vals[1], vals[2], vals[3])
            else -> null
        }
    }

    private fun bgColor(v: String): Long? {
        if (v.contains("gradient") || v.contains("url(")) return null
        for (tok in splitTop(v)) {
            val c = color(tok)
            if (c != null) return c
        }
        return null
    }

    fun gridColumns(p: Map<String, String>): Int {
        val v = p["grid-template-columns"] ?: return 1
        val rep = Regex("repeat\\(\\s*(\\d+)").find(v)
        if (rep != null) return rep.groupValues[1].toIntOrNull() ?: 1
        if (v.contains("repeat(")) return 2
        return maxOf(1, splitTop(v).size)
    }

    private fun align(v: String?): String? = when (v?.trim()) {
        "flex-start", "start" -> "start"
        "center" -> "center"
        "flex-end", "end" -> "end"
        else -> null
    }

    private fun justify(v: String?): String? = when (v?.trim()) {
        "flex-start", "start" -> "start"
        "center" -> "center"
        "flex-end", "end" -> "end"
        "space-between" -> "between"
        "space-around" -> "around"
        "space-evenly" -> "evenly"
        else -> null
    }

    fun toStyle(p: Map<String, String>): StyleSpec {
        var pad: List<Double>? = p["padding"]?.let { box(it) }
        val sides = listOf("padding-top", "padding-right", "padding-bottom", "padding-left")
        if (sides.any { p.containsKey(it) }) {
            val base = (pad ?: listOf(0.0, 0.0, 0.0, 0.0)).toMutableList()
            for (idx in sides.indices) {
                val side = p[sides[idx]]
                val sideVal = if (side == null) null else px(side)
                if (sideVal != null) base[idx] = sideVal
            }
            pad = base
        }
        val bg = p["background-color"]?.let { color(it) } ?: p["background"]?.let { bgColor(it) }
        var borderW: Double? = null
        var borderC: Long? = null
        val border = p["border"]
        if (border != null) {
            for (tok in splitTop(border)) {
                val w = px(tok)
                if (w != null) borderW = w
                val c = color(tok)
                if (c != null) borderC = c
            }
        }
        var radius: Double? = null
        var circle = false
        val br = p["border-radius"]
        if (br != null) {
            val first = splitTop(br).firstOrNull()
            if (first != null) {
                if (first == "50%") circle = true
                else {
                    val r = px(first)
                    if (r != null) {
                        if (r >= 999.0) circle = true else radius = r
                    }
                }
            }
        }
        val width = p["width"]
        val height = p["height"]
        val weight = p["font-weight"]?.trim()
        val bold = weight == "bold" || weight == "bolder" || (weight?.toIntOrNull() ?: 0) >= 600
        val gapV = p["gap"] ?: p["row-gap"] ?: p["column-gap"]
        val flex = p["flex"]?.let { splitTop(it).firstOrNull()?.toDoubleOrNull() } ?: p["flex-grow"]?.toDoubleOrNull()
        return StyleSpec(
            color = p["color"]?.let { color(it) },
            background = bg,
            fontSize = p["font-size"]?.let { px(it) },
            bold = bold,
            italic = p["font-style"]?.trim() == "italic",
            centerText = p["text-align"]?.trim() == "center",
            padding = pad,
            gap = gapV?.let { splitTop(it).firstOrNull() }?.let { px(it) },
            width = if (width == null || width.trim() == "100%") null else px(width),
            height = if (height == null || height.trim() == "100%") null else px(height),
            fillWidth = width?.trim() == "100%",
            fillHeight = height?.trim() == "100%",
            radius = radius,
            circle = circle,
            borderWidth = borderW,
            borderColor = borderC,
            grow = flex,
            alignItems = align(p["align-items"]),
            justify = justify(p["justify-content"])
        )
    }
}
