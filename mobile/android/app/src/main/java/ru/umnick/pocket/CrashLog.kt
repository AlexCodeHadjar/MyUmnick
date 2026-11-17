package ru.umnick.pocket

import android.content.Context
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.time.OffsetDateTime

/**
 * Журнал сбоев без отладки по USB: пишется во внутреннюю память и копируется в папку обмена
 * (`Documents/UmNick/crash.txt`), откуда его видно с ПК по MTP.
 */
object CrashLog {
    private const val LIMIT = 64_000

    fun install(context: Context) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            write(context.applicationContext, "uncaught in ${thread.name}", error)
            previous?.uncaughtException(thread, error)
        }
    }

    fun write(context: Context, where: String, error: Throwable) {
        runCatching {
            val trace = StringWriter().also { error.printStackTrace(PrintWriter(it)) }
            val file = File(context.filesDir, "crash.txt")
            val old = if (file.exists()) file.readText().takeLast(LIMIT) else ""
            file.writeText(old + "=== ${OffsetDateTime.now()} $where\n$trace\n")
            NotesFolder.writeText(context, "crash.txt", file.readText())
        }
    }
}
