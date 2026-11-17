package com.darkith.transliaison

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * AxmlWriter — binary AndroidManifest.xml splice.
 * Locate <application>, splice a self-contained <activity> block after
 * its attribute list. Never re-sort the donor's string pool. Never
 * remap an index. The insertion is a byte-level append.
 */
class AxmlWriter {

    companion object {
        private const val RES_STRING_POOL       = 0x0001
        private const val RES_XML_START_ELEMENT = 0x0102
    }

    fun findApplicationInsertionPoint(axml: ByteArray): Int {
        val buf = ByteBuffer.wrap(axml).order(ByteOrder.LITTLE_ENDIAN)
        var pos = 8
        while (pos + 8 <= axml.size) {
            val type = buf.getShort(pos).toInt() and 0xFFFF
            val chunkSize = buf.getInt(pos + 4)
            if (chunkSize <= 0 || pos + chunkSize > axml.size) break
            if (type == RES_XML_START_ELEMENT) {
                val nameIdx = buf.getInt(pos + 8 + 4)
                if (stringAt(axml, nameIdx) == "application") return pos + chunkSize
            }
            pos += chunkSize
        }
        return -1
    }

    fun spliceActivity(axml: ByteArray, at: Int, block: ByteArray): ByteArray {
        val out = ByteArrayOutputStream(axml.size + block.size + 16)
        out.write(axml, 0, at)
        out.write(block, 0, block.size)
        out.write(axml, at, axml.size - at)
        val spliced = out.toByteArray()
        val bb = ByteBuffer.wrap(spliced).order(ByteOrder.LITTLE_ENDIAN)
        bb.putInt(4, spliced.size)
        return spliced
    }

    fun stringAt(axml: ByteArray, idx: Int): String? {
        val buf = ByteBuffer.wrap(axml).order(ByteOrder.LITTLE_ENDIAN)
        if (axml.size < 8 + 28) return null
        if (buf.getShort(8).toInt() and 0xFFFF != RES_STRING_POOL) return null
        val count = buf.getInt(8 + 8)
        if (idx < 0 || idx >= count) return null
        val off = buf.getInt(8 + 28 + idx * 4)
        val abs = 8 + off
        if (abs >= axml.size) return null
        var p = abs
        var len = axml[p].toInt() and 0xFF; p++
        if (len and 0x80 != 0) { len = ((len and 0x7F) shl 8) or (axml[p].toInt() and 0xFF); p++ }
        val sb = StringBuilder(); var read = 0
        while (read < len && p < axml.size) {
            val b = axml[p].toInt() and 0xFF
            when {
                b < 0x80 -> { sb.append(b.toChar()); p++; read++ }
                b and 0xE0 == 0xC0 -> {
                    sb.append((((b and 0x1F) shl 6) or (axml[p+1].toInt() and 0x3F)).toChar())
                    p += 2; read += 2
                }
                else -> {
                    sb.append((((b and 0x0F) shl 12) or ((axml[p+1].toInt() and 0x3F) shl 6)
                               or (axml[p+2].toInt() and 0x3F)).toChar())
                    p += 3; read += 3
                }
            }
        }
        return sb.toString()
    }
}

