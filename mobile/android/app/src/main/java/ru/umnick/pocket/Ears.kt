package ru.umnick.pocket

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService
import java.util.Locale

/**
 * Слух (S-24.5, ADR-0050): Vosk офлайн. Пока не позвали — распознаватель с узкой грамматикой
 * (только имя и «[unk]»), это дёшево для батареи. Услышал «Умник» — полная диктовка на одну фразу.
 * Команды: «запиши …», «прочитай заметки»; одно имя → следующая фраза — заметка (как ADR-0040, 8 с).
 */
class Ears(
    private val context: Context,
    private val notebook: Notebook,
    private val stage: StageView,
) : RecognitionListener {
    private val main = Handler(Looper.getMainLooper())
    private var model: Model? = null
    private var service: SpeechService? = null
    private var dictating = false
    private var tts: TextToSpeech? = null

    fun start() {
        tts = TextToSpeech(context) { tts?.language = Locale("ru") }
        StorageService.unpack(context, "model", "model", { loaded ->
            model = loaded
            listenForName()
        }, { error -> stage.say("Не слышу: нет модели речи (${error.message})", "sad") })
    }

    fun stop() {
        service?.shutdown()
        tts?.shutdown()
    }

    private fun listenForName() {
        dictating = false
        restart(Recognizer(model, RATE, NAME_GRAMMAR))
    }

    private fun listenForDictation() {
        dictating = true
        restart(Recognizer(model, RATE))
        main.postDelayed({ if (dictating) listenForName() }, FOLLOW_UP_MS)
    }

    private fun restart(recognizer: Recognizer) {
        service?.shutdown()
        service = SpeechService(recognizer, RATE).also { it.startListening(this) }
    }

    override fun onResult(hypothesis: String) {
        val text = JSONObject(hypothesis).optString("text").trim().lowercase()
        if (text.isEmpty()) return
        main.post { if (dictating) onDictation(text) else onNameHeard(text) }
    }

    private fun onNameHeard(text: String) {
        if (NAMES.none { text.contains(it) }) return
        stage.attend()
        listenForDictation()
    }

    private fun onDictation(text: String) {
        val request = Commands.stripName(text)
        if (request.isEmpty()) return
        when (val command = Commands.parse(request)) {
            is Commands.Command.Read -> readNotes()
            is Commands.Command.Write -> save(command.text)
        }
        listenForName()
    }

    private fun save(text: String) {
        notebook.add(text)
        val reply = stage.phrases.pick("saved") ?: "Записал."
        stage.say("$reply «$text»", "happy")
        speak(reply)
    }

    private fun readNotes() {
        val last = notebook.all().takeLast(READ_LIMIT).map { it.text }
        val reply = if (last.isEmpty()) stage.phrases.pick("empty") ?: "Блокнот пуст." else "Заметки: " + last.joinToString("; ")
        stage.say(reply, "thinking", 9000)
        speak(reply)
    }

    private fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "umnick")
    }

    override fun onPartialResult(hypothesis: String) = Unit
    override fun onFinalResult(hypothesis: String) = onResult(hypothesis)
    override fun onError(exception: Exception) = main.post { stage.say("Слух сломался: ${exception.message}", "sad") }.let { }
    override fun onTimeout() = listenForName()

    private companion object {
        const val RATE = 16000f
        const val FOLLOW_UP_MS = 8000L
        const val READ_LIMIT = 5
        val NAMES = listOf("умник", "умничка")
        const val NAME_GRAMMAR = "[\"умник\", \"умничка\", \"[unk]\"]"
    }
}
