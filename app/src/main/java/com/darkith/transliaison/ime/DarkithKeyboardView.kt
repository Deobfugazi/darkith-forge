package com.darkith.transliaison.ime

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View

/**
 * The drawn QWERTY surface. Owns geometry and touch only — lexical policy, clipboard state and
 * personalisation live in their own owners (DK-SIC-001 §5.2). A key press raises exactly one
 * callback; nothing here mutates an editor.
 */
class DarkithKeyboardView(context: Context) : View(context) {

    interface Listener {
        fun onKey(label: String)
        fun onBackspace()
        fun onEnter()
        fun onShift()
        fun onCandidate(text: String)
    }

    var listener: Listener? = null

    private val rows = listOf("qwertyuiop", "asdfghjkl", "zxcvbnm")
    private val maxKeys = 10

    private var shift = false
    private var caps = false
    private var symbolPage = false
    private var candidates: List<String> = emptyList()

    private val keyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#12151A")
        style = Paint.Style.FILL
    }
    private val specialPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#1E232B")
        style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E8ECF1")
        textAlign = Paint.Align.CENTER
        typeface = Typeface.DEFAULT
    }
    private val candPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#39D3A0")
        style = Paint.Style.FILL
    }

    private var keyRect = RectF()
    private var dpr = 1f
    private var keyH = 0f
    private var candH = 0f

    init {
        dpr = context.resources.displayMetrics.density
        keyH = 52f * dpr
        candH = 34f * dpr
    }

    /** G9: the preference actually changes rendered geometry. */
    fun scaleFor(scale: Float) {
        keyH = 52f * dpr * scale
        invalidate()
        requestLayout()
    }

    fun setCandidates(list: List<String>) {
        candidates = list
        invalidate()
    }

    /** Deterministic intrinsic height so the IME window never needs a layout pass from a parent. */
    override fun onMeasure(w: Int, h: Int) {
        val rowsH = (keyH + 6f * dpr) * 4
        setMeasuredDimension(w, (candH + rowsH).toInt())
    }

    private fun keyFor(x: Float, y: Float): String? {
        if (y < candH) {
            if (candidates.isEmpty()) return null
            val w = width.toFloat() / candidates.size
            val i = (x / w).toInt().coerceIn(0, candidates.size - 1)
            return "CANDSEL:" + candidates[i]
        }

        val body = y - candH
        val rowH = keyH + 6f * dpr
        val row = (body / rowH).toInt()
        if (row < 0 || row > 3) return null

        return when (row) {
            0, 1, 2 -> {
                val set = rows[row]
                val cellW = width.toFloat() / maxKeys
                val offset = if (row == 1) cellW * 0.5f else if (row == 2) cellW * 1.4f else 0f
                val i = ((x - offset) / cellW).toInt()
                if (i < 0 || i >= set.length) null else set[i].toString()
            }
            else -> {
                if (x < width * 0.20f) "SHIFT"
                else if (x < width * 0.32f) "SYM"
                else if (x < width * 0.76f) " "
                else if (x < width * 0.90f) "BACK"
                else "ENTER"
            }
        }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_DOWN) return true
        val k = keyFor(e.x, e.y) ?: return true
        val l = listener ?: return true
        when {
            k.startsWith("CANDSEL:") -> l.onCandidate(k.removePrefix("CANDSEL:"))
            k == "SHIFT" -> { shift = !shift; invalidate(); l.onShift() }
            k == "SYM" -> { symbolPage = !symbolPage; invalidate() }
            k == "BACK" -> l.onBackspace()
            k == "ENTER" -> l.onEnter()
            else -> {
                val out = if (shift xor caps) k.uppercase() else k
                if (shift && !caps) { shift = false; invalidate() }
                l.onKey(out)
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Color.parseColor("#050505"))
        if (candidates.isNotEmpty()) {
            val w = width.toFloat() / candidates.size
            labelPaint.textSize = 15f * dpr
            for ((i, c) in candidates.withIndex()) {
                canvas.drawRect(i * w, 0f, (i + 1) * w, candH, candPaint)
                labelPaint.color = Color.parseColor("#050505")
                val ty = candH / 2f - (labelPaint.descent() + labelPaint.ascent()) / 2f
                canvas.drawText(c, i * w + w / 2f, ty, labelPaint)
            }
            labelPaint.color = Color.parseColor("#E8ECF1")
        }

        val rowH = keyH + 6f * dpr
        labelPaint.textSize = 20f * dpr
        for (row in 0..2) {
            val set = rows[row]
            val cellW = width.toFloat() / maxKeys
            val offset = if (row == 1) cellW * 0.5f else if (row == 2) cellW * 1.4f else 0f
            for (i in set.indices) {
                val left = offset + i * cellW + 2f * dpr
                val top = candH + row * rowH + 3f * dpr
                keyRect.set(left, top, left + cellW - 4f * dpr, top + keyH)
                canvas.drawRoundRect(keyRect, 6f * dpr, 6f * dpr, keyPaint)
                val ch = if (shift xor caps) set[i].uppercase() else set[i].toString()
                drawLabel(canvas, ch, keyRect)
            }
        }

        val botTop = candH + 3 * rowH + 3f * dpr
        val specials = listOf(
            0f to 0.20f to "⇧",
            0.20f to 0.32f to "?123",
            0.32f to 0.76f to "space",
            0.76f to 0.90f to "⌫",
            0.90f to 1.00f to "⏎"
        )
        labelPaint.textSize = 13f * dpr
        for ((span, label) in specials) {
            val (a, b) = span
            keyRect.set(width * a + 2f * dpr, botTop, width * b - 2f * dpr, botTop + keyH)
            canvas.drawRoundRect(keyRect, 6f * dpr, 6f * dpr, specialPaint)
            drawLabel(canvas, label, keyRect)
        }
    }

    private fun drawLabel(canvas: Canvas, text: String, r: RectF) {
        val ty = r.centerY() - (labelPaint.descent() + labelPaint.ascent()) / 2f
        canvas.drawText(text, r.centerX(), ty, labelPaint)
    }
}
