package com.darkith.transliaison.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.URLEncoder
import java.net.UnknownHostException
import java.security.MessageDigest
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

// * M2 carrier for one fetched artifact: what it IS and what it IS NOT. Holds iff all nine subfields are non-blank. //
data class IngestBoundary(
    val state: String,
    val property: String,
    val capacity: String,
    val function: String,
    val boundary: String,
    val language: String,
    val dialect: String,
    val version: String,
    val sourceSha256: String
) {
    fun fields(): List<Pair<String, String>> = listOf(
        Pair("state", state), Pair("property", property), Pair("capacity", capacity),
        Pair("function", function), Pair("boundary", boundary), Pair("language", language),
        Pair("dialect", dialect), Pair("version", version), Pair("sourceSha256", sourceSha256)
    )

    fun holds(): Boolean = fields().all { it.second.isNotBlank() }

    fun toJson(): JSONObject {
        val o = JSONObject()
        for (f in fields()) o.put(f.first, f.second)
        return o
    }
}

data class IngestArtifact(
    val source: String,
    val url: String,
    val language: String,
    val snippet: String,
    val snippetSha256: String,
    val fetchSha256: String,
    val boundary: IngestBoundary
) {
    fun toJson(): JSONObject {
        val o = JSONObject()
        o.put("source", source)
        o.put("url", url)
        o.put("language", language)
        o.put("snippet", snippet)
        o.put("snippetSha256", snippetSha256)
        o.put("fetchSha256", fetchSha256)
        o.put("boundary", boundary.toJson())
        return o
    }
}

data class IngestDeficit(val node: String, val reason: String)

// * Invariant: artifacts is non-empty OR deficits is non-empty. Never both empty (an empty answer is a stub). //
class IngestOutcome(val artifacts: List<IngestArtifact>, val deficits: List<IngestDeficit>, val fromCache: Boolean) {
    fun status(): String = if (artifacts.isEmpty()) "DEFICITS" else if (fromCache) "CACHED" else "FOUND"

    fun toBridgeString(): String {
        if (artifacts.isEmpty()) return SubstrateIngestor.formatDeficits(deficits)
        val o = JSONObject()
        o.put("status", status())
        val arr = JSONArray()
        for (a in artifacts) arr.put(a.toJson())
        o.put("artifacts", arr)
        val d = JSONArray()
        for (x in deficits) {
            val e = JSONObject()
            e.put("node", x.node)
            e.put("reason", x.reason)
            d.put(e)
        }
        o.put("deficits", d)
        return o.toString()
    }
}

/*
 * Phi_ingest: Query x Boundary -> Set<HashAddressedArtifact>. MANUAL ONLY: runs once per call to ingest(),
 * which the Operator triggers. No polling, no schedule, no background crawl.
 * Free, key-free sources first (grep.app, searchcode.com, Software Heritage). GITHUB_TOKEN is optional.
 * Every failure is named as a deficit; nothing ever returns a silent empty list.
 */
class SubstrateIngestor(
    private val cacheDir: File?,
    private val githubToken: String? = System.getenv("GITHUB_TOKEN")
) {
    private class Fetch(val body: String?, val sha: String, val deficit: String?)
    private class SourceResult(val node: String, val artifacts: List<IngestArtifact>, val deficit: String?)

    companion object {
        private const val TIMEOUT_MS = 7000
        private const val MAX_BYTES = 1500000
        private const val MAX_CACHE_BYTES = 5000000L
        private const val UA = "darkith-substrate-ingestor/1.0 (manual, operator-initiated)"
        private val IMPORT_PREFIXES = listOf("androidx.", "kotlin.", "kotlinx.", "android.", "java.", "javax.")

        fun formatDeficits(items: List<IngestDeficit>): String =
            "DEFICITS: {" + items.joinToString(", ") { "(" + it.node + ", \"" + esc(it.reason) + "\")" } + "}"

        private fun esc(s: String): String =
            s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", " ")

        fun sha256(bytes: ByteArray): String {
            val d = MessageDigest.getInstance("SHA-256").digest(bytes)
            val sb = StringBuilder(d.size * 2)
            for (b in d) sb.append(String.format("%02x", b.toInt() and 0xFF))
            return sb.toString()
        }

        fun sha256(s: String): String = sha256(s.toByteArray(Charsets.UTF_8))
    }

    private fun enc(s: String): String = URLEncoder.encode(s, "UTF-8")

    private fun readCapped(ins: InputStream): ByteArray {
        val out = ByteArrayOutputStream()
        val buf = ByteArray(8192)
        while (out.size() < MAX_BYTES) {
            val n = ins.read(buf)
            if (n < 0) break
            out.write(buf, 0, n)
        }
        return out.toByteArray()
    }

    private fun rateLimited(node: String): String =
        "[MECHANISM NOT DERIVED: Rate limit reached at Node " + node + ". Bypass not implemented.]"

    private fun httpGet(node: String, urlStr: String, headers: Map<String, String>): Fetch {
        var c: HttpURLConnection? = null
        return try {
            c = URL(urlStr).openConnection() as HttpURLConnection
            c.connectTimeout = TIMEOUT_MS
            c.readTimeout = TIMEOUT_MS
            c.requestMethod = "GET"
            c.instanceFollowRedirects = true
            c.setRequestProperty("User-Agent", UA)
            c.setRequestProperty("Accept", "application/json")
            for (kv in headers.entries) c.setRequestProperty(kv.key, kv.value)
            val code = c.responseCode
            if (code == 429) return Fetch(null, "", rateLimited(node))
            if (code == 403 && c.getHeaderField("X-RateLimit-Remaining") == "0") return Fetch(null, "", rateLimited(node))
            if (code !in 200..299) return Fetch(null, "", node + ": HTTP " + code)
            val bytes = c.inputStream.use { readCapped(it) }
            Fetch(String(bytes, Charsets.UTF_8), sha256(bytes), null)
        } catch (e: UnknownHostException) {
            Fetch(null, "", "[MECHANISM NOT DERIVED: " + node + " unreachable (DNS/no route). Offline fallback is the local .taskbin cache.]")
        } catch (e: SocketTimeoutException) {
            Fetch(null, "", "[MECHANISM NOT DERIVED: " + node + " unreachable (timeout after " + TIMEOUT_MS + " ms).]")
        } catch (e: Exception) {
            Fetch(null, "", node + ": " + e.javaClass.simpleName + ": " + (e.message ?: ""))
        } finally {
            c?.disconnect()
        }
    }

    private fun rawOf(o: JSONObject, key: String): String {
        val v = o.opt(key)
        return when (v) {
            is JSONObject -> v.optString("raw", "")
            is String -> v
            else -> ""
        }
    }

    private fun cleanSnippet(html: String): String {
        var s = html.replace(Regex("(?i)</tr>|<br\\s// ?>"), "\n")
        s = s.replace(Regex("<[^>]*>"), "")
        s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'")
            .replace("&nbsp;", " ").replace("&amp;", "&")
        return s.lines().map { it.trimEnd() }.filter { it.isNotBlank() }.joinToString("\n").take(4000)
    }

    // ---- M2: the qualification gate -------------------------------------------------------------

    private fun qualify(source: String, url: String, language: String, snippet: String, query: String, fetchSha: String): IngestBoundary? {
        val ext = url.substringBefore('?').substringAfterLast('/', "").substringAfterLast('.', "").lowercase()
        val dialect = when (ext) {
            "kt" -> "Kotlin/JVM"
            "kts" -> "Kotlin script (Gradle KTS)"
            "java" -> "Java"
            "gradle" -> "Groovy (Gradle DSL)"
            "xml" -> "XML"
            "js" -> "JavaScript"
            "ts" -> "TypeScript"
            "py" -> "Python"
            else -> "UNDETERMINED: extension '" + ext + "'"
        }
        val lang = if (language.isNotBlank()) language else if (dialect.startsWith("UNDETERMINED")) "UNDETERMINED" else dialect
        val vm = Regex("(?i)(?:kotlin[^\\n]{0,40}version|kotlin-gradle-plugin:|kotlin_version\\s*=)\\s*['\"]?([0-9]+\\.[0-9]+(?:\\.[0-9]+)?)").find(snippet)
        val version = if (vm != null) "Kotlin " + vm.groupValues[1] else "UNDETERMINED: no version marker in snippet"
        val terms = query.lowercase().split(Regex("\\s+")).filter { it.length > 1 }
        val low = snippet.lowercase()
        val hit = terms.count { low.contains(it) }
        val rec = IngestBoundary(
            state = "FETCHED_HASH_ADDRESSED",
            property = "query terms matched in snippet: " + hit + "/" + terms.size,
            capacity = "snippet bytes=" + snippet.toByteArray(Charsets.UTF_8).size + "; fetch sha256=" + fetchSha,
            function = "candidate evidence for repair recall (M6) of: " + query,
            boundary = "IS: bytes returned by " + source + " at fetch time, hash recorded. IS NOT: compiled, licence-checked, or proven current.",
            language = lang,
            dialect = dialect,
            version = version,
            sourceSha256 = sha256(snippet)
        )
        return if (rec.holds()) rec else null
    }

    private fun artifact(source: String, url: String, language: String, snippet: String, query: String, fetchSha: String): IngestArtifact? {
        val b = qualify(source, url, language, snippet, query, fetchSha) ?: return null
        return IngestArtifact(source, url, language.ifBlank { b.language }, snippet, b.sourceSha256, fetchSha, b)
    }

    // ---- sources ---------------------------------------------------------------------------------

    private fun fromGrepApp(query: String, language: String): SourceResult {
        val node = "grep.app"
        var url = "https://grep.app/api/search?q=" + enc(query)
        if (language.isNotBlank()) url += "&f.lang=" + enc(language)
        val f = httpGet(node, url, emptyMap())
        val body = f.body ?: return SourceResult(node, emptyList(), f.deficit)
        try {
            val hits = JSONObject(body).optJSONObject("hits")?.optJSONArray("hits")
                ?: return SourceResult(node, emptyList(), node + ": response has no hits.hits array (schema drift?)")
            val out = ArrayList<IngestArtifact>()
            for (i in 0 until hits.length()) {
                val h = hits.optJSONObject(i) ?: continue
                val repo = rawOf(h, "repo")
                val path = rawOf(h, "path")
                val snip = cleanSnippet(h.optJSONObject("content")?.optString("snippet", "") ?: "")
                if (repo.isBlank() || snip.isBlank()) continue
                val a = artifact(node, "https://github.com/" + repo + "/blob/HEAD/" + path, language, snip, query, f.sha)
                if (a != null) out.add(a)
            }
            return if (out.isEmpty()) SourceResult(node, emptyList(), node + ": reachable, 0 usable hits for this query") else SourceResult(node, out, null)
        } catch (e: Exception) {
            return SourceResult(node, emptyList(), node + ": response did not parse: " + e.javaClass.simpleName)
        }
    }

    private fun fromSearchcode(query: String, language: String): SourceResult {
        val node = "searchcode.com"
        val f = httpGet(node, "https://searchcode.com/api/codesearch_I/?per_page=10&q=" + enc(query), emptyMap())
        val body = f.body ?: return SourceResult(node, emptyList(), f.deficit)
        try {
            val results = JSONObject(body).optJSONArray("results")
                ?: return SourceResult(node, emptyList(), node + ": reachable, response has no results array")
            val out = ArrayList<IngestArtifact>()
            for (i in 0 until results.length()) {
                val r = results.optJSONObject(i) ?: continue
                val lang = r.optString("language", "")
                if (language.isNotBlank() && !lang.equals(language, ignoreCase = true)) continue
                val lines = r.optJSONObject("lines") ?: continue
                val rows = ArrayList<Pair<Int, String>>()
                val keys = lines.keys()
                while (keys.hasNext()) {
                    val k = keys.next()
                    rows.add(Pair(k.toIntOrNull() ?: 0, lines.optString(k, "")))
                }
                val snip = rows.sortedBy { it.first }.joinToString("\n") { it.second }.take(4000)
                val u = r.optString("url", "")
                if (snip.isBlank() || u.isBlank()) continue
                val a = artifact(node, u, if (lang.isNotBlank()) lang else language, snip, query, f.sha)
                if (a != null) out.add(a)
            }
            return if (out.isEmpty()) SourceResult(node, emptyList(), node + ": reachable, 0 usable hits for this query") else SourceResult(node, out, null)
        } catch (e: Exception) {
            return SourceResult(node, emptyList(), node + ": response did not parse: " + e.javaClass.simpleName)
        }
    }

    private fun fromSoftwareHeritage(query: String): SourceResult {
        val node = "Software Heritage"
        if (query.any { it.isWhitespace() }) {
            return SourceResult(node, emptyList(), node + ": skipped, it searches origin URLs and the query has whitespace")
        }
        val f = httpGet(node, "https://archive.softwareheritage.org/api/1/origin/search/" + enc(query) + "/?limit=5", emptyMap())
        val body = f.body ?: return SourceResult(node, emptyList(), f.deficit)
        try {
            val arr = JSONArray(body)
            val out = ArrayList<IngestArtifact>()
            for (i in 0 until arr.length()) {
                val u = arr.optJSONObject(i)?.optString("url", "") ?: ""
                if (u.isBlank()) continue
                val a = artifact(node, u, "", u, query, f.sha)
                if (a != null) out.add(a)
            }
            return if (out.isEmpty()) SourceResult(node, emptyList(), node + ": reachable, 0 archived origins match") else SourceResult(node, out, null)
        } catch (e: Exception) {
            return SourceResult(node, emptyList(), node + ": response did not parse: " + e.javaClass.simpleName)
        }
    }

    private fun fromGithub(query: String, language: String, token: String): SourceResult {
        val node = "GitHub code search"
        val q = query + (if (language.isNotBlank()) " language:" + language else "")
        val f = httpGet(
            node, "https://api.github.com/search/code?per_page=5&q=" + enc(q),
            mapOf("Authorization" to "Bearer " + token, "Accept" to "application/vnd.github.text-match+json")
        )
        val body = f.body ?: return SourceResult(node, emptyList(), f.deficit)
        try {
            val items = JSONObject(body).optJSONArray("items")
                ?: return SourceResult(node, emptyList(), node + ": response has no items array")
            val out = ArrayList<IngestArtifact>()
            for (i in 0 until items.length()) {
                val it0 = items.optJSONObject(i) ?: continue
                val u = it0.optString("html_url", "")
                val tm = it0.optJSONArray("text_matches")
                val sb = StringBuilder()
                if (tm != null) for (j in 0 until tm.length()) sb.append(tm.optJSONObject(j)?.optString("fragment", "") ?: "").append("\n")
                val snip = sb.toString().trim().take(4000)
                if (u.isBlank() || snip.isBlank()) continue
                val a = artifact(node, u, language, snip, query, f.sha)
                if (a != null) out.add(a)
            }
            return if (out.isEmpty()) SourceResult(node, emptyList(), node + ": reachable, 0 usable hits for this query") else SourceResult(node, out, null)
        } catch (e: Exception) {
            return SourceResult(node, emptyList(), node + ": response did not parse: " + e.javaClass.simpleName)
        }
    }

    // ---- the one manual sync ---------------------------------------------------------------------

    fun ingest(queryIn: String, languageIn: String): IngestOutcome {
        val query = queryIn.trim().take(200)
        val language = languageIn.trim()
        if (query.isEmpty()) {
            return IngestOutcome(emptyList(), listOf(IngestDeficit("M2", "empty query: nothing to qualify")), false)
        }
        val deficits = ArrayList<IngestDeficit>()
        val found = ArrayList<IngestArtifact>()
        val pool = Executors.newFixedThreadPool(4)
        try {
            val tasks = ArrayList<Callable<SourceResult>>()
            tasks.add(Callable { fromGrepApp(query, language) })
            tasks.add(Callable { fromSearchcode(query, language) })
            tasks.add(Callable { fromSoftwareHeritage(query) })
            val tok = githubToken
            if (!tok.isNullOrBlank()) tasks.add(Callable { fromGithub(query, language, tok) })
            val futures = tasks.map { pool.submit(it) }
            for (fu in futures) {
                try {
                    val r = fu.get((TIMEOUT_MS + 3000).toLong(), TimeUnit.MILLISECONDS)
                    found.addAll(r.artifacts)
                    if (r.deficit != null) deficits.add(IngestDeficit("M1", r.deficit))
                } catch (e: Exception) {
                    deficits.add(IngestDeficit("M1", "a source did not finish: " + e.javaClass.simpleName))
                }
            }
        } finally {
            pool.shutdownNow()
        }
        val seen = HashSet<String>()
        val unique = found.filter { seen.add(it.snippetSha256) }.take(20)
        if (unique.isNotEmpty()) {
            val w = persist(query, language, unique)
            if (w != null) deficits.add(IngestDeficit("M6", w))
            return IngestOutcome(unique, deficits, false)
        }
        val cached = fromCache(query, language)
        if (cached.isNotEmpty()) {
            deficits.add(IngestDeficit("M6", "network sources produced nothing; served " + cached.size + " cached artifact(s) from .taskbin"))
            return IngestOutcome(cached, deficits, true)
        }
        if (deficits.isEmpty()) deficits.add(IngestDeficit("M1", "no source produced an artifact and none reported why"))
        return IngestOutcome(emptyList(), deficits, false)
    }

    // ---- .taskbin cache (mu: memory) -------------------------------------------------------------

    private fun cacheFile(): File? = if (cacheDir == null) null else File(cacheDir, "substrate.jsonl")

    @Synchronized
    private fun persist(query: String, language: String, items: List<IngestArtifact>): String? {
        val f = cacheFile() ?: return "no cache directory configured; artifacts were not remembered"
        return try {
            f.parentFile?.mkdirs()
            if (f.exists() && f.length() > MAX_CACHE_BYTES) return "cache at " + f.path + " exceeds " + MAX_CACHE_BYTES + " bytes; new artifacts were not remembered (not deleted: operator decides)"
            val sb = StringBuilder()
            for (a in items) {
                val o = a.toJson()
                o.put("query", query)
                o.put("queryLanguage", language)
                o.put("ts", System.currentTimeMillis())
                sb.append(o.toString()).append("\n")
            }
            f.appendText(sb.toString(), Charsets.UTF_8)
            null
        } catch (e: Exception) {
            "cache write failed: " + e.javaClass.simpleName
        }
    }

    @Synchronized
    private fun readCache(): List<JSONObject> {
        val f = cacheFile() ?: return emptyList()
        if (!f.isFile) return emptyList()
        val out = ArrayList<JSONObject>()
        for (line in f.readLines(Charsets.UTF_8)) {
            if (line.isBlank()) continue
            try { out.add(JSONObject(line)) } catch (e: Exception) { }
        }
        return out
    }

    private fun fromCache(query: String, language: String): List<IngestArtifact> {
        val terms = query.lowercase().split(Regex("\\s+")).filter { it.length > 1 }
        val out = ArrayList<IngestArtifact>()
        for (o in readCache().reversed()) {
            val lang = o.optString("language", "")
            if (language.isNotBlank() && !lang.equals(language, ignoreCase = true)) continue
            val snip = o.optString("snippet", "")
            if (terms.isNotEmpty() && terms.none { snip.lowercase().contains(it) }) continue
            val bo = o.optJSONObject("boundary") ?: continue
            val b = IngestBoundary(
                bo.optString("state"), bo.optString("property"), bo.optString("capacity"), bo.optString("function"),
                bo.optString("boundary"), bo.optString("language"), bo.optString("dialect"), bo.optString("version"),
                bo.optString("sourceSha256")
            )
            if (!b.holds()) continue
            out.add(IngestArtifact(o.optString("source"), o.optString("url"), lang, snip, o.optString("snippetSha256"), o.optString("fetchSha256"), b))
            if (out.size >= 10) break
        }
        return out
    }

    // * M6: most-voted fully-qualified import for a bare symbol, from remembered Kotlin/Java artifacts only. //
    fun recallImport(symbol: String): String? {
        if (!Regex("[A-Za-z_][A-Za-z0-9_]*").matches(symbol)) return null
        val rx = Regex("^\\s*import\\s+([A-Za-z0-9_.]+)\\." + Regex.escape(symbol) + "\\s*;?\\s*$")
        val votes = HashMap<String, Int>()
        for (o in readCache()) {
            val lang = o.optString("language", "").lowercase()
            if (lang != "kotlin" && lang != "java") continue
            for (line in o.optString("snippet", "").split("\n")) {
                val m = rx.find(line) ?: continue
                val pkg = m.groupValues[1]
                if (IMPORT_PREFIXES.any { pkg.startsWith(it) }) {
                    val full = pkg + "." + symbol
                    votes[full] = (votes[full] ?: 0) + 1
                }
            }
        }
        var best: String? = null
        var bestN = -1
        for (kv in votes.entries.sortedBy { it.key }) {
            if (kv.value > bestN) { best = kv.key; bestN = kv.value }
        }
        return best
    }
}
