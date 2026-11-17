package com.darkith.transliaison.core

/**
 * NT X Part 7, step 1: the IR. Pure structural intent, no Android types.
 * Lengths are CSS px (emitted as dp/sp). Colors are ARGB longs (0xAARRGGBB).
 */
data class StyleSpec(
    val color: Long? = null,
    val background: Long? = null,
    val fontSize: Double? = null,
    val bold: Boolean = false,
    val italic: Boolean = false,
    val centerText: Boolean = false,
    /** top, right, bottom, left */
    val padding: List<Double>? = null,
    val gap: Double? = null,
    val width: Double? = null,
    val height: Double? = null,
    val fillWidth: Boolean = false,
    val fillHeight: Boolean = false,
    val radius: Double? = null,
    val circle: Boolean = false,
    val borderWidth: Double? = null,
    val borderColor: Long? = null,
    val grow: Double? = null,
    /** start | center | end */
    val alignItems: String? = null,
    /** start | center | end | between | around | evenly */
    val justify: String? = null
)

sealed class LayoutNode {
    abstract val style: StyleSpec

    data class Stack(
        val children: List<LayoutNode>,
        val vertical: Boolean = true,
        override val style: StyleSpec = StyleSpec()
    ) : LayoutNode()

    data class Grid(
        val children: List<LayoutNode>,
        val columns: Int = 1,
        override val style: StyleSpec = StyleSpec()
    ) : LayoutNode()

    data class TextRun(
        val text: String,
        override val style: StyleSpec = StyleSpec()
    ) : LayoutNode()

    /** A button, link or text field. */
    data class Interactive(
        val label: String,
        val actionId: String,
        val isField: Boolean = false,
        override val style: StyleSpec = StyleSpec()
    ) : LayoutNode()

    data class Media(
        val src: String,
        val description: String? = null,
        override val style: StyleSpec = StyleSpec()
    ) : LayoutNode()
}
