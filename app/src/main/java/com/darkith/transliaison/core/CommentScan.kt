package com.darkith.transliaison.core

/**
 * Character-level Kotlin comment integrity check.
 *
 * Detects both ways a comment delimiter can be destroyed:
 *  - UNCLOSED: an opener with no matching closer.
 *  - ORPHAN:   a closer with no opener, which is what stripping the opener off a
 *              KDoc header produces.
 *
 * Delimiters are written as OPEN and CLOSE here on purpose: spelling them out inside this
 * doc comment would terminate it early, which is the very defect being detected.
 *
 * Handles block-comment nesting, string literals, triple-quoted raw strings, escapes and
 * char literals, so a delimiter inside a string is not counted. No Android imports: runs on a
 * plain JVM and in the on-device watchdog.
 */
object CommentScan {

    data class Damage(val kind: String, val line: Int, val detail: String) {
        override fun toString(): String = "$kind at line $line: $detail"
    }

    /** Returns null when the source is balanced. */
    fun scan(src: String): Damage? {
        var i = 0
        var line = 1
        var depth = 0
        var openLine = 0
        var orphanLine = 0

        while (i < src.length) {
            val c = src[i]

            if (c == '\n') { line++; i++; continue }

            // Triple-quoted raw string
            if (depth == 0 && c == '"' && i + 2 < src.length && src[i + 1] == '"' && src[i + 2] == '"') {
                i += 3
                while (i + 2 < src.length &&
                    !(src[i] == '"' && src[i + 1] == '"' && src[i + 2] == '"')) {
                    if (src[i] == '\n') line++
                    i++
                }
                i += 3
                continue
            }

            // Ordinary string literal
            if (depth == 0 && c == '"') {
                i++
                while (i < src.length && src[i] != '"') {
                    if (src[i] == '\\') i++
                    if (i < src.length && src[i] == '\n') line++
                    i++
                }
                i++
                continue
            }

            // Char literal
            if (depth == 0 && c == '\'') {
                if (i + 3 < src.length && src[i + 1] == '\\' && src[i + 3] == '\'') { i += 4; continue }
                if (i + 2 < src.length && src[i + 2] == '\'') { i += 3; continue }
                i++
                continue
            }

            // Line comment. Only meaningful outside a block: inside one, '//' is just text
            // (e.g. the "//" in a content:// URI inside a KDoc line).
            if (depth == 0 && c == '/' && i + 1 < src.length && src[i + 1] == '/') {
                while (i < src.length && src[i] != '\n') i++
                continue
            }

            // Block comment open
            if (c == '/' && i + 1 < src.length && src[i + 1] == '*') {
                depth++
                if (depth == 1) openLine = line
                i += 2
                continue
            }

            // Block comment close
            if (c == '*' && i + 1 < src.length && src[i + 1] == '/') {
                if (depth == 0) {
                    if (orphanLine == 0) orphanLine = line
                } else {
                    depth--
                }
                i += 2
                continue
            }

            i++
        }

        val openTok = "/" + "*"
        val closeTok = "*" + "/"
        return when {
            depth > 0 -> Damage("UNCLOSED", openLine, "$openTok never closed (depth $depth at EOF)")
            orphanLine > 0 -> Damage("ORPHAN", orphanLine, "$closeTok has no opener")
            else -> null
        }
    }

    /** Convenience: scan a file's text, returning null when clean. */
    fun scanFile(text: String): Damage? = scan(text)
}
