package com.darkith.omega

import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * GgufReader — a real, dependency-free GGUF v2/v3 reader.
 *
 * GGUF is the model container the local assistant uses. Reading it needs no
 * native library: the header is little-endian magic + counts, then a typed
 * key/value metadata block, then a tensor table. This parses all three so the
 * app can name a model, its architecture, its quant mix and its byte cost on a
 * 4 GB device without loading the weights.
 *
 * Inference (running the tensors) is a separate concern and needs a native
 * backend; that boundary is reported, never faked (see OmegaBridge.ggufStatus).
 */
object GgufReader {

    // GGML tensor types (the quant tag on each tensor).
    private val GGML_TYPE = mapOf(
        0 to "F32", 1 to "F16", 2 to "Q4_0", 3 to "Q4_1", 6 to "Q5_0", 7 to "Q5_1",
        8 to "Q8_0", 9 to "Q8_1", 10 to "Q2_K", 11 to "Q3_K", 12 to "Q4_K", 13 to "Q5_K",
        14 to "Q6_K", 15 to "Q8_K", 16 to "IQ2_XXS", 17 to "IQ2_XS", 18 to "IQ3_XXS",
        19 to "IQ1_S", 20 to "IQ4_NL", 21 to "IQ3_S", 22 to "IQ2_S", 23 to "IQ4_XS"
    )

    data class Tensor(val name: String, val type: String, val dims: LongArray) {
        val elements: Long get() = dims.fold(1L) { a, b -> a * b }
    }

    data class Info(
        val path: String,
        val sizeBytes: Long,
        val version: Int,
        val tensorCount: Long,
        val kvCount: Long,
        val architecture: String?,
        val name: String?,
        val contextLength: Long?,
        val embeddingLength: Long?,
        val quant: String,
        val tensors: List<Tensor>
    ) {
        /** Conservative resident-cost estimate: weights + KV + scratch headroom. */
        fun estimatedRuntimeBytes(): Long {
            val weights = sizeBytes
            val ctx = contextLength ?: 4096L
            val embd = embeddingLength ?: 0L
            val kv = if (embd > 0) (ctx * embd * 2L * 2L) else (ctx * 4096L * 4L)
            return weights + kv + (64L * 1024 * 1024)
        }
    }

    fun inspect(file: File): Info {
        RandomAccessFile(file, "r").use { raf ->
            val magic = ByteArray(4).also { raf.readFully(it) }
            require(String(magic, Charsets.US_ASCII) == "GGUF") {
                "not a GGUF file (magic=${String(magic, Charsets.US_ASCII)})"
            }
            val version = readU32(raf)
            require(version in 2..3) { "unsupported GGUF version $version" }
            val tensorCount = readU64(raf)
            val kvCount = readU64(raf)

            var architecture: String? = null
            var name: String? = null
            var ctx: Long? = null
            var embd: Long? = null

            for (i in 0 until kvCount) {
                val key = readString(raf)
                val type = readU32(raf)
                when (type) {
                    8 -> { // string
                        val v = readString(raf)
                        when (key) {
                            "general.architecture" -> architecture = v
                            "general.name" -> name = v
                        }
                    }
                    4, 5 -> { val v = readU32(raf).toLong(); if (key.endsWith(".context_length")) ctx = v; if (key.endsWith(".embedding_length")) embd = v }
                    10, 11 -> { val v = readU64(raf); if (key.endsWith(".context_length")) ctx = v; if (key.endsWith(".embedding_length")) embd = v }
                    else -> skipValue(raf, type)
                }
            }

            val tensors = ArrayList<Tensor>(minOf(tensorCount, 4096).toInt())
            for (i in 0 until tensorCount) {
                val tname = readString(raf)
                val nDims = readU32(raf)
                val dims = LongArray(nDims) { readU64(raf) }
                val ttype = readU32(raf)
                readU64(raf) // offset — not needed to describe the model
                if (tensors.size < 4096) tensors.add(Tensor(tname, GGML_TYPE[ttype] ?: "T$ttype", dims))
            }

            return Info(
                path = file.absolutePath,
                sizeBytes = file.length(),
                version = version,
                tensorCount = tensorCount,
                kvCount = kvCount,
                architecture = architecture,
                name = name,
                contextLength = ctx,
                embeddingLength = embd,
                quant = dominantQuant(tensors),
                tensors = tensors
            )
        }
    }

    /** Scan a directory (non-recursive) for *.gguf and describe each. */
    fun scan(dir: File): List<Info> {
        if (!dir.isDirectory) return emptyList()
        return dir.listFiles { f -> f.isFile && f.name.endsWith(".gguf", ignoreCase = true) }
            ?.sortedBy { it.name }
            ?.mapNotNull { runCatching { inspect(it) }.getOrNull() }
            ?: emptyList()
    }

    private fun dominantQuant(tensors: List<Tensor>): String {
        if (tensors.isEmpty()) return "unknown"
        return tensors.groupingBy { it.type }.eachCount().maxByOrNull { it.value }?.key ?: "unknown"
    }

    // ---- primitive readers (little-endian, per the GGUF spec) ----

    private fun readU32(raf: RandomAccessFile): Int {
        val b = ByteArray(4).also { raf.readFully(it) }
        return ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).int
    }

    private fun readU64(raf: RandomAccessFile): Long {
        val b = ByteArray(8).also { raf.readFully(it) }
        return ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).long
    }

    private fun readString(raf: RandomAccessFile): String {
        val len = readU64(raf)
        require(len in 0..(1L shl 20)) { "implausible string length $len" }
        val b = ByteArray(len.toInt()).also { raf.readFully(it) }
        return String(b, Charsets.UTF_8)
    }

    private fun skipValue(raf: RandomAccessFile, type: Int) {
        when (type) {
            0, 1, 7 -> raf.seek(raf.filePointer + 1)
            2, 3 -> raf.seek(raf.filePointer + 2)
            4, 5, 6 -> raf.seek(raf.filePointer + 4)
            10, 11, 12 -> raf.seek(raf.filePointer + 8)
            8 -> { val n = readU64(raf); raf.seek(raf.filePointer + n) }
            9 -> { // array
                val elemType = readU32(raf)
                val count = readU64(raf)
                val fixed = when (elemType) {
                    0, 1, 7 -> 1; 2, 3 -> 2; 4, 5, 6 -> 4; 10, 11, 12 -> 8; else -> 0
                }
                if (elemType == 8) {
                    for (i in 0 until count) { val n = readU64(raf); raf.seek(raf.filePointer + n) }
                } else if (fixed > 0) {
                    raf.seek(raf.filePointer + fixed * count)
                } else {
                    for (i in 0 until count) skipValue(raf, elemType)
                }
            }
            else -> error("unknown GGUF value type $type")
        }
    }
}
