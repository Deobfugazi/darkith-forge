package com.darkith.transliaison.ime

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/** Settings and local clipboard controls. Every toggle is backed by the same ImePrefs as the IME. */
class DarkithImeSettings : Activity() {
    private lateinit var prefs: ImePrefs
    private lateinit var history: ClipHistory
    private lateinit var historyList: LinearLayout
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = ImePrefs(this)
        Elrp.initialize(applicationContext)
        history = ClipHistory(this)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
        }
        root.addView(TextView(this).apply {
            text = "Darkith Keyboard"
            textSize = 22f
            gravity = Gravity.START
        })
        status = TextView(this).apply {
            text = Elrp.status()
            textSize = 12f
        }
        root.addView(status)
        root.addView(toggle("Word completion", prefs.prediction) { prefs.prediction = it })
        root.addView(toggle("Candidate strip", prefs.candidates) { prefs.candidates = it })
        root.addView(toggle("Conservative autocorrect (unique match only)", prefs.autocorrect) { prefs.autocorrect = it })
        root.addView(toggle("Clipboard history capture (off by default)", prefs.clipHistory) { prefs.clipHistory = it })
        root.addView(toggle("Protect sensitive fields", prefs.privacyFieldBlock) { prefs.privacyFieldBlock = it })

        root.addView(TextView(this).apply {
            text = "Clipboard history is local and captures only while the keyboard is visible. Secret-like clips are rejected heuristically; this is not a perfect sensitive-data detector."
            textSize = 12f
            setPadding(0, 12, 0, 12)
        })

        val search = EditText(this).apply {
            hint = "Search saved clipboard text"
            singleLine = true
        }
        root.addView(search)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        actions.addView(Button(this).apply {
            text = "Clear unpinned"
            setOnClickListener { history.clearUnpinned(); renderHistory(search.text.toString()) }
        }, LinearLayout.LayoutParams(0, -2, 1f))
        actions.addView(Button(this).apply {
            text = "Clear all"
            setOnClickListener {
                history.search("", 200).forEach { history.delete(it.id) }
                renderHistory(search.text.toString())
            }
        }, LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(actions)

        historyList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(historyList)
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                renderHistory(s?.toString().orEmpty())
            }
            override fun afterTextChanged(s: Editable?) {}
        })
        renderHistory("")
        setContentView(root)
    }

    private fun renderHistory(query: String) {
        if (!::historyList.isInitialized) return
        historyList.removeAllViews()
        val items = history.search(query, 100)
        if (items.isEmpty()) {
            historyList.addView(TextView(this).apply {
                text = "No matching saved clips."
                textSize = 13f
            })
            return
        }
        items.forEach { item ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, 8, 0, 8)
            }
            row.addView(TextView(this).apply {
                text = item.text.replace("\n", " ").take(180)
                textSize = 14f
            })
            val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            buttons.addView(Button(this@DarkithImeSettings).apply {
                text = if (item.pinned) "Unpin" else "Pin"
                setOnClickListener {
                    history.setPinned(item.id, !item.pinned)
                    renderHistory(query)
                }
            }, LinearLayout.LayoutParams(0, -2, 1f))
            buttons.addView(Button(this@DarkithImeSettings).apply {
                text = "Copy"
                setOnClickListener {
                    val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    cm.setPrimaryClip(ClipData.newPlainText("Darkith clipboard history", item.text))
                    status.text = "Copied to Android clipboard"
                }
            }, LinearLayout.LayoutParams(0, -2, 1f))
            buttons.addView(Button(this@DarkithImeSettings).apply {
                text = "Delete"
                setOnClickListener {
                    history.delete(item.id)
                    renderHistory(query)
                }
            }, LinearLayout.LayoutParams(0, -2, 1f))
            row.addView(buttons)
            historyList.addView(row)
        }
    }

    override fun onDestroy() {
        if (::history.isInitialized) history.close()
        super.onDestroy()
    }

    private fun toggle(label: String, initial: Boolean, onChange: (Boolean) -> Unit): Button =
        Button(this).apply {
            text = (if (initial) "☑ " else "☐ ") + label
            setOnClickListener {
                val next = !text.toString().startsWith("☑")
                onChange(next)
                text = (if (next) "☑ " else "☐ ") + label
            }
        }
}
