package com.darkith.transliaison

import android.os.Environment
import java.io.File
import java.io.RandomAccessFile
import java.util.zip.CRC32
import java.util.zip.ZipFile

object ShellBridge {

    fun apkVerify(path: String): String {
        val f = File(path)
        if (!f.exists()) return "ERROR: not found: $path"
        val sb = StringBuilder()
        sb.append("APK: ").append(f.absolutePath).append('\n')
        sb.append("Size: ").append(f.length()).append(" bytes\n")
        return try {
            ZipFile(f).use { zip ->
                var count = 0; var bad = 0
                val en = zip.entries()
                while (en.hasMoreElements()) {
                    val e = en.nextElement(); count++
                    try {
                        zip.getInputStream(e).use { input ->
                            val buf = ByteArray(8192); var total = 0L; val crc = CRC32()
                            while (true) { val n = input.read(buf); if (n <= 0) break; crc.update(buf, 0, n); total += n }
                            if (total != e.size) { bad++; sb.append("  SIZE MISMATCH: ").append(e.name).append('\n') }
                            if (crc.value != e.crc) { bad++; sb.append("  CRC MISMATCH:  ").append(e.name).append('\n') }
                        }
                    } catch (ex: Exception) { bad++; sb.append("  READ ERROR: ").append(e.name).append(" — ").append(ex.message).append('\n') }
                }
                sb.append("Entries: ").append(count).append('\n')
                sb.append("Bad: ").append(bad).append('\n')
                if (bad == 0) sb.append("STATUS: OK\n") else sb.append("STATUS: FAIL\n")
            }
            sb.toString()
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun apkSignature(path: String): String {
        val f = File(path)
        if (!f.exists()) return "ERROR: not found: $path"
        val sb = StringBuilder()
        return try {
            ZipFile(f).use { zip ->
                val meta = mutableListOf<String>()
                val en = zip.entries()
                while (en.hasMoreElements()) { val e = en.nextElement(); if (e.name.startsWith("META-INF/")) meta.add(e.name) }
                if (meta.isEmpty()) sb.append("V1: MISSING\n")
                else { sb.append("V1: present\n"); meta.sorted().forEach { sb.append("  ").append(it).append('\n') } }
            }
            val raf = RandomAccessFile(f, "r")
            val len = raf.length()
            val start = maxOf(0L, len - 65536L)
            raf.seek(start)
            val tail = ByteArray((len - start).toInt())
            raf.readFully(tail); raf.close()
            val magic = "APK Sig Block 42".toByteArray(Charsets.US_ASCII)
            var v2 = false; var i = 0
            while (i <= tail.size - magic.size && !v2) {
                var j = 0
                while (j < magic.size && tail[i + j] == magic[j]) j++
                if (j == magic.size) v2 = true
                i++
            }
            sb.append("V2/V3: ").append(if (v2) "present" else "MISSING").append('\n')
            sb.toString()
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun apkManifest(path: String): String {
        val f = File(path)
        if (!f.exists()) return "ERROR: not found: $path"
        return try {
            ZipFile(f).use { zip ->
                val e = zip.getEntry("AndroidManifest.xml") ?: return "ERROR: no manifest"
                val bytes = zip.getInputStream(e).readBytes()
                val sb = StringBuilder()
                sb.append("axml_size=").append(bytes.size).append('\n')
                val found = mutableSetOf<String>()
                var i = 0
                val run = StringBuilder()
                while (i + 1 < bytes.size) {
                    val lo = bytes[i].toInt() and 0xFF
                    val hi = bytes[i + 1].toInt() and 0xFF
                    val c = lo or (hi shl 8)
                    if (c in 0x20..0x7E) run.append(c.toChar())
                    else { if (run.length >= 4) found.add(run.toString()); run.setLength(0) }
                    i += 2
                }
                if (run.length >= 4) found.add(run.toString())
                found.sorted().take(120).forEach { sb.append("  ").append(it).append('\n') }
                sb.toString()
            }
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun apkInfo(path: String): String {
        val f = File(path)
        if (!f.exists()) return "ERROR: not found: $path"
        return try {
            ZipFile(f).use { zip ->
                val sb = StringBuilder()
                sb.append("path=").append(f.absolutePath).append('\n')
                sb.append("size=").append(f.length()).append('\n')
                var n = 0
                val en = zip.entries()
                while (en.hasMoreElements() && n < 200) { val e = en.nextElement(); sb.append("  ").append(e.name).append("  ").append(e.size).append('\n'); n++ }
                sb.append("entries=").append(n).append('\n')
                sb.toString()
            }
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun shellExec(cmd: String): String = try {
        val pb = ProcessBuilder("sh", "-c", cmd)
        pb.redirectErrorStream(true)
        pb.directory(Environment.getExternalStorageDirectory())
        val p = pb.start()
        val out = p.inputStream.bufferedReader().readText()
        val done = p.waitFor(30, java.util.concurrent.TimeUnit.SECONDS)
        if (!done) { p.destroyForcibly(); "ERROR: timeout\n$out" } else "exit=${p.exitValue()}\n$out"
    } catch (e: Exception) { "ERROR: ${e.message}" }

    private fun pkgRoot(): File {
        val root = File(Environment.getExternalStorageDirectory(), "Darkith/pkg")
        if (!root.exists()) root.mkdirs()
        return root
    }

    fun pkgExtract(archivePath: String, name: String): String {
        val archive = File(archivePath)
        if (!archive.exists()) return "ERROR: archive not found: $archivePath"
        val root = pkgRoot()
        val dest = File(root, name)
        if (dest.exists()) dest.deleteRecursively()
        if (!dest.mkdirs() && !dest.exists()) return "ERROR: cannot create $dest"
        val destCanon = dest.canonicalPath
        return try {
            var count = 0
            java.util.zip.ZipInputStream(archive.inputStream().buffered()).use { zin ->
                var entry = zin.nextEntry
                while (entry != null) {
                    val out = File(dest, entry.name)
                    if (!out.canonicalPath.startsWith(destCanon)) {
                        return "ERROR: path traversal in entry: ${entry.name}"
                    }
                    if (entry.isDirectory) out.mkdirs() else {
                        out.parentFile?.mkdirs()
                        java.io.FileOutputStream(out).use { fos -> zin.copyTo(fos) }
                        count++
                    }
                    zin.closeEntry()
                    entry = zin.nextEntry
                }
            }
            "OK extracted $count entries into $dest"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun pkgHash(archivePath: String): String {
        return try {
            val md = java.security.MessageDigest.getInstance("SHA-256")
            md.digest(File(archivePath).readBytes()).joinToString("") { "%02x".format(it) }
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun pkgInstallName(name: String): String {
        val root = pkgRoot()
        val pkgDir = File(root, name)
        val manifestFile = File(pkgDir, "manifest.json")
        if (!manifestFile.exists()) return "ERROR: not extracted: $name (run pkg.extract first)"
        return try {
            val parsed = org.json.JSONObject(manifestFile.readText())
            val version = parsed.optString("version", "0.0.0")
            val entry   = parsed.optString("entry", "")
            val surface = parsed.optString("surface", name)
            val stateFile = File(root, "state.txt")
            val existing = if (stateFile.exists()) stateFile.readText() else ""
            if (existing.contains("$name\t")) return "OK already installed: $name"
            stateFile.appendText("$name\t$version\t$entry\t$surface\n")
            "OK installed $name v$version"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun pkgRemoveName(name: String): String {
        val root = pkgRoot()
        val pkgDir = File(root, name)
        if (!pkgDir.exists()) return "ERROR: not installed: $name"
        return try {
            pkgDir.deleteRecursively()
            val stateFile = File(root, "state.txt")
            if (stateFile.exists()) {
                val kept = stateFile.readLines().filter { !it.startsWith("$name\t") }
                stateFile.writeText(if (kept.isEmpty()) "" else kept.joinToString("\n") + "\n")
            }
            "OK removed $name"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun pkgList(): String {
        val root = pkgRoot()
        val stateFile = File(root, "state.txt")
        if (!stateFile.exists()) return "[]"
        val arr = org.json.JSONArray()
        stateFile.readLines().forEach { line ->
            if (line.isBlank()) return@forEach
            val p = line.split("\t")
            if (p.size >= 4) arr.put(org.json.JSONObject().apply {
                put("name", p[0]); put("version", p[1]); put("entry", p[2]); put("surface", p[3])
            })
        }
        return arr.toString()
    }

    fun pkgRegistryDir(): String = pkgRoot().absolutePath
}

