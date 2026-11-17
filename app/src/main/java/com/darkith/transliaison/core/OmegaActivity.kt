package com.darkith.transliaison.core

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.TextView

/**
 * Native Omega endpoint: a GLES 2.0 surface driven by AutophagicAllocator + MemoryGovernor, with a
 * live readout.
 *
 * This Activity owns the ONE live OmegaRenderer (OmegaRenderer.liveInstance). It attaches itself
 * in onCreate and detaches in onDestroy, so forgeNative can route IR into the surface that is
 * actually on screen — and can refuse with "DEFICIT: C7" when no surface is attached.
 */
class OmegaActivity : Activity() {

    private lateinit var glView: GLSurfaceView
    private lateinit var renderer: OmegaRenderer
    private lateinit var builder: NativeOmegaBuilder
    private lateinit var hud: TextView
    private val ui = Handler(Looper.getMainLooper())
    private val hudTick = object : Runnable {
        override fun run() {
            hud.text = builder.status()
            ui.postDelayed(this, 500L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        glView = GLSurfaceView(this)
        glView.setEGLContextClientVersion(2)
        renderer = OmegaRenderer()
        glView.setRenderer(renderer)
        glView.renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        builder = NativeOmegaBuilder(renderer, this)

        // C7: the live renderer is a singleton. Attach before the surface starts drawing.
        OmegaRenderer.registerLive(renderer)

        hud = TextView(this).apply {
            setTextColor(Color.rgb(200, 230, 255))
            setBackgroundColor(Color.argb(140, 0, 0, 0))
            typeface = Typeface.MONOSPACE
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 11f)
            setPadding(16, 48, 16, 12)
            isClickable = false
        }
        val root = FrameLayout(this)
        root.addView(glView, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        root.addView(hud, FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP or Gravity.START))
        setContentView(root)
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

    override fun onDestroy() {
        // C7: detach the live slot so a later forgeNative refuses instead of writing into a dead surface.
        if (OmegaRenderer.liveInstance === renderer) OmegaRenderer.registerLive(null)
        super.onDestroy()
    }
}
