package ru.umnick.pocket

import android.content.Context
import java.util.Calendar

/**
 * Настроение (порт `ui/src/features/companion/mood.ts`, BEHAVIOR §2): бодрость и радость 0…1, меняются
 * медленно и хранятся между запусками; за 8 ч без запуска возвращаются к среднему. От настроения зависят
 * позы (уставший лежит, весёлый танцует) и лицо, которое видно всё время.
 */
class Mood(context: Context) {
    private val prefs = context.getSharedPreferences("mood", 0)
    var energy = MIDDLE
        private set
    var joy = MIDDLE
        private set

    init {
        val age = System.currentTimeMillis() - prefs.getLong("at", 0)
        if (age < RESET_MS) {
            energy = prefs.getFloat("energy", MIDDLE)
            joy = prefs.getFloat("joy", MIDDLE)
        }
    }

    enum class Event(val energy: Float, val joy: Float) {
        PET(0.02f, 0.05f), POKE(0.03f, -0.02f), SHAKE(0.05f, -0.15f), THROW(0.04f, -0.05f),
        TALK(0.01f, 0.04f), NOTE(0.01f, 0.06f), WAKE(0.08f, 0.02f),
    }

    fun nudge(event: Event) {
        energy = (energy + event.energy).coerceIn(0f, 1f)
        joy = (joy + event.joy).coerceIn(0f, 1f)
        save()
    }

    /** Течение времени: ночью бодрость падает, утром растёт; долгий простой тянет радость вниз. */
    fun drift(seconds: Float, idleSeconds: Float) {
        val minutes = seconds / 60f
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        val night = hour >= 23 || hour < 6
        val morning = hour in 6..10
        energy = (energy + (if (night) -0.02f else if (morning) 0.01f else 0f) * minutes).coerceIn(0f, 1f)
        val toward = if (idleSeconds > 600) 0.3f else MIDDLE
        joy = (joy + (toward - joy) * minOf(1f, 0.01f * minutes)).coerceIn(0f, 1f)
    }

    /** Лицо по настроению — `head_<face>` из пакета. */
    fun face(): String = when {
        joy < 0.3f -> "sad"
        energy < 0.25f -> "blink"
        joy > 0.8f -> "happy"
        else -> "happy"
    }

    val tired: Boolean get() = energy < 0.3f
    val cheerful: Boolean get() = joy > 0.75f && energy > 0.5f

    fun save() {
        prefs.edit().putFloat("energy", energy).putFloat("joy", joy).putLong("at", System.currentTimeMillis()).apply()
    }

    private companion object {
        const val MIDDLE = 0.6f
        const val RESET_MS = 8 * 3600 * 1000L
    }
}
