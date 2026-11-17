package com.darkith.transliaison.core

import kotlin.math.max
import kotlin.math.min

/**
 * Turns LayoutNode IR into flat, world-space quads that fit inside a fixed vertex budget.
 *
 * The walk is depth-first and budget-bounded: once maxQuads is reached, traversal stops and
 * reason becomes "vertexBudgetReached". Nothing here is glyph rendering. TextRun and
 * Interactive nodes emit a block plus a bar whose width is proportional to the label length,
 * so the Forge shows the IR's STRUCTURE, not its typography. That limit is reported in the
 * renderer's log line, not hidden.
 */
class IRBuilder(private val maxQuads: Int) {

    data class Quad(val x: Float, val y: Float, val w: Float, val h: Float, val argb: Long)

    private val quads = ArrayList<Quad>(min(maxQuads, 4096))
    private var stopReason = "complete"
    private var textRuns = 0

    val quadCount: Int get() = quads.size
    val vertexCount: Int get() = quads.size * 6
    val reason: String get() = stopReason
    val textRunCount: Int get() = textRuns

    fun build(nodes: List<LayoutNode>, viewportW: Float, viewportH: Float, bgArgb: Long): FloatArray {
        quads.clear()
        stopReason = "complete"
        textRuns = 0
        val pad = 12f
        addQuad(0f, 0f, max(1f, viewportW), max(1f, viewportH), bgArgb)
        var y = pad
        for (n in nodes) {
            if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; break }
            y = place(n, pad, y, max(8f, viewportW - pad * 2f), bgArgb, 0)
        }
        return toVertices()
    }

    private fun place(node: LayoutNode, x: Float, y: Float, w: Float, bg: Long, depth: Int): Float {
        if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; return y }
        if (depth > 24) return y
        val st = node.style
        return when (node) {
            is LayoutNode.Stack -> {
                val pt = (st.padding?.getOrNull(0) ?: 0.0).toFloat()
                val pr = (st.padding?.getOrNull(1) ?: 0.0).toFloat()
                val pb = (st.padding?.getOrNull(2) ?: 0.0).toFloat()
                val pl = (st.padding?.getOrNull(3) ?: 0.0).toFloat()
                val gap = (st.gap ?: 6.0).toFloat()
                val bx = x + pl
                val bw = max(4f, w - pl - pr)
                val bh = blockHeight(node)
                addQuad(x, y, w, bh, containerColor(st.background, bg))
                if (node.vertical) {
                    var cy = y + pt
                    for (c in node.children) {
                        if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; break }
                        cy = place(c, bx, cy, bw, bg, depth + 1) + gap
                    }
                    max(y + 4f, cy - gap + pb)
                } else {
                    val n = node.children.size.coerceAtLeast(1)
                    val cw = max(4f, (bw - gap * (n - 1)) / n)
                    var maxY = y + pt
                    for ((i, c) in node.children.withIndex()) {
                        if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; break }
                        val ey = place(c, bx + i * (cw + gap), y + pt, cw, bg, depth + 1)
                        if (ey > maxY) maxY = ey
                    }
                    maxY + pb
                }
            }
            is LayoutNode.Grid -> {
                val cols = node.columns.coerceAtLeast(1)
                val gap = (st.gap ?: 6.0).toFloat()
                val cw = max(8f, (w - gap * (cols - 1)) / cols)
                if (st.background != null) addQuad(x, y, w, blockHeight(node), containerColor(st.background, bg))
                var cy = y
                var col = 0
                var rowMax = 0f
                for (c in node.children) {
                    if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; break }
                    val ey = place(c, x + col * (cw + gap), cy, cw, bg, depth + 1)
                    val eh = ey - cy
                    if (eh > rowMax) rowMax = eh
                    col++
                    if (col == cols) { col = 0; cy += rowMax + gap; rowMax = 0f }
                }
                if (col != 0) cy += rowMax + gap
                cy
            }
            is LayoutNode.TextRun -> {
                textRuns++
                val h = textHeight(node.text)
                addQuad(x, y, w, h, TEXT_BLOCK)
                addQuad(x + 4f, y + h / 2f - 2f, min(w - 8f, max(8f, node.text.length * 6f)), 4f, TEXT_BAR)
                y + h
            }
            is LayoutNode.Interactive -> {
                val h = 34f
                addQuad(x, y, w, h, FIELD_BLOCK)
                addQuad(x + 4f, y + h / 2f - 3f, min(w - 8f, max(8f, node.label.length * 6f)), 6f, TEXT_BAR)
                y + h
            }
            is LayoutNode.Media -> {
                addQuad(x, y, w, 72f, MEDIA_BLOCK)
                y + 72f
            }
        }
    }

    private fun blockHeight(node: LayoutNode): Float = when (node) {
        is LayoutNode.Stack -> {
            val gap = (node.style.gap ?: 6.0).toFloat()
            val padV = (node.style.padding?.getOrNull(0) ?: 0.0).toFloat() +
                       (node.style.padding?.getOrNull(2) ?: 0.0).toFloat()
            if (node.children.isEmpty()) 20f
            else if (node.vertical) padV + node.children.sumOf { blockHeight(it).toDouble() }.toFloat() + gap * (node.children.size - 1)
            else padV + node.children.maxOf { blockHeight(it) }
        }
        is LayoutNode.Grid -> {
            val cols = node.columns.coerceAtLeast(1)
            val rows = ((node.children.size + cols - 1) / cols).coerceAtLeast(1)
            rows * 30f
        }
        is LayoutNode.TextRun -> textHeight(node.text)
        is LayoutNode.Interactive -> 34f
        is LayoutNode.Media -> 72f
    }

    private fun textHeight(text: String): Float {
        val lines = 1 + text.length / 48
        return 16f * lines + 6f
    }

    private fun containerColor(bg: Long?, pageBg: Long): Long =
        if (bg != null) withAlpha(bg, 0x66) else withAlpha(pageBg, 0x55)

    private fun addQuad(x: Float, y: Float, w: Float, h: Float, argb: Long) {
        if (quads.size >= maxQuads) { stopReason = "vertexBudgetReached"; return }
        quads.add(Quad(x, y, max(1f, w), max(1f, h), argb))
    }

    private fun toVertices(): FloatArray {
        val arr = FloatArray(quads.size * 36)
        var i = 0
        for (q in quads) {
            val x0 = q.x; val y0 = q.y; val x1 = q.x + q.w; val y1 = q.y + q.h
            val r = ((q.argb shr 16) and 0xFF).toFloat() / 255f
            val g = ((q.argb shr 8) and 0xFF).toFloat() / 255f
            val b = (q.argb and 0xFF).toFloat() / 255f
            val a = ((q.argb shr 24) and 0xFF).toFloat() / 255f
            i = put(arr, i, x0, y0, r, g, b, a)
            i = put(arr, i, x1, y0, r, g, b, a)
            i = put(arr, i, x0, y1, r, g, b, a)
            i = put(arr, i, x0, y1, r, g, b, a)
            i = put(arr, i, x1, y0, r, g, b, a)
            i = put(arr, i, x1, y1, r, g, b, a)
        }
        return arr
    }

    private fun put(a: FloatArray, i: Int, x: Float, y: Float, r: Float, g: Float, b: Float, al: Float): Int {
        a[i] = x; a[i + 1] = y; a[i + 2] = r; a[i + 3] = g; a[i + 4] = b; a[i + 5] = al
        return i + 6
    }

    companion object {
        const val VERTEX_STRIDE_FLOATS = 6
        private fun withAlpha(argb: Long, a: Int): Long =
            ((a.coerceIn(0, 255).toLong() shl 24) or (argb and 0x00FFFFFFL))
        private const val TEXT_BLOCK = 0xAA2F6FBF.toLong()
        private const val TEXT_BAR = 0xFFCFE3FF.toLong()
        private const val FIELD_BLOCK = 0xCCB8860B.toLong()
        private const val MEDIA_BLOCK = 0x88445566.toLong()
    }
}
