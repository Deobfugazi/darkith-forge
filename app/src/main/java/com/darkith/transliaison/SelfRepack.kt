package com.darkith.transliaison

import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

/**
 * Rewrites an APK with ONE entry replaced and every other entry carried over unchanged
 * (STORED entries such as resources.arsc stay STORED with their CRC, as Android 11+ requires).
 * The old signature files are dropped: no signature survives a rewrite. The caller must
 * zipalign and sign the result. This is what lets the app rebuild itself with a new
 * homekeeper.html without a compiler: the Kotlin/DEX is reused as-is.
 */
object SelfRepack {
    fun isSignatureEntry(name: String): Boolean {
        val n = name.uppercase()
        if (!n.startsWith("META-INF/")) return false
        val rest = n.removePrefix("META-INF/")
        if (rest.contains('/')) return false
        return rest == "MANIFEST.MF" || rest.endsWith(".SF") || rest.endsWith(".RSA") ||
            rest.endsWith(".DSA") || rest.endsWith(".EC")
    }

    /** Returns the number of entries carried over. Throws if [entryName] is absent from [src]. */
    fun rewrite(src: File, out: File, entryName: String, replacement: ByteArray): Int {
        var found = false
        var carried = 0
        ZipFile(src).use { zf ->
            ZipOutputStream(FileOutputStream(out)).use { zo ->
                val en = zf.entries()
                while (en.hasMoreElements()) {
                    val e = en.nextElement()
                    if (isSignatureEntry(e.name)) continue
                    if (e.name == entryName) { found = true; continue }
                    val ne = ZipEntry(e.name)
                    if (e.method == ZipEntry.STORED) {
                        ne.method = ZipEntry.STORED
                        ne.size = e.size
                        ne.compressedSize = e.size
                        ne.crc = e.crc
                    } else {
                        ne.method = ZipEntry.DEFLATED
                    }
                    zo.putNextEntry(ne)
                    if (!e.isDirectory) zf.getInputStream(e).use { it.copyTo(zo) }
                    zo.closeEntry()
                    carried++
                }
                if (!found) throw IllegalStateException("entry not in source APK: $entryName")
                val ne = ZipEntry(entryName)
                ne.method = ZipEntry.DEFLATED
                zo.putNextEntry(ne)
                zo.write(replacement)
                zo.closeEntry()
            }
        }
        return carried
    }
}
