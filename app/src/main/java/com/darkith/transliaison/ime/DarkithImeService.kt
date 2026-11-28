package com.darkith.transliaison.ime

import android.content.ClipboardManager
import android.content.Context
import android.inputmethodservice.InputMethodService
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection

/**
 * Native Android input-method service. The live InputConnection is the only editor mutation path.
 * Clipboard observation is attached only while the IME window is visible and is preference-gated.
 */
class DarkithImeService : InputMethodService(), DarkithKeyboardView.Listener {
    private var prefs: ImePrefs? = null
    private var clipboardHistory: ClipHistory? = null
    private var keyboard: DarkithKeyboardView? = null
    private var composing = StringBuilder()
    private var revision = 0
    private var sensitiveField = false
    private var clipListenerAttached = false

    private val clipListener = ClipboardManager.OnPrimaryClipChangedListener { captureClip() }

    override fun onCreate() {
        super.onCreate()
        prefs = ImePrefs(this)
        clipboardHistory = ClipHistory(this)
        Elrp.initialize(applicationContext)
    }

    override fun onDestroy() {
        detachClipboardListener()
        clipboardHistory?.close()
        super.onDestroy()
    }

    override fun onCreateInputView(): View {
        val view = DarkithKeyboardView(this)
        view.listener = this
        view.scaleFor(prefs?.heightScale ?: 1.0f)
        val editor = currentInputEditorInfo
        view.setEditorType(editor?.inputType ?: InputType.TYPE_CLASS_TEXT, editor?.imeOptions ?: 0)
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
        keyboard?.setCandidates(emptyList())
        keyboard?.setEditorType(type, info?.imeOptions ?: 0)
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        val p = prefs ?: return
        if (p.clipHistory && !sensitiveField) attachClipboardListener()
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
        if (sensitiveField) {
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
                composing.append(label)
                revision++
                conn.setComposingText(composing, 1)
                refreshCandidates()
            }
        }
    }

    private fun commitWordAndSpace(conn: InputConnection) {
        val raw = composing.toString()
        var committed = raw
        val p = prefs
        if (raw.isNotBlank() && p?.autocorrect == true && !Elrp.isValid(raw)) {
            // Fail closed: only replace when the bounded spelling path yields exactly one candidate.
            val options = Elrp.near(raw, 2)
            if (options.size == 1) committed = options[0]
        }
        conn.commitText(committed + " ", 1)
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    override fun onBackspace() {
        val conn = ic() ?: return
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
        conn.commitText(text + " ", 1)
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    override fun onClipboard() {
        val p = prefs ?: return
        if (!p.clipHistory) return
        val items = clipboardHistory?.recent(4)?.map { it.second }.orEmpty()
        keyboard?.setClipboardItems(items)
    }

    override fun onClip(text: String) {
        val conn = ic() ?: return
        conn.commitText(text, 1)
        composing.setLength(0)
        revision++
        keyboard?.leaveClipboard()
        refreshCandidates()
    }

    private fun refreshCandidates() {
        val view = keyboard ?: return
        val p = prefs ?: return
        if (!p.candidates || sensitiveField) {
            view.setCandidates(emptyList())
            return
        }
        val token = composing.toString().trim()
        if (token.isEmpty()) {
            view.setCandidates(emptyList())
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
        if (!p.clipHistory || sensitiveField || !clipListenerAttached) return
        runCatching {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = cm.primaryClip ?: return
            if (clip.itemCount == 0) return
            val text = clip.getItemAt(0).coerceToText(this)?.toString() ?: return
            if (text.isBlank() || text.length > 20000) return
            if (looksSensitive(text)) return
            clipboardHistory?.admit(text, false, 30)
        }
    }

    private fun looksSensitive(value: String): Boolean {
        val text = value.trim()
        if (text.length in 4..8 && text.all { it.isDigit() }) return true
        val lower = text.lowercase()
        return lower.contains("password") || lower.contains("one-time code") ||
            lower.contains("verification code") || lower.contains("access token")
    }

    override fun onEvaluateInputViewShown(): Boolean = true
}
