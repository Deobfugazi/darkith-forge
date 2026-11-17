package com.darkith.transliaison.core

/**
 * Structural auditor for the LayoutNode IR, run just before it is handed to the renderer.
 *
 * The engine's translator only emits nodes it understood; this pass repairs the two ways the
 * IR can still arrive malformed, in place, and reports what it changed:
 *
 *   1. EMPTY CONTAINERS - a Stack/Grid whose children all dropped out is dead weight on the
 *      surface. It is pruned (recursively; a container emptied by pruning is itself pruned).
 *   2. EMPTY LEAVES - a TextRun with blank text or a Media with no src renders as an invisible
 *      block. It is dropped.
 *   3. DEAD INTERACTIVES - an Interactive with no actionId can never dispatch, and one with a
 *      blank label renders as an unlabelled hole. A field with a blank label is kept (it may be
 *      placeheld); a button with neither label nor action is dropped.
 *   4. INVALID GRIDS - a Grid with columns < 1 has no defined layout; it is clamped to 1.
 *
 * Every mutation is appended to the returned log, so the caller can write it to the ledger.
 * No Android types and no I/O here: this is a pure function of the IR.
 */
object IRAuditor {

    fun healAndAudit(nodes: MutableList<LayoutNode>): List<String> {
        val log = ArrayList<String>()
        val kept = nodes.mapNotNull { audit(it, log) }
        if (kept.size != nodes.size) {
            nodes.clear()
            nodes.addAll(kept)
        }
        return log
    }

    private fun audit(node: LayoutNode, log: MutableList<String>): LayoutNode? {
        return when (node) {
            is LayoutNode.Stack -> {
                val healed = node.children.mapNotNull { audit(it, log) }
                if (healed.size != node.children.size) {
                    log.add("pruned ${node.children.size - healed.size} malformed child(ren) from Stack")
                }
                if (healed.isEmpty()) {
                    log.add("dropped empty Stack (all children were malformed)")
                    null
                } else node.copy(children = healed)
            }
            is LayoutNode.Grid -> {
                val healed = node.children.mapNotNull { audit(it, log) }
                if (healed.size != node.children.size) {
                    log.add("pruned ${node.children.size - healed.size} malformed child(ren) from Grid")
                }
                if (healed.isEmpty()) {
                    log.add("dropped empty Grid (all children were malformed)")
                    null
                } else {
                    val cols = if (node.columns < 1) {
                        log.add("clamped Grid columns ${node.columns} -> 1")
                        1
                    } else node.columns
                    node.copy(children = healed, columns = cols)
                }
            }
            is LayoutNode.TextRun -> {
                if (node.text.isBlank()) {
                    log.add("dropped blank TextRun")
                    null
                } else node
            }
            is LayoutNode.Media -> {
                if (node.src.isBlank()) {
                    log.add("dropped Media with no src")
                    null
                } else node
            }
            is LayoutNode.Interactive -> {
                if (node.actionId.isBlank() && !node.isField) {
                    log.add("dropped Interactive with no actionId: '${node.label}'")
                    null
                } else if (node.label.isBlank() && !node.isField) {
                    log.add("dropped unlabelled button with actionId '${node.actionId}'")
                    null
                } else node
            }
        }
    }
}
