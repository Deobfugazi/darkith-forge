package com.darkith.transliaison

import java.io.ByteArrayOutputStream
import java.io.File
import java.util.zip.ZipFile

class DonorUiConcat {

    private val uiExt = setOf(
        "html","htm","css","js","mjs","json","svg",
        "png","jpg","jpeg","gif","webp","ico","bmp",
        "woff","woff2","ttf","otf","eot","wasm"
    )

    fun merge(donor: File, payloadHtml: String): String {
        if (!donor.exists()) return payloadHtml
        val ui = linkedMapOf<String, ByteArray>()
        try {
            ZipFile(donor).use { z ->
                val en = z.entries()
                while (en.hasMoreElements()) {
                    val e = en.nextElement()
                    if (e.isDirectory) continue
                    val n = e.name
                    if (n.startsWith("META-INF/")) continue
                    val ext = n.substringAfterLast('.', "").lowercase()
                    if (ext !in uiExt) continue
                    ui[n] = z.getInputStream(e).readBytes()
                }
            }
        } catch (_: Throwable) { return payloadHtml }
        if (ui.isEmpty()) return payloadHtml

        val donorHtml = ui.keys.firstOrNull { it == "assets/index.html" }
            ?: ui.keys.firstOrNull { it == "assets/www/index.html" }
            ?: ui.keys.firstOrNull { it == "assets/public/index.html" }
            ?: ui.keys.firstOrNull { it == "assets/web/index.html" }
            ?: ui.keys.firstOrNull { it == "assets/html/index.html" }
            ?: ui.keys.firstOrNull { it.endsWith(".html") && it.startsWith("assets/") }
            ?: ui.keys.firstOrNull { it.endsWith(".html") }

        val cssBlock = ByteArrayOutputStream()
        val jsBlock  = ByteArrayOutputStream()
        for ((name, bytes) in ui) {
            val ext = name.substringAfterLast('.', "").lowercase()
            when (ext) {
                "css" -> {
                    cssBlock.write("\n/* donor:$name */\n".toByteArray())
                    cssBlock.write(bytes)
                    cssBlock.write("\n".toByteArray())
                }
                "js", "mjs" -> {
                    jsBlock.write("\n/* donor:$name */\n".toByteArray())
                    jsBlock.write(String(bytes, Charsets.UTF_8).replace("</script", "<\\/script").toByteArray())
                    jsBlock.write("\n".toByteArray())
                }
            }
        }

        val donorBody = donorHtml?.let { name -> ui[name]?.let { bodyOf(String(it, Charsets.UTF_8)) } } ?: ""
        val projectBody = bodyOf(payloadHtml)

        val sb = StringBuilder()
        sb.append("<!DOCTYPE html>\n<html lang=\"en\"><head>\n")
        sb.append("<meta charset=\"utf-8\">\n")
        sb.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n")
        if (cssBlock.size() > 0) sb.append("<style>\n").append(cssBlock.toString("UTF-8")).append("\n</style>\n")
        sb.append("</head><body>\n")
        sb.append("<!-- donor-ui:start -->\n")
        sb.append(donorBody).append("\n")
        sb.append("<!-- donor-ui:end -->\n")
        sb.append("<!-- project-payload:start -->\n")
        sb.append(projectBody).append("\n")
        sb.append("<!-- project-payload:end -->\n")
        if (jsBlock.size() > 0) sb.append("<script>\n").append(jsBlock.toString("UTF-8")).append("\n</script>\n")
        sb.append("\n</body></html>\n")

        val merged = sb.toString()
        val lo = merged.lowercase()
        val so = Regex("<script\\b").findAll(lo).count()
        val sc = Regex("</script>").findAll(lo).count()
        val to = Regex("<style\\b").findAll(lo).count()
        val tc = Regex("</style>").findAll(lo).count()
        if (so != sc || to != tc || !lo.contains("<html") || !lo.contains("</html>")) return payloadHtml
        return merged
    }

    private fun bodyOf(raw: String): String {
        val lo = raw.lowercase()
        val b = lo.indexOf("<body")
        val e = lo.indexOf("</body>")
        if (b >= 0 && e > b) {
            val gt = raw.indexOf('>', b)
            if (gt > 0) return raw.substring(gt + 1, e)
        }
        return raw
    }
}
