package com.darkith.transliaison

import android.content.Context
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

class ChimeraBuilder(private val context: Context) {

    private class ToolFailure(msg: String) : Exception(msg)

    fun forgeChimera(donorsJson: String, html: String, appName: String, pkgName: String): String {
        return try {
            build(html, appName, pkgName, donorsJson)
        } catch (e: ToolFailure) {
            "ERROR: " + e.message
        } catch (e: Throwable) {
            "ERROR: forge failed: ${e.javaClass.simpleName}: ${e.message}"
        }
    }

    private fun build(html: String, appName: String, pkgName: String, options: String): String {
        // 1. native tools
        val nativeDir = File(context.applicationInfo.nativeLibraryDir)
        val aapt2 = File(nativeDir, "libaapt2.so")
        val zipalign = File(nativeDir, "libzipalign.so")
        if (!aapt2.isFile) throw ToolFailure("libaapt2.so missing in ${nativeDir.absolutePath}")
        if (!zipalign.isFile) throw ToolFailure("libzipalign.so missing in ${nativeDir.absolutePath}")

        // 2. stage data files (never executables) into filesDir/engine
        val engineDir = File(context.filesDir, "engine").apply { mkdirs() }
        for (n in listOf("android.jar", "template.dex", "AndroidManifest.tpl.xml")) stage(n, engineDir)
        val androidJar = File(engineDir, "android.jar")
        val templateDex = File(engineDir, "template.dex")

        // 3. manifest from template
        val pkg = sanitizePkg(pkgName)
        if (pkg == context.packageName) throw ToolFailure("refusing to forge over the host app ($pkg)")
        val safeName = appName.replace(Regex("[^A-Za-z0-9._-]"), "_").ifBlank { "app" }
        val manifestText = File(engineDir, "AndroidManifest.tpl.xml").readText()
            .replace("{{PKG_NAME}}", pkg)
            .replace("{{APP_NAME}}", xmlEscape(appName))
        val work = File(context.cacheDir, "chimera_${System.currentTimeMillis()}").apply { mkdirs() }
        val manifestFile = File(work, "AndroidManifest.xml").apply { writeText(withPermissions(manifestText, options)) }

        // 4. aapt2 link
        val unaligned = File(work, "unaligned.apk")
        val link = mutableListOf(
            aapt2.absolutePath, "link", "-o", unaligned.absolutePath,
            "-I", androidJar.absolutePath, "--manifest", manifestFile.absolutePath
        )
        if (!manifestText.contains("targetSdkVersion")) link += listOf("--min-sdk-version", "24", "--target-sdk-version", "34")
        val versionCode = (System.currentTimeMillis() / 1000L).toInt()
        link += listOf("--version-code", versionCode.toString(), "--version-name", "1.0.$versionCode", "--replace-version")
        run("aapt2", link, nativeDir, work)
        if (!unaligned.isFile) throw ToolFailure("aapt2 produced no output")

        // 5. staged.apk = everything from unaligned.apk + homekeeper.html + classes.dex
        val staged = File(work, "staged.apk")
        ZipFile(unaligned).use { zf ->
            ZipOutputStream(staged.outputStream().buffered()).use { zo ->
                for (e in zf.entries().asSequence()) {
                    if (e.isDirectory || e.name == "assets/homekeeper.html" || e.name == "classes.dex") continue
                    copyEntry(zf, e, zo)
                }
                putDeflated(zo, "assets/homekeeper.html", html.toByteArray(Charsets.UTF_8))
                putDeflated(zo, "classes.dex", templateDex.readBytes())
                fun copyAssetsRecursively(assetPath: String) {
                    val files = context.assets.list(assetPath) ?: return
                    for (file in files) {
                        val fullPath = if (assetPath.isEmpty()) file else "$assetPath/$file"
                        if (fullPath == "homekeeper.html" || fullPath == "engine/template.dex") continue
                        try {
                            val bytes = context.assets.open(fullPath).use { it.readBytes() }
                            putDeflated(zo, "assets/$fullPath", bytes)
                        } catch (e: Exception) {
                            copyAssetsRecursively(fullPath)
                        }
                    }
                }
                copyAssetsRecursively("")
            }
        }

        // 6. zipalign AFTER injection (input = staged.apk)
        val aligned = File(work, "aligned.apk")
        run("zipalign", listOf(zipalign.absolutePath, "-f", "4", staged.absolutePath, aligned.absolutePath), nativeDir, work)
        if (!aligned.isFile) throw ToolFailure("zipalign produced no output")

        // 7. sign
        val signedTmp = File(work, "signed.apk")
        try {
            ApkSignerRunner(context).sign(aligned, signedTmp)
        } catch (e: Throwable) {
            throw ToolFailure("apksig signing failed: ${e.javaClass.simpleName}: ${e.message}")
        }
        if (!signedTmp.isFile || signedTmp.length() == 0L) throw ToolFailure("signing produced no output")

        // 9. deliver (Download, falling back to app-private external dir)
        val name = safeName + "_signed.apk"
        val finalFile = try {
            val dl = File("/sdcard/Download", name)
            dl.parentFile?.mkdirs()
            signedTmp.copyTo(dl, overwrite = true)
            dl
        } catch (e: Exception) {
            val alt = File(context.getExternalFilesDir(null) ?: context.filesDir, name)
            signedTmp.copyTo(alt, overwrite = true)
            alt
        }
        work.deleteRecursively()
        return "OK:" + finalFile.absolutePath
    }

    // ---- helpers ----
    // Only these can ever reach the manifest, whatever the page asks for.
    private val allowedPermissions = setOf<String>()

    private fun withPermissions(manifest: String, options: String): String {
        val wanted = LinkedHashSet<String>()
        try {
            val arr = org.json.JSONObject(options).optJSONArray("permissions")
            if (arr != null) for (i in 0 until arr.length()) {
                val p = arr.optString(i)
                if (p.isNotEmpty()) wanted.add(p)
            }
        } catch (e: Exception) { }
        if (wanted.isEmpty()) return manifest
        val xml = wanted.joinToString("\n    ") { "<uses-permission android:name=\"$it\" />" }
        var fgsXml = ""
        if (wanted.contains("android.permission.CAMERA")) fgsXml += "\n    <uses-permission android:name=\"android.permission.FOREGROUND_SERVICE_CAMERA\" />"
        if (wanted.contains("android.permission.RECORD_AUDIO")) fgsXml += "\n    <uses-permission android:name=\"android.permission.FOREGROUND_SERVICE_MICROPHONE\" />"
        if (wanted.contains("android.permission.ACCESS_FINE_LOCATION")) fgsXml += "\n    <uses-permission android:name=\"android.permission.FOREGROUND_SERVICE_LOCATION\" />"
        val idx = manifest.indexOf("<application")
        if (idx < 0) throw Exception("manifest template has no <application> element")
        return manifest.substring(0, idx) + xml + fgsXml + "\n    " + manifest.substring(idx)
    }

    private fun stage(name: String, dir: File) {
        val dest = File(dir, name)
        var len = 0L
        context.assets.open("engine/$name").use { ins ->
            val buf = ByteArray(65536)
            while (true) { val n = ins.read(buf); if (n < 0) break; len += n }
        }
        if (dest.exists() && dest.length() == len) return
        context.assets.open("engine/$name").use { ins -> dest.outputStream().use { ins.copyTo(it) } }
    }

    private fun sanitizePkg(p: String): String {
        val segs = p.lowercase().split('.').map { s ->
            var t = s.replace(Regex("[^a-z0-9_]"), "_")
            if (t.isEmpty() || !t[0].isLetter()) t = "a$t"
            t
        }
        return if (segs.size >= 2) segs.joinToString(".") else "com.darkith." + (segs.firstOrNull() ?: "app")
    }

    private fun xmlEscape(s: String): String =
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")

    private fun copyEntry(zf: ZipFile, e: ZipEntry, zo: ZipOutputStream) {
        val bytes = zf.getInputStream(e).use { it.readBytes() }
        val ne = ZipEntry(e.name)
        if (e.method == ZipEntry.STORED) {
            val crc = CRC32(); crc.update(bytes)
            ne.method = ZipEntry.STORED
            ne.size = bytes.size.toLong()
            ne.compressedSize = bytes.size.toLong()
            ne.crc = crc.value
        } else {
            ne.method = ZipEntry.DEFLATED
        }
        zo.putNextEntry(ne); zo.write(bytes); zo.closeEntry()
    }

    private fun putDeflated(zo: ZipOutputStream, name: String, bytes: ByteArray) {
        val ne = ZipEntry(name); ne.method = ZipEntry.DEFLATED
        zo.putNextEntry(ne); zo.write(bytes); zo.closeEntry()
    }

    private fun run(tool: String, cmd: List<String>, nativeDir: File, cwd: File) {
        val pb = ProcessBuilder(cmd).directory(cwd).redirectErrorStream(true)
        pb.environment()["LD_LIBRARY_PATH"] = nativeDir.absolutePath
        val p = pb.start()
        val sb = StringBuilder()
        val reader = Thread {
            try {
                p.inputStream.bufferedReader().use { r ->
                    val buf = CharArray(4096)
                    while (true) {
                        val n = r.read(buf)
                        if (n < 0) break
                        synchronized(sb) { if (sb.length < 20000) sb.append(buf, 0, n) }
                    }
                }
            } catch (e: Exception) { }
        }
        reader.start()
        if (!p.waitFor(120, TimeUnit.SECONDS)) {
            p.destroyForcibly(); reader.join(2000)
            throw ToolFailure("$tool failed (timeout 120s): " + synchronized(sb) { sb.take(600) })
        }
        reader.join(2000)
        val code = p.exitValue()
        if (code != 0) throw ToolFailure("$tool failed (code $code): " + synchronized(sb) { sb.take(600) })
    }
}
