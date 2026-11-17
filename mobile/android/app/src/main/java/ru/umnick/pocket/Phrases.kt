package ru.umnick.pocket

import org.json.JSONObject
import java.util.Calendar
import kotlin.random.Random

/** Выбор реплики без повтора последних 12 (как `phrases/index.ts` на ПК, BEHAVIOR §7). */
class Phrases(private val all: JSONObject) {
    private val recent = ArrayDeque<String>()

    fun pick(section: String): String? {
        // «pet.раздел» — фразы поглаживания, остальное — реплики болванчика верхнего уровня.
        val list = (if (section.startsWith("pet.")) all.getJSONObject("pet").optJSONArray(section.removePrefix("pet."))
        else all.optJSONArray(section)) ?: return null
        val options = (0 until list.length()).map { list.getString(it) }
        val fresh = options.filter { it !in recent }.ifEmpty { options }
        val choice = fresh[Random.nextInt(fresh.size)]
        recent.addLast(choice)
        if (recent.size > MEMORY) recent.removeFirst()
        return choice
    }

    /** Раздел поглаживания (`pet.…`) по номеру клика серии и состоянию; `null` — на этом клике молчит. */
    fun petSection(count: Int, sleeping: Boolean, shaken: Boolean): String? = petKey(count, sleeping, shaken)?.let { "pet.$it" }

    private fun petKey(count: Int, sleeping: Boolean, shaken: Boolean): String? {
        val section = SPOKEN[count] ?: return null
        if (section != "first") return section
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        return when {
            sleeping -> "sleepy"
            shaken -> "held"
            hour in 5..10 && Random.nextInt(3) == 0 -> "morning"
            (hour >= 23 || hour < 4) && Random.nextInt(3) == 0 -> "night"
            else -> "first"
        }
    }

    companion object {
        private const val MEMORY = 12
        private val SPOKEN = mapOf(1 to "first", 3 to "more", 6 to "lots", 10 to "overload", 15 to "max")
    }
}
