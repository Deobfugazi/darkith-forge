package com.darkith.transliaison.ime

import android.content.ClipboardManager
import android.content.Context
import android.inputmethodservice.InputMethodService
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection

/**
 * The Darkith system keyboard: a real Android IME (DK-SIC-001 §5.1).
 *
 * One service owns the session. It reads [EditorInfo] for the target editor's contract, keeps its
 * own bounded composing state (never trusting the editor to expose full text), and commits only
 * through the live [InputConnection]. Every asynchronous candidate result carries a revision; a
 * result for an obsolete revision is discarded rather than overwriting newer text.
 */
class DarkithImeService : InputMethodService(), DarkithKeyboardView.Listener {

    private var prefs: ImePrefs? = null
    private var clipboardHistory: ClipHistory? = null
    private var keyboard: DarkithKeyboardView? = null

    private var composing = StringBuilder()
    private var revision = 0
    private var sensitiveField = false
    private var lastClip: String? = null

    private val clipListener = ClipboardManager.OnPrimaryClipChangedListener {
        captureClip()
    }

    override fun onCreate() {
        super.onCreate()
        prefs = ImePrefs(this)
        clipboardHistory = ClipHistory(this)
        runCatching {
            (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                .addPrimaryClipChangedListener(clipListener)
        }
    }

    override fun onDestroy() {
        runCatching {
            (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                .removePrimaryClipChangedListener(clipListener)
        }
        clipboardHistory?.close()
        super.onDestroy()
    }

    /** G1/G2: the IME window body. Built natively so no layout file can silently stub it. */
    override fun onCreateInputView(): View {
        val v = DarkithKeyboardView(this)
        v.listener = this
        v.scaleFor(prefs?.heightScale ?: 1.0f)
        keyboard = v
        refreshCandidates()
        return v
    }

    override fun onStartInput(info: EditorInfo?, restarting: Boolean) {
        super.onStartInput(info, restarting)
        composing.setLength(0)
        revision++
        val type = info?.inputType ?: InputType.TYPE_CLASS_TEXT
        sensitiveField = prefs?.privacyFieldBlock == true && isSensitive(type, info)
        keyboard?.setCandidates(emptyList())
    }

    override fun onFinishInput() {
        composing.setLength(0)
        revision++
        super.onFinishInput()
    }

    /** §5.1: limited editors (TYPE_NULL) must degrade, not assume rich composing support. */
    private fun isSensitive(type: Int, info: EditorInfo?): Boolean {
        val variation = type and InputType.TYPE_MASK_VARIATION
        if (type and InputType.TYPE_MASK_CLASS == InputType.TYPE_CLASS_TEXT) {
            return variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
        }
        if (type and InputType.TYPE_MASK_CLASS == InputType.TYPE_CLASS_NUMBER) {
            return variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD
        }
        val flags = info?.imeOptions ?: 0
        return (flags and EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) != 0
    }

    private fun ic(): InputConnection? = currentInputConnection

    override fun onKey(label: String) {
        if (sensitiveField) {
            ic()?.commitText(label, 1)
            return
        }
        composing.append(label)
        revision++
        ic()?.setComposingText(composing, 1)
        refreshCandidates()
    }

    override fun onBackspace() {
        val conn = ic() ?: return
        if (composing.isNotEmpty()) {
            composing.setLength(composing.length - 1)
            revision++
            if (composing.isEmpty()) conn.deleteSurroundingText(1, 0) else conn.setComposingText(composing, 1)
            refreshCandidates()
        } else {
            conn.deleteSurroundingText(1, 0)
        }
    }

    override fun onEnter() {
        val conn = ic() ?: return
        val action = currentInputEditorInfo?.imeOptions?.and(EditorInfo.IME_MASK_ACTION)
            ?: EditorInfo.IME_ACTION_NONE
        if (action != EditorInfo.IME_ACTION_NONE && action != EditorInfo.IME_ACTION_UNSPECIFIED) {
            conn.performEditorAction(action)
        } else {
            conn.commitText("\n", 1)
        }
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    override fun onShift() {
        refreshCandidates()
    }

    override fun onCandidate(text: String) {
        val conn = ic() ?: return
        conn.commitText(text + " ", 1)
        composing.setLength(0)
        revision++
        refreshCandidates()
    }

    /** Bounded, revision-stamped candidate refresh (§5.1, §5.6). */
    private fun refreshCandidates() {
        val v = keyboard ?: return
        val p = prefs ?: return
        if (!p.candidates || sensitiveField) { v.setCandidates(emptyList()); return }
        val token = composing.toString().trim()
        if (token.isEmpty()) { v.setCandidates(emptyList()); return }

        val myRevision = revision
        val out = ArrayList<String>()
        if (p.prediction) out.addAll(Elrp.completing(token, 6))
        if (!Elrp.isValid(token) && !sensitiveField) out.addAll(Elrp.near(token, 4))
        val deduped = out.distinct().take(8)
        if (revision == myRevision) v.setCandidates(deduped)
    }

    /** §5.8: observe only while authorised; never claim completeness; never store sensitive. */
    private fun captureClip() {
        val p = prefs ?: return
        if (!p.clipHistory || sensitiveField) return
        runCatching {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = cm.primaryClip ?: return
            if (clip.itemCount == 0) return
            val text = clip.getItemAt(0).coerceToText(this)?.toString() ?: return
            if (text == lastClip) return
            lastClip = text
            val looksSecret = looksSensitive(text)
            clipboardHistory?.admit(text, looksSecret, 30)
        }
    }

    /** Conservative heuristic only; the declared policy, not a security guarantee (§5.8). */
    private fun looksSensitive(s: String): Boolean {
        val t = s.trim()
        if (t.length in 4..8 && t.all { it.isDigit() }) return true
        val lower = t.lowercase()
        return lower.contains("password") || lower.contains("otp") || lower.contains("token")
    }

    /** G1: expose the picker entry point without pretending a stub settings flow exists. */
    override fun onEvaluateInputViewShown(): Boolean = true
}
