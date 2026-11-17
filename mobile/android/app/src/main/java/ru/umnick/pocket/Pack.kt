package ru.umnick.pocket

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import org.json.JSONArray
import org.json.JSONObject

/**
 * Пакет персонажа из assets (`ui/scripts/export-mobile-pack.ts`): кадры поз `поза`, `поза_1…_4`,
 * `поза_blink` и фразы. Нет позы — цепочка замен, как `FALLBACK` в `ui/src/features/companion/pack.ts`.
 */
class Pack private constructor(context: Context) {
    private val frames: Map<String, Bitmap>
    val phrases: JSONObject

    init {
        val assets = context.assets
        val names = JSONArray(assets.open("character/index.json").bufferedReader().readText())
        val options = BitmapFactory.Options().apply { inSampleSize = 2 }
        frames = (0 until names.length()).associate { i ->
            val name = names.getString(i)
            name to assets.open("character/$name.webp").use { BitmapFactory.decodeStream(it, null, options)!! }
        }
        phrases = JSONObject(assets.open("character/phrases.json").bufferedReader().readText())
    }

    /** Кадр позы: `step` — номер кадра цикла, `blink` — моргнуть, если есть такой кадр. */
    fun frame(pose: String, step: Int, blink: Boolean, fallback: String = pose): Bitmap {
        val base = if (has(pose)) pose else resolve(fallback)
        if (blink) frames["${base}_blink"]?.let { return it }
        // У части поз нет базового кадра, только `_1…_4` (например, dance).
        val cycle = (listOf(base) + (1..4).map { "${base}_$it" }).filter { it in frames }
        return frames.getValue(cycle[step % cycle.size])
    }

    fun head(emotion: String): Bitmap? = frames["head_$emotion"] ?: frames["head"]

    private fun has(pose: String) = pose in frames || "${pose}_1" in frames

    private fun resolve(pose: String): String =
        (listOf(pose) + (FALLBACK[pose] ?: emptyList()) + "stand").first { it in frames || "${it}_1" in frames }

    companion object {
        @Volatile private var shared: Pack? = null

        /** Один пакет на процесс: оверлей и окно блокировки не грузят 122 кадра дважды. */
        fun get(context: Context): Pack =
            shared ?: synchronized(this) { shared ?: Pack(context.applicationContext).also { shared = it } }

        private val FALLBACK = mapOf(
            "walk" to listOf("stand"),
            "sleep" to listOf("laydown", "sit_edge"),
            "laydown" to listOf("sit_edge"),
            "held" to listOf("float"),
            "float" to listOf("held"),
            "dizzy" to listOf("float"),
            "poke" to listOf("lean_side"),
            "wave" to listOf("stand"),
            "yawn" to listOf("sit_edge"),
            "dance" to listOf("stand"),
            "watch" to listOf("sit_corner", "sit_edge"),
            "sing" to listOf("radio_idle"),
            "radio_idle" to listOf("stand"),
            "climb" to listOf("hang_side", "held"),
            "peek" to listOf("lean_side"),
            "perch_corner" to listOf("sit_edge"),
            "sit_corner" to listOf("laydown", "sit_edge"),
        )
    }
}
