package com.darkith.transliaison.ime

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Darkith local clipboard history — a separate store from the Android primary clipboard
 * (DK-SIC-001 §5.8). It records only what the IME observed while authorised; it never claims to
 * reconstruct clips it did not see, and it never becomes the system clipboard.
 *
 * Payloads are stored because paste requires them. Sensitive clips are rejected before admission.
 */
class ClipHistory(context: Context) : SQLiteOpenHelper(context, "darkith_clip.db", null, 1) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE clip(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 text TEXT NOT NULL,
                 created INTEGER NOT NULL,
                 pinned INTEGER NOT NULL DEFAULT 0,
                 sensitive INTEGER NOT NULL DEFAULT 0
               )"""
        )
        db.execSQL("CREATE INDEX clip_created ON clip(created DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) {
        db.execSQL("DROP TABLE IF EXISTS clip")
        onCreate(db)
    }

    /** Admit one observed clip. Deduplicates against the newest entry only, so distinct older
     *  user-intended duplicates survive (§5.8 "without destroying distinct items"). */
    fun admit(text: String, sensitive: Boolean, retentionDays: Int) {
        val t = text.trim()
        if (t.isEmpty() || sensitive) return
        val db = writableDatabase
        db.rawQuery("SELECT id, text FROM clip ORDER BY created DESC LIMIT 1", null).use { c ->
            if (c.moveToFirst() && c.getString(1) == t) return
        }
        db.execSQL(
            "INSERT INTO clip(text, created, pinned, sensitive) VALUES(?,?,?,?)",
            arrayOf(t, System.currentTimeMillis(), 0, 0)
        )
        val cutoff = System.currentTimeMillis() - retentionDays.coerceIn(1, 365).toLong() * 86_400_000L
        db.execSQL("DELETE FROM clip WHERE pinned=0 AND created < ?", arrayOf(cutoff))
        db.execSQL(
            "DELETE FROM clip WHERE pinned=0 AND id NOT IN (SELECT id FROM clip WHERE pinned=0 ORDER BY created DESC LIMIT 200)"
        )
    }

    fun recent(limit: Int = 25): List<Pair<Long, String>> {
        val out = ArrayList<Pair<Long, String>>()
        readableDatabase.rawQuery(
            "SELECT id, text FROM clip ORDER BY pinned DESC, created DESC LIMIT ?",
            arrayOf(limit.toString())
        ).use { c ->
            while (c.moveToNext()) out.add(c.getLong(0) to c.getString(1))
        }
        return out
    }

    data class Item(val id: Long, val text: String, val pinned: Boolean, val created: Long)

    fun search(query: String, limit: Int = 100): List<Item> {
        val out = ArrayList<Item>()
        readableDatabase.rawQuery(
            "SELECT id, text, pinned, created FROM clip WHERE instr(lower(text), lower(?)) > 0 ORDER BY pinned DESC, created DESC LIMIT ?",
            arrayOf(query, limit.coerceIn(1, 200).toString())
        ).use { c ->
            while (c.moveToNext()) out.add(Item(c.getLong(0), c.getString(1), c.getInt(2) != 0, c.getLong(3)))
        }
        return out
    }

    fun pin(id: Long) {
        writableDatabase.execSQL("UPDATE clip SET pinned=1 WHERE id=?", arrayOf(id))
    }

    fun setPinned(id: Long, pinned: Boolean) {
        writableDatabase.execSQL("UPDATE clip SET pinned=? WHERE id=?", arrayOf(if (pinned) 1 else 0, id))
    }

    fun delete(id: Long) {
        writableDatabase.execSQL("DELETE FROM clip WHERE id=?", arrayOf(id))
    }

    fun clearUnpinned() {
        writableDatabase.execSQL("DELETE FROM clip WHERE pinned=0")
    }

    fun clearAll() {
        writableDatabase.execSQL("DELETE FROM clip")
    }

    fun count(): Int {
        readableDatabase.rawQuery("SELECT COUNT(*) FROM clip", null).use { c ->
            return if (c.moveToFirst()) c.getInt(0) else 0
        }
    }
}
