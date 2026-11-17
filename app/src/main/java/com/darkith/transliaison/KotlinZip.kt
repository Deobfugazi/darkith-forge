package com.darkith.transliaison

import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object KotlinZip {
    fun zip(outputPath: String, joinedInputs: String): String {
        return try {
            val out = File(outputPath).absoluteFile
            out.parentFile?.mkdirs()
            val baseDir = out.parentFile ?: File("/")
            val inputs = joinedInputs.split('\u0001').filter { it.isNotBlank() }
            if (inputs.isEmpty()) return "ERROR: no inputs"
            ZipOutputStream(out.outputStream().buffered()).use { zos ->
                inputs.forEach { raw ->
                    val f = File(raw)
                    if (!f.exists()) return@forEach
                    if (f.isDirectory) addDir(zos, f, baseDir)
                    else addFile(zos, f, baseDir)
                }
            }
            "OK ${out.length()} B -> $outputPath"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }
    private fun addDir(zos: ZipOutputStream, dir: File, base: File) {
        dir.listFiles()?.forEach { c ->
            if (c.isDirectory) addDir(zos, c, base) else addFile(zos, c, base)
        }
    }
    private fun addFile(zos: ZipOutputStream, f: File, base: File) {
        val rel = f.absoluteFile.canonicalFile.path
            .removePrefix(base.canonicalFile.path)
            .trimStart('/', '\\')
        if (rel.isEmpty() || rel.contains("..")) return
        zos.putNextEntry(ZipEntry(rel))
        f.inputStream().use { it.copyTo(zos) }
        zos.closeEntry()
    }
}
