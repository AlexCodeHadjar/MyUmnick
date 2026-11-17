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
class Pack(context: Context) {
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
    fun frame(pose: String, step: Int, blink: Boolean): Bitmap {
        val base = resolve(pose)
        if (blink) frames["${base}_blink"]?.let { return it }
        val cycle = listOf(base) + (1..4).map { "${base}_$it" }.filter { it in frames }
        return frames.getValue(cycle[step % cycle.size])
    }

    fun head(emotion: String): Bitmap? = frames["head_$emotion"] ?: frames["head"]

    private fun resolve(pose: String): String =
        (listOf(pose) + (FALLBACK[pose] ?: emptyList()) + "stand").first { it in frames }

    companion object {
        private val FALLBACK = mapOf(
            "walk" to listOf("stand"),
            "sleep" to listOf("laydown", "sit_edge"),
            "laydown" to listOf("sit_edge"),
            "held" to listOf("float"),
            "float" to listOf("held"),
            "dizzy" to listOf("float"),
            "poke" to listOf("lean_side"),
        )
    }
}
