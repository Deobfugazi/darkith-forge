package com.darkith.omega

import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * MainActivity — the Darkith Ω standalone surface.
 *
 * One job: bring the userspace up and keep it up. The crash handler is installed
 * before the first view is inflated, the WebView is loaded from the bundled
 * asset (fully offline), and every post-UI step is best-effort so no optional
 * subsystem can take the launcher down after the surface is already painted.
 */
class MainActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var bridge: OmegaBridge

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bridge = OmegaBridge(this)
        val prev = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            bridge.captureCrash(t, e)
            prev?.uncaughtException(t, e)
        }
        setContentView(R.layout.activity_main)
        webView = findViewById(R.id.webView)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            databaseEnabled = true
            mediaPlaybackRequiresUserGesture = false
            setSupportZoom(false)
        }
        webView.webViewClient = WebViewClient()
        webView.addJavascriptInterface(bridge, "darkith")
        webView.addJavascriptInterface(bridge, "darkithNative")
        webView.loadUrl("file:///android_asset/omega_studio.html")
    }

    override fun onBackPressed() {
        if (this::webView.isInitialized && webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
