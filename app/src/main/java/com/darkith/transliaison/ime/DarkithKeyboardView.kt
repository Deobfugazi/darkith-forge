package com.darkith.transliaison.ime

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.text.InputType
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo

/** Native key surface. It owns layout geometry and touch only; editor mutations stay in the IME. */
class DarkithKeyboardView(context: Context) : View(context) {
    interface Listener {
        fun onKey(label: String)
        fun onBackspace()
        fun onEnter()
        fun onShift()
        fun onCandidate(text: String)
        fun onClipboard()
        fun onClip(text: String)
        fun onToggleIncognito()
        fun onRejectCandidate(text: String)
        fun onCursorMove(direction: Int)
    }
    var listener: Listener? = null

    private val qwerty = listOf("qwertyuiop", "asdfghjkl", "zxcvbnm")
    private var inputClass = InputType.TYPE_CLASS_TEXT
    private var variation = 0
    private var imeOptions = 0
    private var shift = false
    private var caps = false
    private var lastShiftTapAt = 0L
    private var symbolPage = false
    private var candidates: List<String> = emptyList()
    private var clipboardMode = false
    private var clips: List<String> = emptyList()
    private var incognito = false
    private var downKey: String? = null
    private var downX = 0f
    private var downY = 0f
    private var downAt = 0L
    private var altOptions: List<String> = emptyList()
    private val altRect = RectF()
    private var altCellWidth = 0f
    private val keyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#12151A"); style = Paint.Style.FILL
    }
    private val specialPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#1E232B"); style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E8ECF1"); textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT
    }
    private val candidatePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#39D3A0"); style = Paint.Style.FILL
    }
    private val keyRect = RectF()
    private val dpr = context.resources.displayMetrics.density
    private var keyH = 52f * dpr
    private val candidateH = 34f * dpr

    fun scaleFor(scale: Float) {
        keyH = 52f * dpr * scale.coerceIn(0.8f, 1.6f)
        invalidate(); requestLayout()
    }
    fun setCandidates(list: List<String>) { candidates = list; altOptions = emptyList(); invalidate() }
    fun setClipboardItems(items: List<String>) { clips = items.take(4); altOptions = emptyList(); clipboardMode = true; invalidate() }
    fun leaveClipboard() { clipboardMode = false; altOptions = emptyList(); invalidate() }
    fun setIncognito(enabled: Boolean) { incognito = enabled; altOptions = emptyList(); invalidate() }

    /** Input-type adaptation: number/phone fields get digits; email and URI get useful symbols. */
    fun setEditorType(type: Int, options: Int) {
        inputClass = type and InputType.TYPE_MASK_CLASS
        variation = type and InputType.TYPE_MASK_VARIATION
        imeOptions = options
        symbolPage = false
        shift = false
        caps = false
        altOptions = emptyList()
        invalidate()
    }

    private fun numericMode() =
        inputClass == InputType.TYPE_CLASS_NUMBER || inputClass == InputType.TYPE_CLASS_PHONE

    private fun activeRows(): List<String> = when {
        numericMode() -> listOf("123", "456", "789")
        symbolPage -> listOf("1234567890", "@#$%&*+-=", "()[]{}!?")
        else -> qwerty
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val rowsHeight = (keyH + 6f * dpr) * 4
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec), (candidateH + rowsHeight).toInt())
    }

    private fun keyFor(x: Float, y: Float): String? {
        if (altOptions.isNotEmpty() && altRect.contains(x, y)) {
            val index = ((x - altRect.left) / altCellWidth).toInt().coerceIn(0, altOptions.lastIndex)
            return "ALTSEL:$index"
        }
        if (clipboardMode) {
            if (y < candidateH) return "CLIPBACK"
            val rowH = keyH + 6f * dpr
            val row = ((y - candidateH) / rowH).toInt()
            return if (row in clips.indices) "CLIPSEL:$row" else null
        }
        if (y < candidateH) {
            if (x < width * 0.14f) return "CLIP"
            if (x > width * 0.86f) return "PRIV"
            if (candidates.isEmpty()) return null
            val candidateWidth = width * 0.72f / candidates.size
            val index = ((x - width * 0.14f) / candidateWidth).toInt().coerceIn(0, candidates.lastIndex)
            return "CANDSEL:" + candidates[index]
        }
        val body = y - candidateH
        val rowH = keyH + 6f * dpr
        val row = (body / rowH).toInt()
        if (row !in 0..3) return null
        if (row < 3) {
            val set = activeRows()[row]
            val offset: Float
            val cellW: Float
            if (numericMode()) {
                cellW = width.toFloat() / set.length
                offset = 0f
            } else {
                cellW = width.toFloat() / 10f
                offset = if (row == 1) cellW * 0.5f else if (row == 2) cellW * 1.4f else 0f
            }
            val index = ((x - offset) / cellW).toInt()
            return if (index in set.indices) set[index].toString() else null
        }
        if (numericMode()) {
            return when {
                x < width * 0.18f -> "-"
                x < width * 0.36f -> "SYM"
                x < width * 0.56f -> "0"
                x < width * 0.72f -> "."
                x < width * 0.86f -> "BACK"
                else -> "ENTER"
            }
        }
        val email = variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS ||
            variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS
        val uri = variation == InputType.TYPE_TEXT_VARIATION_URI
        return when {
            x < width * 0.12f -> "SHIFT"
            x < width * 0.24f -> "SYM"
            x < width * 0.36f -> if (email) "@" else if (uri) "/" else ","
            x < width * 0.72f -> " "
            x < width * 0.84f -> "."
            x < width * 0.93f -> "BACK"
            else -> "ENTER"
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val target = listener ?: return true
        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                downX = event.x
                downY = event.y
                downAt = event.eventTime
                downKey = keyFor(event.x, event.y)
                if (altOptions.isNotEmpty() && downKey?.startsWith("ALTSEL:") != true) {
                    altOptions = emptyList()
                    invalidate()
                }
                return true
            }
            MotionEvent.ACTION_UP -> {
                val key = downKey ?: keyFor(event.x, event.y)
                downKey = null
                if (key == null) return true
                if (key == " " && kotlin.math.abs(event.x - downX) > 18f * dpr) {
                    target.onCursorMove(if (event.x > downX) 1 else -1)
                    return true
                }
                if (key.startsWith("ALTSEL:")) {
                    val selected = altOptions.getOrNull(key.removePrefix("ALTSEL:").toIntOrNull() ?: -1)
                    altOptions = emptyList()
                    val output = selected?.let { if (shift xor caps) it.uppercase() else it }
                    if (shift) shift = false
                    invalidate()
                    output?.let(target::onKey)
                    return true
                }
                if (event.eventTime - downAt >= 500L && key.length == 1) {
                    val alternatives = alternativesFor(key)
                    if (alternatives.isNotEmpty()) {
                        altOptions = alternatives
                        altCellWidth = minOf(40f * dpr, (width - 8f * dpr).coerceAtLeast(1f) / altOptions.size)
                        val total = altCellWidth * altOptions.size
                        val left = (downX - total / 2f).coerceIn(4f * dpr, (width - total - 4f * dpr).coerceAtLeast(4f * dpr))
                        val top = (downY - 48f * dpr).coerceAtLeast(candidateH)
                        altRect.set(left, top, left + total, top + 42f * dpr)
                        invalidate()
                        return true
                    }
                }
                when {
                    key.startsWith("CANDSEL:") && event.eventTime - downAt >= 500L ->
                        target.onRejectCandidate(key.removePrefix("CANDSEL:"))
                    key.startsWith("CANDSEL:") -> target.onCandidate(key.removePrefix("CANDSEL:"))
                    key.startsWith("CLIPSEL:") -> clips.getOrNull(key.removePrefix("CLIPSEL:").toIntOrNull() ?: -1)?.let(target::onClip)
                    key == "CLIP" -> target.onClipboard()
                    key == "PRIV" -> target.onToggleIncognito()
                    key == "CLIPBACK" -> { clipboardMode = false; invalidate() }
                    key == "SHIFT" -> {
                        if (event.eventTime - lastShiftTapAt in 1..350L) {
                            caps = !caps
                            shift = false
                        } else shift = !shift
                        lastShiftTapAt = event.eventTime
                        invalidate()
                        target.onShift()
                    }
                    key == "SYM" -> { symbolPage = !symbolPage; invalidate() }
                    key == "BACK" -> target.onBackspace()
                    key == "ENTER" -> target.onEnter()
                    else -> {
                        val out = if (key.length == 1 && key[0].isLetter() && (shift xor caps)) key.uppercase() else key
                        if (shift) { shift = false; invalidate() }
                        target.onKey(out)
                    }
                }
                return true
            }
            MotionEvent.ACTION_CANCEL -> { downKey = null; return true }
        }
        return true
    }

    private fun alternativesFor(key: String): List<String> = when (key.lowercase()) {
        "a" -> listOf("á", "à", "â", "ä", "æ", "å")
        "e" -> listOf("é", "è", "ê", "ë")
        "i" -> listOf("í", "ì", "î", "ï")
        "o" -> listOf("ó", "ò", "ô", "ö", "œ")
        "u" -> listOf("ú", "ù", "û", "ü")
        "n" -> listOf("ñ")
        "c" -> listOf("ç")
        "s" -> listOf("ß")
        "." -> listOf("…", "?", "!")
        "," -> listOf(";", "–", "—")
        "'" -> listOf("’", "`", "´")
        "-" -> listOf("–", "—")
        else -> emptyList()
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Color.parseColor("#050505"))
        if (clipboardMode) {
            labelPaint.textSize = 12f * dpr
            labelPaint.color = Color.parseColor("#39D3A0")
            canvas.drawText("CLIPBOARD HISTORY · TAP HEADER TO RETURN", width / 2f,
                candidateH / 2f - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
            val rowH = keyH + 6f * dpr
            for (index in 0..3) {
                val top = candidateH + index * rowH + 3f * dpr
                keyRect.set(4f * dpr, top, width - 4f * dpr, top + keyH)
                canvas.drawRoundRect(keyRect, 6f * dpr, 6f * dpr, specialPaint)
                val value = clips.getOrNull(index)?.replace("\\n", " ")?.take(42) ?: "—"
                labelPaint.color = Color.parseColor("#E8ECF1")
                labelPaint.textSize = 13f * dpr
                drawLabel(canvas, value, keyRect)
            }
            return
        }
        labelPaint.textSize = 12f * dpr
        labelPaint.color = Color.parseColor("#39D3A0")
        canvas.drawText("CLIP", width * 0.07f, candidateH / 2f - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
        labelPaint.color = if (incognito) Color.parseColor("#FF8A80") else Color.parseColor("#39D3A0")
        canvas.drawText(if (incognito) "PRIVATE" else "PRIV", width * 0.93f,
            candidateH / 2f - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
        if (candidates.isNotEmpty()) {
            val start = width * 0.14f
            val w = width * 0.72f / candidates.size
            labelPaint.textSize = 15f * dpr
            candidates.forEachIndexed { index, value ->
                canvas.drawRect(start + index * w, 0f, start + (index + 1) * w, candidateH, candidatePaint)
                labelPaint.color = Color.BLACK
                val baseline = candidateH / 2f - (labelPaint.descent() + labelPaint.ascent()) / 2f
                canvas.drawText(value, start + index * w + w / 2f, baseline, labelPaint)
            }
            labelPaint.color = Color.parseColor("#E8ECF1")
        }
        val rowH = keyH + 6f * dpr
        val rows = activeRows()
        labelPaint.textSize = 20f * dpr
        for (row in 0..2) {
            val set = rows[row]
            val cellW = if (numericMode()) width.toFloat() / set.length else width.toFloat() / 10f
            val offset = if (numericMode() || symbolPage) 0f else if (row == 1) cellW * 0.5f else if (row == 2) cellW * 1.4f else 0f
            for (index in set.indices) {
                val left = offset + index * cellW + 2f * dpr
                val top = candidateH + row * rowH + 3f * dpr
                keyRect.set(left, top, left + cellW - 4f * dpr, top + keyH)
                canvas.drawRoundRect(keyRect, 6f * dpr, 6f * dpr, keyPaint)
                val label = if (!numericMode() && !symbolPage && (shift xor caps)) set[index].uppercase() else set[index].toString()
                drawLabel(canvas, label, keyRect)
            }
        }
        drawBottomRow(canvas, candidateH + 3 * rowH + 3f * dpr)
        if (altOptions.isNotEmpty()) {
            canvas.drawRoundRect(altRect, 7f * dpr, 7f * dpr, specialPaint)
            labelPaint.textSize = 18f * dpr
            labelPaint.color = Color.parseColor("#E8ECF1")
            altOptions.forEachIndexed { index, value ->
                val cell = RectF(altRect.left + index * altCellWidth, altRect.top,
                    altRect.left + (index + 1) * altCellWidth, altRect.bottom)
                drawLabel(canvas, value, cell)
            }
        }
    }

    private fun drawBottomRow(canvas: Canvas, top: Float) {
        val spans: List<Triple<Float, Float, String>> = if (numericMode()) {
            listOf(Triple(0f,0.18f,"−"), Triple(0.18f,0.36f,"SYM"), Triple(0.36f,0.56f,"0"),
                Triple(0.56f,0.72f,"."), Triple(0.72f,0.86f,"⌫"), Triple(0.86f,1f,"⏎"))
        } else {
            val email = variation == InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS ||
                variation == InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS
            val uri = variation == InputType.TYPE_TEXT_VARIATION_URI
            listOf(Triple(0f,0.12f,"⇧"), Triple(0.12f,0.24f,"?123"),
                Triple(0.24f,0.36f,if (email) "@" else if (uri) "/" else ","),
                Triple(0.36f,0.72f,"space"), Triple(0.72f,0.84f,"."),
                Triple(0.84f,0.93f,"⌫"), Triple(0.93f,1f,"⏎"))
        }
        labelPaint.textSize = 13f * dpr
        spans.forEach { (start, end, label) ->
            keyRect.set(width * start + 2f*dpr, top, width * end - 2f*dpr, top + keyH)
            canvas.drawRoundRect(keyRect, 6f*dpr, 6f*dpr, specialPaint)
            drawLabel(canvas, label, keyRect)
        }
    }

    private fun drawLabel(canvas: Canvas, text: String, rect: RectF) {
        val baseline = rect.centerY() - (labelPaint.descent() + labelPaint.ascent()) / 2f
        canvas.drawText(text, rect.centerX(), baseline, labelPaint)
    }
}
