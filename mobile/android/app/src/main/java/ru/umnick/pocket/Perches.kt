package ru.umnick.pocket

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Опоры на экране телефона — аналог окон и значков рабочего стола на ПК (`anchors.ts`): верхние края
 * иконок, кнопок и карточек активного окна. Узнать их можно только через службу специальных
 * возможностей; текст и содержимое не читаем и не храним — только прямоугольники.
 */
object Perches {
    @Volatile var spots: List<Rect> = emptyList()
        private set

    fun update(found: List<Rect>) {
        spots = found
    }

    /** Случайная опора, на которую персонаж поместится, или `null`. */
    fun pick(screenWidth: Int): Rect? =
        spots.filter { it.width() in MIN_WIDTH..(screenWidth * 9 / 10) && it.top > MIN_TOP }.randomOrNull()

    fun stillThere(spot: Rect): Boolean = spots.any { abs(it.top - spot.top) < 8 && abs(it.centerX() - spot.centerX()) < 8 }

    private fun abs(value: Int) = if (value < 0) -value else value

    private const val MIN_WIDTH = 90
    private const val MIN_TOP = 300
}

class PerchService : AccessibilityService() {
    private var lastScan = 0L

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val now = SystemClock.uptimeMillis()
        if (now - lastScan < SCAN_EVERY_MS) return
        lastScan = now
        val root = rootInActiveWindow ?: return
        val found = mutableListOf<Rect>()
        collect(root, found, 0)
        Perches.update(found.take(MAX_SPOTS))
    }

    private fun collect(node: AccessibilityNodeInfo, out: MutableList<Rect>, depth: Int) {
        if (depth > MAX_DEPTH || out.size >= MAX_SPOTS) return
        if (node.isVisibleToUser && (node.isClickable || node.contentDescription != null)) {
            val box = Rect().also { node.getBoundsInScreen(it) }
            if (box.height() in MIN_HEIGHT..MAX_HEIGHT) out += box
        }
        for (i in 0 until node.childCount) node.getChild(i)?.let { collect(it, out, depth + 1) }
    }

    override fun onInterrupt() = Unit

    private companion object {
        const val SCAN_EVERY_MS = 700L
        const val MAX_DEPTH = 25
        const val MAX_SPOTS = 80
        const val MIN_HEIGHT = 60
        const val MAX_HEIGHT = 900
    }
}
