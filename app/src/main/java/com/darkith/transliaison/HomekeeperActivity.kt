package com.darkith.transliaison

import android.Manifest
import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.net.URLDecoder

class HomekeeperActivity : Activity() {
    lateinit var webView: WebView
    private lateinit var root: FrameLayout
    private var browserLayer: LinearLayout? = null
    private var browserView: WebView? = null
    private var urlBar: EditText? = null
    private var progressBar: ProgressBar? = null
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val FILE_CHOOSER_RESULT_CODE = 1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // VFS: "All files access" on Android 11+, runtime permissions below that
        askAllFiles()

        // M-11: read ApplicationExitInfo on boot for 4GB discipline
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val am = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                am.getHistoricalProcessExitReasons(packageName, 0, 1).forEach { exitInfo ->
                    val desc = exitInfo.description ?: ""
                    if (desc.contains("MemoryLimiter", ignoreCase = true)) {
                        try {
                            File("/sdcard/Darkith/constraints/4gb_ledger.jsonl").appendText(
                                "{\"event\":\"memory_pressure\",\"exit_info\":\"$desc\",\"ts\":${System.currentTimeMillis()}}\n"
                            )
                        } catch (e: Exception) { }
                    }
                }
            } catch (e: Exception) { }
        }

        try {
            val serviceIntent = Intent(this, AegisReaper::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
        } catch (e: Exception) { }

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.allowFileAccess = true
            settings.domStorageEnabled = true
            settings.allowContentAccess = true
            settings.mediaPlaybackRequiresUserGesture = false
            WebView.setWebContentsDebuggingEnabled(false)

            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView,
                    request: WebResourceRequest
                ): WebResourceResponse? {
                    val url = request.url.toString()
                    if (url.startsWith("aegis://fs/")) {
                        return try {
                            val path = URLDecoder.decode(url.replace("aegis://fs/", "/sdcard/"), "UTF-8")
                            val file = File(path)
                            if (file.exists() && file.isFile) {
                                WebResourceResponse(getMimeType(path), "UTF-8", FileInputStream(file))
                            } else null
                        } catch (e: Exception) { null }
                    }
                    return super.shouldInterceptRequest(view, request)
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    webView: WebView?,
                    callback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?
                ): Boolean {
                    return this@HomekeeperActivity.launchChooser(callback, fileChooserParams)
                }
            }

            addJavascriptInterface(HomekeeperBridge(this@HomekeeperActivity), "darkith")
            loadUrl("file:///android_asset/homekeeper.html")
        }

        root = FrameLayout(this)
        root.addView(
            webView,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        )
        setContentView(root)
    }

    // ------------------------------------------------------------------ permissions
    fun askAllFiles() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!android.os.Environment.isExternalStorageManager()) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    intent.addCategory("android.intent.category.DEFAULT")
                    intent.data = Uri.parse("package:$packageName")
                    startActivity(intent)
                } catch (e: Exception) {
                    try {
                        startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
                    } catch (e2: Exception) { }
                }
            }
        } else {
            requestPermissions(
                arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE),
                100
            )
        }
    }

    // ------------------------------------------------------------------ file chooser (the picker fix)
    // WebView hands us acceptTypes = [""] when the input has no accept attribute, and raw
    // extensions like ".apk" when it does. Neither is a valid MIME type. Only trust real MIME types.
    private fun resolveMimes(accept: Array<String>?): List<String> {
        val out = LinkedHashSet<String>()
        if (accept != null) {
            for (raw in accept) {
                for (part in raw.split(",")) {
                    val t = part.trim().lowercase()
                    if (t.isEmpty()) continue
                    if (t.startsWith(".") || !t.contains("/")) return emptyList()
                    out.add(t)
                }
            }
        }
        if (out.contains("*/*")) return emptyList()
        return out.toList()
    }

    fun launchChooser(callback: ValueCallback<Array<Uri>>?, params: WebChromeClient.FileChooserParams?): Boolean {
        this.filePathCallback?.onReceiveValue(null)
        this.filePathCallback = callback

        val intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.type = "*/*"

        val mimes = resolveMimes(params?.acceptTypes)
        if (mimes.size == 1) {
            intent.type = mimes[0]
        } else if (mimes.size > 1) {
            intent.putExtra(Intent.EXTRA_MIME_TYPES, mimes.toTypedArray())
        }
        if (params != null && params.mode == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) {
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
        }

        return try {
            startActivityForResult(Intent.createChooser(intent, "Select file"), FILE_CHOOSER_RESULT_CODE)
            true
        } catch (e: Exception) {
            this.filePathCallback = null
            callback?.onReceiveValue(null)
            true
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == FILE_CHOOSER_RESULT_CODE) {
            val cb = this.filePathCallback
            this.filePathCallback = null
            if (cb != null) {
                var results: Array<Uri>? = null
                if (resultCode == RESULT_OK && data != null) {
                    results = WebChromeClient.FileChooserParams.parseResult(resultCode, data)
                }
                cb.onReceiveValue(results)
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    // ------------------------------------------------------------------ native browser overlay
    private fun dp(n: Int): Int = (n * resources.displayMetrics.density + 0.5f).toInt()

    private fun toolButton(label: String, onTap: () -> Unit): TextView {
        val t = TextView(this)
        t.text = label
        t.textSize = 20f
        t.gravity = Gravity.CENTER
        t.setTextColor(Color.parseColor("#5cc8ff"))
        t.minWidth = dp(44)
        t.minHeight = dp(44)
        t.setOnClickListener { onTap() }
        return t
    }

    private fun ensureBrowser() {
        if (browserLayer != null) return

        val layer = LinearLayout(this)
        layer.orientation = LinearLayout.VERTICAL
        layer.setBackgroundColor(Color.parseColor("#050505"))
        layer.visibility = View.GONE
        layer.isClickable = true
        layer.setOnApplyWindowInsetsListener { v, insets ->
            v.setPadding(0, insets.systemWindowInsetTop, 0, insets.systemWindowInsetBottom)
            insets
        }

        val bar = LinearLayout(this)
        bar.orientation = LinearLayout.HORIZONTAL
        bar.gravity = Gravity.CENTER_VERTICAL
        bar.setBackgroundColor(Color.parseColor("#0a0c13"))
        bar.setPadding(dp(4), dp(4), dp(4), dp(4))

        val url = EditText(this)
        url.setSingleLine(true)
        url.hint = "Search or enter address"
        url.setTextColor(Color.parseColor("#f0f2f5"))
        url.setHintTextColor(Color.parseColor("#8b93a1"))
        url.textSize = 14f
        url.setBackgroundColor(Color.parseColor("#14161d"))
        url.setPadding(dp(12), dp(8), dp(12), dp(8))
        url.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
        url.imeOptions = EditorInfo.IME_ACTION_GO
        url.setOnEditorActionListener { v, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_GO || (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER)) {
                browserGo(v.text.toString())
                true
            } else {
                false
            }
        }
        urlBar = url

        bar.addView(toolButton("◀") { browserBack() })
        bar.addView(toolButton("▶") { browserView?.let { if (it.canGoForward()) it.goForward() } })
        bar.addView(toolButton("↻") { browserView?.reload() })
        bar.addView(url, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        bar.addView(toolButton("★") {
            val u = browserView?.url ?: ""
            if (u.isNotEmpty()) {
                webView.evaluateJavascript("window.hkBookmark&&window.hkBookmark(" + JSONObject.quote(u) + ")", null)
            }
        })
        bar.addView(toolButton("↗") {
            val u = browserView?.url ?: ""
            if (u.isNotEmpty()) {
                try {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(u)))
                } catch (e: Exception) { }
            }
        })
        bar.addView(toolButton("✕") { hideBrowser() })
        layer.addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        val pb = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal)
        pb.max = 100
        pb.visibility = View.GONE
        progressBar = pb
        layer.addView(pb, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))

        val bw = WebView(this)
        bw.settings.javaScriptEnabled = true
        bw.settings.domStorageEnabled = true
        bw.settings.setSupportZoom(true)
        bw.settings.builtInZoomControls = true
        bw.settings.displayZoomControls = false
        bw.settings.loadWithOverviewMode = true
        bw.settings.useWideViewPort = true
        bw.settings.allowFileAccess = false
        bw.settings.setSupportMultipleWindows(false)
        bw.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val u = request?.url?.toString() ?: return false
                val low = u.lowercase()
                if (low.startsWith("http://") || low.startsWith("https://")) return false
                if (low.startsWith("tel:") || low.startsWith("mailto:") || low.startsWith("sms:")) {
                    try {
                        this@HomekeeperActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(u)))
                    } catch (e: Exception) { }
                }
                return true
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                if (url != null && !url.startsWith("about:")) this@HomekeeperActivity.urlBar?.setText(url)
                this@HomekeeperActivity.progressBar?.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                this@HomekeeperActivity.progressBar?.visibility = View.GONE
            }
        }
        bw.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                this@HomekeeperActivity.progressBar?.progress = newProgress
            }

            override fun onShowFileChooser(
                webView: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                return this@HomekeeperActivity.launchChooser(callback, fileChooserParams)
            }
        }
        bw.setDownloadListener { dlUrl, _, _, _, _ ->
            try {
                this@HomekeeperActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(dlUrl)))
            } catch (e: Exception) { }
        }
        browserView = bw
        layer.addView(bw, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        root.addView(
            layer,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        )
        browserLayer = layer
    }

    fun showBrowser(input: String?) {
        ensureBrowser()
        browserLayer?.visibility = View.VISIBLE
        browserLayer?.requestApplyInsets()
        if (input != null && input.isNotBlank()) browserGo(input)
    }

    fun hideBrowser() {
        urlBar?.clearFocus()
        browserLayer?.visibility = View.GONE
    }

    private fun browserGo(raw: String) {
        val t = raw.trim()
        if (t.isEmpty()) return
        val target = if (t.startsWith("http://", true) || t.startsWith("https://", true)) {
            t
        } else if (t.contains(" ") || !t.contains(".")) {
            "https://duckduckgo.com/?q=" + Uri.encode(t)
        } else {
            "https://" + t
        }
        browserView?.loadUrl(target)
    }

    private fun browserBack() {
        val bw = browserView
        if (bw != null && bw.canGoBack()) bw.goBack() else hideBrowser()
    }

    // ------------------------------------------------------------------ lifecycle
    @Deprecated("legacy back handling")
    override fun onBackPressed() {
        val bl = browserLayer
        if (bl != null && bl.visibility == View.VISIBLE) {
            browserBack()
            return
        }
        webView.evaluateJavascript("(window.hkBack?window.hkBack():false)") { v ->
            if (v != "true") finish()
        }
    }

    private fun getMimeType(path: String): String {
        return when {
            path.endsWith(".html") || path.endsWith(".htm") -> "text/html"
            path.endsWith(".js") -> "application/javascript"
            path.endsWith(".css") -> "text/css"
            path.endsWith(".json") -> "application/json"
            path.endsWith(".svg") -> "image/svg+xml"
            path.endsWith(".png") -> "image/png"
            path.endsWith(".jpg") || path.endsWith(".jpeg") -> "image/jpeg"
            else -> "application/octet-stream"
        }
    }

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= TRIM_MEMORY_RUNNING_LOW) {
            webView.post {
                webView.evaluateJavascript("window.triggerMemoryYield && window.triggerMemoryYield()", null)
            }
            val bl = browserLayer
            if (bl != null && bl.visibility != View.VISIBLE) browserView?.loadUrl("about:blank")
        }
    }

    override fun onDestroy() {
        try {
            browserView?.destroy()
        } catch (e: Exception) { }
        super.onDestroy()
    }
}
