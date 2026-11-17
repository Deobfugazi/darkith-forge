package com.darkith.transliaison

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

/**
 * EntryPointRewriter — the mint.
 * Donor in. Receptacle out. Payload injected. Launcher spliced.
 * Signed by caller.
 */
class EntryPointRewriter(private val context: Context) {

    data class Outcome(val status: String, val reason: String, val apk: File?)

    companion object {
        private val PAYLOAD_CANDIDATES = listOf(
            "assets/index.html",
            "assets/www/index.html",
            "assets/public/index.html",
            "assets/web/index.html",
            "assets/html/index.html"
        )
    }

    fun rewrite(donor: File, output: File, payloadHtml: String,
                appName: String, pkgName: String): Outcome {
        val entries = mutableListOf<Triple<String, Int, ByteArray>>()
        ZipFile(donor).use { z ->
            val en = z.entries()
            while (en.hasMoreElements()) {
                val e = en.nextElement()
                entries.add(Triple(e.name, e.method, z.getInputStream(e).readBytes()))
            }
        }
        val mi = entries.indexOfFirst { it.first == "AndroidManifest.xml" }
        if (mi < 0) return Outcome("fail", "no AndroidManifest.xml", null)

        val origManifest = entries[mi].third
        val writer = AxmlWriter()

        val template = try {
            context.assets.open("receptacle/template-manifest.axml").use { it.readBytes() }
        } catch (_: Exception) { ByteArray(0) }

        var patchedManifest = origManifest
        var status = "asset-swap-only"
        var reason = "manifest splice not attempted"

        if (template.isNotEmpty()) {
            val at = writer.findApplicationInsertionPoint(origManifest)
            if (at < 0) {
                reason = "<application> not located in donor AXML"
            } else {
                patchedManifest = writer.spliceActivity(origManifest, at, template)
                status = "spliced"
                reason = "activity spliced at byte $at"
            }
        } else {
            reason = "template-manifest.axml empty"
        }

        val target = PAYLOAD_CANDIDATES.firstOrNull { c -> entries.any { it.first == c } }
                    ?: "assets/index.html"

        val receptorDex = try {
            context.assets.open("receptacle/receptacle.dex").use { it.readBytes() }
        } catch (_: Exception) { null }

        ZipOutputStream(FileOutputStream(output)).use { out ->
            for ((name, method, data) in entries) {
                val body = when (name) {
                    "AndroidManifest.xml" -> patchedManifest
                    target -> payloadHtml.toByteArray(Charsets.UTF_8)
                    else -> data
                }
                val e = ZipEntry(name); e.method = method
                out.putNextEntry(e); out.write(body); out.closeEntry()
            }
            if (receptorDex != null && entries.none { it.first == "classes2.dex" }) {
                val e = ZipEntry("classes2.dex"); e.method = ZipEntry.DEFLATED
                out.putNextEntry(e); out.write(receptorDex); out.closeEntry()
            }
            if (entries.none { it.first == "assets/index.html" }) {
                val e = ZipEntry("assets/index.html"); e.method = ZipEntry.DEFLATED
                out.putNextEntry(e); out.write(payloadHtml.toByteArray(Charsets.UTF_8)); out.closeEntry()
            }
        }
        return Outcome(status, "$reason; target=$target", output)
    }
}

