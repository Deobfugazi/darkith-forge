package com.darkith.transliaison.core

/**
 * Ordering for the GitHub surfaces: most recently active first.
 *
 * GitHub's own web UI defaults to "Recently updated" and the app hides it behind a menu, which
 * is why lists look frozen. Sorting is the whole reason a list feels live, so it is done here,
 * once, and shared by every surface (releases, pulls, commits, issues).
 *
 * Pure Kotlin: the comparator is testable without Android and without a network.
 */
object ActivitySort {

    /** One row as the UI needs it. [updatedAtMs] is epoch millis from the API. */
    data class Row(
        val id: String,
        val title: String,
        val updatedAtMs: Long,
        /** Higher wins ties, so a PR with a fresh comment beats a silent commit. */
        val weight: Int = 0,
        /** True for anything the operator must act on. Sorted above everything else. */
        val actionable: Boolean = false,
    )

    /**
     * The default view: what needs the operator first, then what moved most recently.
     *
     * Actionable rows lead regardless of age, because a stale decision is exactly the backlog
     * this project keeps hitting. Within each band, newest first. Ties break by weight, then by
     * id so the order is stable across reloads (a list that reshuffles on every poll is
     * unusable on a phone).
     */
    fun order(rows: List<Row>): List<Row> =
        rows.sortedWith(
            compareByDescending<Row> { it.actionable }
                .thenByDescending { it.updatedAtMs }
                .thenByDescending { it.weight }
                .thenBy { it.id },
        )

    /** Pure recency, for surfaces where nothing is actionable (releases, tags). */
    fun byRecency(rows: List<Row>): List<Row> =
        rows.sortedWith(
            compareByDescending<Row> { it.updatedAtMs }
                .thenByDescending { it.weight }
                .thenBy { it.id },
        )

    /**
     * Rows that have not moved in [staleMs]. Surfaced separately so a dead list is visible
     * as dead rather than merely old.
     */
    fun stale(rows: List<Row>, nowMs: Long, staleMs: Long = 14L * 24 * 60 * 60 * 1000): List<Row> =
        rows.filter { nowMs - it.updatedAtMs > staleMs }

    /**
     * How long ago, in words the operator can act on without arithmetic.
     * Deliberately coarse: "3d" is enough to decide, "2 days 4 hours 11 minutes" is noise.
     */
    fun age(updatedAtMs: Long, nowMs: Long): String {
        val d = nowMs - updatedAtMs
        if (d < 0) return "now"
        val m = d / 60_000L
        return when {
            m < 1 -> "now"
            m < 60 -> "${m}m"
            m < 60 * 24 -> "${m / 60}h"
            m < 60 * 24 * 30 -> "${m / (60 * 24)}d"
            else -> "${m / (60 * 24 * 30)}mo"
        }
    }
}
