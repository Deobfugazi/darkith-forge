package com.darkith.transliaison

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

object Axml {

    const val CHUNK_STRING_POOL = 0x0001
    const val CHUNK_XML         = 0x0003
    const val CHUNK_START_NS    = 0x0100
    const val CHUNK_END_NS      = 0x0101
    const val CHUNK_START_ELEM  = 0x0102
    const val CHUNK_END_ELEM    = 0x0103
    const val CHUNK_RES_MAP     = 0x0180

    const val TYPE_NULL         = 0x00
    const val TYPE_REFERENCE    = 0x01
    const val TYPE_ATTRIBUTE    = 0x02
    const val TYPE_STRING       = 0x03
    const val TYPE_FLOAT        = 0x04
    const val TYPE_DIMENSION    = 0x05
    const val TYPE_FRACTION     = 0x06
    const val TYPE_INT_DEC      = 0x10
    const val TYPE_INT_HEX      = 0x11
    const val TYPE_INT_BOOLEAN  = 0x12

    const val ANDROID_NS = "http://schemas.android.com/apk/res/android"

    data class Attr(var ns: String, var name: String, var type: Int, var value: String)
    data class Element(
        var ns: String,
        var name: String,
        val attrs: MutableList<Attr> = mutableListOf(),
        val children: MutableList<Element> = mutableListOf()
    )

    private val ANDROID_ATTR: Map<Int, String> = mapOf(
        0x01010000 to "theme", 0x01010001 to "label", 0x01010002 to "icon",
        0x01010003 to "name", 0x01010004 to "permission",
        0x01010010 to "authorities", 0x01010018 to "description",
        0x0101001c to "process", 0x0101001d to "taskAffinity",
        0x0101001e to "allowTaskReparenting", 0x0101001f to "finishOnTaskLaunch",
        0x01010020 to "clearTaskOnLaunch", 0x01010021 to "alwaysRetainTaskState",
        0x01010022 to "stateNotNeeded", 0x01010023 to "excludeFromRecents",
        0x01010024 to "launchMode", 0x01010025 to "screenOrientation",
        0x01010026 to "configChanges", 0x01010204 to "installLocation",
        0x0101020a to "permission", 0x0101020c to "minSdkVersion",
        0x0101020d to "exported", 0x0101020e to "required",
        0x0101021b to "versionCode", 0x0101021c to "versionName",
        0x0101021e to "debuggable", 0x0101021f to "protectionLevel",
        0x0101026c to "enabled", 0x0101026e to "maxSdkVersion",
        0x01010270 to "targetSdkVersion", 0x01010271 to "maxSdkVersion"
    )

    fun parse(axml: ByteArray): Element? {
        if (axml.size < 8) return null
        val bb = ByteBuffer.wrap(axml).order(ByteOrder.LITTLE_ENDIAN)
        val magic = bb.getShort(0).toInt() and 0xFFFF
        if (magic != CHUNK_XML) return null
        val headerSize = bb.getShort(2).toInt() and 0xFFFF

        var strings: List<String> = emptyList()
        var resMap: IntArray? = null
        var offset = if (headerSize >= 8) headerSize else 8
        val len = axml.size
        val stack = ArrayDeque<Element>()
        var root: Element? = null

        while (offset + 8 <= len) {
            val type = bb.getShort(offset).toInt() and 0xFFFF
            val cHeaderSize = bb.getShort(offset + 2).toInt() and 0xFFFF
            val cSize = bb.getInt(offset + 4)
            if (cSize <= 0 || offset + cSize > len) break

            when (type) {
                CHUNK_STRING_POOL -> strings = parseStringPool(bb, offset)
                CHUNK_RES_MAP -> {
                    val count = (cSize - cHeaderSize) / 4
                    val arr = IntArray(count)
                    for (i in 0 until count) arr[i] = bb.getInt(offset + cHeaderSize + i * 4)
                    resMap = arr
                }
                CHUNK_START_ELEM -> {
                    val nsIdx = bb.getInt(offset + 16)
                    val nameIdx = bb.getInt(offset + 20)
                    val attrStart = bb.getShort(offset + 24).toInt() and 0xFFFF
                    val attrSize = bb.getShort(offset + 26).toInt() and 0xFFFF
                    val attrCount = bb.getShort(offset + 28).toInt() and 0xFFFF

                    val elemNs = if (nsIdx == -1) "" else strings.getOrElse(nsIdx) { "" }
                    val elemName = strings.getOrElse(nameIdx) { "#$nameIdx" }
                    val el = Element(elemNs, elemName)

                    val attrBase = offset + 16 + attrStart
                    for (a in 0 until attrCount) {
                        val aOff = attrBase + a * attrSize
                        val aNs = bb.getInt(aOff)
                        val aName = bb.getInt(aOff + 4)
                        val aRaw = bb.getInt(aOff + 8)
                        val aType = bb.getShort(aOff + 12).toInt() and 0xFF
                        val aData = bb.getInt(aOff + 16)

                        var attrName = strings.getOrElse(aName) { "" }
                        var attrNs = if (aNs == -1) "" else strings.getOrElse(aNs) { "" }

                        val rm = resMap
                        if ((attrName.isEmpty() || attrName.startsWith("#")) &&
                            rm != null && aName in rm.indices) {
                            ANDROID_ATTR[rm[aName]]?.let {
                                attrName = it
                                attrNs = ANDROID_NS
                            }
                        }
                        if (attrName.isEmpty()) attrName = "#$aName"

                        val value: String = when (aType) {
                            TYPE_STRING -> {
                                val idx = if (aRaw != -1 && aRaw in strings.indices) aRaw else aData
                                strings.getOrElse(idx) { "@str/$idx" }
                            }
                            TYPE_INT_DEC -> aData.toString()
                            TYPE_INT_HEX -> "0x" + Integer.toHexString(aData)
                            TYPE_INT_BOOLEAN -> if (aData != 0) "true" else "false"
                            TYPE_REFERENCE -> "@ref/0x" + Integer.toHexString(aData)
                            TYPE_ATTRIBUTE -> "?attr/0x" + Integer.toHexString(aData)
                            TYPE_FLOAT -> java.lang.Float.intBitsToFloat(aData).toString()
                            else -> if (aRaw != -1 && aRaw in strings.indices) strings[aRaw] else aData.toString()
                        }

                        el.attrs.add(Attr(attrNs, attrName, aType, value))
                    }

                    val parent = stack.lastOrNull()
                    if (parent != null) parent.children.add(el)
                    else if (root == null) root = el
                    stack.addLast(el)
                }
                CHUNK_END_ELEM -> if (stack.isNotEmpty()) stack.removeLast()
            }
            offset += cSize
        }
        return root
    }

    private fun parseStringPool(bb: ByteBuffer, base: Int): List<String> {
        val count = bb.getInt(base + 8)
        val flags = bb.getInt(base + 16)
        val stringsStart = bb.getInt(base + 20)
        val isUtf8 = (flags and 0x100) != 0
        val offsets = IntArray(count)
        for (i in 0 until count) offsets[i] = bb.getInt(base + 28 + i * 4)
        val out = ArrayList<String>(count)
        for (i in 0 until count) {
            val strOff = base + stringsStart + offsets[i]
            out.add(if (isUtf8) readUtf8(bb, strOff) else readUtf16(bb, strOff))
        }
        return out
    }

    private fun readUtf8(bb: ByteBuffer, off: Int): String {
        var p = off
        val b0 = bb.get(p).toInt() and 0xFF
        if (b0 and 0x80 != 0) p += 2 else p += 1
        val b1 = bb.get(p).toInt() and 0xFF
        val byteLen: Int
        if (b1 and 0x80 != 0) {
            byteLen = ((b1 and 0x7F) shl 8) or (bb.get(p + 1).toInt() and 0xFF)
            p += 2
        } else {
            byteLen = b1
            p += 1
        }
        val bytes = ByteArray(byteLen)
        for (i in 0 until byteLen) bytes[i] = bb.get(p + i)
        return String(bytes, Charsets.UTF_8)
    }

    private fun readUtf16(bb: ByteBuffer, off: Int): String {
        val v = bb.getShort(off).toInt() and 0xFFFF
        val charLen: Int
        val dataOff: Int
        if (v and 0x8000 != 0) {
            charLen = ((v and 0x7FFF) shl 16) or (bb.getShort(off + 2).toInt() and 0xFFFF)
            dataOff = off + 4
        } else {
            charLen = v
            dataOff = off + 2
        }
        val sb = StringBuilder(charLen)
        for (i in 0 until charLen) sb.append(bb.getShort(dataOff + i * 2).toInt().toChar())
        return sb.toString()
    }

    fun encode(root: Element): ByteArray {
        ensureUsesSdk(root)
        val pool = ArrayList<String>()
        val index = HashMap<String, Int>()
        fun intern(s: String): Int {
            index[s]?.let { return it }
            val j = pool.size
            pool.add(s)
            index[s] = j
            return j
        }
        intern(""); intern("android"); intern(ANDROID_NS)
        preintern(root) { intern(it) }
        val spBytes = buildStringPool(pool)

        val resSet = java.util.TreeSet<Int>()
        collectResIds(root, resSet)
        val resIds = resSet.toList()
        val resMapStream = ByteArrayOutputStream()
        writeResMapChunk(resMapStream, resIds)
        val resMapBytes = resMapStream.toByteArray()

        val body = ByteArrayOutputStream()
        writeNamespace(body, CHUNK_START_NS, intern("android"), intern(ANDROID_NS))
        writeElement(body, root) { intern(it) }
        writeNamespace(body, CHUNK_END_NS, intern("android"), intern(ANDROID_NS))
        val bodyBytes = body.toByteArray()

        val xmlHeaderSize = 8
        val total = xmlHeaderSize + spBytes.size + resMapBytes.size + bodyBytes.size
        val out = ByteArrayOutputStream(total)
        val head = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN)
        head.putShort(CHUNK_XML.toShort())
        head.putShort(xmlHeaderSize.toShort())
        head.putInt(total)
        out.write(head.array())
        out.write(spBytes)
        out.write(resMapBytes)
        out.write(bodyBytes)
        return out.toByteArray()
}

    private fun preintern(el: Element, intern: (String) -> Int) {
        intern(el.name)
        if (el.ns.isNotEmpty()) intern(el.ns)
        for (a in el.attrs) {
            intern(a.name)
            if (a.ns.isNotEmpty()) intern(a.ns)
            if (a.type == TYPE_STRING) intern(a.value)
        }
        for (c in el.children) preintern(c, intern)
    }

    private fun buildStringPool(pool: List<String>): ByteArray {
        val count = pool.size
        val encoded = ArrayList<ByteArray>(count)
        for (s in pool) {
            val utf8 = s.toByteArray(Charsets.UTF_8)
            val baos = ByteArrayOutputStream()
            writeVarint(baos, s.length)
            writeVarint(baos, utf8.size)
            baos.write(utf8)
            baos.write(0)
            encoded.add(baos.toByteArray())
        }
        val headerSize = 28
        val offsetTableSize = count * 4
        val stringsStartRel = headerSize + offsetTableSize
        var running = stringsStartRel
        val offsets = IntArray(count)
        for (i in 0 until count) { offsets[i] = running; running += encoded[i].size }
        val dataLen = running - stringsStartRel
        val pad = (4 - (dataLen % 4)) % 4
        val chunkSize = headerSize + offsetTableSize + dataLen + pad
        val buf = ByteBuffer.allocate(chunkSize).order(ByteOrder.LITTLE_ENDIAN)
        buf.putShort(CHUNK_STRING_POOL.toShort()); buf.putShort(headerSize.toShort())
        buf.putInt(chunkSize); buf.putInt(count); buf.putInt(0); buf.putInt(0x100)
        buf.putInt(stringsStartRel); buf.putInt(0)
        for (o in offsets) buf.putInt(o)
        for (e in encoded) buf.put(e)
        repeat(pad) { buf.put(0) }
        return buf.array()
    }

    private fun writeVarint(out: ByteArrayOutputStream, v: Int) {
        if (v < 0x80) out.write(v)
        else { out.write((v shr 8) or 0x80); out.write(v and 0xFF) }
    }

    private fun writeNamespace(out: ByteArrayOutputStream, type: Int, prefixIdx: Int, uriIdx: Int) {
        val size = 24
        val buf = ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN)
        buf.putShort(type.toShort()); buf.putShort(16); buf.putInt(size)
        buf.putInt(-1); buf.putInt(-1); buf.putInt(prefixIdx); buf.putInt(uriIdx)
        out.write(buf.array())
    }

    private fun writeElement(out: ByteArrayOutputStream, el: Element, intern: (String) -> Int) {
        val attrSize = 20
        val startHeaderSize = 36
        val startSize = startHeaderSize + el.attrs.size * attrSize
        val start = ByteBuffer.allocate(startSize).order(ByteOrder.LITTLE_ENDIAN)
        start.putShort(CHUNK_START_ELEM.toShort()); start.putShort(startHeaderSize.toShort())
        start.putInt(startSize); start.putInt(-1); start.putInt(-1)
        start.putInt(if (el.ns.isEmpty()) -1 else intern(el.ns))
        start.putInt(intern(el.name))
        start.putShort(20); start.putShort(attrSize.toShort()); start.putShort(el.attrs.size.toShort())
        start.putShort(0); start.putShort(0); start.putShort(0)
        for (a in el.attrs) {
            start.putInt(if (a.ns.isEmpty()) -1 else intern(a.ns))
            start.putInt(intern(a.name))
            start.putInt(if (a.type == TYPE_STRING) intern(a.value) else -1)
            start.putShort(20); start.put(0); start.put(a.type.toByte())
            start.putInt(typedValue(a, intern))
        }
        out.write(start.array())
        for (c in el.children) writeElement(out, c, intern)
        val endSize = 24
        val end = ByteBuffer.allocate(endSize).order(ByteOrder.LITTLE_ENDIAN)
        end.putShort(CHUNK_END_ELEM.toShort()); end.putShort(16); end.putInt(endSize)
        end.putInt(-1); end.putInt(-1)
        end.putInt(if (el.ns.isEmpty()) -1 else intern(el.ns))
        end.putInt(intern(el.name))
        out.write(end.array())
    }

    private fun typedValue(a: Attr, intern: (String) -> Int): Int = when (a.type) {
        TYPE_STRING -> intern(a.value)
        TYPE_INT_DEC -> a.value.toIntOrNull() ?: 0
        TYPE_INT_HEX -> a.value.removePrefix("0x").toIntOrNull(16) ?: 0
        TYPE_INT_BOOLEAN -> if (a.value.equals("true", true)) -1 else 0
        TYPE_REFERENCE -> a.value.removePrefix("@ref/0x").removePrefix("@").toLongOrNull(16)?.toInt() ?: 0
        TYPE_ATTRIBUTE -> a.value.removePrefix("?attr/0x").toLongOrNull(16)?.toInt() ?: 0
        else -> a.value.toIntOrNull() ?: 0
    }

    fun setAttr(el: Element, ns: String, name: String, value: String) {
        for (a in el.attrs) {
            if (a.name == name && a.ns == ns) { a.value = value; a.type = TYPE_STRING; return }
        }
        el.attrs.add(Attr(ns, name, TYPE_STRING, value))
    }

    fun getAttr(el: Element, ns: String, name: String): Attr? =
        el.attrs.firstOrNull { it.name == name && it.ns == ns }

    fun findChild(el: Element, name: String): Element? =
        el.children.firstOrNull { it.name == name }

    // AXML_RES_MAP_USES_SDK_V20_2
    private val USES_SDK_MIN = 24
    private val USES_SDK_TGT = 34
    private val RES_MIN_SDK   = 0x0101020c
    private val RES_TGT_SDK   = 0x01010270

    private fun ensureUsesSdk(root: Element) {
        val existing = root.children.firstOrNull { it.name == "uses-sdk" }
        if (existing == null) {
            val u = Element("", "uses-sdk")
            u.attrs.add(Attr(ANDROID_NS, "minSdkVersion", TYPE_INT_DEC, USES_SDK_MIN.toString()))
            u.attrs.add(Attr(ANDROID_NS, "targetSdkVersion", TYPE_INT_DEC, USES_SDK_TGT.toString()))
            val appIdx = root.children.indexOfFirst { it.name == "application" }
            if (appIdx >= 0) root.children.add(appIdx, u) else root.children.add(0, u)
            return
        }
        fun ensureInt(name: String, def: Int) {
            val a = existing.attrs.firstOrNull { it.name == name }
            if (a == null) {
                existing.attrs.add(Attr(ANDROID_NS, name, TYPE_INT_DEC, def.toString()))
            } else {
                a.ns = ANDROID_NS
                a.type = TYPE_INT_DEC
                val n = a.value.toIntOrNull() ?: def
                a.value = n.toString()
            }
        }
        ensureInt("minSdkVersion", USES_SDK_MIN)
        ensureInt("targetSdkVersion", USES_SDK_TGT)
    }

    private fun collectResIds(root: Element, out: MutableSet<Int>) {
        val rev = HashMap<String, Int>(ANDROID_ATTR.size * 2)
        for ((k, v) in ANDROID_ATTR) rev[v] = k
        fun walk(e: Element) {
            for (a in e.attrs) {
                if (a.ns == ANDROID_NS) {
                    val id = rev[a.name]
                    if (id != null) out.add(id)
                }
            }
            for (c in e.children) walk(c)
        }
        walk(root)
        out.add(RES_MIN_SDK)
        out.add(RES_TGT_SDK)
    }

    private fun writeResMapChunk(out: ByteArrayOutputStream, ids: List<Int>) {
        if (ids.isEmpty()) return
        val headerSize = 8
        val chunkSize = headerSize + ids.size * 4
        val buf = ByteBuffer.allocate(chunkSize).order(ByteOrder.LITTLE_ENDIAN)
        buf.putShort(CHUNK_RES_MAP.toShort())
        buf.putShort(headerSize.toShort())
        buf.putInt(chunkSize)
        for (id in ids) buf.putInt(id)
        out.write(buf.array())
    }

}

