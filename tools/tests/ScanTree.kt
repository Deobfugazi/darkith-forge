import com.darkith.transliaison.core.CommentScan
import java.io.File

fun main(args: Array<String>) {
    var clean = 0; var damaged = 0
    for (root in args) {
        File(root).walkTopDown()
            .filter { it.isFile && it.name.endsWith(".kt") }
            .forEach { f ->
                val d = CommentScan.scan(f.readText())
                if (d == null) clean++ else { damaged++; println("DAMAGED  ${f.path}  -> $d") }
            }
    }
    println("---")
    println("clean=$clean  damaged=$damaged")
    if (damaged > 0) kotlin.system.exitProcess(1)
}
