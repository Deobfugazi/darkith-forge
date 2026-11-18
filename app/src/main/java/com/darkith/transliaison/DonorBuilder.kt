package com.darkith.transliaison

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

class DonorBuilder(private val context: Context) {

    companion object {
        const val DOWNLOADS_DIR = "/sdcard/Download"
        const val DEFAULT_DONOR_DIR = "/sdcard/Darkith/donors"
        const val SCAFFOLD_APK = "$DEFAULT_DONOR_DIR/scaffold.apk"
        const val ANDROID_NS = "http://schemas.android.com/apk/res/android"
    }

    fun selfApkPath(): String = context.applicationInfo.sourceDir

    fun scaffoldApkPath(): String {
        val s = File(SCAFFOLD_APK)
        return if (s.exists()) s.absolutePath else context.applicationInfo.sourceDir
    }

    fun listEntries(apkPath: String): String {
        val f = File(apkPath)
        if (!f.exists()) return "[]"
        return try {
            ZipFile(f).use { zip ->
                val arr = JSONArray()
                val en = zip.entries()
                while (en.hasMoreElements()) {
                    val e = en.nextElement()
                    arr.put(JSONObject().apply {
                        put("name", e.name); put("size", e.size)
                        put("compressedSize", e.compressedSize); put("crc", e.crc)
                        put("method", if (e.method == ZipEntry.STORED) "STORED" else "DEFLATED")
                        put("isDirectory", e.isDirectory)
                    })
                }
                arr.toString()
            }
        } catch (e: Exception) { "[]" }
    }

    fun readEntry(apkPath: String, entryName: String): String {
        val f = File(apkPath)
        if (!f.exists()) return "ERROR: not found"
        return try {
            ZipFile(f).use { zip ->
                val e = zip.getEntry(entryName) ?: return "ERROR: no entry: $entryName"
                val bytes = zip.getInputStream(e).readBytes()
                val text = String(bytes, Charsets.UTF_8)
                val printable = text.count { it.code in 0x20..0x7E || it == '\n' || it == '\r' || it == '\t' }
                if (printable.toDouble() / maxOf(1, text.length) > 0.85) text
                else "BASE64:" + android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
            }
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun writeEntry(apkPath: String, entryName: String, content: String): String {
        return try {
            val bytes = if (content.startsWith("BASE64:"))
                android.util.Base64.decode(content.removePrefix("BASE64:"), android.util.Base64.DEFAULT)
            else content.toByteArray(Charsets.UTF_8)
            val f = File(apkPath)
            if (!f.exists()) return "ERROR: not found"
            val tmp = File(f.parentFile, f.name + ".tmp")
            ZipOutputStream(FileOutputStream(tmp)).use { out ->
                ZipFile(f).use { zin ->
                    val en = zin.entries()
                    while (en.hasMoreElements()) {
                        val e = en.nextElement()
                        if (e.name == entryName) continue
                        copyEntry(zin, e, out)
                    }
                }
                val ne = ZipEntry(entryName)
                ne.method = ZipEntry.DEFLATED
                out.putNextEntry(ne); out.write(bytes); out.closeEntry()
            }
            if (!tmp.renameTo(f)) { tmp.copyTo(f, overwrite = true); tmp.delete() }
            "OK wrote $entryName (${bytes.size} bytes)"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun deleteEntry(apkPath: String, entryName: String): String {
        return try {
            val f = File(apkPath)
            if (!f.exists()) return "ERROR: not found"
            val tmp = File(f.parentFile, f.name + ".tmp")
            ZipOutputStream(FileOutputStream(tmp)).use { out ->
                ZipFile(f).use { zin ->
                    val en = zin.entries()
                    while (en.hasMoreElements()) {
                        val e = en.nextElement()
                        if (e.name == entryName) continue
                        copyEntry(zin, e, out)
                    }
                }
            }
            if (!tmp.renameTo(f)) { tmp.copyTo(f, overwrite = true); tmp.delete() }
            "OK deleted $entryName"
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    fun shipProject(dirPath: String, outputName: String, donorPath: String?): File {
        val dir = File(dirPath)
        if (!dir.exists() || !dir.isDirectory) throw RuntimeException("Project dir not found: $dirPath")
        val files = mutableListOf<ProjectFile>()
        walk(dir, dir, files)
        if (files.isEmpty()) throw RuntimeException("Project is empty")
        val donor = File(donorPath?.takeIf { it.isNotBlank() } ?: SCAFFOLD_APK)
        val src = if (donor.exists()) donor else File(context.applicationInfo.sourceDir)
        if (!src.exists()) throw RuntimeException("No donor and no installed APK")
        return clone(src, files, outputName, File(dirPath).name)
    }

    fun buildFromManifest(manifestJson: String, outputName: String, donorPath: String?): File {
        val root = JSONObject(manifestJson)
        val arr = root.optJSONArray("files") ?: throw RuntimeException("Manifest missing 'files'")
        val files = mutableListOf<ProjectFile>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            files.add(ProjectFile(o.getString("path"), o.optString("content", "").toByteArray(Charsets.UTF_8)))
        }
        if (files.isEmpty()) throw RuntimeException("Manifest empty")
        val donor = File(donorPath?.takeIf { it.isNotBlank() } ?: SCAFFOLD_APK)
        val src = if (donor.exists()) donor else File(context.applicationInfo.sourceDir)
        if (!src.exists()) throw RuntimeException("No donor and no installed APK")
        return clone(src, files, outputName, outputName)
    }

    fun listDonors(): List<File> {
        val dir = File(DEFAULT_DONOR_DIR)
        if (!dir.exists() || !dir.isDirectory) return emptyList()
        return (dir.listFiles { f -> f.isFile && f.name.endsWith(".apk") } ?: emptyArray()).sortedBy { it.name }
    }

    private data class ProjectFile(val path: String, val content: ByteArray)

    private fun walk(root: File, dir: File, out: MutableList<ProjectFile>) {
        val children = dir.listFiles() ?: return
        for (f in children) {
            if (f.isDirectory) { walk(root, f, out); continue }
            val rel = f.relativeTo(root).path.replace(File.separatorChar, '/')
            out.add(ProjectFile(rel, f.readBytes()))
        }
    }

    private fun deriveIdentity(title: String): Pair<String, String> {
        val safe = title.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_').ifEmpty { "app" }
        return ("com.darkith.$safe.app") to (title.ifEmpty { "Darkith App" })
    }

    private fun reencodeManifest(inBytes: ByteArray, pkg: String, lbl: String): ByteArray {
        val root = Axml.parse(inBytes)
            ?: throw RuntimeException("AXML parse failed: donor manifest not decodable")
        Axml.setAttr(root, "", "package", pkg)
        Axml.setAttr(root, ANDROID_NS, "versionName", lbl)
        val app = Axml.findChild(root, "application")
        if (app != null) Axml.setAttr(app, ANDROID_NS, "label", lbl)
        return Axml.encode(root)
    }

    private fun clone(donor: File, project: List<ProjectFile>, outputName: String, title: String): File {
        val (pkg, lbl) = deriveIdentity(title)
        val work = File(context.cacheDir, "donorbuild_${System.currentTimeMillis()}")
        if (!work.mkdirs() && !work.exists()) throw RuntimeException("Cannot create working dir")

        val entries = linkedMapOf<String, ByteArray>()
        var donorManifest: ByteArray? = null
        ZipFile(donor).use { zin ->
            val en = zin.entries()
            while (en.hasMoreElements()) {
                val e = en.nextElement()
                if (e.name.startsWith("META-INF/")) continue
                val data = zin.getInputStream(e).readBytes()
                if (e.name == "AndroidManifest.xml") donorManifest = data else entries[e.name] = data
            }
        }
        val inManifest = donorManifest ?: throw RuntimeException("Donor has no AndroidManifest.xml")
        entries["AndroidManifest.xml"] = reencodeManifest(inManifest, pkg, lbl)
        for (pf in project) entries["assets/" + pf.path.trimStart('/')] = pf.content
        try { entries["assets/vendor/darkith-rt.js"] = context.assets.open("vendor/darkith-rt.js").readBytes() } catch (_: Exception) {}
        if (project.none { it.path == "index.html" }) {
            entries["assets/index.html"] = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Payload</title></head><body><h1>No index.html</h1></body></html>".toByteArray()
        }

        val unsigned = File(work, "unsigned.apk")
        ZipOutputStream(FileOutputStream(unsigned)).use { out ->
            for ((name, data) in entries) {
                if (name == "resources.arsc") {
                    // MUST stay STORED or Android 11+ rejects the APK (App not installed).
                    val crc = java.util.zip.CRC32(); crc.update(data)
                    val e = ZipEntry(name)
                    e.method = ZipEntry.STORED; e.size = data.size.toLong()
                    e.compressedSize = data.size.toLong(); e.crc = crc.value
                    out.putNextEntry(e); out.write(data); out.closeEntry()
                } else {
                    val e = ZipEntry(name); e.method = ZipEntry.DEFLATED
                    out.putNextEntry(e); out.write(data); out.closeEntry()
                }
            }
        }
        val safeName = outputName.replace(Regex("[^A-Za-z0-9._-]"), "_").let { if (it.endsWith(".apk")) it else "$it.apk" }
        val downloads = File(DOWNLOADS_DIR)
        if (!downloads.exists()) downloads.mkdirs()
        val finalApk = File(downloads, safeName)
        // Uncompressed entries (resources.arsc) must be 4-byte aligned or Android 11+ rejects the APK.
        val aligned = File(work, "aligned.apk")
        NativeTools.zipalign(context, unsigned, aligned)
        val cacheSigned = File(context.cacheDir, "signed_${System.currentTimeMillis()}.apk")
        ApkSignerRunner(context).sign(aligned, cacheSigned)
        cacheSigned.copyTo(finalApk, overwrite = true)
        cacheSigned.delete()

        SynchronicityScheduler.reset()
        val syncStatus = SynchronicityScheduler.onBuildComplete("pending")
        if (syncStatus.startsWith("ERROR:")) {
            throw RuntimeException("SYNC_GATE_REFUSED: $syncStatus")
        }

        SynchronicityScheduler.reset()
        if (syncStatus.startsWith("ERROR:")) {
        }

        SynchronicityScheduler.reset()
        if (syncStatus.startsWith("ERROR:")) {
        }

        SynchronicityScheduler.reset()
        // The gate awaits the 10s nonce from the WebView
        if (syncStatus.startsWith("ERROR:")) {
        }
        try { unsigned.delete() } catch (_: Exception) {}
        try { work.deleteRecursively() } catch (_: Exception) {}

        ZipFile(finalApk).use { zf ->
            val me = zf.getEntry("AndroidManifest.xml")
                ?: throw RuntimeException("DARKITH_VERIFY: manifest missing from output")
            val bytes = zf.getInputStream(me).readBytes()
            val parsed = Axml.parse(bytes)
                ?: throw RuntimeException("DARKITH_VERIFY: reencoded manifest not parseable")
            val seenPkg = Axml.getAttr(parsed, "", "package")?.value
            if (seenPkg != pkg) throw RuntimeException("DARKITH_VERIFY: package mismatch wanted=$pkg got=$seenPkg")
            val names = mutableSetOf<String>()
            val it = zf.entries(); while (it.hasMoreElements()) names.add(it.nextElement().name)
            if (!names.contains("classes.dex") && !names.contains("classes2.dex")) {
                throw RuntimeException("DARKITH_VERIFY: no classes.dex in output")
            }
        }
        return finalApk
    }

    private fun copyEntry(zin: ZipFile, e: ZipEntry, out: ZipOutputStream) {
        val copy = ZipEntry(e.name)
        if (e.method == ZipEntry.STORED) {
            copy.method = ZipEntry.STORED
            copy.size = e.size; copy.compressedSize = e.compressedSize; copy.crc = e.crc
        } else copy.method = ZipEntry.DEFLATED
        out.putNextEntry(copy); zin.getInputStream(e).copyTo(out); out.closeEntry()
    }
}

