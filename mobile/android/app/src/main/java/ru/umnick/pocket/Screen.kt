package ru.umnick.pocket

import android.content.Context
import android.os.Build
import android.view.WindowInsets
import android.view.WindowManager

/**
 * Размер экрана сейчас — в координатах экрана, как рамки иконок от службы спец. возможностей.
 * `displayMetrics` контекста службы после поворота может остаться старым (персонаж «пропадал» за край),
 * поэтому спрашиваем `currentWindowMetrics` при каждом обращении.
 */
data class Screen(val widthPixels: Int, val heightPixels: Int, val bottomInset: Int) {
    companion object {
        fun of(context: Context): Screen {
            val windows = context.getSystemService(WindowManager::class.java)
            if (Build.VERSION.SDK_INT < 30) {
                val metrics = context.resources.displayMetrics
                return Screen(metrics.widthPixels, metrics.heightPixels, 0)
            }
            val window = windows.currentWindowMetrics
            val nav = window.windowInsets.getInsets(WindowInsets.Type.navigationBars()).bottom
            return Screen(window.bounds.width(), window.bounds.height(), nav)
        }
    }
}
