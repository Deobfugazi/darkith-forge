package com.darkith.transliaison

import android.content.Context
import android.os.Environment
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager

class DarkithBridge(private val context: Context) {

    @JavascriptInterface
    fun donorShip(donorPath: String, outputName: String, html: String, appName: String, pkgName: String): String {
        return try {
            val donor = File(donorPath)
            if (!donor.exists()) return "ERROR: donor not found: $donorPath"
            val downloads = File("/sdcard/Download")
            if (!downloads.exists()) downloads.mkdirs()
            val safe = outputName.replace(Regex("[^A-Za-z0-9._-]"), "_").let {
                if (it.endsWith(".apk")) it else "$it.apk"
            }
            val staged = File(downloads, "staged_$safe")
            val merged = DonorUiConcat().merge(donor, html)
            val outcome = EntryPointRewriter(context).rewrite(donor, staged, merged, appName, pkgName)
            val final = File(downloads, safe)
            ApkSignerRunner(context).sign(staged, final)
            try { staged.delete() } catch (_: Exception) {}
            try {
                val zf = java.util.zip.ZipFile(final)
                val names = zf.entries().asSequence().map { it.name }.toSet()
                zf.close()
                if (!names.contains("AndroidManifest.xml")) return "ERROR: signed APK missing AndroidManifest.xml"
                if (!names.contains("classes.dex") && !names.contains("classes2.dex")) return "ERROR: signed APK missing classes.dex"
                println("DARKITH_EP: status=${outcome.status} out=${final.absolutePath} verified=true")
            } catch (e: Exception) { return "ERROR: ${e.message}" }
            ApkInstaller(context).install(final)
            final.absolutePath
        } catch (e: Exception) {
            "ERROR: ${e.message}"
        }
    }





    private var webView: WebView? = null
    fun attachWebView(wv: WebView) { webView = wv }

    private val repoDir: File by lazy { File(context.filesDir, "darkith_repo").apply { mkdirs() } }
    private fun sanitize(s: String): String = s.replace(Regex("[^A-Za-z0-9._-]"), "_")

    @JavascriptInterface fun repoPut(key: String, value: String): Boolean = try { File(repoDir, sanitize(key) + ".dat").writeText(value); true } catch (e: Exception) { false }
    @JavascriptInterface fun repoGet(key: String): String? = try { val f = File(repoDir, sanitize(key) + ".dat"); if (f.exists()) f.readText() else null } catch (e: Exception) { null }
    @JavascriptInterface fun repoDrop(key: String): Boolean = try { File(repoDir, sanitize(key) + ".dat").delete() } catch (e: Exception) { false }
    @JavascriptInterface fun repoWipe(): Boolean = try { repoDir.deleteRecursively(); repoDir.mkdirs() } catch (e: Exception) { false }
    @JavascriptInterface fun repoKeys(): String = try { val a = JSONArray(); repoDir.listFiles()?.forEach { if (it.name.endsWith(".dat")) a.put(it.name.dropLast(4)) }; a.toString() } catch (e: Exception) { "[]" }

    @JavascriptInterface fun fileWrite(path: String, content: String): String = try { val f = File(path); f.parentFile?.mkdirs(); f.writeText(content); f.absolutePath } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun fileRead(path: String): String = try { val f = File(path); when { !f.exists() -> "ERROR: not found: $path"; !f.canRead() -> "ERROR: cannot read: $path"; else -> f.readText() } } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun fileSize(path: String): Long = try { File(path).length() } catch (e: Exception) { -1L }

    @JavascriptInterface fun forgeSourceVersion(): String = try {
        context.assets.open("src.manifest").bufferedReader().use { it.readText() }
    } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun forgeSourceList(): String = try {
        val zin = java.util.zip.ZipInputStream(context.assets.open("src.zip"))
        val arr = org.json.JSONArray()
        var e = zin.nextEntry
        while (e != null) {
            val o = org.json.JSONObject(); o.put("name", e.name); o.put("size", e.size); arr.put(o)
            e = zin.nextEntry
        }
        zin.close(); arr.toString()
    } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun forgeSourceExtract(destPath: String): String = try {
        val dest = File(destPath); if (!dest.exists()) dest.mkdirs()
        val zin = java.util.zip.ZipInputStream(context.assets.open("src.zip"))
        var count = 0; var e = zin.nextEntry
        while (e != null) {
            val out = File(dest, e.name)
            if (e.isDirectory) out.mkdirs()
            else { out.parentFile?.mkdirs(); java.io.FileOutputStream(out).use { zin.copyTo(it) }; count++ }
            zin.closeEntry(); e = zin.nextEntry
        }
        zin.close(); "OK extracted " + count + " files to " + dest.absolutePath
    } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun forgeSourceVerify(): String = try {
        val expected = context.assets.open("src.sha256").bufferedReader().use { it.readText().trim() }
        val md = java.security.MessageDigest.getInstance("SHA-256")
        val buf = ByteArray(8192); val zin = context.assets.open("src.zip")
        var n = zin.read(buf); while (n > 0) { md.update(buf, 0, n); n = zin.read(buf) }
        zin.close()
        val actual = md.digest().joinToString("") { "%02x".format(it) }
        if (actual == expected) "OK " + actual else "MISMATCH expected=" + expected
    } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface fun fileExists(path: String): String = try { File(path).exists().toString() } catch (e: Exception) { "false" }
    @JavascriptInterface fun fileDelete(path: String): String = try { val f = File(path); (if (f.isDirectory) f.deleteRecursively() else f.delete()).toString() } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun fileDirs(path: String): String = try { File(path).mkdirs().toString() } catch (e: Exception) { "ERROR: ${e.message}" }
    @JavascriptInterface fun fileList(path: String): String = try { val d = File(path); if (!d.exists() || !d.isDirectory) "[]" else { val a = JSONArray(); d.listFiles()?.sortedBy { it.name }?.forEach { f -> a.put(JSONObject().apply { put("name", f.name); put("dir", f.isDirectory); put("size", if (f.isFile) f.length() else 0L) }) }; a.toString() } } catch (e: Exception) { "[]" }
    @JavascriptInterface fun fileRoots(): String = try { val r = mutableListOf<String>(); r.add(Environment.getExternalStorageDirectory().absolutePath); context.getExternalFilesDirs(null).forEach { it?.let { f -> r.add(f.absolutePath) } }; r.distinct().joinToString("\u0001") } catch (e: Exception) { "" }

    @JavascriptInterface fun wireHttp(optionsJson: String): String {
        return try {
            val o = JSONObject(optionsJson)
            val url = URL(o.getString("url"))
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = o.optString("method", "GET")
            val t = o.optInt("timeout", 15000)
            conn.connectTimeout = t; conn.readTimeout = t
            conn.instanceFollowRedirects = true
            if (o.optBoolean("trustAllCerts", false) && conn is HttpsURLConnection) {
                val tm = object : X509TrustManager {
                    override fun checkClientTrusted(c: Array<java.security.cert.X509Certificate>?, a: String?) {}
                    override fun checkServerTrusted(c: Array<java.security.cert.X509Certificate>?, a: String?) {}
                    override fun getAcceptedIssuers(): Array<java.security.cert.X509Certificate> = arrayOf()
                }
                val ctx = SSLContext.getInstance("TLS"); ctx.init(null, arrayOf(tm), SecureRandom())
                conn.sslSocketFactory = ctx.socketFactory; conn.hostnameVerifier = HostnameVerifier { _, _ -> true }
            }
            o.optJSONObject("headers")?.let { h -> val it = h.keys(); while (it.hasNext()) { val k = it.next(); conn.setRequestProperty(k, h.getString(k)) } }
            val body = o.optString("body", "")
            if (body.isNotEmpty()) { conn.doOutput = true; conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) } }
            val status = conn.responseCode
            val stream = if (status in 200..299) conn.inputStream else conn.errorStream
            val respBody = stream?.bufferedReader()?.use { it.readText() } ?: ""
            val hdrs = JSONObject()
            conn.headerFields.forEach { (k, v) -> if (k != null && v != null && v.isNotEmpty()) hdrs.put(k, v.first()) }
            JSONObject().apply { put("ok", status in 200..299); put("status", status); put("headers", hdrs); put("body", respBody) }.toString()
        } catch (e: Exception) { JSONObject().apply { put("ok", false); put("error", e.message ?: "wire error") }.toString() }
    }

    @JavascriptInterface fun wireHttpAsync(optionsJson: String, cbId: String) {
        Thread {
            val result = wireHttp(optionsJson)
            val quoted = JSONObject.quote(result)
            val id = cbId.replace("\\", "\\\\").replace("'", "\\'")
            val js = "(function(){var c=(window._darkithCb||{})['$id'];if(typeof c==='function'){try{c(JSON.parse($quoted));}catch(e){c({ok:false,error:'callback parse'});}}})()"
            webView?.post { webView?.evaluateJavascript(js, null) }
        }.start()
    }

    @JavascriptInterface fun wireFetch(url: String, destPath: String): String = try {
        val u = URL(url); val conn = u.openConnection() as HttpURLConnection
        conn.connectTimeout = 15000; conn.readTimeout = 30000; conn.instanceFollowRedirects = true; conn.connect()
        val code = conn.responseCode
        if (code != 200) "ERROR: HTTP $code" else {
            val bytes = conn.inputStream.readBytes()
            if (bytes.size > 64) {
                val head = String(bytes, 0, 64, Charsets.UTF_8).lowercase()
                if (head.contains("<html") || head.contains("<!doctype")) "ERROR: HTML response"
                else { val f = File(destPath); f.parentFile?.mkdirs(); f.writeBytes(bytes); "OK ${f.absolutePath} (${bytes.size} bytes)" }
            } else { val f = File(destPath); f.parentFile?.mkdirs(); f.writeBytes(bytes); "OK ${f.absolutePath} (${bytes.size} bytes)" }
        }
    } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface fun bodyName(): String = "Darkith Forge"
    @JavascriptInterface fun bodyPackage(): String = context.packageName
    @JavascriptInterface fun bodyAvailable(): Boolean = true

    @JavascriptInterface fun forgeBuildShell(html: String, appName: String, pkgName: String): String {
        if (html.length > 5_000_000) return "ERROR: HTML too large (max 5MB)"
        if (!appName.matches(Regex("^[a-zA-Z0-9_ ]+$"))) return "ERROR: invalid app name"
        if (!pkgName.matches(Regex("^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$"))) return "ERROR: invalid package name"
        return try {
            val downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            val work = File(downloads, "build_${System.currentTimeMillis()}").apply { mkdirs() }
            val apk = BuildEngine(context).build(html, appName, pkgName, work)
            ApkInstaller(context).install(apk); apk.absolutePath
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    @JavascriptInterface fun forgeShip(dirPath: String, outputName: String, donorPath: String?): String = try {
        val apk = DonorBuilder(context).shipProject(dirPath, outputName, donorPath)
        ApkInstaller(context).install(apk); apk.absolutePath
    } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface fun forgeClone(html: String, outputName: String): String = try {
        val manifest = """{"entry":"index.html","files":[{"path":"index.html","content":""" + JSONObject.quote(html) + "}]}"
        val apk = DonorBuilder(context).buildFromManifest(manifest, outputName, DonorBuilder(context).scaffoldApkPath())
        ApkInstaller(context).install(apk); apk.absolutePath
    } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface fun forgeDonors(): String = try { val a = JSONArray(); DonorBuilder(context).listDonors().forEach { f -> a.put(JSONObject().apply { put("name", f.name); put("path", f.absolutePath); put("size", f.length()) }) }; a.toString() } catch (e: Exception) { "[]" }
    @JavascriptInterface fun forgeDonorDir(): String = DonorBuilder.DEFAULT_DONOR_DIR
    @JavascriptInterface fun forgeUi(): String = try { context.assets.open("darkith_ui.html").bufferedReader().use { it.readText() } } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface fun apkVerify(path: String): String = ShellBridge.apkVerify(path)
    @JavascriptInterface fun apkSignature(path: String): String = ShellBridge.apkSignature(path)
    @JavascriptInterface fun apkManifest(path: String): String = ShellBridge.apkManifest(path)
    @JavascriptInterface fun apkInfo(path: String): String = ShellBridge.apkInfo(path)
    @JavascriptInterface fun shellExec(cmd: String): String = ShellBridge.shellExec(cmd)

    @JavascriptInterface fun donorList(path: String): String = DonorBuilder(context).listEntries(path)
    @JavascriptInterface fun donorRead(apkPath: String, entryName: String): String = DonorBuilder(context).readEntry(apkPath, entryName)
    @JavascriptInterface fun donorWrite(apkPath: String, entryName: String, content: String): String = DonorBuilder(context).writeEntry(apkPath, entryName, content)
    @JavascriptInterface fun donorDelete(apkPath: String, entryName: String): String = DonorBuilder(context).deleteEntry(apkPath, entryName)

    @JavascriptInterface fun forgeShipV2(donorPath: String, outputName: String, html: String, appName: String, pkgName: String): String {
        return donorShip(donorPath, outputName, html, appName, pkgName)
    }

    @JavascriptInterface fun pkgExtract(archivePath: String, name: String): String =
        ShellBridge.pkgExtract(archivePath, name)
    @JavascriptInterface fun pkgHash(archivePath: String): String =
        ShellBridge.pkgHash(archivePath)
    @JavascriptInterface fun pkgInstall(name: String): String =
        ShellBridge.pkgInstallName(name)
    @JavascriptInterface fun pkgRemove(name: String): String =
        ShellBridge.pkgRemoveName(name)
    @JavascriptInterface fun pkgList(): String =
        ShellBridge.pkgList()
    @JavascriptInterface fun pkgRegistryDir(): String =
        ShellBridge.pkgRegistryDir()



    // ═══ DARKITH ABSORBED LAYERS ═══
    private val chainReader   by lazy { DarkithChainReader(context) }
    private val contentStore  by lazy { DarkithContentStore(context) }
    private val evmKit        by lazy { DarkithEVMKit(context) }
    private val runtimeHost   by lazy { DarkithRuntimeHost(context) }
    private val alpineGuest   by lazy { DarkithAlpineGuest(context) }
    private val solCompiler   by lazy { DarkithSolidityCompiler(context) }

    @JavascriptInterface fun graftStatus(): String {
        return """{"chainReader":"${chainReader.status()}","contentStore":"${contentStore.status()}","evmKit":"${evmKit.status()}","runtimeHost":"${runtimeHost.list()}","alpineGuest":"${alpineGuest.status()}","solCompiler":"${solCompiler.status()}"}"""
    }
    @JavascriptInterface fun graftChainStart(rpc: String): String = chainReader.start(rpc)
    @JavascriptInterface fun graftChainEndpoint(): String = chainReader.localEndpoint()
    @JavascriptInterface fun graftContentPin(path: String): String = contentStore.pin(path)
    @JavascriptInterface fun graftContentGateway(): String = contentStore.gateway()
    @JavascriptInterface fun graftEVMChains(): String = evmKit.supportedChains()
    @JavascriptInterface fun graftRuntimeRun(runtime: String, script: String): String = runtimeHost.run(runtime, script)
    @JavascriptInterface fun graftAlpineAdd(pkg: String): String = alpineGuest.apkAdd(pkg)
    @JavascriptInterface fun graftSolidityCompile(sol: String, outDir: String): String = solCompiler.compile(sol, outDir)

    @JavascriptInterface
    fun donorCopyEntry(srcApk: String, srcEntry: String, dstApk: String, dstEntry: String): String {
        try {
            val src = java.util.zip.ZipFile(srcApk)
            val srcE = src.getEntry(srcEntry)
            if (srcE == null) { src.close(); return "ERROR: src entry not found: " + srcEntry }
            val bytes = src.getInputStream(srcE).readBytes()
            src.close()
            val dst = File(dstApk)
            if (!dst.exists()) return "ERROR: dst apk not found: " + dstApk
            val tmp = File(dst.parentFile, dst.name + ".donorcopy.tmp")
            java.util.zip.ZipInputStream(java.io.FileInputStream(dst)).use { zin ->
                java.util.zip.ZipOutputStream(java.io.FileOutputStream(tmp)).use { zout ->
                    val buf = ByteArray(8192)
                    var wrote = false
                    while (true) {
                        val e = zin.nextEntry ?: break
                        if (e.name == dstEntry) {
                            zout.putNextEntry(java.util.zip.ZipEntry(dstEntry))
                            zout.write(bytes)
                            zout.closeEntry()
                            wrote = true
                        } else {
                            zout.putNextEntry(java.util.zip.ZipEntry(e.name))
                            var n = zin.read(buf)
                            while (n > 0) { zout.write(buf, 0, n); n = zin.read(buf) }
                            zout.closeEntry()
                        }
                        zin.closeEntry()
                    }
                    if (!wrote) {
                        zout.putNextEntry(java.util.zip.ZipEntry(dstEntry))
                        zout.write(bytes)
                        zout.closeEntry()
                    }
                }
            }
            if (!tmp.renameTo(dst)) { tmp.copyTo(dst, overwrite = true); tmp.delete() }
            return "OK " + srcEntry + " -> " + dstEntry + " (" + bytes.size + " B)"
        } catch (e: Exception) { return "ERROR: " + e.message }
    }

    // OMEGAGUARD_v1

    @JavascriptInterface
    fun donorDexClasses(apkPath: String): String {
        try {
            val zip = java.util.zip.ZipFile(apkPath)
            val out = StringBuilder()
            val seen = HashSet<String>()
            val en = zip.entries()
            while (en.hasMoreElements()) {
                val e = en.nextElement()
                if (!Regex("^classes\\d*\\.dex$").matches(e.name)) continue
                val bytes = zip.getInputStream(e).readBytes()
                for (cls in parseDexClasses(bytes)) if (seen.add(cls)) out.append(cls).append('\n')
            }
            zip.close()
            return out.toString()
        } catch (e: Exception) { return "ERROR: " + e.message }
    }

    private fun parseDexClasses(b: ByteArray): List<String> {
        val out = ArrayList<String>()
        try {
            if (b.size < 112) return out
            if (b[0].toInt() != 0x64 || b[1].toInt() != 0x65 ||
                b[2].toInt() != 0x78 || b[3].toInt() != 0x0A) return out
            val strSize = le32s(b, 0x38)
            val strOff  = le32s(b, 0x3C)
            if (strSize <= 0 || strSize > 1000000) return out
            if (strOff <= 0 || strOff + strSize * 4 > b.size) return out
            var i = 0
            while (i < strSize) {
                val so = strOff + i * 4
                if (so + 4 > b.size) break
                val off = le32s(b, so)
                if (off <= 0 || off >= b.size) { i++; continue }
                var p2 = off
                var shift = 0
                var len = 0
                while (p2 < b.size) {
                    val x = b[p2].toInt() and 0xFF; p2++
                    len = len or ((x and 0x7F) shl shift)
                    if ((x and 0x80) == 0) break
                    shift += 7
                    if (shift > 28) { len = -1; break }
                }
                if (len > 0 && len < 4096 && p2 + len <= b.size) {
                    val s2 = String(b, p2, len, Charsets.UTF_8)
                    if (s2.startsWith("L") && s2.endsWith(";")) out.add(s2)
                }
                i++
            }
        } catch (_: Throwable) {}
        return out
    }

    @JavascriptInterface
    fun donorArscIds(apkPath: String): String {
        try {
            val zip = java.util.zip.ZipFile(apkPath)
            val e = zip.getEntry("resources.arsc") ?: run { zip.close(); return "" }
            val b = zip.getInputStream(e).readBytes()
            zip.close()
            if (b.size < 12) return ""
            if (le16s(b, 0) != 0x0002) return ""
            var p = le16s(b, 2)
            val tblSize = le32s(b, 4)
            val out = StringBuilder()
            val seen = HashSet<Int>()
            while (p + 8 <= b.size && p < tblSize) {
                val ct = le16s(b, p)
                val cs = le32s(b, p + 4)
                if (cs <= 0 || p + cs > b.size) break
                if (ct == 0x0200) {
                    val pkgId = le32s(b, p + 8)
                    var q = p + le16s(b, p + 2)
                    val pkgEnd = p + cs
                    while (q + 8 <= pkgEnd) {
                        val t = le16s(b, q)
                        val sz = le32s(b, q + 4)
                        if (sz <= 0 || q + sz > b.size) break
                        if (t == 0x0202) {
                            val typeId = le32s(b, q + 8) and 0xFF
                            val rid = (pkgId shl 24) or (typeId shl 16)
                            if (seen.add(rid)) out.append(String.format("%08x", rid)).append('\n')
                        }
                        q += sz
                    }
                }
                p += cs
            }
            return out.toString()
        } catch (e: Exception) { return "ERROR: " + e.message }
    }

    @JavascriptInterface
    fun donorManifestComponents(apkPath: String): String {
        try {
            val zip = java.util.zip.ZipFile(apkPath)
            val e = zip.getEntry("AndroidManifest.xml") ?: run { zip.close(); return "" }
            val b = zip.getInputStream(e).readBytes()
            zip.close()
            var p = 8
            while (p + 8 <= b.size) {
                val ct = le16s(b, p)
                val cs = le32s(b, p + 4)
                if (cs <= 0 || p + cs > b.size) break
                if (ct == 0x0001) {
                    val cnt = le32s(b, p + 8)
                    val flags = le32s(b, p + 16)
                    val strStart = le32s(b, p + 20)
                    val isUtf8 = (flags and (1 shl 8)) != 0
                    if (cnt in 1..50000) {
                        val out = StringBuilder()
                        val hdr = le16s(b, p + 2)
                        var i = 0
                        while (i < cnt) {
                            val offPos = p + hdr + i * 4
                            if (offPos + 4 > b.size) break
                            val off = le32s(b, offPos)
                            val sp = p + strStart + off
                            if (sp > 0 && sp < b.size) {
                                val s2 = readPoolString(b, sp, isUtf8)
                                if (s2 != null && s2.contains('.') && s2.length in 3..150) {
                                    out.append(s2).append('\n')
                                }
                            }
                            i++
                        }
                        return out.toString()
                    }
                }
                p += cs
            }
            return ""
        } catch (e: Exception) { return "ERROR: " + e.message }
    }

    private fun readPoolString(b: ByteArray, off: Int, utf8: Boolean): String? {
        try {
            var p = off
            if (utf8) {
                if (p + 2 > b.size) return null
                p += 2
                if (p >= b.size) return null
                var len = b[p].toInt() and 0xFF; p++
                if ((len and 0x80) != 0) {
                    if (p >= b.size) return null
                    len = ((b[p].toInt() and 0xFF) shl 8) or (len and 0x7F); p++
                }
                if (len <= 0 || len > 4096 || p + len > b.size) return null
                return String(b, p, len, Charsets.UTF_8)
            } else {
                if (p + 2 > b.size) return null
                var len = le16s(b, p); p += 2
                if ((len and 0x8000) != 0) {
                    if (p + 2 > b.size) return null
                    len = ((le16s(b, p) and 0xFFFF) shl 16) or (len and 0x7FFF)
                    p += 2
                }
                if (len <= 0 || len > 4096 || p + len * 2 > b.size) return null
                val sb = StringBuilder(len)
                for (i in 0 until len) {
                    val c = le16s(b, p + i * 2)
                    if (c == 0) break
                    sb.append(c.toChar())
                }
                return sb.toString()
            }
        } catch (_: Throwable) { return null }
    }

    @JavascriptInterface
    fun donorSoList(apkPath: String): String {
        try {
            val zip = java.util.zip.ZipFile(apkPath)
            val out = StringBuilder()
            val en = zip.entries()
            while (en.hasMoreElements()) {
                val e = en.nextElement()
                if (!e.name.startsWith("lib/") || !e.name.endsWith(".so")) continue
                val b = zip.getInputStream(e).readBytes()
                val aligned = elfAlign16k(b)
                out.append(e.name).append('|').append(if (aligned) "aligned" else "unaligned").append('\n')
            }
            zip.close()
            return out.toString()
        } catch (e: Exception) { return "ERROR: " + e.message }
    }

    private fun elfAlign16k(so: ByteArray): Boolean {
        try {
            if (so.size < 64) return true
            if (so[0].toInt() != 0x7F || so[1].toInt() != 0x45 ||
                so[2].toInt() != 0x4C || so[3].toInt() != 0x46) return true
            if (so[4].toInt() != 2) return true
            val phOff = le32s(so, 0x20)
            val phEnt = le16s(so, 0x36)
            val phNum = le16s(so, 0x38)
            if (phOff <= 0 || phNum <= 0) return true
            var i = 0
            while (i < phNum) {
                val ph = phOff + i * phEnt
                if (ph + 56 > so.size) break
                if (le32s(so, ph) == 1) {
                    val aLo = le32s(so, ph + 48).toLong() and 0xFFFFFFFFL
                    val aHi = le32s(so, ph + 52).toLong() and 0xFFFFFFFFL
                    val al = (aHi shl 32) or aLo
                    if (al != 0L && al < 0x4000L) return false
                }
                i++
            }
            return true
        } catch (_: Throwable) { return false }
    }

    private fun le16s(b: ByteArray, i: Int): Int {
        if (i + 1 >= b.size) return 0
        return (b[i].toInt() and 0xFF) or ((b[i+1].toInt() and 0xFF) shl 8)
    }
    private fun le32s(b: ByteArray, i: Int): Int {
        if (i + 3 >= b.size) return 0
        return (b[i].toInt() and 0xFF) or
               ((b[i+1].toInt() and 0xFF) shl 8) or
               ((b[i+2].toInt() and 0xFF) shl 16) or
               ((b[i+3].toInt() and 0xFF) shl 24)
    }

    // ── TASK A · Termux-free runtime methods · 2026-10-10 ──
    @JavascriptInterface
    fun deviceZip(outputPath: String, joinedInputs: String): String =
        com.darkith.transliaison.KotlinZip.zip(outputPath, joinedInputs)

    @JavascriptInterface
    fun deviceUnzipList(archivePath: String): String =
        com.darkith.transliaison.KotlinUnzip.list(archivePath)

    @JavascriptInterface
    fun deviceUnzipExtract(archivePath: String, destDir: String): String =
        com.darkith.transliaison.KotlinUnzip.extract(archivePath, destDir)

    @JavascriptInterface
    fun deviceUnzipOne(archivePath: String, entryName: String, destDir: String): String =
        com.darkith.transliaison.KotlinUnzip.extractOne(archivePath, entryName, destDir)

    @JavascriptInterface
    fun donorListAll(): String = try {
        val dir = File(com.darkith.transliaison.DonorBuilder.DEFAULT_DONOR_DIR)
        val a = JSONArray()
        if (dir.exists() && dir.isDirectory) {
            dir.listFiles()
                ?.filter { it.isFile && it.name.endsWith(".apk", ignoreCase = true) }
                ?.sortedBy { it.name }
                ?.forEach { f ->
                    a.put(JSONObject().apply {
                        put("name", f.name)
                        put("path", f.absolutePath)
                        put("size", f.length())
                    })
                }
        }
        a.toString()
    } catch (e: Exception) { "[]" }
    @JavascriptInterface
    fun appendFile(path: String, content: String): String = try {
        val f = File(path)
        f.parentFile?.mkdirs()
        f.appendText(content)
        f.absolutePath
    } catch (e: Exception) { "ERROR: ${e.message}" }

    @JavascriptInterface
    fun getAuditMarkdown(): String = try {
        val f = File("/sdcard/Darkith/ledger/AUDIT.md")
        if (f.exists()) f.readText() else ""
    } catch (e: Exception) { "" }

    @JavascriptInterface
    fun laborTodaySeconds(): Long = LaborClock.todaySeconds()

    @JavascriptInterface
    fun laborCumulativeHours(): String = "%.4f".format(LaborClock.cumulativeHours())

    @JavascriptInterface
    fun emitProgressEvent(cls: String, detailsJson: String) {
        ProgressLedger.onEvent(cls, detailsJson)
    }


    @JavascriptInterface
    fun executeAbsolutionVM(donorPath: String, payloadDexPath: String): String {
        return AegisVM.executeAbsolution(context, donorPath, payloadDexPath, 0.0)
    }

    @JavascriptInterface
    fun installApkNative(apkPath: String): String {
        return try {
            val file = File(apkPath)
            if (!file.exists()) return "ERROR: APK not found at $apkPath"
            // Raw framework install via PackageInstaller (androidx FileProvider is not in android.jar).
            ApkInstaller(context).install(file)
        } catch (e: Exception) { "ERROR: ${e.message}" }
    }

    @JavascriptInterface
    fun aegisSplitFile(filePath: String, linesStr: String, prefix: String): String {
        return try {
            val inputFile = File(filePath)
            if (!inputFile.exists()) return "ERROR: File not found at $filePath"

            val outDir = File("/sdcard/Darkith/split_${System.currentTimeMillis()}")
            outDir.mkdirs()

            val splitCmd = arrayOf("sh", "-c", "split -l $linesStr -d --additional-suffix=.txt \"$filePath\" \"$outDir/$prefix\"_")
            val p = Runtime.getRuntime().exec(splitCmd)
            p.waitFor()

            val manifestPath = File(outDir, "manifest.json")
            val hashCmd = arrayOf("sh", "-c", "sha256sum \"$filePath\" | awk '{print \$1}'")
            val hp = Runtime.getRuntime().exec(hashCmd)
            val reader = java.io.BufferedReader(java.io.InputStreamReader(hp.inputStream))
            val originalHash = reader.readLine() ?: "unknown"

            val manifestJson = StringBuilder()
            manifestJson.append("{\n  \"originalFile\": \"${inputFile.name}\",\n")
            manifestJson.append("  \"sha256\": \"$originalHash\",\n")
            manifestJson.append("  \"chunks\": [\n")

            val chunks = outDir.listFiles { _, name -> name.endsWith(".txt") }
            if (chunks != null) {
                java.util.Arrays.sort(chunks)
                for (i in chunks.indices) {
                    manifestJson.append("    {\"name\": \"${chunks[i].name}\", \"size\": ${chunks[i].length()}}")
                    if (i < chunks.size - 1) manifestJson.append(",")
                    manifestJson.append("\n")
                }
            }
            manifestJson.append("  ]\n}")

            manifestPath.writeText(manifestJson.toString())

            val zipPath = "/sdcard/Download/${inputFile.name.replace(".txt", "")}_chunks.zip"
            val zipCmd = arrayOf("sh", "-c", "cd \"$outDir\" && zip -r \"$zipPath\" .")
            val zp = Runtime.getRuntime().exec(zipCmd)
            zp.waitFor()

            "Success! Zipped to: $zipPath\n${chunks?.size ?: 0} chunks created."
        } catch (e: Exception) {
            "ERROR: ${e.message}"
        }
    }


    @android.webkit.JavascriptInterface
    fun forgeChimera(donorsJson: String, launcherHtml: String, appName: String, pkgName: String): String {
        return ChimeraBuilder(context).forgeChimera(donorsJson, launcherHtml, appName, pkgName)
    }
}
