package com.darkith.transliaison.ime

/**
 * English Language Resource Pack — the offline lexical substrate (DK-SIC-001 §5.3).
 *
 * The bundled seed is deliberately small and inspectable: it is the *mechanism* proof, not a claim
 * of full English coverage. Valid-word membership, morphology and frequency are kept separate, as
 * §5.3 requires. A larger pinned dictionary is admitted later by replacing [SEED] and recording its
 * identity, version, licence and checksum — never by inventing a second code path.
 */
object Elrp {

    const val IDENTITY = "darkith-elrp-seed"
    const val VERSION = "1"

    /** Common English headwords plus the technical/darkith vocabulary the host actually types. */
    private val SEED: Set<String> = setOf(
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on",
        "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we",
        "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their",
        "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when",
        "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into",
        "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now",
        "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two",
        "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any",
        "these", "give", "day", "most", "us", "is", "are", "was", "were", "been", "has", "had",
        "did", "does", "said", "made", "went", "got", "seen", "known", "taken", "given",
        "word", "words", "text", "type", "typing", "keyboard", "key", "keys", "press", "space",
        "darkith", "omega", "forge", "homekeeper", "android", "kotlin", "build", "termux",
        "phone", "device", "file", "files", "path", "data", "code", "run", "test", "gate",
        "clipboard", "copy", "paste", "cut", "history", "sync", "local", "offline", "native",
        "the", "and", "yes", "no", "ok", "okay", "thanks", "please", "hello", "sorry", "sure"
    )

    private val FREQ: Map<String, Int> by lazy {
        SEED.withIndex().associate { (i, w) -> w to (SEED.size - i) }
    }

    /** Suffix rules that expand the seed into valid inflections (§5.3 morphology, kept separate). */
    private val SUFFIXES = listOf("s", "es", "ed", "d", "ing", "er", "est", "ly", "s'", "'s")

    private val PREFIXES = listOf("un", "re", "in", "dis", "pre", "non")

    fun isValid(word: String): Boolean {
        val w = word.lowercase()
        if (w.isEmpty()) return false
        if (w in SEED) return true
        for (s in SUFFIXES) {
            if (w.endsWith(s) && w.length > s.length + 1 && w.dropLast(s.length) in SEED) return true
        }
        for (p in PREFIXES) {
            if (w.startsWith(p) && w.length > p.length + 1 && w.removePrefix(p) in SEED) return true
        }
        return false
    }

    fun frequency(word: String): Int = FREQ[word.lowercase()] ?: 0

    /** Prefix lookup over the seed: the primary completion path (§5.4, one path only). */
    fun completing(prefix: String, limit: Int = 8): List<String> {
        val p = prefix.lowercase()
        if (p.isEmpty()) return emptyList()
        return SEED.asSequence()
            .filter { it.startsWith(p) && it != p }
            .sortedByDescending { frequency(it) }
            .take(limit)
            .toList()
    }

    /** Bounded edit-distance-1 candidates over the seed — the spelling-suggestion path. */
    fun near(word: String, limit: Int = 8): List<String> {
        val w = word.lowercase()
        if (w.isEmpty()) return emptyList()
        val out = ArrayList<Pair<String, Int>>()
        for (cand in SEED) {
            val d = editDistance(w, cand, 2)
            if (d in 1..2) out.add(cand to d)
        }
        return out.sortedWith(compareBy({ it.second }, { -frequency(it.first) }))
            .take(limit)
            .map { it.first }
    }

    private fun editDistance(a: String, b: String, cap: Int): Int {
        if (Math.abs(a.length - b.length) > cap) return cap + 1
        var prev = IntArray(b.length + 1) { it }
        var cur = IntArray(b.length + 1)
        for (i in 1..a.length) {
            cur[0] = i
            var rowMin = cur[0]
            for (j in 1..b.length) {
                val cost = if (a[i - 1] == b[j - 1]) 0 else 1
                cur[j] = minOf(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
                if (cur[j] < rowMin) rowMin = cur[j]
            }
            if (rowMin > cap) return cap + 1
            val t = prev; prev = cur; cur = t
        }
        return prev[b.length]
    }
}
