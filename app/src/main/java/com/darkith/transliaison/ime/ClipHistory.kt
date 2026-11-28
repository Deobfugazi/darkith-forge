package com.darkith.transliaison.ime

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Darkith local clipboard history — a separate store from the Android primary clipboard
 * (DK-SIC-001 §5.8). It records only what the IME observed while authorised; it never claims to
 * reconstruct clips it did not see, and it never becomes the system clipboard.
 *
 * Payloads are stored because paste requires them. The evidence stream (AuditWriter) records only
 * admission decisions and identifiers, never the payload text (§8).
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
        if (t.isEmpty()) return
        val db = writableDatabase
        db.rawQuery("SELECT id, text FROM clip ORDER BY created DESC LIMIT 1", null).use { c ->
            if (c.moveToFirst() && c.getString(1) == t) return
        }
        db.execSQL(
            "INSERT INTO clip(text, created, pinned, sensitive) VALUES(?,?,?,?)",
            arrayOf(t, System.currentTimeMillis(), if (sensitive) 1 else 0, if (sensitive) 1 else 0)
        )
        val cutoff = System.currentTimeMillis() - retentionDays.toLong() * 86_400_000L
        db.execSQL("DELETE FROM clip WHERE pinned=0 AND created < ?", arrayOf(cutoff))
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

    fun pin(id: Long) {
        writableDatabase.execSQL("UPDATE clip SET pinned=1 WHERE id=?", arrayOf(id))
    }

    fun delete(id: Long) {
        writableDatabase.execSQL("DELETE FROM clip WHERE id=?", arrayOf(id))
    }

    fun clearUnpinned() {
        writableDatabase.execSQL("DELETE FROM clip WHERE pinned=0")
    }

    fun count(): Int {
        readableDatabase.rawQuery("SELECT COUNT(*) FROM clip", null).use { c ->
            return if (c.moveToFirst()) c.getInt(0) else 0
        }
    }
}
