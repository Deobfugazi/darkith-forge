package com.darkith.transliaison.core

/** Minimal DOM node. Text nodes have tag "#text". script/style/textarea/title keep their raw content in [text]. */
class DomNode(val tag: String, val attrs: Map<String, String> = emptyMap(), val parent: DomNode? = null) {
    val children = mutableListOf<DomNode>()
    var text: String = ""
    val isText: Boolean get() = tag == "#text"

    fun attr(name: String): String = attrs[name] ?: ""

    fun classes(): List<String> = attr("class").split(Regex("\\s+")).filter { it.isNotEmpty() }

    fun find(tagName: String): DomNode? {
        if (tag == tagName) return this
        for (c in children) {
            val hit = c.find(tagName)
            if (hit != null) return hit
        }
        return null
    }

    fun findAll(tagName: String, out: MutableList<DomNode> = mutableListOf()): MutableList<DomNode> {
        if (tag == tagName) out.add(this)
        for (c in children) c.findAll(tagName, out)
        return out
    }
}

/** Hand-rolled HTML tokenizer + tree builder. Nested same-name tags nest correctly. */
object HtmlParser {
    private val VOID = setOf("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr")
    private val RAW = setOf("script", "style", "textarea", "title")
    private val WS = Regex("\\s+")

    fun parse(html: String): DomNode {
        val root = DomNode("#root")
        var cur = root
        var i = 0
        val n = html.length
        while (i < n) {
            val c = html[i]
            if (c != '<') {
                val found = html.indexOf('<', i)
                val next = if (found < 0) n else found
                addText(cur, html.substring(i, next))
                i = next
                continue
            }
            if (html.startsWith("<!--", i)) {
                val e = html.indexOf("-->", i + 4)
                i = if (e < 0) n else e + 3
                continue
            }
            if (i + 1 < n && (html[i + 1] == '!' || html[i + 1] == '?')) {
                val e = html.indexOf('>', i)
                i = if (e < 0) n else e + 1
                continue
            }
            if (i + 1 < n && html[i + 1] == '/') {
                val e = html.indexOf('>', i)
                if (e < 0) {
                    i = n
                    continue
                }
                val name = html.substring(i + 2, e).trim().lowercase()
                var up: DomNode? = cur
                while (up != null && up.tag != name) up = up.parent
                if (up != null) {
                    val p = up.parent
                    if (p != null) cur = p
                }
                i = e + 1
                continue
            }
            if (i + 1 < n && html[i + 1].isLetter()) {
                var j = i + 1
                while (j < n && !html[j].isWhitespace() && html[j] != '>' && html[j] != '/') j++
                val name = html.substring(i + 1, j).lowercase()
                val attrs = LinkedHashMap<String, String>()
                var selfClose = false
                while (j < n) {
                    while (j < n && html[j].isWhitespace()) j++
                    if (j >= n) break
                    if (html[j] == '>') {
                        j++
                        break
                    }
                    if (html[j] == '/') {
                        selfClose = true
                        j++
                        continue
                    }
                    val ns = j
                    while (j < n && !html[j].isWhitespace() && html[j] != '=' && html[j] != '>' && html[j] != '/') j++
                    val an = html.substring(ns, j).lowercase()
                    while (j < n && html[j].isWhitespace()) j++
                    var av = ""
                    if (j < n && html[j] == '=') {
                        j++
                        while (j < n && html[j].isWhitespace()) j++
                        if (j < n && (html[j] == '"' || html[j] == '\'')) {
                            val q = html[j]
                            j++
                            val qf = html.indexOf(q, j)
                            val qe = if (qf < 0) n else qf
                            av = html.substring(j, qe)
                            j = minOf(qe + 1, n)
                        } else {
                            val vs = j
                            while (j < n && !html[j].isWhitespace() && html[j] != '>') j++
                            av = html.substring(vs, j)
                        }
                    }
                    if (an.isNotEmpty()) attrs[an] = decodeEntities(av)
                }
                val node = DomNode(name, attrs, cur)
                cur.children.add(node)
                if (name in VOID || selfClose) {
                    i = j
                    continue
                }
                if (name in RAW) {
                    val close = Regex("</" + name + "\\s*>", RegexOption.IGNORE_CASE).find(html, j)
                    val end = if (close == null) n else close.range.first
                    val raw = html.substring(j, end)
                    node.text = if (name == "script" || name == "style") raw else decodeEntities(raw)
                    i = if (close == null) n else close.range.last + 1
                    continue
                }
                cur = node
                i = j
                continue
            }
            addText(cur, "<")
            i++
        }
        return root
    }

    private fun addText(parent: DomNode, raw: String) {
        if (raw.isEmpty()) return
        val t = DomNode("#text", emptyMap(), parent)
        t.text = decodeEntities(raw).replace(WS, " ")
        parent.children.add(t)
    }

    private val NAMED = mapOf(
        "amp" to "&", "lt" to "<", "gt" to ">", "quot" to "\"", "apos" to "'", "nbsp" to " ",
        "copy" to "\u00A9", "hellip" to "\u2026", "middot" to "\u00B7", "mdash" to "\u2014",
        "ndash" to "\u2013", "bull" to "\u2022", "larr" to "\u2190", "rarr" to "\u2192"
    )
    private val ENTITY = Regex("&(#[xX][0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);")

    fun decodeEntities(s: String): String {
        if (s.indexOf('&') < 0) return s
        return ENTITY.replace(s) { m ->
            val g = m.groupValues[1]
            val decoded: String? = when {
                g.startsWith("#x") || g.startsWith("#X") -> codePoint(g.substring(2).toIntOrNull(16))
                g.startsWith("#") -> codePoint(g.substring(1).toIntOrNull())
                else -> NAMED[g]
            }
            decoded ?: m.value
        }
    }

    private fun codePoint(cp: Int?): String? {
        if (cp == null || cp < 0 || cp > 0x10FFFF) return null
        return try {
            String(Character.toChars(cp))
        } catch (e: IllegalArgumentException) {
            null
        }
    }
}
