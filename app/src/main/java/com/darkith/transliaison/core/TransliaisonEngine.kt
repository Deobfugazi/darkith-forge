package com.darkith.transliaison.core

/**
 * NT X Part 4.2 - The Architect. HTML intent in, List<LayoutNode> out.
 * Pure Kotlin: no Android, no external parser, runs on the device and in plain JVM tests.
 */
class TransliaisonEngine {

    data class Result(
        val nodes: List<LayoutNode>,
        val rootStyle: StyleSpec,
        /** Plain-language notes on everything the engine could not carry over. */
        val report: List<String>
    )

    private class Ctx(val css: CssLite) {
        var buttonSeq = 0
        val ignored = LinkedHashMap<String, Int>()
    }

    fun translate(html: String): List<LayoutNode> = translateWithReport(html).nodes

    fun translateWithReport(html: String): Result {
        val root = HtmlParser.parse(html)
        val css = CssLite(root.findAll("style").map { it.text })
        val body = root.find("body") ?: root
        val ctx = Ctx(css)
        val bodyProps = css.resolve(body)
        val rootStyle = CssMap.toStyle(bodyProps)
        val nodes = convertChildren(body, CssMap.inheritFrom(bodyProps), ctx, false)
        val report = mutableListOf<String>()
        for ((k, v) in ctx.ignored) report.add("Ignored CSS '" + k + "' x" + v + " (no Compose equivalent was emitted).")
        for (s in css.skipped.distinct()) report.add("Skipped CSS rule '" + s + "' (selector or at-rule not supported).")
        return Result(nodes, rootStyle, report)
    }

    private fun defaultsFor(tag: String): Map<String, String> = when (tag) {
        "h1" -> mapOf("font-size" to "28px", "font-weight" to "700")
        "h2" -> mapOf("font-size" to "22px", "font-weight" to "700")
        "h3" -> mapOf("font-size" to "18px", "font-weight" to "700")
        "h4" -> mapOf("font-size" to "16px", "font-weight" to "700")
        "h5" -> mapOf("font-size" to "14px", "font-weight" to "700")
        "h6" -> mapOf("font-size" to "12px", "font-weight" to "700")
        "b", "strong", "th" -> mapOf("font-weight" to "700")
        "i", "em" -> mapOf("font-style" to "italic")
        else -> emptyMap()
    }

    private fun isInlineOnly(el: DomNode): Boolean {
        for (c in el.children) {
            if (c.isText) continue
            if (c.tag == "br") continue
            if (c.tag in INLINE && isInlineOnly(c)) continue
            return false
        }
        return true
    }

    private fun collectText(el: DomNode, sb: StringBuilder) {
        for (c in el.children) {
            if (c.isText) sb.append(c.text)
            else if (c.tag == "br") sb.append('\n')
            else if (c.tag !in SKIP) collectText(c, sb)
        }
    }

    private fun textOf(el: DomNode): String {
        val sb = StringBuilder()
        collectText(el, sb)
        return sb.toString().trim()
    }

    private fun convertChildren(parent: DomNode, inherited: Map<String, String>, ctx: Ctx, blockItems: Boolean): List<LayoutNode> {
        val out = mutableListOf<LayoutNode>()
        val group = mutableListOf<LayoutNode>()
        val run = StringBuilder()

        fun flushRun() {
            val t = run.toString().trim()
            if (t.isNotEmpty()) group.add(LayoutNode.TextRun(t, CssMap.toStyle(inherited)))
            run.setLength(0)
        }

        fun flushGroup() {
            flushRun()
            if (group.size == 1) out.add(group[0])
            else if (group.size > 1) out.add(LayoutNode.Stack(group.toList(), false, StyleSpec(gap = 4.0)))
            group.clear()
        }

        for (c in parent.children) {
            if (c.isText) {
                run.append(c.text)
                continue
            }
            if (c.tag in SKIP) continue
            if (c.tag == "br") {
                run.append('\n')
                continue
            }
            if (!blockItems && c.tag in INLINE) {
                val own = ctx.css.resolve(c)
                val d = own["display"]
                if (d != null && d != "inline" && d != "inline-block") {
                    flushGroup()
                    val n = convertElement(c, inherited, ctx)
                    if (n != null) out.add(n)
                } else if (!isInlineOnly(c)) {
                    flushGroup()
                    val n = convertElement(c, inherited, ctx)
                    if (n != null) out.add(n)
                } else if (own.isEmpty() && defaultsFor(c.tag).isEmpty()) {
                    collectText(c, run)
                } else {
                    flushRun()
                    val t = textOf(c)
                    if (t.isNotEmpty()) {
                        val props = LinkedHashMap<String, String>(inherited)
                        props.putAll(defaultsFor(c.tag))
                        props.putAll(own)
                        group.add(LayoutNode.TextRun(t, CssMap.toStyle(props)))
                    }
                }
                continue
            }
            flushGroup()
            val n = convertElement(c, inherited, ctx)
            if (n != null) out.add(n)
        }
        flushGroup()
        return out
    }

    private fun noteIgnored(own: Map<String, String>, ctx: Ctx) {
        for (k in own.keys) {
            if (k in IGNORED || k.startsWith("margin")) ctx.ignored[k] = (ctx.ignored[k] ?: 0) + 1
        }
    }

    private fun convertElement(el: DomNode, inherited: Map<String, String>, ctx: Ctx): LayoutNode? {
        if (el.attrs.containsKey("hidden")) return null
        val own = ctx.css.resolve(el)
        if (own["display"] == "none") return null
        noteIgnored(own, ctx)
        val props = LinkedHashMap<String, String>(inherited)
        props.putAll(defaultsFor(el.tag))
        props.putAll(own)
        val style = CssMap.toStyle(props)
        val tag = el.tag

        when (tag) {
            "button" -> {
                val label = textOf(el).ifEmpty { el.attr("aria-label") }.ifEmpty { "button" }
                return LayoutNode.Interactive(label, actionFor(el, ctx), false, style)
            }
            "a" -> {
                val href = el.attr("href")
                if (href.isNotEmpty()) {
                    val label = textOf(el).ifEmpty { href }
                    return LayoutNode.Interactive(label, "link:" + href, false, style)
                }
            }
            "input" -> {
                val type = el.attr("type").lowercase()
                if (type == "hidden") return null
                if (type == "button" || type == "submit" || type == "reset") {
                    val label = el.attr("value").ifEmpty { type }
                    return LayoutNode.Interactive(label, actionFor(el, ctx), false, style)
                }
                val hint = el.attr("placeholder").ifEmpty { el.attr("name") }.ifEmpty { "input" }
                return LayoutNode.Interactive(hint, actionFor(el, ctx), true, style)
            }
            "textarea" -> {
                val hint = el.attr("placeholder").ifEmpty { el.attr("name") }.ifEmpty { "text" }
                return LayoutNode.Interactive(hint, actionFor(el, ctx), true, style)
            }
            "select" -> {
                val first = el.findAll("option").firstOrNull()
                val label = if (first == null) "select" else textOf(first).ifEmpty { "select" }
                return LayoutNode.Interactive(label, "select:" + actionFor(el, ctx), false, style)
            }
            "img" -> return LayoutNode.Media(el.attr("src"), el.attr("alt").ifEmpty { null }, style)
            "svg", "canvas", "video", "audio", "iframe" ->
                return LayoutNode.Media(tag, el.attr("aria-label").ifEmpty { tag }, style)
            "hr" -> return LayoutNode.Stack(
                emptyList(), true,
                StyleSpec(height = 1.0, fillWidth = true, background = 0x33FFFFFFL)
            )
        }

        val display = own["display"] ?: ""
        val flexLike = display == "flex" || display == "inline-flex" || display == "grid"
        val kids = convertChildren(el, CssMap.inheritFrom(props), ctx, flexLike)
        if (kids.isEmpty()) {
            return if (style.width != null || style.height != null || style.background != null || style.fillHeight)
                LayoutNode.Stack(emptyList(), true, style) else null
        }
        if (!flexLike && kids.size == 1) {
            val only = kids[0]
            if (only is LayoutNode.TextRun && tag != "tr") return LayoutNode.TextRun(only.text, style)
        }
        if (display == "grid") return LayoutNode.Grid(kids, CssMap.gridColumns(own), style)
        if (flexLike) {
            val vertical = (own["flex-direction"] ?: "row").startsWith("column")
            return LayoutNode.Stack(kids, vertical, style)
        }
        return LayoutNode.Stack(kids, tag != "tr", style)
    }

    private fun actionFor(el: DomNode, ctx: Ctx): String {
        val act = el.attr("data-act")
        if (act.isNotEmpty()) return act
        val id = el.attr("id")
        if (id.isNotEmpty()) return id
        val n = ctx.buttonSeq
        ctx.buttonSeq = n + 1
        return "action" + n
    }

    private companion object {
        val SKIP = setOf("script", "style", "head", "meta", "link", "title", "noscript", "template", "base")
        val INLINE = setOf("span", "b", "strong", "i", "em", "u", "small", "code", "label", "abbr", "mark", "sub", "sup", "s", "kbd", "time", "cite", "q")
        val IGNORED = setOf(
            "position", "top", "left", "right", "bottom", "transform", "box-shadow", "transition", "animation",
            "z-index", "overflow", "cursor", "opacity", "backdrop-filter", "filter", "flex-wrap", "text-shadow"
        )
    }
}
