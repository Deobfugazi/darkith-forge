package com.darkith.transliaison.keyboard

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONArray
import java.util.Locale

/**
 * Native Darkith IME. The editor connection is the sole authority for text commits.
 * Clipboard capture is opt-in and only active while this IME is visible.
 */
class DarkithKeyboardService : InputMethodService() {
    private val prefs by lazy { getSharedPreferences("darkith_keyboard", Context.MODE_PRIVATE) }
    private var root: LinearLayout? = null
    private var candidateRow: LinearLayout? = null
    private var keysPanel: LinearLayout? = null
    private var numeric = false
    private var shifted = false
    private var clipboardPanel = false
    private var sensitiveField = false
    private var lastCandidates: List<String> = emptyList()
    private lateinit var clipboard: ClipboardManager
    private var clipboardListener: ClipboardManager.OnPrimaryClipChangedListener? = null
    private val lexicon by lazy { EnglishLexicon(this) }

    override fun onCreate() {
        super.onCreate()
        clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboardListener = ClipboardManager.OnPrimaryClipChangedListener {
            if (prefs.getBoolean("clipboard_enabled", false) && !sensitiveField) captureClipboard()
        }
    }

    override fun onCreateInputView(): View {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(4), dp(5), dp(4), dp(6))
            setBackgroundColor(Color.rgb(25, 28, 34))
        }
        root = panel
        candidateRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        panel.addView(candidateRow, LinearLayout.LayoutParams(-1, dp(42)))
        keysPanel = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        panel.addView(keysPanel, LinearLayout.LayoutParams(-1, -2))
        renderCandidates(emptyList())
        renderKeys()
        return panel
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        super.onStartInput(attribute, restarting)
        val inputType = attribute?.inputType ?: 0
        val variation = inputType and android.text.InputType.TYPE_MASK_VARIATION
        sensitiveField = variation == android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD ||
            variation == android.text.InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
            variation == android.text.InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD ||
            (inputType and android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD) ==
                android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD
        numeric = (inputType and android.text.InputType.TYPE_MASK_CLASS) ==
            android.text.InputType.TYPE_CLASS_NUMBER ||
            (inputType and android.text.InputType.TYPE_MASK_CLASS) ==
            android.text.InputType.TYPE_CLASS_PHONE
        clipboardPanel = false
        lastCandidates = emptyList()
        renderKeys()
        refreshCandidates()
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        if (prefs.getBoolean("clipboard_enabled", false) && !sensitiveField) {
            clipboardListener?.let { clipboard.addPrimaryClipChangedListener(it) }
        }
    }

    override fun onFinishInputView(finishingInput: Boolean) {
        clipboardListener?.let { try { clipboard.removePrimaryClipChangedListener(it) } catch (_: Exception) {} }
        super.onFinishInputView(finishingInput)
    }

    override fun onDestroy() {
        clipboardListener?.let { try { clipboard.removePrimaryClipChangedListener(it) } catch (_: Exception) {} }
        super.onDestroy()
    }

    private fun renderKeys() {
        val panel = keysPanel ?: return
        panel.removeAllViews()
        if (clipboardPanel) {
            renderClipboard(panel)
            return
        }
        val toolbar = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        toolbar.addView(keyButton(if (prefs.getBoolean("autocorrect", false)) "AUTO ✓" else "AUTO —") {
            prefs.edit().putBoolean("autocorrect", !prefs.getBoolean("autocorrect", false)).apply()
            renderKeys()
        }, weighted())
        toolbar.addView(keyButton(if (prefs.getBoolean("clipboard_enabled", false)) "CLIP ✓" else "CLIP") {
            val enabled = !prefs.getBoolean("clipboard_enabled", false)
            prefs.edit().putBoolean("clipboard_enabled", enabled).apply()
            clipboardPanel = enabled
            renderKeys()
        }, weighted())
        toolbar.addView(keyButton("ABC / 123") { numeric = !numeric; renderKeys() }, weighted())
        toolbar.addView(keyButton("SHIFT") { shifted = !shifted; renderKeys() }, weighted())
        panel.addView(toolbar, rowParams())

        val rows = if (numeric) listOf(
            listOf("1","2","3","4","5","6","7","8","9","0"),
            listOf("@","#","$","%","&","-","+","(",")","/"),
            listOf("*","\"","' ",":",";","!","?"),
            listOf("ABC","SYM","⌫","↵")
        ) else listOf(
            listOf("q","w","e","r","t","y","u","i","o","p"),
            listOf("a","s","d","f","g","h","j","k","l"),
            listOf("⇧","z","x","c","v","b","n","m","⌫"),
            listOf("?123",",","space",".","↵")
        )
        rows.forEach { keys ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }
            keys.forEach { key ->
                val label = when {
                    key == "space" -> "English (US)"
                    key == "⇧" -> "⇧"
                    key.length == 1 && key[0].isLetter() && shifted -> key.uppercase(Locale.US)
                    else -> key
                }
                val weight = when (key) {
                    "space" -> 5f
                    "⌫", "↵", "⇧", "?123", "ABC", "SYM" -> 1.35f
                    else -> 1f
                }
                row.addView(keyButton(label) { onKey(key) }, LinearLayout.LayoutParams(0, dp(48), weight).apply {
                    setMargins(dp(2), dp(3), dp(2), dp(3))
                })
            }
            panel.addView(row, rowParams())
        }
    }

    private fun onKey(key: String) {
        val ic = currentInputConnection ?: return
        when (key) {
            "⌫" -> {
                val before = ic.getTextBeforeCursor(1, 0)
                if (!before.isNullOrEmpty()) ic.deleteSurroundingText(1, 0)
            }
            "↵" -> {
                val action = currentInputEditorInfo?.imeOptions?.and(EditorInfo.IME_MASK_ACTION) ?: EditorInfo.IME_ACTION_NONE
                if (action != EditorInfo.IME_ACTION_NONE && action != EditorInfo.IME_ACTION_UNSPECIFIED) {
                    ic.performEditorAction(action)
                } else ic.commitText("\n", 1)
            }
            "space" -> {
                maybeCorrect(ic)
                ic.commitText(" ", 1)
                if (shifted) shifted = false
            }
            "?123", "SYM" -> { numeric = true; renderKeys(); return }
            "ABC" -> { numeric = false; renderKeys(); return }
            "⇧" -> { shifted = !shifted; renderKeys(); return }
            else -> {
                val value = if (key == "' ") "'" else key
                val out = if (value.length == 1 && value[0].isLetter() && shifted) value.uppercase(Locale.US) else value
                ic.commitText(out, 1)
                if (shifted) shifted = false
            }
        }
        refreshCandidates()
        renderKeysIfShiftChanged()
    }

    private fun maybeCorrect(ic: InputConnection) {
        if (!prefs.getBoolean("autocorrect", false) || sensitiveField) return
        val before = ic.getTextBeforeCursor(80, 0)?.toString() ?: return
        val word = before.takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
        if (word.length < 3 || lexicon.contains(word)) return
        val candidates = lexicon.suggest(word, 2)
        if (candidates.size == 1) {
            ic.deleteSurroundingText(word.length, 0)
            ic.commitText(candidates[0], 1)
        }
    }

    private fun refreshCandidates() {
        if (sensitiveField || clipboardPanel) { renderCandidates(emptyList()); return }
        val before = currentInputConnection?.getTextBeforeCursor(80, 0)?.toString() ?: ""
        val token = before.takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
        val candidates = if (token.isBlank()) emptyList() else lexicon.suggest(token, 3)
        lastCandidates = candidates
        renderCandidates(candidates)
    }

    private fun renderCandidates(items: List<String>) {
        val row = candidateRow ?: return
        row.removeAllViews()
        val clipLabel = if (clipboardPanel) "KEYS" else "CLIPS"
        row.addView(keyButton(clipLabel) {
            clipboardPanel = !clipboardPanel
            renderKeys()
        }, LinearLayout.LayoutParams(dp(64), dp(38)))
        if (items.isEmpty()) {
            row.addView(TextView(this).apply {
                text = if (sensitiveField) "Private field — suggestions off" else "Darkith English"
                setTextColor(Color.LTGRAY); textSize = 12f; gravity = Gravity.CENTER
            }, LinearLayout.LayoutParams(0, -1, 1f))
        } else items.forEach { candidate ->
            row.addView(keyButton(candidate) { replaceCurrentWord(candidate) },
                LinearLayout.LayoutParams(0, dp(38), 1f))
        }
    }

    private fun replaceCurrentWord(value: String) {
        val ic = currentInputConnection ?: return
        val before = ic.getTextBeforeCursor(80, 0)?.toString() ?: return
        val word = before.takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
        if (word.isNotEmpty()) ic.deleteSurroundingText(word.length, 0)
        ic.commitText(value, 1)
        refreshCandidates()
    }

    private fun renderClipboard(panel: LinearLayout) {
        val header = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        header.addView(keyButton("BACK") { clipboardPanel = false; renderKeys() }, weighted())
        header.addView(keyButton("CLEAR") { saveHistory(emptyList()); renderKeys() }, weighted())
        panel.addView(header, rowParams())
        val history = loadHistory()
        if (history.isEmpty()) {
            panel.addView(TextView(this).apply {
                text = "No saved clips. Enable CLIP to capture while this keyboard is visible."
                setTextColor(Color.LTGRAY); gravity = Gravity.CENTER; textSize = 13f
                setPadding(dp(8), dp(18), dp(8), dp(18))
            })
        } else history.take(8).forEach { item ->
            panel.addView(keyButton(item.take(72)) {
                currentInputConnection?.commitText(item, 1)
                clipboardPanel = false
                renderKeys()
            }, rowParams())
        }
    }

    private fun captureClipboard() {
        try {
            val clip = clipboard.primaryClip ?: return
            if (clip.itemCount == 0) return
            val text = clip.getItemAt(0).coerceToText(this)?.toString()?.trim() ?: return
            if (text.isEmpty() || text.length > 10000) return
            val history = loadHistory().toMutableList()
            history.remove(text)
            history.add(0, text)
            saveHistory(history.take(50))
        } catch (_: SecurityException) {
            // Android/OEM clipboard policy denied access: no false capture claim.
        } catch (_: Exception) {}
    }

    private fun loadHistory(): List<String> = try {
        val raw = prefs.getString("clipboard_history", "[]") ?: "[]"
        val array = JSONArray(raw)
        (0 until array.length()).mapNotNull { array.optString(it, null) }.filter { it.isNotBlank() }
    } catch (_: Exception) { emptyList() }

    private fun saveHistory(items: List<String>) {
        val array = JSONArray()
        items.forEach { array.put(it) }
        prefs.edit().putString("clipboard_history", array.toString()).apply()
    }

    private fun renderKeysIfShiftChanged() { if (shifted) renderKeys() }
    private fun keyButton(label: String, action: () -> Unit): Button = Button(this).apply {
        text = label
        textSize = if (label.length > 8) 10f else 14f
        isAllCaps = false
        setTextColor(Color.WHITE)
        setTypeface(typeface, Typeface.BOLD)
        setBackgroundColor(Color.rgb(54, 60, 70))
        setPadding(dp(2), 0, dp(2), 0)
        minHeight = 0; minimumHeight = 0
        setOnClickListener { action() }
    }
    private fun rowParams() = LinearLayout.LayoutParams(-1, -2)
    private fun weighted() = LinearLayout.LayoutParams(0, dp(38), 1f).apply {
        setMargins(dp(2), dp(2), dp(2), dp(2))
    }
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
}

/**
 * Small deterministic Hunspell-dictionary reader. It expands simple single affix
 * rules from the bundled en_US.aff file. Complex compounds are intentionally not
 * claimed as supported by this first runtime profile.
 */
private class EnglishLexicon(context: Context) {
    private val words = HashSet<String>()
    private val prefixes = HashMap<String, MutableList<String>>()
    private var loaded = false

    @Synchronized fun contains(word: String): Boolean { ensureLoaded(); return word.lowercase(Locale.US) in words }

    @Synchronized fun suggest(input: String, limit: Int): List<String> {
        ensureLoaded()
        val w = input.lowercase(Locale.US)
        if (w.isBlank()) return emptyList()
        val out = LinkedHashSet<String>()
        prefixes[w]?.take(6)?.forEach { out.add(it) }
        if (w !in words) {
            editsOne(w).forEach { if (it in words) out.add(it) }
        }
        out.remove(w)
        return out.take(limit)
    }

    private fun ensureLoaded() {
        if (loaded) return
        synchronized(this) {
            if (loaded) return
            val rules = HashMap<String, List<AffixRule>>()
            val affLines = contextAssets.readLines("keyboard/en_US.aff")
            var i = 0
            while (i < affLines.size) {
                val p = affLines[i].trim().split(Regex("\\s+"))
                if (p.size >= 4 && (p[0] == "SFX" || p[0] == "PFX") && p[2] in setOf("Y", "N")) {
                    val kind = p[0]; val flag = p[1]; val count = p[3].toIntOrNull() ?: 0
                    val list = ArrayList<AffixRule>()
                    repeat(count) {
                        if (i + 1 < affLines.size) {
                            val q = affLines[++i].trim().split(Regex("\\s+"))
                            if (q.size >= 5 && q[0] == kind && q[1] == flag) {
                                list.add(AffixRule(kind, q[2], q[3], q[4]))
                            }
                        }
                    }
                    rules[flag] = list
                }
                i++
            }
            val lines = contextAssets.readLines("keyboard/en_US.dic")
            lines.drop(1).forEach { line ->
                val entry = line.trim()
                if (entry.isEmpty() || entry.startsWith("#")) return@forEach
                val parts = entry.split("/", limit = 2)
                val stem = parts[0].lowercase(Locale.US)
                if (stem.any { it.isLetter() } && stem.length <= 40) words.add(stem)
                if (parts.size > 1) {
                    parts[1].forEach { flag ->
                        rules[flag.toString()]?.forEach { rule ->
                            val expanded = rule.apply(stem) ?: return@forEach
                            if (expanded.length <= 48) words.add(expanded)
                        }
                    }
                }
            }
            words.forEach { word ->
                if (word.length >= 2) prefixes.getOrPut(word.take(2)) { ArrayList() }.add(word)
            }
            prefixes.values.forEach { it.sort() }
            loaded = true
        }
    }

    private fun editsOne(word: String): Set<String> {
        val out = HashSet<String>()
        val alphabet = "abcdefghijklmnopqrstuvwxyz"
        for (i in word.indices) {
            out.add(word.removeRange(i, i + 1))
            if (i + 1 < word.length) {
                val chars = word.toCharArray()
                val t = chars[i]; chars[i] = chars[i + 1]; chars[i + 1] = t
                out.add(String(chars))
            }
            for (c in alphabet) out.add(word.substring(0, i) + c + word.substring(i + 1))
        }
        for (i in 0..word.length) for (c in alphabet) out.add(word.substring(0, i) + c + word.substring(i))
        return out
    }

    private data class AffixRule(val kind: String, val strip: String, val add: String, val condition: String) {
        fun apply(stem: String): String? {
            val regex = try { Regex(if (kind == "SFX") condition + "$" else "^" + condition) } catch (_: Exception) { return null }
            if (!regex.containsMatchIn(stem)) return null
            val base = if (strip == "0") stem else if (kind == "SFX") stem.removeSuffix(strip) else stem.removePrefix(strip)
            return if (kind == "SFX") base + add else add + base
        }
    }

    private val contextAssets get() = AssetLines
    private object AssetLines {
        lateinit var appContext: Context
        fun readLines(path: String): List<String> = appContext.assets.open(path).bufferedReader(Charsets.UTF_8).use { it.readLines() }
    }

    init { AssetLines.appContext = context.applicationContext }
}
