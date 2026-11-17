package com.darkith.transliaison

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

/**
 * Shared on-device tooling for the forge.
 *
 * The handcoded binaries (libaapt2.so, libzipalign.so) are STATIC AArch64 ET_EXEC images: they
 * carry no interpreter and no dynamic dependencies, so they run directly with no LD_LIBRARY_PATH.
 * They ship under lib/arm64-v8a/ and Android extracts them to nativeLibraryDir (the only
 * exec-capable location for a targetSdk 34 app — the data dir is noexec under SELinux).
 */
object NativeTools {

    fun nativeDir(context: Context): File = File(context.applicationInfo.nativeLibraryDir)

    /** True if the OS actually extracted the handcoded binary where we can exec it. */
    fun hasTool(context: Context, name: String): Boolean {
        val f = File(nativeDir(context), name)
        return f.isFile && f.canExecute()
    }

    /**
     * Align uncompressed (STORED) entries to 4 bytes, as Android 11+ requires for resources.arsc.
     * Prefers the handcoded libzipalign.so; falls back to a pure-Kotlin rewrite so the forge works
     * even before extraction completes.
     */
    fun zipalign(context: Context, input: File, output: File) {
        val tool = File(nativeDir(context), "libzipalign.so")
        if (tool.isFile && tool.canExecute()) {
            try {
                val p = ProcessBuilder(tool.absolutePath, "-f", "4", input.absolutePath, output.absolutePath)
                    .redirectErrorStream(true).start()
                p.inputStream.bufferedReader().readText()
                if (p.waitFor() == 0 && output.isFile && output.length() > 0) return
            } catch (_: Exception) { }
        }
        alignByRewrite(input, output)
    }

    private fun alignByRewrite(input: File, output: File) {
        ZipFile(input).use { zin ->
            ZipOutputStream(FileOutputStream(output)).use { out ->
                val en = zin.entries()
                while (en.hasMoreElements()) {
                    val e = en.nextElement()
                    val data = zin.getInputStream(e).readBytes()
                    val ne = ZipEntry(e.name)
                    if (e.method == ZipEntry.STORED) {
                        val crc = CRC32(); crc.update(data)
                        ne.method = ZipEntry.STORED; ne.size = data.size.toLong()
                        ne.compressedSize = data.size.toLong(); ne.crc = crc.value
                        val off = 30 + e.name.toByteArray(Charsets.UTF_8).size
                        val pad = (4 - (off % 4)) % 4
                        if (pad > 0) ne.extra = ByteArray(pad)
                    } else ne.method = ZipEntry.DEFLATED
                    out.putNextEntry(ne); out.write(data); out.closeEntry()
                }
            }
        }
    }
}
