package com.darkith.transliaison.ime

import android.content.Context
import android.content.SharedPreferences

/**
 * The single authoritative preference owner (DK-SIC-001 §5.10).
 *
 * Every setting here must change a real runtime behaviour and have a test; a toggle without a
 * runtime consequence is a stub and fails G9. Values are read through one object so no subsystem
 * keeps a divergent copy.
 */
class ImePrefs(context: Context) {

    private val sp: SharedPreferences =
        context.getSharedPreferences("darkith_ime", Context.MODE_PRIVATE)

    /** G9: prediction on/off, read by DarkithIme on every keystroke. */
    var prediction: Boolean
        get() = sp.getBoolean("prediction", true)
        set(v) = sp.edit().putBoolean("prediction", v).apply()

    /** Opt-in personalized next-word prediction from locally observed adjacent word pairs. */
    var nextWordPrediction: Boolean
        get() = sp.getBoolean("next_word_prediction", false)
        set(v) = sp.edit().putBoolean("next_word_prediction", v).apply()

    /** Opt-in learning; stores word pairs only, never full sentences. */
    var personalLearning: Boolean
        get() = sp.getBoolean("personal_learning", false)
        set(v) = sp.edit().putBoolean("personal_learning", v).apply()

    /** G9: suggestion strip visibility. */
    var candidates: Boolean
        get() = sp.getBoolean("candidates", true)
        set(v) = sp.edit().putBoolean("candidates", v).apply()

    /** G9: define the correction policy — suggestion-only, never silent replacement. */
    var autocorrect: Boolean
        get() = sp.getBoolean("autocorrect", false)
        set(v) = sp.edit().putBoolean("autocorrect", v).apply()

    /** G9: clipboard history capture gate. */
    var clipHistory: Boolean
        get() = sp.getBoolean("clip_history", false)
        set(v) = sp.edit().putBoolean("clip_history", v).apply()

    /** Clipboard retention window, independently configurable by the user. */
    var clipRetentionDays: Int
        get() = sp.getInt("clip_retention_days", 30)
        set(v) = sp.edit().putInt("clip_retention_days", v.coerceIn(1, 365)).apply()

    /** G9: optional phone/email/URI exclusion; password and platform no-learning flags are unconditional. */
    var privacyFieldBlock: Boolean
        get() = sp.getBoolean("privacy_field_block", true)
        set(v) = sp.edit().putBoolean("privacy_field_block", v).apply()

    /** G9: keyboard height scale. */
    var heightScale: Float
        get() = sp.getFloat("height_scale", 1.0f)
        set(v) = sp.edit().putFloat("height_scale", v.coerceIn(0.8f, 1.6f)).apply()
}
