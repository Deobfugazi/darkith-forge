package com.darkith.transliaison.ime

import android.content.Context
import java.util.Locale

/**
 * Offline English Language Resource Pack.
 *
 * Resource: LibreOffice en_US Hunspell dictionary, SCOWL-derived, bundled as source assets:
 * en_US.dic Git blob ID b41fd203e6daf76934db99dec6572a230516368a
 * en_US.aff Git blob ID 290acfe87caf0f7ef44cf04dba4cd3b3cf2dbc58
 * Upstream copyright and permission notice: assets/keyboard/README_en_US.txt.
 *
 * The reader admits dictionary headwords and the simple single-affix rules represented in the
 * bundled .aff file. It does NOT claim complete Hunspell compatibility, compound-rule support,
 * or frequency-corpus coverage. Those remain explicit profile boundaries.
 */
object Elrp {
    const val IDENTITY = "LibreOffice-en_US-SCOWL-derived"
    const val VERSION = "2020.12.07+affix-2024-01-29"

    private val lock = Any()
    @Volatile private var loaded = false
    private val words = HashSet<String>()
    private val suggestible = HashSet<String>()
    private val personal = LinkedHashSet<String>()
    private val byInitial = HashMap<String, MutableList<String>>()
    private val commonRank = HashMap<String, Int>()
    private var loadError: String? = null

    // A small transparent common-word ordering is only a tie-breaker, not a corpus frequency claim.
    private val common = listOf(
        "the","be","to","of","and","a","in","that","have","i","it","for","not","on","with",
        "he","as","you","do","at","this","but","his","by","from","they","we","say","her","she",
        "or","an","will","my","one","all","would","there","their","what","so","up","out","if",
        "about","who","get","which","go","me","when","make","can","like","time","no","just","him",
        "know","take","people","into","year","your","good","some","could","them","see","other",
        "than","then","now","look","only","come","its","over","think","also","back","after","use",
        "two","how","our","work","first","well","way","even","new","want","because","any","these",
        "give","day","most","us","is","are","was","were","been","has","had","did","does","said",
        "made","went","got","seen","known","taken","given","hello","thanks","please","okay"
    )

    fun initialize(context: Context) {
        if (loaded) return
        synchronized(lock) {
            if (loaded) return
            try {
                common.forEachIndexed { index, word -> commonRank[word] = index }
                val affixLines = context.assets.open("keyboard/en_US.aff").bufferedReader(Charsets.UTF_8).use { it.readLines() }
                val rules = parseAffix(affixLines)
                val noSuggestFlag = affixLines.firstOrNull { it.trim().startsWith("NOSUGGEST ") }
                    ?.trim()?.split(Regex("\\s+"))?.getOrNull(1)
                val lines = context.assets.open("keyboard/en_US.dic").bufferedReader(Charsets.UTF_8).use { it.readLines() }
                require(lines.isNotEmpty()) { "dictionary asset is empty" }
                val declared = lines.first().trim().toIntOrNull()
                    ?: throw IllegalArgumentException("dictionary count header is malformed")
                var accepted = 0
                for (line in lines.drop(1)) {
                    val raw = line.trim()
                    if (raw.isEmpty() || raw.startsWith("#")) continue
                    val parts = raw.split("/", limit = 2)
                    val stem = parts[0].lowercase(Locale.US)
                    if (!stem.any { it.isLetter() } || stem.length > 48) continue
                    words.add(stem)
                    accepted++
                    val flags = parts.getOrNull(1).orEmpty()
                    val suppressSuggestions = noSuggestFlag != null && flags.contains(noSuggestFlag)
                    if (!suppressSuggestions) suggestible.add(stem)
                    if (parts.size == 2) {
                        for (flag in flags) {
                            for (rule in rules[flag.toString()].orEmpty()) {
                                val form = rule.apply(stem) ?: continue
                                if (form.length <= 56) {
                                    words.add(form)
                                    if (!suppressSuggestions) suggestible.add(form)
                                }
                            }
                        }
                    }
                }
                require(accepted == declared) { "dictionary count mismatch: declared $declared, read $accepted" }
                require(accepted > 10000) { "dictionary admission count too small: $accepted" }
                val overlay = context.getSharedPreferences("darkith_ime", Context.MODE_PRIVATE)
                    .getStringSet("personal_words", emptySet()).orEmpty()
                personal.addAll(overlay.map { it.lowercase(Locale.US) }.filter { it.matches(Regex("[a-z][a-z'’-]{1,39}")) })
                suggestible.addAll(personal)
                suggestible.forEach { word ->
                    if (word.length >= 2) byInitial.getOrPut(word.substring(0, 2)) { ArrayList() }.add(word)
                }
                byInitial.values.forEach { bucket ->
                    bucket.sortWith(compareBy<String>({ commonRank[it] ?: Int.MAX_VALUE }, { it }))
                }
                loaded = true
                loadError = null
            } catch (e: Exception) {
                words.clear()
                suggestible.clear()
                personal.clear()
                byInitial.clear()
                loadError = e.message ?: e.javaClass.simpleName
            }
        }
    }

    fun status(): String = when {
        loaded -> "$IDENTITY/$VERSION · ${words.size} forms loaded"
        loadError != null -> "ELRP unavailable: $loadError"
        else -> "ELRP not initialized"
    }

    fun isValid(word: String): Boolean {
        ensureLoaded()
        val normalized = word.lowercase(Locale.US)
        return normalized in words || normalized in personal
    }

    /** Prefix completion from the single admitted lexical resource. */
    fun completing(prefix: String, limit: Int = 8): List<String> {
        ensureLoaded()
        val p = prefix.lowercase(Locale.US)
        if (p.isEmpty() || p.length < 2) return emptyList()
        val matches = LinkedHashSet<String>()
        byInitial[p.take(2)].orEmpty().asSequence().filter { it.startsWith(p) && it != p }
            .take(limit * 4).forEach(matches::add)
        personal.asSequence().filter { it.startsWith(p) && it != p }.forEach(matches::add)
        return matches.sortedWith(compareBy<String>({ commonRank[it] ?: Int.MAX_VALUE }, { it }))
            .take(limit)
    }

    /** Bounded edit-distance-one generation; no full-dictionary scan per keystroke. */
    fun near(word: String, limit: Int = 8): List<String> {
        ensureLoaded()
        val w = word.lowercase(Locale.US)
        if (w.length < 2 || w.length > 32) return emptyList()
        val candidates = LinkedHashSet<String>()
        val alphabet = "abcdefghijklmnopqrstuvwxyz"
        for (i in w.indices) {
            candidates.add(w.removeRange(i, i + 1))
            if (i + 1 < w.length) {
                val chars = w.toCharArray()
                val c = chars[i]; chars[i] = chars[i + 1]; chars[i + 1] = c
                candidates.add(String(chars))
            }
            for (c in alphabet) candidates.add(w.substring(0, i) + c + w.substring(i + 1))
        }
        for (i in 0..w.length) for (c in alphabet) candidates.add(w.substring(0, i) + c + w.substring(i))
        return candidates.asSequence()
            .filter { it != w && (it in suggestible || it in personal) }
            .sortedWith(compareBy<String>({ commonRank[it] ?: Int.MAX_VALUE }, { it }))
            .take(limit)
            .toList()
    }

    fun personalWords(): Set<String> = synchronized(lock) { personal.toSet() }

    fun addPersonalWord(context: Context, input: String): Boolean {
        ensureLoaded()
        val word = input.trim().lowercase(Locale.US)
        if (!word.matches(Regex("[a-z][a-z'’-]{1,39}"))) return false
        synchronized(lock) {
            if (!personal.add(word)) return true
            context.getSharedPreferences("darkith_ime", Context.MODE_PRIVATE).edit()
                .putStringSet("personal_words", personal.toSet()).apply()
        }
        return true
    }

    fun removePersonalWord(context: Context, input: String) {
        val word = input.lowercase(Locale.US)
        synchronized(lock) {
            personal.remove(word)
            context.getSharedPreferences("darkith_ime", Context.MODE_PRIVATE).edit()
                .putStringSet("personal_words", personal.toSet()).apply()
        }
    }

    private fun ensureLoaded() {
        check(loaded || loadError != null) {
            "ELRP must be initialized by DarkithImeService before lookup"
        }
    }

    private data class Rule(val kind: String, val strip: String, val add: String, val condition: Regex) {
        fun apply(stem: String): String? {
            if (!condition.containsMatchIn(stem)) return null
            val base = if (strip == "0") stem else if (kind == "SFX") {
                if (!stem.endsWith(strip)) return null
                stem.dropLast(strip.length)
            } else {
                if (!stem.startsWith(strip)) return null
                stem.drop(strip.length)
            }
            return if (kind == "SFX") base + add else add + base
        }
    }

    private fun parseAffix(lines: List<String>): Map<String, List<Rule>> {
        val result = HashMap<String, List<Rule>>()
        var i = 0
        while (i < lines.size) {
            val header = lines[i].trim().split(Regex("\\s+"))
            if (header.size >= 4 && header[0] in setOf("PFX", "SFX") &&
                header[2] in setOf("Y", "N")) {
                val kind = header[0]
                val flag = header[1]
                val count = header[3].toIntOrNull() ?: 0
                val rules = ArrayList<Rule>()
                repeat(count) {
                    if (i + 1 >= lines.size) return@repeat
                    val fields = lines[++i].trim().split(Regex("\\s+"))
                    if (fields.size < 5 || fields[0] != kind || fields[1] != flag) return@repeat
                    val condition = try {
                        Regex(if (kind == "SFX") fields[4] + "$" else "^" + fields[4])
                    } catch (_: Exception) { return@repeat }
                    rules.add(Rule(kind, fields[2], fields[3], condition))
                }
                result[flag] = rules
            }
            i++
        }
        return result
    }
}
