package com.darkith.transliaison.ime

import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import android.view.KeyCharacterMap
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.ExtractedTextRequest
import android.view.inputmethod.InputConnection

/**
 * Native Android input-method service. The live InputConnection is the only editor mutation path.
 * Clipboard observation is attached only while the IME window is visible and is preference-gated.
 */
class DarkithImeService : InputMethodService(), DarkithKeyboardView.Listener {
    private var prefs: ImePrefs? = null
    private var clipboardHistory: ClipHistory? = null
    private var languageModel: PersonalLanguageModel? = null
    private var keyboard: DarkithKeyboardView? = null
    private var composing = StringBuilder()
    private var revision = 0
    private var sensitiveField = false
    private var limitedEditor = false
    private var incognito = false
    private var lastCorrection: Pair<String, String>? = null
    private var clipListenerAttached = false

    private val clipListener = ClipboardManager.OnPrimaryClipChangedListener { captureClip() }

    override fun onCreate() {
        super.onCreate()
        prefs = ImePrefs(this)
        clipboardHistory = ClipHistory(this)
        languageModel = PersonalLanguageModel(this)
        Elrp.initialize(applicationContext)
    }

    override fun onDestroy() {
        detachClipboardListener()
        clipboardHistory?.close()
        languageModel?.close()
        super.onDestroy()
    }

    override fun onCreateInputView(): View {
        val view = DarkithKeyboardView(this)
        view.listener = this
        view.scaleFor(prefs?.heightScale ?: 1.0f)
        val editor = currentInputEditorInfo
        view.setEditorType(editor?.inputType ?: InputType.TYPE_CLASS_TEXT, editor?.imeOptions ?: 0)
        view.setIncognito(incognito)
        keyboard = view
        refreshCandidates()
        return view
    }

    override fun onStartInput(info: EditorInfo?, restarting: Boolean) {
        super.onStartInput(info, restarting)
        composing.setLength(0)
        revision++
        val type = info?.inputType ?: InputType.TYPE_CLASS_TEXT
        sensitiveField = prefs?.privacyFieldBlock == true && isSensitive(type, info)
        limitedEditor = type == InputType.TYPE_NULL
        incognito = false
        lastCorrection = null
        keyboard?.setCandidates(emptyList())
        keyboard?.setIncognito(false)
        keyboard?.setEditorType(type, info?.imeOptions ?: 0)
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        val p = prefs ?: return
        if (p.clipHistory && !sensitiveField && !incognito) attachClipboardListener()
    }

    override fun onFinishInputView(finishingInput: Boolean) {
        detachClipboardListener()
        super.onFinishInputView(finishingInput)
    }

    override fun onFinishInput() {
        composing.setLength(0)
        revision++
        super.onFinishInput()
    }

    private fun isSensitive(type: Int, info: EditorInfo?): Boolean {
        val klass = type and InputType.TYPE_MASK_CLASS
        val variation = type and InputType.TYPE_MASK_VARIATION
        if (klass == InputType.TYPE_CLASS_TEXT) {
            if (variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD) return true
        }
        if (klass == InputType.TYPE_CLASS_NUMBER &&
            variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD) return true
        return ((info?.imeOptions ?: 0) and EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) != 0
    }

    private fun ic(): InputConnection? = currentInputConnection

    override fun onKey(label: String) {
        val conn = ic() ?: return
        if (limitedEditor) {
            sendRawText(conn, label)
            return
        }
        if (sensitiveField || incognito) {
            lastCorrection = null
            conn.commitText(label, 1)
            return
        }
        when {
            label == " " -> commitWordAndSpace(conn)
            label.length == 1 && !label[0].isLetter() -> {
                conn.commitText(composing.toString() + label, 1)
                composing.setLength(0)
                revision++
                refreshCandidates()
            }
            else -> {
                lastCorrection = null
                composing.append(label)
                revision++
                conn.setComposingText(composing, 1)
                refreshCandidates()
            }
        }
    }

    private fun commitWordAndSpace(conn: InputConnection) {
        val raw = composing.toString()
        if (limitedEditor) {
            sendRawText(conn, raw + " ")
            composing.setLength(0)
            revision++
            refreshCandidates()
            return
        }
        if (sensitiveField || incognito) {
            conn.commitText(raw + " ", 1)
            composing.setLength(0)
            revision++
            refreshCandidates()
            return
        }
        val before = conn.getTextBeforeCursor(120, 0)?.toString().orEmpty()
        val contextBefore = if (raw.isNotEmpty() && before.endsWith(raw)) before.dropLast(raw.length) else before
        val previousWord = contextBefore.trimEnd().takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
        var committed = raw
        val p = prefs
        if (raw.isNotBlank() && p?.autocorrect == true && !Elrp.isValid(raw)) {
            // Fail closed: only replace when the bounded spelling path yields exactly one candidate.
            val options = Elrp.near(raw, 2)
            if (options.size == 1) committed = options[0]
        }
        conn.commitText(committed + " ", 1)
        lastCorrection = if (committed != raw) raw to committed else null
        if (raw.isNotBlank() && previousWord.isNotBlank() && prefs?.personalLearning == true) {
            runCatching { languageModel?.observe(previousWord, committed) }
        }
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    override fun onBackspace() {
        val conn = ic() ?: return
        if (limitedEditor) {
            sendKey(conn, KeyEvent.KEYCODE_DEL)
            return
        }
        val undo = lastCorrection
        if (undo != null && !sensitiveField && !incognito) {
            val before = conn.getTextBeforeCursor(120, 0)?.toString().orEmpty()
            val suffix = undo.second + " "
            if (before.endsWith(suffix)) {
                conn.deleteSurroundingText(suffix.length, 0)
                conn.commitText(undo.first, 1)
                lastCorrection = null
                composing.setLength(0)
                revision++
                refreshCandidates()
                return
            }
            lastCorrection = null
        }
        if (composing.isNotEmpty()) {
            composing.setLength(composing.length - 1)
            revision++
            if (composing.isEmpty()) conn.deleteSurroundingText(1, 0)
            else conn.setComposingText(composing, 1)
            refreshCandidates()
        } else conn.deleteSurroundingText(1, 0)
    }

    override fun onEnter() {
        val conn = ic() ?: return
        lastCorrection = null
        if (limitedEditor) {
            sendKey(conn, KeyEvent.KEYCODE_ENTER)
            composing.setLength(0)
            return
        }
        val action = currentInputEditorInfo?.imeOptions?.and(EditorInfo.IME_MASK_ACTION)
            ?: EditorInfo.IME_ACTION_NONE
        conn.commitText(composing.toString(), 1)
        composing.setLength(0)
        revision++
        if (action != EditorInfo.IME_ACTION_NONE && action != EditorInfo.IME_ACTION_UNSPECIFIED) {
            conn.performEditorAction(action)
        } else conn.commitText("\n", 1)
        refreshCandidates()
    }

    override fun onShift() { refreshCandidates() }

    override fun onCandidate(text: String) {
        val conn = ic() ?: return
        if (limitedEditor || sensitiveField || incognito) return
        lastCorrection = null
        val raw = composing.toString()
        if (prefs?.personalLearning == true) {
            val before = conn.getTextBeforeCursor(120, 0)?.toString().orEmpty()
            val contextBefore = if (raw.isNotEmpty() && before.endsWith(raw)) before.dropLast(raw.length) else before
            val previous = contextBefore.trimEnd().takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
            if (previous.isNotBlank()) runCatching { languageModel?.observe(previous, text) }
        }
        conn.commitText(text + " ", 1)
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    override fun onClipboard() {
        val p = prefs ?: return
        if (!p.clipHistory || sensitiveField || incognito || limitedEditor) return
        val items = clipboardHistory?.recent(4)?.map { it.second }.orEmpty()
        keyboard?.setClipboardItems(items)
    }

    override fun onClip(text: String) {
        val conn = ic() ?: return
        if (sensitiveField || incognito) return
        if (limitedEditor) sendRawText(conn, text) else conn.commitText(text, 1)
        composing.setLength(0)
        revision++
        keyboard?.leaveClipboard()
        refreshCandidates()
    }

    override fun onToggleIncognito() {
        incognito = !incognito
        lastCorrection = null
        keyboard?.setIncognito(incognito)
        if (incognito) {
            detachClipboardListener()
            keyboard?.setCandidates(emptyList())
        } else {
            val p = prefs
            if (p?.clipHistory == true && !sensitiveField) attachClipboardListener()
            refreshCandidates()
        }
    }

    override fun onRejectCandidate(text: String) {
        if (sensitiveField || incognito || limitedEditor) return
        Elrp.rejectSuggestion(this, text)
        refreshCandidates()
    }

    override fun onCursorMove(direction: Int) {
        val conn = ic() ?: return
        lastCorrection = null
        if (limitedEditor) {
            sendKey(conn, if (direction < 0) KeyEvent.KEYCODE_DPAD_LEFT else KeyEvent.KEYCODE_DPAD_RIGHT)
            return
        }
        runCatching {
            val extracted = conn.getExtractedText(ExtractedTextRequest(), 0)
            if (extracted == null) {
                sendKey(conn, if (direction < 0) KeyEvent.KEYCODE_DPAD_LEFT else KeyEvent.KEYCODE_DPAD_RIGHT)
            } else {
                val start = extracted.startOffset.coerceAtLeast(0)
                val low = minOf(extracted.selectionStart, extracted.selectionEnd)
                val high = maxOf(extracted.selectionStart, extracted.selectionEnd)
                val relative = if (low != high) {
                    if (direction < 0) low else high
                } else low + direction
                val absolute = (start + relative).coerceAtLeast(0)
                conn.setSelection(absolute, absolute)
            }
        }
    }

    private fun sendRawText(conn: InputConnection, value: String) {
        if (value.isEmpty()) return
        val events = runCatching {
            KeyCharacterMap.load(KeyCharacterMap.VIRTUAL_KEYBOARD).getEvents(value.toCharArray())
        }.getOrNull() ?: return
        events.forEach { event ->
            conn.sendKeyEvent(KeyEvent.changeFlags(event, event.flags or KeyEvent.FLAG_SOFT_KEYBOARD))
        }
    }

    private fun sendKey(conn: InputConnection, keyCode: Int) {
        val down = SystemClock.uptimeMillis()
        conn.sendKeyEvent(KeyEvent(down, down, KeyEvent.ACTION_DOWN, keyCode, 0, 0,
            KeyCharacterMap.VIRTUAL_KEYBOARD, 0, KeyEvent.FLAG_SOFT_KEYBOARD))
        conn.sendKeyEvent(KeyEvent(down, SystemClock.uptimeMillis(), KeyEvent.ACTION_UP, keyCode, 0, 0,
            KeyCharacterMap.VIRTUAL_KEYBOARD, 0, KeyEvent.FLAG_SOFT_KEYBOARD))
    }

    private fun refreshCandidates() {
        val view = keyboard ?: return
        val p = prefs ?: return
        if (!p.candidates || sensitiveField || incognito || limitedEditor) {
            view.setCandidates(emptyList())
            return
        }
        if (!ic()?.getSelectedText(0).isNullOrEmpty()) {
            view.setCandidates(emptyList())
            return
        }
        val token = composing.toString().trim()
        if (token.isEmpty()) {
            val before = ic()?.getTextBeforeCursor(120, 0)?.toString().orEmpty()
            val previous = before.trimEnd().takeLastWhile { it.isLetter() || it == '\'' || it == '’' }
            val next = if (p.nextWordPrediction && previous.isNotBlank())
                runCatching { languageModel?.predict(previous, 3).orEmpty() }.getOrDefault(emptyList()) else emptyList()
            view.setCandidates(next)
            return
        }
        val requestRevision = revision
        val out = ArrayList<String>()
        if (p.prediction) out.addAll(Elrp.completing(token, 6))
        if (!Elrp.isValid(token)) out.addAll(Elrp.near(token, 4))
        if (revision == requestRevision) view.setCandidates(out.distinct().take(8))
    }

    private fun attachClipboardListener() {
        if (clipListenerAttached) return
        try {
            (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                .addPrimaryClipChangedListener(clipListener)
            clipListenerAttached = true
        } catch (_: SecurityException) {
            clipListenerAttached = false
        }
    }

    private fun detachClipboardListener() {
        if (!clipListenerAttached) return
        try {
            (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                .removePrimaryClipChangedListener(clipListener)
        } catch (_: Exception) {}
        clipListenerAttached = false
    }

    private fun captureClip() {
        val p = prefs ?: return
        if (!p.clipHistory || sensitiveField || incognito || !clipListenerAttached) return
        runCatching {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = cm.primaryClip ?: return
            if (clip.itemCount == 0 || !clip.description.hasMimeType(ClipDescription.MIMETYPE_TEXT_PLAIN)) return
            if (Build.VERSION.SDK_INT >= 33 &&
                clip.description.extras?.getBoolean(ClipDescription.EXTRA_IS_SENSITIVE, false) == true) return
            val texts = ArrayList<String>(clip.itemCount)
            for (index in 0 until clip.itemCount) {
                val item = clip.getItemAt(index)
                if (item.uri != null || item.intent != null) return
                val text = item.text?.toString() ?: return
                if (text.isBlank() || text.length > 20000 || looksSensitive(text)) return
                texts.add(text)
            }
            texts.forEach { clipboardHistory?.admit(it, false, p.clipRetentionDays) }
        }
    }

    private fun looksSensitive(value: String): Boolean {
        val text = value.trim()
        if (text.length in 4..8 && text.all { it.isDigit() }) return true
        val lower = text.lowercase()
        val digits = text.filter(Char::isDigit)
        val cardLike = digits.length in 13..19 && passesLuhn(digits)
        val tokenLike = Regex("(?i)(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})").containsMatchIn(text)
        val jwtLike = Regex("eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}").containsMatchIn(text)
        val keyLike = text.contains("-----BEGIN") && text.contains("PRIVATE KEY-----")
        val bearerLike = Regex("(?i)\\bBearer\\s+[A-Za-z0-9._~+/-]{16,}").containsMatchIn(text)
        val labelledCode = Regex("(?i)(otp|verification|security|one.time)\\s*(code)?\\D{0,12}\\d{4,8}").containsMatchIn(text)
        return cardLike || tokenLike || jwtLike || keyLike || bearerLike || labelledCode ||
            lower.contains("password") || lower.contains("one-time code") ||
            lower.contains("verification code") || lower.contains("access token")
    }

    private fun passesLuhn(number: String): Boolean {
        var sum = 0
        var double = false
        for (index in number.lastIndex downTo 0) {
            var digit = number[index].digitToIntOrNull() ?: return false
            if (double) {
                digit *= 2
                if (digit > 9) digit -= 9
            }
            sum += digit
            double = !double
        }
        return sum % 10 == 0
    }

    override fun onEvaluateInputViewShown(): Boolean = true
}
