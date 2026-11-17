package com.darkith.transliaison

import java.io.File
import java.util.zip.ZipFile

object KotlinUnzip {
    fun list(archivePath: String): String {
        return try {
            val f = File(archivePath)
            if (!f.exists()) return "ERROR: not found: $archivePath"
            val sb = StringBuilder()
            ZipFile(f).use { zf ->
                zf.entries().asSequence().forEach { e ->
                    sb.append(e.name).append('\t')
                      .append(e.size).append('\t')
                      .append(if (e.isDirectory) "dir" else "file")
                      .append('\n')
                }
            }
            sb.toString()
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun extract(archivePath: String, destDir: String): String {
        return try {
            val src = File(archivePath)
            if (!src.exists()) return "ERROR: not found: $archivePath"
            val dst = File(destDir).apply { mkdirs() }
            val dstCanon = dst.canonicalPath
            var n = 0
            ZipFile(src).use { zf ->
                zf.entries().asSequence().forEach { e ->
                    val target = File(dst, e.name).canonicalFile
                    if (!target.path.startsWith(dstCanon)) return@forEach
                    if (e.isDirectory) target.mkdirs()
                    else {
                        target.parentFile?.mkdirs()
                        zf.getInputStream(e).use { input ->
                            target.outputStream().use { input.copyTo(it) }
                        }
                    }
                    n++
                }
            }
            "OK $n entries -> $destDir"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun extractOne(archivePath: String, entryName: String, destDir: String): String {
        return try {
            val src = File(archivePath)
            if (!src.exists()) return "ERROR: not found: $archivePath"
            val dst = File(destDir).apply { mkdirs() }
            val dstCanon = dst.canonicalPath
            var extracted = ""
            ZipFile(src).use { zf ->
                val e = zf.getEntry(entryName)
                    ?: return "ERROR: entry not found: $entryName"
                val target = File(dst, e.name).canonicalFile
                if (!target.path.startsWith(dstCanon)) return "ERROR: path traversal"
                if (e.isDirectory) target.mkdirs()
                else {
                    target.parentFile?.mkdirs()
                    zf.getInputStream(e).use { input ->
                        target.outputStream().use { input.copyTo(it) }
                    }
                }
                extracted = target.absolutePath
            }
            "OK $extracted"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }
}
