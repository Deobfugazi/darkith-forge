package com.darkith.transliaison.ime

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/**
 * G9 settings surface: every control is bound to [ImePrefs], and [ImePrefs] is the same object the
 * service reads. A toggle here changes runtime behaviour or the test for it fails.
 */
class DarkithImeSettings : Activity() {

    private lateinit var prefs: ImePrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = ImePrefs(this)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }

        val title = TextView(this).apply {
            text = "Darkith Keyboard"
            textSize = 22f
            gravity = Gravity.START
        }
        root.addView(title)

        val status = TextView(this).apply {
            text = Elrp.IDENTITY + " v" + Elrp.VERSION + " · offline"
            textSize = 13f
        }
        root.addView(status)

        root.addView(toggle("Next-word prediction", prefs.prediction) { prefs.prediction = it })
        root.addView(toggle("Candidate strip", prefs.candidates) { prefs.candidates = it })
        root.addView(toggle("Autocorrect", prefs.autocorrect) { prefs.autocorrect = it })
        root.addView(toggle("Clipboard history", prefs.clipHistory) { prefs.clipHistory = it })
        root.addView(toggle("Protect sensitive fields", prefs.privacyFieldBlock) { prefs.privacyFieldBlock = it })

        val clear = Button(this).apply {
            text = "Clear clipboard history"
            setOnClickListener {
                val h = ClipHistory(this@DarkithImeSettings)
                h.clearUnpinned()
                h.close()
                status.text = "Clipboard history cleared"
            }
        }
        root.addView(clear)

        setContentView(root)
    }

    private fun toggle(label: String, initial: Boolean, onChange: (Boolean) -> Unit): Button =
        Button(this).apply {
            text = (if (initial) "☑ " else "☐ ") + label
            setOnClickListener {
                val current = text.toString().startsWith("☑")
                val next = !current
                onChange(next)
                text = (if (next) "☑ " else "☐ ") + label
            }
        }
}
