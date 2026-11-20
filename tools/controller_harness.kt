// Behavioural harness for AutophagicAllocator, executed by tools/controller_gate.py.
// It compiles and runs the REAL controller, not a model of it: a Python replica of the law
// would have agreed with the buggy version just as happily as with the fixed one.
import com.darkith.transliaison.core.AutophagicAllocator

data class Case(val freeMb: Long, val gpuMb: Long, val cpu: Double, val frame: Double, val label: String)

fun main() {
    val a = AutophagicAllocator()
    fun step(f: Long, g: Long, c: Double, fr: Double) =
        a.tick(f * 1_000_000L, g * 1_000_000L, c, fr)

    // 1. It must TRACK the affordable ceiling, not rail. A controller that only ever emits
    //    65536 or 524288 is a constant, whatever its formulas say.
    val probes = listOf(
        Case(8L, 1L, 0.30, 16.6, "low-ram"),
        Case(16L, 1L, 0.30, 16.6, "mid-ram"),
        Case(1_200L, 20L, 0.30, 16.6, "ample-ram")
    )
    var interior = 0
    for (p in probes) {
        var r = step(p.freeMb, p.gpuMb, p.cpu, p.frame)
        repeat(400) { r = step(p.freeMb, p.gpuMb, p.cpu, p.frame) }
        val mBudget = 0.45 * (p.freeMb * 1_000_000.0) * (1.0 - 0.08 * p.cpu)
        val affordable = mBudget / 24.0
        val expected = affordable.coerceIn(65_536.0, 524_288.0)
        val errPct = kotlin.math.abs(r.vertexBudget - expected) / expected * 100.0
        println("TRACK ${p.label} free=${p.freeMb}MB vK=${r.vertexBudget} expected=${expected.toLong()} err=${"%.2f".format(errPct)}%")
        if (errPct <= 2.0) interior++
    }
    println(if (interior >= 2) "RESULT track=PASS" else "RESULT track=FAIL")

    // 2. The resolution scale must RECOVER. A bounded multiplicative integrator on a bounded
    //    state can only descend; it ratcheted to the 0.5 floor and stayed there at idle.
    val b = AutophagicAllocator()
    var s = b.tick(1_200_000_000L, 20_000_000L, 0.30, 16.6).resolutionScale
    repeat(600) { s = b.tick(1_200_000_000L, 20_000_000L, 0.30, 16.6).resolutionScale }
    println("SCALE idle_sK=${"%.3f".format(s)}")
    println(if (s >= 0.99) "RESULT scale=PASS" else "RESULT scale=FAIL")

    // 3. Documented invariants, under adversarial input including a stalled clock and huge dt.
    val c = AutophagicAllocator()
    var ok = true
    for (t in 0 until 4000) {
        val free = (t * 7919L) % 2_000_000_000L
        val gpu = (t * 104729L) % 300_000_000L
        val cpu = (t % 101) / 100.0
        val frame = if (t % 17 == 0) 999.0 else 16.6 + (t % 40)
        val r = c.tick(free, gpu, cpu, frame)
        if (r.vertexBudget < 65_536L || r.vertexBudget > 524_288L) { ok = false; println("VIOLATION bound vK=${r.vertexBudget}") }
        if (!r.resolutionScale.isFinite() || r.resolutionScale < 0.5 || r.resolutionScale > 1.0) { ok = false; println("VIOLATION scale") }
        if (!r.memoryResidual.isFinite() || !r.budgetCeiling.isFinite()) { ok = false; println("VIOLATION nonfinite") }
        if (r.gpuConcurrency < 1 || r.gpuConcurrency > 8) { ok = false; println("VIOLATION concurrency") }
    }
    println(if (ok) "RESULT invariants=PASS" else "RESULT invariants=FAIL")
}
