package ru.umnick.pocket

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.time.OffsetDateTime
import java.util.UUID

/**
 * Блокнот (S-24.5): одна заметка — строка JSON в `notes.jsonl` (формат — `docs/phone-sync.md`).
 * Основная копия — во внутренней памяти; `NotesFolder` зеркалит её в общую папку для ПК.
 */
class Notebook(private val context: Context) {
    private val file = File(context.filesDir, "notes.jsonl")

    data class Note(val id: String, val text: String, val created: String, val origin: String) {
        fun toJson(): String = JSONObject()
            .put("id", id).put("text", text).put("created", created).put("origin", origin).toString()

        companion object {
            fun parse(line: String): Note? = runCatching {
                val o = JSONObject(line)
                Note(o.getString("id"), o.getString("text"), o.getString("created"), o.optString("origin", "phone"))
            }.getOrNull()
        }
    }

    @Synchronized
    fun all(): List<Note> =
        if (file.exists()) file.readLines().mapNotNull(Note::parse) else emptyList()

    @Synchronized
    fun add(text: String, origin: String = "phone"): Note {
        val note = Note(UUID.randomUUID().toString(), text.trim(), OffsetDateTime.now().toString(), origin)
        file.appendText(note.toJson() + "\n")
        NotesFolder.mirror(context, this)
        return note
    }

    /** Заметки с ПК (`from_pc.jsonl` или живой канал): берём только незнакомые `id`. */
    @Synchronized
    fun merge(incoming: List<Note>): Int {
        val known = all().map { it.id }.toSet()
        val fresh = incoming.filter { it.id !in known }
        if (fresh.isNotEmpty()) file.appendText(fresh.joinToString("") { it.toJson() + "\n" })
        return fresh.size
    }
}
