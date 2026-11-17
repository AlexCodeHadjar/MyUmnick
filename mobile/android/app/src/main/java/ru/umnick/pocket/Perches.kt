package ru.umnick.pocket

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo

/**
 * Опоры на экране телефона — аналог окон и значков рабочего стола на ПК (`anchors.ts`, BEHAVIOR §4, §6):
 * рамки иконок, кнопок и карточек активного окна с их короткой подписью («YouTube») и имя активного
 * приложения (T12). Узнать это можно только через службу специальных возможностей; содержимое экрана
 * (тексты переписки и т.п.) не читаем и не храним — только рамки, подписи элементов до 24 знаков и пакет.
 */
object Perches {
    data class Spot(val box: Rect, val label: String)

    @Volatile var spots: List<Spot> = emptyList()
        private set

    /** Растёт при смене экрана: листнули страницу, открыли приложение. Сидящий на иконке спрыгивает. */
    @Volatile var scene = 0
        private set

    /** Пакет активного приложения (`com.google.android.youtube`) и когда он сменился. */
    @Volatile var app = ""
        private set
    @Volatile var appSince = 0L
        private set

    /** Рамка экранной клавиатуры или `null` — спрятана (триггер «не мешать», просьба пользователя). */
    @Volatile var keyboard: Rect? = null
        private set

    /** Где последний раз нажали на элемент экрана (центр его рамки) и когда — персонаж смотрит туда. */
    @Volatile var touchX = 0
        private set
    @Volatile var touchAt = 0L
        private set

    fun touched(x: Int) {
        touchX = x
        touchAt = SystemClock.uptimeMillis()
        Trace.event("touch:$x")
    }

    fun keyboardChanged(box: Rect?) {
        keyboard = box
    }

    fun update(found: List<Spot>) {
        spots = found
    }

    fun sceneChanged() {
        scene++
    }

    fun appChanged(name: String) {
        if (name == app || name.isEmpty()) return
        app = name
        appSince = SystemClock.uptimeMillis()
    }

    /** Случайная опора, на которую персонаж поместится, или `null`. */
    fun pick(screenWidth: Int): Spot? =
        spots.filter { it.box.width() in MIN_WIDTH..(screenWidth * 9 / 10) && it.box.top > MIN_TOP }.randomOrNull()

    fun stillThere(spot: Spot): Boolean =
        spots.any { abs(it.box.top - spot.box.top) < 8 && abs(it.box.centerX() - spot.box.centerX()) < 8 }

    private fun abs(value: Int) = if (value < 0) -value else value

    private const val MIN_WIDTH = 90
    private const val MIN_TOP = 300
}

class PerchService : AccessibilityService() {
    private var lastScan = 0L

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val type = event.eventType
        // Касание чужого приложения система не сообщает, но нажатие на элемент — да, с его рамкой.
        if (type == AccessibilityEvent.TYPE_VIEW_CLICKED || type == AccessibilityEvent.TYPE_VIEW_LONG_CLICKED) {
            event.source?.let { node -> Perches.touched(Rect().also(node::getBoundsInScreen).centerX()) }
        }
        if (type == AccessibilityEvent.TYPE_WINDOWS_CHANGED || type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            checkKeyboard()
        }
        // Свайп страницы рабочего стола и смена окна — иконки под ним другие, даже если клетки те же.
        if (type == AccessibilityEvent.TYPE_VIEW_SCROLLED || type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            Perches.sceneChanged()
        }
        if (type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED && event.packageName != packageName) {
            Perches.appChanged(event.packageName?.toString().orEmpty())
        }
        val now = SystemClock.uptimeMillis()
        if (now - lastScan < SCAN_EVERY_MS) return
        lastScan = now
        val root = rootInActiveWindow ?: return
        val found = mutableListOf<Perches.Spot>()
        collect(root, found, 0)
        Perches.update(found)
    }

    /** Окно клавиатуры среди окон экрана (нужен flagRetrieveInteractiveWindows). */
    private fun checkKeyboard() {
        val all = windows
        val ime = all.firstOrNull { it.type == AccessibilityWindowInfo.TYPE_INPUT_METHOD }
        val shown = ime != null
        if (shown != (Perches.keyboard != null)) Trace.event("keyboard-window:$shown of ${all.size}")
        Perches.keyboardChanged(ime?.let { Rect().also(it::getBoundsInScreen) }?.takeIf { it.height() > 0 })
    }

    private fun collect(node: AccessibilityNodeInfo, out: MutableList<Perches.Spot>, depth: Int) {
        if (depth > MAX_DEPTH || out.size >= MAX_SPOTS) return
        if (node.isVisibleToUser && (node.isClickable || node.contentDescription != null)) {
            val box = Rect().also { node.getBoundsInScreen(it) }
            if (box.height() in MIN_HEIGHT..MAX_HEIGHT) out += Perches.Spot(box, label(node))
        }
        for (i in 0 until node.childCount) node.getChild(i)?.let { collect(it, out, depth + 1) }
    }

    /** Короткая подпись элемента (имя иконки): длинный текст — это содержимое, его не берём. */
    private fun label(node: AccessibilityNodeInfo): String {
        val text = (node.contentDescription ?: node.text)?.toString()?.trim().orEmpty()
        return if (text.length in 1..MAX_LABEL) text else ""
    }

    override fun onInterrupt() = Unit

    private companion object {
        const val SCAN_EVERY_MS = 700L
        const val MAX_DEPTH = 25
        const val MAX_SPOTS = 80
        const val MIN_HEIGHT = 60
        const val MAX_HEIGHT = 900
        const val MAX_LABEL = 24
    }
}
