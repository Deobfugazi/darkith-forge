package com.darkith.transliaison.core

import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.util.Log
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * The live GLES 2.0 surface. Two things draw here:
 *   1. the rotating grid backdrop (the ambient GPU layer), and
 *   2. the IR surface: real geometry built from LayoutNode IR by IRBuilder.
 *
 * The control law runs FIRST, every frame, in onDrawFrame -> tickFrameBoundary:
 *   allocator.tick -> governor.reciprocate -> GpuScanner.safetyCap -> apply.
 * The renderer is a singleton (liveInstance) so forgeNative can route into THIS instance
 * instead of spawning a phantom one.
 */
class OmegaRenderer : GLSurfaceView.Renderer {

    private val targetFrameMs = 16.6f
    private val minResScale = 0.5f
    private val maxResScale = 1.0f
    private val minSubdiv = 8
    private val maxSubdiv = 96
    private val heapPressureTarget = 0.65f

    @Volatile var resScale = 1.0f; private set
    @Volatile var subdiv = 32; private set
    @Volatile var lastFrameMs = 16.6f; private set
    /** GL bytes this renderer owns right now: FBO + grid VBO/IBO + IR VBO. Pole A for the governor. */
    @Volatile var trackedBytes = 0L; private set
    @Volatile var capBreached = false; private set
    private var lastFrameNs = System.nanoTime()

    @Volatile private var screenW = 0
    @Volatile private var screenH = 0
    @Volatile private var gridBytes = 0L
    private var fboW = 0
    private var fboH = 0
    private var fbo = 0
    private var fboTex = 0
    private var fboDepth = 0

    private var gridProgram = 0
    private var blitProgram = 0
    private var irProgram = 0
    private var gridVbo = 0
    private var gridIbo = 0
    private var irVbo = 0
    private var indexCount = 0
    private var quadVbo = 0
    @Volatile private var irVertexCount = 0
    @Volatile private var irBytes = 0L
    @Volatile private var hasIr = false

    private val mvpMatrix = FloatArray(16)
    private val projMatrix = FloatArray(16)
    private val viewMatrix = FloatArray(16)
    private var rotation = 0f

    // ---- control law (runs every frame) ----
    private val allocator = AutophagicAllocator()
    private val governor = MemoryGovernor()
    @Volatile var lastAlloc: Allocation? = null; private set
    @Volatile var lastSafeVertexBudget: Long = 65_536L; private set
    private var lastFreeMem = 0L
    private var lastRawVB = 0L
    private var lastTraceMs = 0L
    @Volatile var freeMemProvider: () -> Long = {
        val rt = Runtime.getRuntime()
        rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())
    }
    @Volatile var cpuProvider: () -> Double = { 0.0 }
    @Volatile var modelAllocatedBytes: () -> Long = { 0L }

    // ---- IR handoff ----
    @Volatile private var allocationDriven = false
    @Volatile private var forgeNodes: List<LayoutNode>? = null
    @Volatile private var pendingRes: Float = -1f
    @Volatile private var pendingSub: Int = -1
    @Volatile private var lastAllocatorVertexBudget: Long = 65_536L

    /** Safe from any thread. rendererMaxBytes is the governor's Pole-A cap; Long.MAX_VALUE = no cap. */
    fun apply(allocation: Allocation, rendererMaxBytes: Long = Long.MAX_VALUE) {
        allocationDriven = true
        var res = allocation.resolutionScale.toFloat().coerceIn(minResScale, maxResScale)
        val w = screenW; val h = screenH
        if (rendererMaxBytes != Long.MAX_VALUE && w > 0 && h > 0) {
            val room = (rendererMaxBytes - gridBytes).coerceAtLeast(0L).toDouble()
            val capScale = sqrt(room / (w.toDouble() * h.toDouble() * FBO_BYTES_PER_PX)).toFloat()
            capBreached = capScale < minResScale
            if (capScale < res) res = max(capScale, minResScale)
        } else capBreached = false
        pendingRes = res
        pendingSub = sqrt(allocation.vertexBudget.toFloat()).toInt().coerceIn(minSubdiv, maxSubdiv)
        lastAllocatorVertexBudget = allocation.vertexBudget
    }

    /**
     * The per-frame control boundary. Runs first in onDrawFrame, on the GL thread (so
     * GpuScanner has a current context). Callers must NOT tick the allocator themselves.
     */
    fun tickFrameBoundary() {
        val free = freeMemProvider().coerceAtLeast(0L)
        val alloc = allocator.tick(free, trackedBytes, cpuProvider(), lastFrameMs.toDouble())
        val gov = governor.reciprocate(trackedBytes, modelAllocatedBytes())
        val cap = GpuScanner.safetyCap(free)
        val quadsFromCap = (cap / (IRBuilder.VERTEX_STRIDE_FLOATS.toLong() * 4L)).coerceAtLeast(1L)
        val safeV = min(alloc.vertexBudget, quadsFromCap)
        lastAlloc = alloc
        lastSafeVertexBudget = safeV
        lastFreeMem = free
        lastRawVB = alloc.vertexBudget
        apply(alloc, gov.rendererMaxBytes)
        trace("tickFrameBoundary: freeMem=$free trackedBytes=$trackedBytes raw.vB=${alloc.vertexBudget} safe.vB=$safeV")
    }

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        // A new GL context: every id from the old one is dead. Forget them (never delete them).
        fbo = 0; fboTex = 0; fboDepth = 0; fboW = 0; fboH = 0
        gridVbo = 0; gridIbo = 0; quadVbo = 0; irVbo = 0; indexCount = 0
        gridProgram = 0; blitProgram = 0; irProgram = 0
        irVertexCount = 0; irBytes = 0L; hasIr = false
        GLES20.glClearColor(0.04f, 0.05f, 0.07f, 1f)
        GLES20.glEnable(GLES20.GL_DEPTH_TEST)
        gridProgram = buildProgram(GRID_VS, GRID_FS)
        blitProgram = buildProgram(BLIT_VS, BLIT_FS)
        irProgram = buildProgram(IR_VS, IR_FS)
        quadVbo = makeFullscreenQuad()
        buildGrid(subdiv)
        GpuScanner.scan()
    }

    override fun onSurfaceChanged(gl: GL10?, w: Int, h: Int) {
        screenW = w; screenH = h
        GLES20.glViewport(0, 0, w, h)
        Matrix.perspectiveM(projMatrix, 0, 55f, w.toFloat() / max(1, h), 0.1f, 50f)
        resizeFbo(resScale)
    }

    /** Queue IR for the next GL frame. Never touches GL itself. */
    fun applyLayoutNodes(nodes: List<LayoutNode>) {
        this.forgeNodes = nodes
    }

    override fun onDrawFrame(gl: GL10?) {
        tickFrameBoundary()

        val nodes = forgeNodes
        if (nodes != null) {
            val budget = lastSafeVertexBudget
            trace("GL frame received ${nodes.size} IR nodes. Building within vertexBudget=$budget")
            val verts = buildIrGeometry(nodes, budget, screenW, screenH)
            uploadIr(verts)
            irVertexCount = verts.size / IRBuilder.VERTEX_STRIDE_FLOATS
            irBytes = verts.size.toLong() * 4L
            refreshTrackedBytes()
            hasIr = irVertexCount > 0
            trace("IR VBO: $irVertexCount verts, $irBytes bytes, budget=$budget")
            forgeNodes = null
        }

        val now = System.nanoTime()
        val dtMs = (now - lastFrameNs) / 1_000_000f
        lastFrameNs = now
        if (dtMs in 0.1f..500f) lastFrameMs = dtMs

        if (!allocationDriven) adapt()

        val pr = pendingRes
        if (pr >= 0f && pr != resScale) {
            resScale = pr
            resizeFbo(resScale)
            pendingRes = -1f
        }
        val ps = pendingSub
        if (ps >= 0 && ps != subdiv) {
            subdiv = ps
            buildGrid(subdiv)
            pendingSub = -1
        }

        // Invariant witness: grid verts (max 9,409) must not exceed allocator budget (min 65,536).
        check((subdiv + 1) * (subdiv + 1) <= lastAllocatorVertexBudget) {
            "INVARIANT VIOLATED: grid verts (${(subdiv + 1) * (subdiv + 1)}) exceed allocator budget ($lastAllocatorVertexBudget)"
        }

        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo)
        GLES20.glViewport(0, 0, fboW, fboH)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        drawGrid()
        if (hasIr) drawIr()

        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
        GLES20.glViewport(0, 0, screenW, screenH)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
        blitFbo()
    }

    private fun buildIrGeometry(nodes: List<LayoutNode>, vertexBudget: Long, w: Int, h: Int): FloatArray {
        val maxQuads = (vertexBudget / 6L).coerceIn(1L, 200_000L).toInt()
        return IRBuilder(maxQuads).build(nodes, w.toFloat(), h.toFloat(), BG_ARGB)
    }

    private fun uploadIr(verts: FloatArray) {
        if (irVbo == 0) { val a = IntArray(1); GLES20.glGenBuffers(1, a, 0); irVbo = a[0] }
        val buf = ByteBuffer.allocateDirect(verts.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        buf.put(verts).position(0)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, irVbo)
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, verts.size * 4, buf, GLES20.GL_DYNAMIC_DRAW)
    }

    private fun drawIr() {
        if (irVertexCount <= 0 || irVbo == 0 || irProgram == 0) return
        GLES20.glUseProgram(irProgram)
        val posLoc = GLES20.glGetAttribLocation(irProgram, "aPos")
        val colLoc = GLES20.glGetAttribLocation(irProgram, "aColor")
        val vpLoc = GLES20.glGetUniformLocation(irProgram, "uViewport")
        GLES20.glUniform2f(vpLoc, max(1, screenW).toFloat(), max(1, screenH).toFloat())
        GLES20.glEnable(GLES20.GL_BLEND)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, irVbo)
        GLES20.glEnableVertexAttribArray(posLoc)
        GLES20.glVertexAttribPointer(posLoc, 2, GLES20.GL_FLOAT, false, 24, 0)
        GLES20.glEnableVertexAttribArray(colLoc)
        GLES20.glVertexAttribPointer(colLoc, 4, GLES20.GL_FLOAT, false, 24, 8)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, irVertexCount)
        GLES20.glDisableVertexAttribArray(posLoc)
        GLES20.glDisableVertexAttribArray(colLoc)
        GLES20.glDisable(GLES20.GL_BLEND)
    }

    private fun refreshTrackedBytes() {
        trackedBytes = fboW.toLong() * fboH.toLong() * FBO_BYTES_PER_PX + gridBytes + irBytes
    }

    /**
     * The three evidence lines go to logcat and to an on-disk trace. The trace exists because this
     * device has no adb: it is the "in-app Aegis Logs" surface. The per-frame tick line is
     * throttled to about once a second so the file stays small; the IR lines are never throttled.
     */
    private fun trace(line: String) {
        Log.d(TAG, line)
        val now = System.currentTimeMillis()
        val isTick = line.startsWith("tickFrameBoundary")
        if (isTick && now - lastTraceMs < TRACE_THROTTLE_MS) return
        lastTraceMs = now
        try {
            val f = java.io.File(TRACE_FILE)
            f.parentFile?.mkdirs()
            f.appendText(line + "\n")
        } catch (_: Throwable) { /* a missing log file must never break rendering */ }
    }

    private fun adapt() {
        val frameError = lastFrameMs - targetFrameMs
        var nextRes = resScale
        if (frameError > 2f) nextRes -= 0.03f else if (frameError < -3f) nextRes += 0.015f
        nextRes = nextRes.coerceIn(minResScale, maxResScale)
        if (nextRes != resScale) { resScale = nextRes; resizeFbo(resScale) }

        var nextSub = subdiv
        if (frameError > 2f) nextSub = max(minSubdiv, subdiv - 2)
        else if (frameError < -3f) nextSub = min(maxSubdiv, subdiv + 1)
        if (nextSub != subdiv) { subdiv = nextSub; buildGrid(subdiv) }
    }

    private fun resizeFbo(scale: Float) {
        if (screenW == 0 || screenH == 0) return
        val w = max(1, (screenW * scale).toInt())
        val h = max(1, (screenH * scale).toInt())
        if (w == fboW && h == fboH && fbo != 0) return
        fboW = w; fboH = h
        if (fbo != 0) GLES20.glDeleteFramebuffers(1, intArrayOf(fbo), 0)
        if (fboTex != 0) GLES20.glDeleteTextures(1, intArrayOf(fboTex), 0)
        if (fboDepth != 0) GLES20.glDeleteRenderbuffers(1, intArrayOf(fboDepth), 0)

        val texIds = IntArray(1); GLES20.glGenTextures(1, texIds, 0); fboTex = texIds[0]
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, fboTex)
        GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, fboW, fboH, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
        // GLES2 needs CLAMP_TO_EDGE for non-power-of-two textures (the scaled FBO is NPOT) or the texture is incomplete.
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)

        val rbIds = IntArray(1); GLES20.glGenRenderbuffers(1, rbIds, 0); fboDepth = rbIds[0]
        GLES20.glBindRenderbuffer(GLES20.GL_RENDERBUFFER, fboDepth)
        GLES20.glRenderbufferStorage(GLES20.GL_RENDERBUFFER, GLES20.GL_DEPTH_COMPONENT16, fboW, fboH)

        val fbIds = IntArray(1); GLES20.glGenFramebuffers(1, fbIds, 0); fbo = fbIds[0]
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo)
        GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, fboTex, 0)
        GLES20.glFramebufferRenderbuffer(GLES20.GL_FRAMEBUFFER, GLES20.GL_DEPTH_ATTACHMENT, GLES20.GL_RENDERBUFFER, fboDepth)
        val fbStatus = GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER)
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
        if (fbStatus != GLES20.GL_FRAMEBUFFER_COMPLETE) {
            Log.e(TAG, "FBO incomplete: 0x" + Integer.toHexString(fbStatus) + " at ${fboW}x$fboH")
            throw IllegalStateException("FBO incomplete: 0x" + Integer.toHexString(fbStatus) + " at ${fboW}x$fboH")
        }
        refreshTrackedBytes()
    }

    private fun buildGrid(cells: Int) {
        val n = cells.coerceIn(2, maxSubdiv)
        val verts = FloatArray((n + 1) * (n + 1) * 3)
        var vi = 0
        for (z in 0..n) for (x in 0..n) {
            verts[vi++] = (x.toFloat() / n - 0.5f) * 6f
            verts[vi++] = 0f
            verts[vi++] = (z.toFloat() / n - 0.5f) * 6f
        }
        val idx = ArrayList<Short>((n * n * 6))
        for (z in 0 until n) for (x in 0 until n) {
            val a = (z * (n + 1) + x).toShort()
            val b = (z * (n + 1) + x + 1).toShort()
            val c = ((z + 1) * (n + 1) + x).toShort()
            val d = ((z + 1) * (n + 1) + x + 1).toShort()
            idx.add(a); idx.add(c); idx.add(b)
            idx.add(b); idx.add(c); idx.add(d)
        }
        indexCount = idx.size

        val vb = ByteBuffer.allocateDirect(verts.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        vb.put(verts).position(0)
        val ib = ByteBuffer.allocateDirect(idx.size * 2).order(ByteOrder.nativeOrder()).asShortBuffer()
        for (v in idx) ib.put(v)
        ib.position(0)

        if (gridVbo == 0) { val a = IntArray(1); GLES20.glGenBuffers(1, a, 0); gridVbo = a[0] }
        if (gridIbo == 0) { val a = IntArray(1); GLES20.glGenBuffers(1, a, 0); gridIbo = a[0] }
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, gridVbo)
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, verts.size * 4, vb, GLES20.GL_STATIC_DRAW)
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, gridIbo)
        GLES20.glBufferData(GLES20.GL_ELEMENT_ARRAY_BUFFER, idx.size * 2, ib, GLES20.GL_STATIC_DRAW)
        gridBytes = verts.size * 4L + idx.size * 2L
        refreshTrackedBytes()
    }

    private fun drawGrid() {
        rotation += 0.6f
        Matrix.setLookAtM(viewMatrix, 0, 0f, 3.2f, 4.2f, 0f, 0f, 0f, 0f, 1f, 0f)
        val model = FloatArray(16)
        Matrix.setIdentityM(model, 0)
        Matrix.rotateM(model, 0, rotation, 0f, 1f, 0f)
        val vm = FloatArray(16)
        Matrix.multiplyMM(vm, 0, viewMatrix, 0, model, 0)
        Matrix.multiplyMM(mvpMatrix, 0, projMatrix, 0, vm, 0)

        GLES20.glUseProgram(gridProgram)
        val posLoc = GLES20.glGetAttribLocation(gridProgram, "aPos")
        val mvpLoc = GLES20.glGetUniformLocation(gridProgram, "uMvp")
        val colorLoc = GLES20.glGetUniformLocation(gridProgram, "uColor")
        GLES20.glUniformMatrix4fv(mvpLoc, 1, false, mvpMatrix, 0)
        GLES20.glUniform4f(colorLoc, 0.33f, 0.72f, 1f, 1f)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, gridVbo)
        GLES20.glEnableVertexAttribArray(posLoc)
        GLES20.glVertexAttribPointer(posLoc, 3, GLES20.GL_FLOAT, false, 0, 0)
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, gridIbo)
        GLES20.glDrawElements(GLES20.GL_TRIANGLES, indexCount, GLES20.GL_UNSIGNED_SHORT, 0)
        GLES20.glDisableVertexAttribArray(posLoc)
    }

    private fun blitFbo() {
        GLES20.glUseProgram(blitProgram)
        val posLoc = GLES20.glGetAttribLocation(blitProgram, "aPos")
        val uvLoc = GLES20.glGetAttribLocation(blitProgram, "aUv")
        val texLoc = GLES20.glGetUniformLocation(blitProgram, "uTex")
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, fboTex)
        GLES20.glUniform1i(texLoc, 0)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, quadVbo)
        GLES20.glEnableVertexAttribArray(posLoc)
        GLES20.glVertexAttribPointer(posLoc, 2, GLES20.GL_FLOAT, false, 16, 0)
        GLES20.glEnableVertexAttribArray(uvLoc)
        GLES20.glVertexAttribPointer(uvLoc, 2, GLES20.GL_FLOAT, false, 16, 8)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
        GLES20.glDisableVertexAttribArray(posLoc)
        GLES20.glDisableVertexAttribArray(uvLoc)
    }

    private fun makeFullscreenQuad(): Int {
        val data = floatArrayOf(-1f, -1f, 0f, 1f, 1f, -1f, 1f, 1f, -1f, 1f, 0f, 0f, 1f, 1f, 1f, 0f)
        val buf = ByteBuffer.allocateDirect(data.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        buf.put(data).position(0)
        val id = IntArray(1); GLES20.glGenBuffers(1, id, 0)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, id[0])
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, data.size * 4, buf, GLES20.GL_STATIC_DRAW)
        return id[0]
    }

    private fun buildProgram(vsSrc: String, fsSrc: String): Int {
        val vs = compileShader(GLES20.GL_VERTEX_SHADER, vsSrc)
        val fs = compileShader(GLES20.GL_FRAGMENT_SHADER, fsSrc)
        val prog = GLES20.glCreateProgram()
        GLES20.glAttachShader(prog, vs)
        GLES20.glAttachShader(prog, fs)
        GLES20.glLinkProgram(prog)
        val st = IntArray(1)
        GLES20.glGetProgramiv(prog, GLES20.GL_LINK_STATUS, st, 0)
        if (st[0] == 0) {
            val log = GLES20.glGetProgramInfoLog(prog)
            GLES20.glDeleteProgram(prog)
            Log.e(TAG, "program link failed: $log")
            throw IllegalStateException("program link failed: $log")
        }
        return prog
    }

    private fun compileShader(type: Int, src: String): Int {
        val id = GLES20.glCreateShader(type)
        GLES20.glShaderSource(id, src)
        GLES20.glCompileShader(id)
        val st = IntArray(1)
        GLES20.glGetShaderiv(id, GLES20.GL_COMPILE_STATUS, st, 0)
        if (st[0] == 0) {
            val log = GLES20.glGetShaderInfoLog(id)
            GLES20.glDeleteShader(id)
            Log.e(TAG, "shader compile failed: $log")
            throw IllegalStateException("shader compile failed: $log\n$src")
        }
        return id
    }

    companion object {
        private const val TAG = "OmegaRenderer"
        private const val FBO_BYTES_PER_PX = 6L   // RGBA8 colour (4) + DEPTH_COMPONENT16 (2)
        private const val BG_ARGB = 0xFF0A0D12L
        private const val TRACE_FILE = "/sdcard/Darkith/logs/omega_trace.txt"
        private const val TRACE_THROTTLE_MS = 1000L
        private const val GRID_VS = "attribute vec4 aPos; uniform mat4 uMvp; void main() { gl_Position = uMvp * aPos; }"
        private const val GRID_FS = "precision mediump float; uniform vec4 uColor; void main() { gl_FragColor = uColor; }"
        private const val BLIT_VS = "attribute vec2 aPos; attribute vec2 aUv; varying vec2 vUv; void main() { vUv = aUv; gl_Position = vec4(aPos, 0.0, 1.0); }"
        private const val BLIT_FS = "precision mediump float; varying vec2 vUv; uniform sampler2D uTex; void main() { gl_FragColor = texture2D(uTex, vUv); }"
        private const val IR_VS = "attribute vec2 aPos; attribute vec4 aColor; varying vec4 vColor; uniform vec2 uViewport; void main() { vec2 ndc = vec2((aPos.x / uViewport.x) * 2.0 - 1.0, 1.0 - (aPos.y / uViewport.y) * 2.0); gl_Position = vec4(ndc, 0.0, 1.0); vColor = aColor; }"
        private const val IR_FS = "precision mediump float; varying vec4 vColor; void main() { gl_FragColor = vColor; }"

        /** The live OmegaRenderer attached to the visible Omega surface, if any. */
        @Volatile var liveInstance: OmegaRenderer? = null
            private set

        fun registerLive(r: OmegaRenderer?) {
            liveInstance = r
            Log.d(TAG, if (r == null) "live OmegaRenderer detached" else "live OmegaRenderer attached")
        }
    }
}
