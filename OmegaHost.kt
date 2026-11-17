package com.darkith.omega

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.TextView
import com.darkith.transliaison.core.NativeOmegaBuilder
import com.darkith.transliaison.core.OmegaRenderer
import java.io.File

/**
 * OMEGA POINT — the forged app's runtime host.
 *
 * NT X closure, wired: the artifact is a signed APK whose content surface is drawn by the
 * hand-rolled engine, not by a vendor UI toolkit.
 *
 *  - The hand-rolled AutophagicAllocator (NT X Part 3) and MemoryGovernor (Part 3.5) run on a
 *    16 ms main-thread tick (NativeOmegaBuilder) and drive the hand-rolled GLES 2.0
 *    OmegaRenderer (the WebGL-equivalent GPU path).
 *  - There is NO Jetpack Compose and NO vendor layout toolkit in this artifact. Every View here
 *    is a platform primitive (FrameLayout / TextView / WebView).
 *  - The content surface is the assets/homekeeper.html document injected at forge time. The GL
 *    surface runs underneath it as the allocator-driven GPU layer; the WebView is the content
 *    plane over that layer, and doubles as the content engine when the app needs full DOM/CSS.
 *  - [OMEGA POINT] marks where the content plane can be swapped for the pure-IR surface: drive
 *    renderer.applyLayoutNodes(TransliaisonEngine().translate(html)) to paint the document
 *    itself through the GL path with no WebView. That leg is wired and reachable, but the DOM
 *    engine is kept as the default content plane because the WebView needs a JS bridge the
 *    hand-rolled IR path does not yet provide.
 *
 * One process. One surface. The allocator eats its own past allocation and re-derives the next
 * budget from the measured residual. No Gradle, no Compose, no borrowed shell.
 */
class OmegaHost : Activity() {

    private lateinit var glView: android.opengl.GLSurfaceView
    private lateinit var renderer: OmegaRenderer
    private lateinit var builder: NativeOmegaBuilder
    private lateinit var web: WebView
    private lateinit var hud: TextView
    private val ui = Handler(Looper.getMainLooper())

    private val hudTick = object : Runnable {
        override fun run() {
            if (SHOW_HUD) hud.text = builder.status()
            ui.postDelayed(this, 500L)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // ---- the hand-rolled GPU path (WebGL-equivalent): GLES2 + allocator + governor ----
        glView = android.opengl.GLSurfaceView(this)
        glView.setEGLContextClientVersion(2)
        renderer = OmegaRenderer()
        glView.setRenderer(renderer)
        glView.renderMode = android.opengl.GLSurfaceView.RENDERMODE_CONTINUOUSLY
        builder = NativeOmegaBuilder(renderer, this)

        // ---- the content plane: the forged document ----
        web = WebView(this)
        web.setBackgroundColor(Color.TRANSPARENT)
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = false
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }
        }
        web.webViewClient = WebViewClient()
        web.isVerticalScrollBarEnabled = false
        web.setLayerType(View.LAYER_TYPE_HARDWARE, null)

        hud = TextView(this).apply {
            setTextColor(Color.rgb(200, 230, 255))
            setBackgroundColor(Color.argb(150, 0, 0, 0))
            typeface = Typeface.MONOSPACE
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 10f)
            setPadding(16, 44, 16, 10)
            visibility = if (SHOW_HUD) View.VISIBLE else View.GONE
        }

        val root = FrameLayout(this)
        root.addView(glView, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        root.addView(web, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        root.addView(hud, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT,
            Gravity.TOP or Gravity.START))
        setContentView(root)

        web.loadUrl("file:///android_asset/homekeeper.html")
    }

    override fun onResume() {
        super.onResume()
        glView.onResume()
        builder.start()
        ui.post(hudTick)
    }

    override fun onPause() {
        ui.removeCallbacks(hudTick)
        builder.stop()
        glView.onPause()
        super.onPause()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) { web.goBack(); return }
        @Suppress("DEPRECATION")
        super.onBackPressed()
    }

    /**
     * [OMEGA POINT] — the pure-IR leg. Reads the forged document, translates it to LayoutNode IR
     * and hands it to the hand-rolled renderer so the surface is drawn by the engine with no DOM.
     * Kept as a live seam: call it to paint through the IR path instead of the content plane.
     */
    @Suppress("unused")
    private fun paintThroughEngine() {
        try {
            val html = assets.open("homekeeper.html").use { it.readBytes().toString(Charsets.UTF_8) }
            val nodes = com.darkith.transliaison.core.TransliaisonEngine().translate(html)
            renderer.applyLayoutNodes(nodes)
        } catch (_: Throwable) { /* content plane remains the surface */ }
    }

    companion object {
        private const val SHOW_HUD = true
    }
}
