package ru.umnick.pocket

import android.util.Log

/**
 * Служебный журнал поведения (logcat, метка `UmNick`): смена позы и режима, реплики, касания, триггеры.
 * По нему считается статистика наблюдения (скрипт наблюдения на эмуляторе, вне репозитория). Только события — без содержимого экрана.
 */
object Trace {
    private const val TAG = "UmNick"

    fun state(mode: String, pose: String, x: Int, y: Int) = Log.i(TAG, "STATE $mode $pose $x $y")

    fun say(text: String) = Log.i(TAG, "SAY $text")

    fun event(name: String) = Log.i(TAG, "EVENT $name")
}
