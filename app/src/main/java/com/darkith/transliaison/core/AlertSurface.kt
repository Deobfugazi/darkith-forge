package com.darkith.transliaison.core

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * The popup blob / decision dialog for one Activity.
 *
 * Built from raw android.widget views on purpose: no AndroidX, no Material, no Dialog
 * theme dependency. It is a sibling of the Activity's content inside the same window,
 * so it needs no SYSTEM_ALERT_WINDOW grant and cannot be blocked by another app's overlay.
 *
 * [showAlert] is idempotent per alert id: raising the same alert twice reuses the blob.
 */
class AlertSurface(private val activity: Activity) : AlertBus.Surface {

    private var host: FrameLayout? = null
    private val blobs = LinkedHashMap<String, View>()

    private fun dp(n: Int): Int = (n * activity.resources.displayMetrics.density + 0.5f).toInt()

    private fun ensureHost(): FrameLayout {
        host?.let { return it }
        val content = activity.findViewById<ViewGroup>(android.R.id.content)
        val f = FrameLayout(activity)
        f.layoutParams = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        )
        f.isClickable = false
        f.isFocusable = false
        // Pass through everything outside a blob, so the WebView stays usable behind alerts.
        f.setOnTouchListener { _, _ -> false }
        content.addView(f)
        host = f
        return f
    }

    override fun showAlert(alert: Alert, onChoose: (String) -> Unit) {
        if (blobs.containsKey(alert.id)) return
        val root = ensureHost()

        val accent = when (alert.severity) {
            Severity.CRITICAL -> Color.parseColor("#ff4d4d")
            Severity.DECISION -> Color.parseColor("#5cc8ff")
            Severity.NOTICE -> Color.parseColor("#e8b84b")
            Severity.INFO -> Color.parseColor("#7f8b9e")
        }

        val card = LinearLayout(activity)
        card.orientation = LinearLayout.VERTICAL
        card.isClickable = true
        card.setPadding(dp(18), dp(14), dp(18), dp(14))
        card.background = GradientDrawable().apply {
            setColor(Color.parseColor("#0a0c13"))
            cornerRadius = dp(12).toFloat()
            setStroke(dp(2), accent)
        }

        val head = TextView(activity).apply {
            text = alert.title.ifBlank { alert.cls }
            setTextColor(accent)
            typeface = Typeface.DEFAULT_BOLD
            textSize = 15f
            setPadding(0, 0, 0, dp(6))
        }
        card.addView(head)

        if (alert.body.isNotBlank()) {
            val bodyView = TextView(activity).apply {
                text = alert.body
                setTextColor(Color.parseColor("#dfe5ee"))
                typeface = Typeface.MONOSPACE
                textSize = 12f
                setPadding(0, 0, 0, dp(10))
            }
            val scroll = ScrollView(activity).apply {
                addView(bodyView)
                isVerticalScrollBarEnabled = true
            }
            card.addView(
                scroll,
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    dp(260),
                ),
            )
        }

        val meta = TextView(activity).apply {
            text = "${alert.severity.name} · ${alert.cls} · ${alert.origin}"
            setTextColor(Color.parseColor("#8b93a1"))
            textSize = 10f
            setPadding(0, 0, 0, dp(8))
        }
        card.addView(meta)

        val row = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
        }
        val choices = alert.options.ifEmpty { listOf("OK") }
        for (choice in choices) {
            val b = TextView(activity).apply {
                text = choice
                setTextColor(accent)
                textSize = 13f
                setPadding(dp(14), dp(10), dp(14), dp(10))
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    onChoose(choice)
                    dismissAlert(alert.id)
                }
            }
            row.addView(b)
        }
        card.addView(row)

        val wrapper = FrameLayout(activity).apply {
            setPadding(dp(12), dp(12), dp(12), dp(12))
            isClickable = false
            addView(
                card,
                FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                ).apply { gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL },
            )
        }
        val lp = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT,
        ).apply {
            gravity = Gravity.TOP
            topMargin = dp(48)
        }
        wrapper.layoutParams = lp
        root.addView(wrapper)
        blobs[alert.id] = wrapper
    }

    override fun dismissAlert(id: String) {
        val v = blobs.remove(id) ?: return
        (v.parent as? ViewGroup)?.removeView(v)
    }

    /** Called when the Activity goes away so no stale blob survives a recreation. */
    fun detachAll() {
        val h = host ?: return
        blobs.clear()
        (h.parent as? ViewGroup)?.removeView(h)
        host = null
    }

    companion object {
        /** Convenience for bridges that only have a Context and can reach their Activity. */
        fun attachTo(activity: Activity): AlertSurface {
            val s = AlertSurface(activity)
            AlertBus.attach(s)
            return s
        }

        fun apiLevel(): Int = Build.VERSION.SDK_INT
    }
}
