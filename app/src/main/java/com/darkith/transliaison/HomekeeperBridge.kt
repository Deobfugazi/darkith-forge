package com.darkith.transliaison

import android.content.ClipData
import com.darkith.transliaison.core.NativeForgeBuilder
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class HomekeeperBridge(private val host: HomekeeperActivity) {
    companion object {
        const val MAX_TEXT: Long = 3L * 1024L * 1024L
        const val VERSION = "hk-bridge-52"
        private const val HIST_MAX = 200
        private val shellCwd = java.util.concurrent.atomic.AtomicReference(
            Environment.getExternalStorageDirectory().absolutePath)
        private val shellEnvExtra = java.util.concurrent.ConcurrentHashMap<String, String>()
        private val shellHist = java.util.Collections.synchronizedList(ArrayList<String>())
    }

    private fun norm(p: String?): String {
        var s = (p ?: "").trim()
        if (s.startsWith("aegis://fs")) s = "/sdcard/" + s.removePrefix("aegis://fs").trimStart('/')
        if (s.startsWith("file://")) s = Uri.decode(s.removePrefix("file://"))
        if (s.isEmpty()) s = "/sdcard/"
        if (!s.startsWith("/")) s = "/sdcard/" + s
        return s
    }
    private fun err(e: Throwable): String = "ERROR: " + (e.message ?: e.javaClass.simpleName)

    @JavascriptInterface fun version(): String = VERSION

    /** The installed package's real version, read from the APK itself — never guessed. */
    @JavascriptInterface fun apkVersion(): String = try {
        val pi = host.packageManager.getPackageInfo(host.packageName, 0)
        val code = if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else pi.versionCode.toLong()
        "bridge=$VERSION pkg=${pi.versionName} ($code)"
    } catch (e: Exception) { "bridge=$VERSION pkg=UNKNOWN (${e.message})" }
    @JavascriptInterface fun storageGranted(): Boolean = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) Environment.isExternalStorageManager() else true
    @JavascriptInterface fun requestStorage(): String { host.runOnUiThread { host.askAllFiles() }; return "OK" }

    @JavascriptInterface fun fileList(path: String?): String {
        return try {
            val d = File(norm(path))
            if (!d.exists()) "ERROR: not found" else if (!d.isDirectory) "ERROR: not a folder" else {
                val arr = JSONArray()
                d.listFiles()?.sortedWith(compareBy({ !it.isDirectory }, { it.name.lowercase() }))?.forEach { f ->
                    arr.put(JSONObject().apply { put("name", f.name); put("type", if (f.isDirectory) "dir" else "file"); put("bytes", if (f.isDirectory) 0L else f.length()); put("mtime", f.lastModified()) })
                }
                arr.toString()
            }
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface fun fileRead(path: String?): String {
        return try {
            val f = File(norm(path))
            if (!f.exists()) return "ERROR: not found"
            if (f.isDirectory) return "ERROR: is a folder"
            if (f.length() > MAX_TEXT) return "ERROR: too large"
            val bytes = f.readBytes()
            if (bytes.size >= 4) {
                val b0 = bytes[0].toInt() and 0xFF; val b1 = bytes[1].toInt() and 0xFF; val b2 = bytes[2].toInt() and 0xFF
                if ((b0 == 0x50 && b1 == 0x4B) || (b0 == 0x64 && b1 == 0x65 && b2 == 0x78) || (b0 == 0x30 && b1 == 0x82)) return "ERROR: BINARY_REFUSAL"
            }
            String(bytes, Charsets.UTF_8)
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface fun fileWrite(path: String?, content: String?): String {
        return try {
            val f = File(norm(path))
            if (f.isDirectory) "ERROR: is a folder" else { f.parentFile?.mkdirs(); f.writeText(content ?: "", Charsets.UTF_8); "OK" }
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface fun fileDirs(path: String?): String = try { val d = File(norm(path)); if (d.isDirectory || d.mkdirs()) "OK" else "ERROR: mkdir failed" } catch (e: Throwable) { err(e) }
    /** Same contract as DarkithBridge.fileRoots: U+0001-joined absolute roots, SD card first (SPI-8). */
    @JavascriptInterface fun fileRoots(): String = try {
        val r = mutableListOf<String>()
        r.add(Environment.getExternalStorageDirectory().absolutePath)
        host.getExternalFilesDirs(null).forEach { it?.let { f -> r.add(f.absolutePath) } }
        r.distinct().joinToString("\u0001")
    } catch (e: Throwable) { "" }
    @JavascriptInterface fun fileMove(src: String?, dst: String?): String = try { val s = File(norm(src)); val d = File(norm(dst)); if (s.renameTo(d)) "OK" else "ERROR: move failed" } catch (e: Throwable) { err(e) }
    @JavascriptInterface fun fileCopy(src: String?, dst: String?): String = try { val s = File(norm(src)); val d = File(norm(dst)); s.copyTo(d, overwrite = true); "OK" } catch (e: Throwable) { err(e) }
    @JavascriptInterface fun fileDelete(path: String?): String = try { val f = File(norm(path)); if (f.deleteRecursively()) "OK" else "ERROR: delete failed" } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun fileStat(path: String?): String = try {
        val f = File(norm(path))
        if (!f.exists()) "ERROR: not found" else JSONObject().apply {
            put("name", f.name); put("path", f.path); put("type", if (f.isDirectory) "dir" else "file"); put("bytes", if (f.isDirectory) 0L else f.length()); put("mtime", f.lastModified())
        }.toString()
    } catch (e: Throwable) { err(e) }

    // ---- persistent shell session: one session, one surface (omega principle) ----
    private fun startShell(cmd: String): Process {
        val nativeDir = java.io.File(host.applicationInfo.nativeLibraryDir)
        val bash = java.io.File(nativeDir, "libbash.so")
        val execPath = if (bash.exists() && bash.canExecute()) bash.absolutePath else "/system/bin/sh"
        val cwd = java.io.File(shellCwd.get())
        val pb = ProcessBuilder(execPath, "-c", cmd)
        val env = pb.environment()
        env["PATH"] = nativeDir.absolutePath + ":/system/bin:/system/xbin"
        env["LD_LIBRARY_PATH"] = nativeDir.absolutePath
        env["HOME"] = host.filesDir.absolutePath
        env["TMPDIR"] = host.cacheDir.absolutePath
        env["PWD"] = shellCwd.get()
        shellEnvExtra.forEach { (k, v) -> env[k] = v }
        if (cwd.isDirectory) pb.directory(cwd)
        pb.redirectErrorStream(true)
        return pb.start()
    }

    private fun recordHist(cmd: String) {
        synchronized(shellHist) {
            shellHist.add(cmd)
            while (shellHist.size > HIST_MAX) shellHist.removeAt(0)
        }
    }

    @JavascriptInterface
    fun shell(cmd: String?): String {
        return try {
            val c = (cmd ?: "").trim()
            if (c.isNotEmpty()) recordHist(c)
            val out = startShell(c).inputStream.bufferedReader().readText()
            if (out.isEmpty()) "(no output)" else out
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface
    fun shellExec(cmd: String?): String {
        return try {
            val c = (cmd ?: "").trim()
            if (c.isNotEmpty()) recordHist(c)
            val p = startShell(c)
            val out = p.inputStream.bufferedReader().readText()
            val done = p.waitFor(30, java.util.concurrent.TimeUnit.SECONDS)
            if (!done) { p.destroyForcibly(); "ERROR: timeout\n$out" } else "exit=${p.exitValue()}\n$out"
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface
    fun shellSetCwd(path: String?): String {
        return try {
            val d = java.io.File(norm(path))
            if (!d.isDirectory) "ERROR: not a directory: ${d.path}"
            else { shellCwd.set(d.absolutePath); "OK cwd=${d.absolutePath}" }
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface
    fun shellSetEnv(name: String?, value: String?): String {
        return try {
            val k = (name ?: "").trim()
            if (!k.matches(Regex("[A-Za-z_][A-Za-z0-9_]*"))) "ERROR: invalid env name: '$k'"
            else {
                val v = value ?: ""
                if (v.isEmpty()) shellEnvExtra.remove(k) else shellEnvExtra[k] = v
                "OK $k=${shellEnvExtra[k] ?: "(unset)"}"
            }
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface
    fun shellEnv(): String {
        return try {
            val e = JSONObject()
            e.put("PATH", host.applicationInfo.nativeLibraryDir + ":/system/bin:/system/xbin")
            e.put("HOME", host.filesDir.absolutePath)
            e.put("TMPDIR", host.cacheDir.absolutePath)
            e.put("PWD", shellCwd.get())
            shellEnvExtra.forEach { (k, v) -> e.put(k, v) }
            JSONObject().apply { put("cwd", shellCwd.get()); put("env", e) }.toString()
        } catch (e: Throwable) { err(e) }
    }

    @JavascriptInterface
    fun shellHistory(): String {
        return try {
            val arr = JSONArray()
            synchronized(shellHist) { shellHist.forEach { arr.put(it) } }
            arr.toString()
        } catch (e: Throwable) { err(e) }
    }


    // ---- hk558 launcher bridge: list / icon / launch other apps ----
    @JavascriptInterface
    fun getInstalledApps(): String {
        return try {
            val pm = host.packageManager
            val q = android.content.Intent(android.content.Intent.ACTION_MAIN)
            q.addCategory(android.content.Intent.CATEGORY_LAUNCHER)
            val seen = HashSet<String>()
            val arr = org.json.JSONArray()
            for (ri in pm.queryIntentActivities(q, 0)) {
                val pkg = ri.activityInfo.packageName
                if (pkg == host.packageName || !seen.add(pkg)) continue
                val o = org.json.JSONObject()
                o.put("name", ri.loadLabel(pm).toString())
                o.put("pkg", pkg)
                arr.put(o)
            }
            arr.toString()
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun getAppIcon(pkg: String): String {
        return try {
            val d = host.packageManager.getApplicationIcon(pkg)
            val sz = 96
            val bmp = android.graphics.Bitmap.createBitmap(sz, sz, android.graphics.Bitmap.Config.ARGB_8888)
            val c = android.graphics.Canvas(bmp)
            d.setBounds(0, 0, sz, sz)
            d.draw(c)
            val bos = java.io.ByteArrayOutputStream()
            bmp.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, bos)
            "data:image/png;base64," + android.util.Base64.encodeToString(bos.toByteArray(), android.util.Base64.NO_WRAP)
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun launchApp(pkg: String): String {
        return try {
            val i = host.packageManager.getLaunchIntentForPackage(pkg)
            if (i == null) {
                "ERROR: no launch intent for " + pkg
            } else {
                i.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
                host.runOnUiThread { host.startActivity(i) }
                "OK"
            }
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    // ---- hk558 kit bridge ----
    @JavascriptInterface
    fun memInfo(): String {
        return try {
            val am = host.getSystemService(android.content.Context.ACTIVITY_SERVICE) as android.app.ActivityManager
            val mi = android.app.ActivityManager.MemoryInfo()
            am.getMemoryInfo(mi)
            val pss = am.getProcessMemoryInfo(intArrayOf(android.os.Process.myPid()))[0].totalPss
            "{\"total\":" + mi.totalMem + ",\"avail\":" + mi.availMem + ",\"threshold\":" + mi.threshold + ",\"low\":" + mi.lowMemory + ",\"pssKb\":" + pss + "}"
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun zipPaths(pathsJson: String, dest: String): String {
        val out = java.io.File(dest)
        return try {
            if (out.exists()) return "ERROR: destination already exists"
            val arr = org.json.JSONArray(pathsJson)
            var n = 0
            val outC = out.canonicalPath
            java.util.zip.ZipOutputStream(java.io.BufferedOutputStream(java.io.FileOutputStream(out))).use { zos ->
                fun add(f: java.io.File, name: String) {
                    if (f.canonicalPath == outC) return
                    if (f.isDirectory) {
                        val kids = f.listFiles()
                        if (kids == null || kids.isEmpty()) {
                            zos.putNextEntry(java.util.zip.ZipEntry(name + "/")); zos.closeEntry()
                        } else for (k in kids) add(k, name + "/" + k.name)
                    } else {
                        zos.putNextEntry(java.util.zip.ZipEntry(name))
                        f.inputStream().use { it.copyTo(zos) }
                        zos.closeEntry(); n++
                    }
                }
                for (i in 0 until arr.length()) { val f = java.io.File(arr.getString(i)); add(f, f.name) }
            }
            "Created " + out.name + " (" + n + " files)"
        } catch (e: Exception) { out.delete(); "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun unzipTo(src: String, dest: String): String {
        return try {
            val root = java.io.File(dest); root.mkdirs()
            val rootP = root.canonicalPath
            val rootS = rootP + java.io.File.separator
            var n = 0
            java.util.zip.ZipInputStream(java.io.BufferedInputStream(java.io.FileInputStream(src))).use { zis ->
                var e = zis.nextEntry
                while (e != null) {
                    val t = java.io.File(root, e.name)
                    val c = t.canonicalPath
                    if (c != rootP && !c.startsWith(rootS)) throw SecurityException("blocked unsafe path in zip: " + e.name)
                    if (e.isDirectory) t.mkdirs() else {
                        t.parentFile?.mkdirs()
                        java.io.FileOutputStream(t).use { zis.copyTo(it) }
                        n++
                    }
                    zis.closeEntry()
                    e = zis.nextEntry
                }
            }
            "Extracted " + n + " files into " + dest
        } catch (ex: Exception) { "ERROR: " + (ex.message ?: ex.javaClass.simpleName) }
    }

    // No content-URI provider: androidx FileProvider is not in android.jar and the raw chain
    // ships no res/xml provider paths. Callers degrade to a clear "needs FileProvider" message.
    private fun hkUri(p: String): android.net.Uri? = null

    @JavascriptInterface
    fun openWith(path: String, mime: String, pkg: String): String {
        return try {
            val uri = hkUri(path) ?: return "ERROR: open-with needs a FileProvider; not in this raw-chain build"
            val i = android.content.Intent(android.content.Intent.ACTION_VIEW)
            i.setDataAndType(uri, if (mime.isEmpty()) "*/*" else mime)
            i.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            if (pkg.isNotEmpty()) i.setPackage(pkg)
            host.runOnUiThread { try { host.startActivity(i) } catch (ex: Exception) { android.util.Log.w("Darkith", "open-with launch failed", ex) } }
            "OK"
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun shareFiles(pathsJson: String): String {
        return try {
            val arr = org.json.JSONArray(pathsJson)
            val uris = ArrayList<android.net.Uri>()
            for (k in 0 until arr.length()) hkUri(arr.getString(k))?.let { uris.add(it) }
            if (uris.isEmpty()) return "ERROR: sharing needs a FileProvider; not in this raw-chain build"
            val i = android.content.Intent(if (uris.size == 1) android.content.Intent.ACTION_SEND else android.content.Intent.ACTION_SEND_MULTIPLE)
            if (uris.size == 1) i.putExtra(android.content.Intent.EXTRA_STREAM, uris[0])
            else i.putParcelableArrayListExtra(android.content.Intent.EXTRA_STREAM, uris)
            i.type = "*/*"
            val cd = android.content.ClipData.newRawUri("files", uris[0])
            for (u in uris.drop(1)) cd.addItem(android.content.ClipData.Item(u))
            i.clipData = cd
            i.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            val ch = android.content.Intent.createChooser(i, "Share")
            ch.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            host.runOnUiThread { try { host.startActivity(ch) } catch (ex: Exception) { android.util.Log.w("Darkith", "share launch failed", ex) } }
            "OK"
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface
    fun openFolderIn(pkg: String, path: String): String {
        return try {
            val li = host.packageManager.getLaunchIntentForPackage(pkg) ?: return "ERROR: app not installed: " + pkg
            li.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            host.runOnUiThread {
                try {
                    val cm = host.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                    cm.setPrimaryClip(android.content.ClipData.newPlainText("path", path))
                    host.startActivity(li)
                } catch (ex: Exception) { android.util.Log.w("Darkith", "open-folder launch failed", ex) }
            }
            "OK"
        } catch (e: Exception) { "ERROR: " + (e.message ?: e.javaClass.simpleName) }
    }

    @JavascriptInterface fun installApkNative(path: String?): String {
        return try { if (path.isNullOrBlank()) "ERROR: empty path" else ApkInstaller(host).install(java.io.File(path)) } catch (e: Throwable) { "ERROR: installApkNative: ${e.message}" }
    }

    // ---- Omega: HTML -> Compose translator, Healer, Substrate Ingestor (wire_final.sh) ----
    private fun omegaEsc(s: String): String = s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", " ")

    private fun omegaTaskbin(): java.io.File {
        val d = java.io.File(host.filesDir, ".taskbin")
        d.mkdirs()
        return d
    }

    /** mu: append one JSON line to .taskbin. Returns false if the write failed (callers must surface that). */
    private fun omegaRecord(kind: String, detail: org.json.JSONObject): Boolean {
        return try {
            val o = org.json.JSONObject()
            o.put("ts", System.currentTimeMillis())
            o.put("kind", kind)
            o.put("detail", detail)
            java.io.File(omegaTaskbin(), "taskbin.jsonl").appendText(o.toString() + "\n", Charsets.UTF_8)
            true
        } catch (e: Throwable) { false }
    }

    private fun omegaSanitizePkg(p: String?): String {
        val kw = setOf("as", "break", "class", "continue", "do", "else", "false", "for", "fun", "if", "in", "interface", "is", "null", "object", "package", "return", "super", "this", "throw", "true", "try", "typealias", "typeof", "val", "var", "when", "while")
        val segs = (p ?: "").lowercase().split('.').filter { it.isNotEmpty() }.map { s ->
            var t = s.replace(Regex("[^a-z0-9_]"), "_")
            if (t.isEmpty() || !t[0].isLetter()) t = "a" + t
            if (t in kw) t = t + "_"
            t
        }
        return if (segs.size >= 2) segs.joinToString(".") else "com.darkith." + (segs.firstOrNull() ?: "app")
    }

    private fun omegaFunctionName(n: String?): String {
        val core = (n ?: "").filter { it.isLetterOrDigit() && it.code < 128 }
        if (core.isEmpty()) return "DarkithNativeUi"
        val head = if (core[0].isDigit()) "App" + core else core.substring(0, 1).uppercase() + core.substring(1)
        return head + "Ui"
    }

    @JavascriptInterface
    fun translateHtml(html: String?, pkgName: String?, appName: String?): String {
        return try {
            if (html.isNullOrBlank()) return "DEFICITS: {(M1, \"empty HTML: nothing to reduce\")}"
            val result = com.darkith.transliaison.core.TransliaisonEngine().translateWithReport(html)
            if (result.nodes.isEmpty()) return "DEFICITS: {(M1, \"HTML parsed but produced no translatable nodes (empty body or only unsupported elements)\")}"
            return "DEFICIT: ComposeEmitter was purged. HTML to Compose translation is closed."
        } catch (e: Throwable) {
            "DEFICITS: {(M1, \"" + omegaEsc(e.message ?: e.javaClass.simpleName) + "\")}"
        }
    }

    @JavascriptInterface
    fun healSource(sourcePath: String?, compilerOutput: String?): String {
        return try {
            val f = java.io.File(norm(sourcePath))
            if (!f.isFile) return "DEFICITS: {(M1, \"no such source file: " + omegaEsc(f.path) + "\")}"
            if (f.length() > MAX_TEXT) return "DEFICITS: {(M1, \"source too large to heal\")}"
            val log = compilerOutput ?: ""
            if (log.isBlank()) return "DEFICITS: {(M1, \"no compiler output supplied: nothing to heal against\")}"
            val origBytes = f.readBytes()
            val orig = String(origBytes, Charsets.UTF_8)
            if (!java.util.Arrays.equals(orig.toByteArray(Charsets.UTF_8), origBytes)) return "DEFICITS: {(M1, \"source is not valid UTF-8 text; refusing to rewrite it\")}"
            var dict: Map<String, String> = com.darkith.transliaison.core.HealerDictionary.imports
            var out = com.darkith.transliaison.core.AutofillCorrector(dict).heal(orig, log)
            // M6: names the fixed dictionary lacks are looked up in remembered substrate artifacts (.taskbin)
            val ing = com.darkith.transliaison.core.SubstrateIngestor(omegaTaskbin())
            val recalled = LinkedHashMap<String, String>()
            for (d in out.deficits) {
                val sym = d.symbol
                if (d.code == "unresolved" && sym != null) {
                    val fqn = ing.recallImport(sym)
                    if (fqn != null) recalled[sym] = fqn
                }
            }
            if (recalled.isNotEmpty()) {
                val merged = LinkedHashMap<String, String>(dict)
                merged.putAll(recalled)
                dict = merged
                out = com.darkith.transliaison.core.AutofillCorrector(dict).heal(orig, log)
            }
            if (out.actions.isEmpty() && out.deficits.isEmpty()) return "DEFICITS: {(M1, \"compiler output contained no error lines the Healer recognises; nothing was changed\")}"
            var applied = ""
            if (out.actions.isNotEmpty()) {
                val again = com.darkith.transliaison.core.AutofillCorrector(dict).preAnalyze(out.source)
                if (again.actions.isNotEmpty()) return "DEFICITS: {(M4, \"repair is not idempotent (a second pass wants to change it again); nothing was written\")}"
                val beforeSha = com.darkith.transliaison.core.SubstrateIngestor.sha256(origBytes)
                val arch = java.io.File(omegaTaskbin(), "archive")
                arch.mkdirs()
                val archFile = java.io.File(arch, beforeSha + ".src")
                if (!archFile.exists()) archFile.writeBytes(origBytes)
                if (!archFile.isFile || com.darkith.transliaison.core.SubstrateIngestor.sha256(archFile.readBytes()) != beforeSha) return "DEFICITS: {(M9, \"could not archive the original under its SHA256; nothing was written\")}"
                val newBytes = out.source.toByteArray(Charsets.UTF_8)
                val afterSha = com.darkith.transliaison.core.SubstrateIngestor.sha256(newBytes)
                f.writeBytes(newBytes)
                if (com.darkith.transliaison.core.SubstrateIngestor.sha256(f.readBytes()) != afterSha) {
                    f.writeBytes(archFile.readBytes())
                    return "DEFICITS: {(M9, \"written file did not hash to the intended bytes; original resurrected from archive\")}"
                }
                val rec = org.json.JSONObject()
                rec.put("file", f.path)
                rec.put("shaBefore", beforeSha)
                rec.put("shaAfter", afterSha)
                rec.put("actions", org.json.JSONArray(out.actions))
                rec.put("recalledFromSubstrate", org.json.JSONObject(recalled as Map<*, *>))
                if (!omegaRecord("heal", rec)) return "DEFICITS: {(M5, \"repair WAS applied to " + omegaEsc(f.path) + " but could not be recorded in .taskbin\")}"
                applied = " [applied " + out.actions.size + " verified repair(s): " + omegaEsc(out.actions.joinToString("; ")) + "; recompile to confirm]"
            }
            if (out.deficits.isEmpty()) "HEALED"
            else "DEFICITS: {" + out.deficits.joinToString(", ") { "(" + it.code + ", \"" + omegaEsc(it.plain) + "\")" } + "}" + applied
        } catch (e: Throwable) {
            "DEFICITS: {(M7, \"" + omegaEsc(e.message ?: e.javaClass.simpleName) + "\")}"
        }
    }

    @JavascriptInterface
    fun ingestSubstrate(query: String?, language: String?): String {
        return try {
            com.darkith.transliaison.core.SubstrateIngestor(omegaTaskbin()).ingest(query ?: "", language ?: "").toBridgeString()
        } catch (e: Throwable) {
            "DEFICITS: {(M1, \"" + omegaEsc(e.message ?: e.javaClass.simpleName) + "\")}"
        }
    }

    @JavascriptInterface fun forgeChimera(donorsJson: String, html: String, appName: String, pkgName: String): String {
        return ChimeraBuilder(host).forgeChimera(donorsJson, html, appName, pkgName)
    }

    /**
     * Coditorus "Build APK". Builds a real, signed APK from the given HTML and returns
     * "OK:<absolute apk path>" — the contract homekeeper.html expects (it strips the
     * "OK:" prefix and hands the path to installApkNative). ChimeraBuilder drives the raw
     * aapt2 / zipalign / apksig toolchain; "[]" donors forges a clean standalone app.
     */
    @JavascriptInterface
    fun forgeNative(html: String?, appName: String?, pkgName: String?): String {
        return try {
            if (html.isNullOrBlank()) return "ERROR: HTML intent is empty."
            val name = appName?.takeIf { it.isNotBlank() } ?: "App"
            val pkg = pkgName?.takeIf { it.isNotBlank() } ?: "com.darkith.app"
            ChimeraBuilder(host).forgeChimera("[]", html, name, pkg)
        } catch (e: Throwable) {
            "ERROR: " + e.javaClass.simpleName + ": " + e.message
        }
    }

    /**
     * Floating Forge ("Forge (no Gradle)"). Parses HTML into LayoutNode IR, heals it with
     * IRAuditor, then renders via OmegaRenderer. Builds no APK: returns "OK: Forged N nodes".
     */
    @JavascriptInterface
    fun forgeRenderNative(html: String?, appName: String?, pkgName: String?): String {
        return try {
            NativeForgeBuilder(host).execute(html, appName, pkgName)
        } catch (e: Throwable) {
            "DEFICIT: " + e.javaClass.simpleName + ": " + e.message
        }
    }

    /** Opens the live Omega surface. C7 needs it attached before any IR forge can land. */
    @JavascriptInterface
    fun openOmegaScreen(): String = try {
        host.startActivity(Intent(host, com.darkith.transliaison.core.OmegaActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        "OK: Omega screen opening — attach the live renderer, then press Forge."
    } catch (e: Throwable) { err(e) }


    @JavascriptInterface fun openExternal(url: String?): String = try { host.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); "OK" } catch (e: Throwable) { err(e) }
    @JavascriptInterface fun copyText(text: String?): String = try { host.runOnUiThread { (host.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("d", text)) }; "OK" } catch (e: Throwable) { err(e) }
    @JavascriptInterface fun browserOpen(url: String?): String = try { host.runOnUiThread { host.showBrowser(url) }; "OK" } catch (e: Throwable) { err(e) }
    @JavascriptInterface fun browserClose(): String = try { host.runOnUiThread { host.hideBrowser() }; "OK" } catch (e: Throwable) { err(e) }

    // ---- signer identity ----
    // The signature is keyed by the APK's signing certificate and the device identity, and
    // carries a fresh nanosecond nonce per call, so every identity is unique and unreplayable,
    // and is coupled to whoever signed this APK (the user's build identity).
    private fun signerDigest(): String = try {
        @Suppress("DEPRECATION")
        val sigs = if (Build.VERSION.SDK_INT >= 28)
            host.packageManager.getPackageInfo(host.packageName, android.content.pm.PackageManager.GET_SIGNING_CERTIFICATES).signingInfo?.apkContentsSigners
        else host.packageManager.getPackageInfo(host.packageName, android.content.pm.PackageManager.GET_SIGNATURES).signatures
        val md = java.security.MessageDigest.getInstance("SHA-256")
        md.digest(sigs?.firstOrNull()?.toByteArray() ?: ByteArray(0)).joinToString("") { "%02x".format(it) }
    } catch (e: Throwable) { "unsigned" }

    private fun deviceId(): String = try {
        @Suppress("HardwareIds")
        val id = android.provider.Settings.Secure.getString(host.contentResolver, android.provider.Settings.Secure.ANDROID_ID)
        if (id.isNullOrEmpty()) "unknown" else id
    } catch (e: Throwable) { "unknown" }

    private fun hmacHex(keyHex: String, msg: String): String {
        val mac = javax.crypto.Mac.getInstance("HmacSHA256")
        val key = keyHex.chunked(2).mapNotNull { it.toIntOrNull(16)?.toByte() }.toByteArray()
        mac.init(javax.crypto.spec.SecretKeySpec(key, "HmacSHA256"))
        return mac.doFinal(msg.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }

    /** Signer-coupled identity: {signer, device, nonce (ns), sig=HMAC-SHA256(signer, …)}. */
    @JavascriptInterface
    fun signerSignature(): String = try {
        val nonce = System.nanoTime()
        val digest = signerDigest()
        val dev = deviceId()
        val sig = hmacHex(digest, "darkith:signer=$digest:device=$dev:nonce=$nonce")
        JSONObject().apply {
            put("signer", digest)
            put("device", dev)
            put("nonce", nonce.toString())
            put("sig", sig)
            put("algo", "HmacSHA256(signerDigest)")
        }.toString()
    } catch (e: Throwable) { err(e) }

    /** Recompute the HMAC for a returned {signer, nonce} and compare — proves coupling. */
    @JavascriptInterface
    fun verifySignerSignature(signer: String?, nonce: String?, sig: String?): Boolean = try {
        val digest = signerDigest()
        if (signer != digest) false
        else hmacHex(digest, "darkith:signer=$digest:device=${deviceId()}:nonce=$nonce") == sig
    } catch (e: Throwable) { false }

    /* ------------------------------------------------------------ device families
       One JS object ("darkith") must expose everything, so DeviceBridge's families are
       forwarded here rather than registered as a second interface. SPI-19: each family
       (dial/sms/contacts/camera/clock/media/notif/sys) is whole. */
    private val dev by lazy { DeviceBridge(host) }

    @JavascriptInterface fun deviceVersion(): String = dev.version()
    @JavascriptInterface fun deviceResult(id: String?): String = dev.deviceResult(id)

    /* sys */
    @JavascriptInterface fun sysInfo(): String = dev.sysInfo()
    @JavascriptInterface fun sysPermissions(): String = dev.sysPermissions()
    @JavascriptInterface fun sysRequest(perms: String?): String = dev.sysRequest(perms ?: "")

    /* dial */
    @JavascriptInterface fun dialNumber(number: String?): String = dev.dialNumber(number)
    @JavascriptInterface fun dialCall(number: String?): String = dev.dialCall(number)
    @JavascriptInterface fun dialTelephony(): String = dev.dialTelephony()

    /* sms */
    @JavascriptInterface fun smsSend(number: String?, text: String?): String = dev.smsSend(number, text)
    @JavascriptInterface fun smsCompose(number: String?, text: String?): String = dev.smsCompose(number, text)
    @JavascriptInterface fun smsInbox(limit: Int): String = dev.smsInbox(limit)

    /* contacts */
    @JavascriptInterface fun contactsList(limit: Int): String = dev.contactsList(limit)
    @JavascriptInterface fun contactsSearch(q: String?): String = dev.contactsSearch(q)
    @JavascriptInterface fun contactsAdd(name: String?, number: String?, email: String?): String = dev.contactsAdd(name, number, email)

    /* camera */
    @JavascriptInterface fun cameraList(): String = dev.cameraList()
    @JavascriptInterface fun cameraCapture(): String = dev.cameraCapture()
    @JavascriptInterface fun cameraPickImage(): String = dev.cameraPickImage()

    /* clock */
    @JavascriptInterface fun clockSetAlarm(h: Int, m: Int, label: String?, skipUi: Boolean): String = dev.clockSetAlarm(h, m, label, skipUi)
    @JavascriptInterface fun clockTimer(seconds: Int, label: String?): String = dev.clockTimer(seconds, label)
    @JavascriptInterface fun clockShowAlarms(): String = dev.clockShowAlarms()

    /* media */
    @JavascriptInterface fun mediaList(kind: String?, limit: Int): String = dev.mediaList(kind, limit)

    /* notif */
    @JavascriptInterface fun notifPost(title: String?, body: String?): String = dev.notifPost(title, body)
    @JavascriptInterface fun notifCancelAll(): String = dev.notifCancelAll()

}
