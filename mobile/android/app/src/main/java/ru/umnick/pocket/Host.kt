package ru.umnick.pocket

import android.app.Activity
import android.view.View
import android.view.WindowManager

/**
 * Где живёт окно спутника: оверлей поверх приложений или окно на экране блокировки. Оверлей
 * (`TYPE_APPLICATION_OVERLAY`) Android поверх блокировки не рисует — там нужна активность с
 * `showWhenLocked` (`LockActivity`), её окно двигаем так же, по `x`/`y`.
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

/** Окно активности размером с персонажа: остальной экран блокировки остаётся рабочим. */
class LockHost(private val activity: Activity) : Host {
    override fun add(view: View, params: WindowManager.LayoutParams) {
        activity.setContentView(view)
        move(view, params)
    }

    override fun move(view: View, params: WindowManager.LayoutParams) {
        val attrs = activity.window.attributes
        attrs.width = params.width
        attrs.height = params.height
        attrs.x = params.x
        attrs.y = params.y
        attrs.gravity = params.gravity
        activity.window.attributes = attrs
    }

    override fun remove(view: View) = Unit
}
