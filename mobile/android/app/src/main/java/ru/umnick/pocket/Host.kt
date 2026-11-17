package ru.umnick.pocket

import android.view.View
import android.view.WindowManager

/**
 * Где живёт окно спутника. Сейчас — только оверлей поверх приложений. Показ на экране блокировки
 * (окно `showWhenLocked`) убран по решению пользователя 2026-11-17: оно перекрывало блокировку,
 * мешало паролю и отпечатку; правильный путь там — живые обои.
 */
interface Host {
    fun add(view: View, params: WindowManager.LayoutParams)
    fun move(view: View, params: WindowManager.LayoutParams)
    fun remove(view: View)
}

class OverlayHost(private val windows: WindowManager) : Host {
    override fun add(view: View, params: WindowManager.LayoutParams) = windows.addView(view, params)
    override fun move(view: View, params: WindowManager.LayoutParams) = windows.updateViewLayout(view, params)
    override fun remove(view: View) = windows.removeView(view)
}

/** Спутник на виду: слух говорит через него. */
object Stages {
    var overlay: StageView? = null

    fun current(): StageView? = overlay
}
