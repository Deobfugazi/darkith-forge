package com.darkith.transliaison

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

class BuildEngine(private val context: Context) {

    private val nativeDir = context.applicationInfo.nativeLibraryDir
    private val aapt2 = File(nativeDir, "libaapt2.so")

    fun build(html: String, appName: String, pkgName: String, workingDir: File): File {
        val manifestTpl = context.assets.open("engine/AndroidManifest.tpl.xml").bufferedReader().use { it.readText() }
        val manifest = manifestTpl.replace("{{APP_NAME}}", appName).replace("{{PKG_NAME}}", pkgName)
        val manifestFile = File(workingDir, "AndroidManifest.xml")
        manifestFile.writeText(manifest)

        val assetsDir = File(workingDir, "assets"); assetsDir.mkdirs()
        val injected = injectRuntimeExternal(html)
        File(assetsDir, "index.html").writeText(injected)
        val vendorDir = File(assetsDir, "vendor"); vendorDir.mkdirs()
        context.assets.open("vendor/darkith-rt.js").use { input -> FileOutputStream(File(vendorDir, "darkith-rt.js")).use { output -> input.copyTo(output) } }

        val resDir = File(workingDir, "res"); resDir.mkdirs()
        val valuesDir = File(resDir, "values"); valuesDir.mkdirs()
        File(valuesDir, "strings.xml").writeText(
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources><string name=\"app_name\">$appName</string></resources>"
        )
        val resZip = File(workingDir, "res.zip")
        runProcess(listOf(aapt2.absolutePath, "compile", "--dir", resDir.absolutePath, "-o", resZip.absolutePath))

        val androidJar = File(workingDir, "android.jar")
        context.assets.open("engine/android.jar").use { input -> FileOutputStream(androidJar).use { output -> input.copyTo(output) } }
        val baseApk = File(workingDir, "base.apk")
        runProcess(listOf(aapt2.absolutePath, "link", "-o", baseApk.absolutePath, "-I", androidJar.absolutePath, "--manifest", manifestFile.absolutePath, "-R", resZip.absolutePath, "-0", "arsc", "--auto-add-overlay"))

        val templateDex = File(workingDir, "classes.dex")
        context.assets.open("engine/template.dex").use { input -> FileOutputStream(templateDex).use { output -> input.copyTo(output) } }
        val mergedApk = File(workingDir, "merged.apk")
        val extras = mutableListOf(
            "classes.dex" to templateDex.readBytes(),
            "assets/index.html" to injected.toByteArray(),
            "assets/vendor/darkith-rt.js" to File(vendorDir, "darkith-rt.js").readBytes()
        )
        // Ship the handcoded native tools STORED under lib/<abi>/ so the child is itself a forge.
        // The template's extractNativeLibs=true is what makes Android extract them where they can run.
        File(nativeDir).listFiles().orEmpty().filter { it.isDirectory }.forEach { abi ->
            abi.listFiles().orEmpty().filter { it.isFile && it.name.endsWith(".so") }.forEach { so ->
                extras += "lib/${abi.name}/${so.name}" to so.readBytes()
            }
        }
        mergeIntoApk(baseApk, mergedApk, extras)

        val signedApk = File(workingDir, "${sanitize(appName)}.apk")
        val aligned = File(workingDir, "aligned.apk")
        NativeTools.zipalign(context, mergedApk, aligned)
        ApkSignerRunner(context).sign(aligned, signedApk)
        listOf(baseApk, mergedApk, resZip, androidJar, templateDex).forEach { it.delete() }
        return signedApk
    }

    private fun injectRuntimeExternal(html: String): String {
        if (html.contains("darkith-rt")) return html
        val tag = "<script src=\"vendor/darkith-rt.js\"></script>"
        return when {
            html.contains("<head>") -> html.replaceFirst("<head>", "<head>\n$tag")
            html.contains("<html") -> html.replaceFirst(Regex("<html[^>]*>"), "$0\n$tag")
            else -> "$tag\n$html"
        }
    }

    private fun mergeIntoApk(baseApk: File, outputApk: File, entries: List<Pair<String, ByteArray>>) {
        ZipFile(baseApk).use { zip ->
            ZipOutputStream(FileOutputStream(outputApk)).use { out ->
                val seen = mutableSetOf<String>()
                val en = zip.entries()
                while (en.hasMoreElements()) {
                    val entry = en.nextElement(); seen.add(entry.name)
                    val data = zip.getInputStream(entry).use { it.readBytes() }
                    // resources.arsc MUST stay STORED or Android 11+ rejects the APK (App not installed).
                    if (entry.name == "resources.arsc") {
                        val crc = java.util.zip.CRC32(); crc.update(data)
                        val ne = ZipEntry(entry.name)
                        ne.method = ZipEntry.STORED; ne.size = data.size.toLong()
                        ne.compressedSize = data.size.toLong(); ne.crc = crc.value
                        out.putNextEntry(ne); out.write(data); out.closeEntry()
                    } else {
                        out.putNextEntry(ZipEntry(entry.name)); out.write(data); out.closeEntry()
                    }
                }
                for ((name, data) in entries) {
                    if (seen.contains(name)) continue
                    // lib/*.so MUST be STORED (uncompressed) and aligned, or Android 11+ refuses
                    // the APK and the native tools cannot be exec'd from nativeLibraryDir.
                    if (name.startsWith("lib/") && name.endsWith(".so")) {
                        val crc = java.util.zip.CRC32(); crc.update(data)
                        val ne = ZipEntry(name)
                        ne.method = ZipEntry.STORED; ne.size = data.size.toLong()
                        ne.compressedSize = data.size.toLong(); ne.crc = crc.value
                        out.putNextEntry(ne); out.write(data); out.closeEntry()
                    } else {
                        val e = ZipEntry(name); e.method = ZipEntry.DEFLATED
                        out.putNextEntry(e); out.write(data); out.closeEntry()
                    }
                }
            }
        }
    }

    private fun sanitize(name: String): String = name.replace(Regex("[^a-zA-Z0-9_]"), "_")

    private fun runProcess(cmd: List<String>) {
        val pb = ProcessBuilder(cmd); pb.redirectErrorStream(true)
        val process = pb.start()
        val output = process.inputStream.bufferedReader().readText()
        val code = process.waitFor()
        if (code != 0) throw RuntimeException("Command failed ($code): ${cmd.joinToString(" ")}\n$output")
    }
}

