package ru.umnick.pocket

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService
import java.util.Locale

/**
 * Слух (S-24.5, ADR-0050): Vosk офлайн, **один** распознаватель на всё время работы. Перезапуск
 * `SpeechService` на каждое имя ронял приложение: старый `AudioRecord` ещё держал микрофон, новый
 * не открывался (исключение в конструкторе). Теперь имя ищется в тексте полной фразы:
 * «Умник, запиши молоко» — сразу заметка; одно «Умник» — следующая фраза в течение 8 с (как ADR-0040).
 */
class Ears(
    private val context: Context,
    private val notebook: Notebook,
    private val fallback: StageView,
) : RecognitionListener {
    /** Говорим через того спутника, что на виду: на экране блокировки — через окно блокировки. */
    private val stage: StageView get() = Stages.current() ?: fallback
    private val main = Handler(Looper.getMainLooper())
    private var model: Model? = null
    private var service: SpeechService? = null
    private var waitUntil = 0L
    private var tts: TextToSpeech? = null

    fun start() {
        tts = TextToSpeech(context) { tts?.language = Locale("ru") }
        StorageService.unpack(context, "model", "model", ::listen) { error ->
            CrashLog.write(context, "vosk unpack", error)
            stage.say("Не слышу: нет модели речи", "sad")
        }
    }

    fun stop() {
        service?.shutdown()
        model?.close()
        tts?.shutdown()
    }

    private fun listen(loaded: Model) {
        model = loaded
        try {
            service = SpeechService(Recognizer(loaded, RATE), RATE).also { it.startListening(this) }
        } catch (error: Exception) {
            CrashLog.write(context, "mic", error)
            stage.say("Микрофон занят другим приложением", "sad")
        }
    }

    override fun onResult(hypothesis: String) {
        val text = runCatching { JSONObject(hypothesis).optString("text") }.getOrDefault("").trim().lowercase()
        if (text.isNotEmpty()) main.post { safely { hear(text) } }
    }

    private fun hear(text: String) {
        val named = Commands.hasName(text)
        val waiting = SystemClock.uptimeMillis() < waitUntil
        if (!named && !waiting) return
        val request = Commands.stripName(text)
        if (request.isEmpty()) {
            waitUntil = SystemClock.uptimeMillis() + FOLLOW_UP_MS
            stage.attend()
            return
        }
        waitUntil = 0
        when (val command = Commands.parse(request)) {
            is Commands.Command.Read -> readNotes()
            is Commands.Command.Write -> save(command.text)
        }
    }

    private fun save(text: String) {
        notebook.add(text)
        stage.noteSaved()
        val reply = stage.phrases.pick("saved") ?: "Записал."
        stage.say("$reply «$text»", "happy")
        speak(reply)
    }

    private fun readNotes() {
        val last = notebook.all().takeLast(READ_LIMIT).map { it.text }
        val reply = if (last.isEmpty()) stage.phrases.pick("empty") ?: "Блокнот пуст."
        else "Заметки: " + last.joinToString("; ")
        stage.say(reply, "thinking", 9000)
        speak(reply)
    }

    private fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "umnick")
    }

    private fun safely(block: () -> Unit) {
        try {
            block()
        } catch (error: Exception) {
            CrashLog.write(context, "ears", error)
            stage.say("Ой, что-то сломалось, но я тут.", "sad")
        }
    }

    override fun onPartialResult(hypothesis: String) = Unit
    override fun onFinalResult(hypothesis: String) = onResult(hypothesis)
    override fun onError(exception: Exception) {
        CrashLog.write(context, "vosk", exception)
    }
    override fun onTimeout() = Unit

    private companion object {
        const val RATE = 16000f
        const val FOLLOW_UP_MS = 8000L
        const val READ_LIMIT = 5
    }
}
