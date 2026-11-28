package com.darkith.transliaison.ime

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.util.Locale

data class LearnedWordPair(val previous: String, val next: String, val count: Int)

/**
 * Opt-in, local-only next-word model. It stores adjacent accepted word pairs, never full sentences.
 * No learning occurs in sensitive fields or while the preference is disabled.
 */
class PersonalLanguageModel(context: Context) :
    SQLiteOpenHelper(context, "darkith_personal_language.db", null, 1) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE bigram(
                previous TEXT NOT NULL,
                next TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                updated INTEGER NOT NULL,
                PRIMARY KEY(previous, next)
            )"""
        )
        db.execSQL("CREATE INDEX bigram_previous ON bigram(previous, count DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS bigram")
        onCreate(db)
    }

    fun observe(previous: String, next: String) {
        val p = normalize(previous)
        val n = normalize(next)
        if (p.isEmpty() || n.isEmpty() || p == n || !Elrp.isValid(p) || !Elrp.isValid(n)) return
        val db = writableDatabase
        db.beginTransaction()
        try {
            val values = ContentValues().apply {
                put("previous", p)
                put("next", n)
                put("count", 0)
                put("updated", System.currentTimeMillis())
            }
            db.insertWithOnConflict("bigram", null, values, SQLiteDatabase.CONFLICT_IGNORE)
            db.execSQL(
                "UPDATE bigram SET count=count+1, updated=? WHERE previous=? AND next=?",
                arrayOf(System.currentTimeMillis(), p, n)
            )
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun predict(previous: String, limit: Int = 3): List<String> {
        val p = normalize(previous)
        if (p.isEmpty()) return emptyList()
        val out = ArrayList<String>()
        readableDatabase.rawQuery(
            "SELECT next FROM bigram WHERE previous=? ORDER BY count DESC, updated DESC LIMIT ?",
            arrayOf(p, limit.coerceIn(1, 8).toString())
        ).use { cursor ->
            while (cursor.moveToNext()) {
                val candidate = cursor.getString(0)
                if (Elrp.isValid(candidate)) out.add(candidate)
            }
        }
        return out
    }

    fun patterns(limit: Int = 100): List<LearnedWordPair> {
        val out = ArrayList<LearnedWordPair>()
        readableDatabase.rawQuery(
            "SELECT previous, next, count FROM bigram ORDER BY count DESC, updated DESC LIMIT ?",
            arrayOf(limit.coerceIn(1, 500).toString())
        ).use { cursor ->
            while (cursor.moveToNext()) {
                out.add(LearnedWordPair(cursor.getString(0), cursor.getString(1), cursor.getInt(2)))
            }
        }
        return out
    }

    fun exportPatterns(): String = buildString {
        append("previous\\tnext\\tcount\\n")
        patterns(500).forEach { append(it.previous).append('\\t').append(it.next).append('\\t').append(it.count).append('\\n') }
    }

    fun deletePair(previous: String, next: String): Int =
        writableDatabase.delete("bigram", "previous=? AND next=?", arrayOf(normalize(previous), normalize(next)))

    fun clear() {
        writableDatabase.delete("bigram", null, null)
    }

    private fun normalize(value: String): String =
        value.trim().lowercase(Locale.US).takeIf { it.matches(Regex("[a-z][a-z'’-]{1,39}")) }.orEmpty()
}
