package ru.umnick.pocket

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.RectF
import android.os.SystemClock
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.Gravity
import android.view.MotionEvent
import android.view.VelocityTracker
import android.view.View
import android.view.WindowManager
import kotlin.math.abs
import kotlin.math.sin

/**
 * Спутник поверх экрана телефона (S-24.3, S-24.4). Окно размером с персонажа (остальной экран не
 * перехватывает касания) ходит по низу экрана. Поведение — упрощённый `brain.ts` ПК без LLM:
 * гуляет, садится, ложится, засыпает; тап — поглаживание сериями, долгий тап — тык, перетаскивание — held,
 * отпустил — падает. Перетащили за правый край — перебежка на ПК (S-24.11, `onEdgeExit`).
 */
class StageView(context: Context, private val host: Host) : View(context) {
    private val pack = Pack.get(context)
    val phrases = Phrases(pack.phrases)
    private val params = WindowManager.LayoutParams(
        WIDTH, HEIGHT, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        PixelFormat.TRANSLUCENT,
    ).apply { gravity = Gravity.TOP or Gravity.START }
    private val screen get() = resources.displayMetrics
    private val floor get() = screen.heightPixels - HEIGHT

    private var mode = Mode.IDLE
    private var modeUntil = 0L
    private var targetX = 0
    private var vy = 0f
    private var vx = 0f
    private var perch: Rect? = null
    private var jumpFrom = 0 to 0
    private var jumpTo = 0 to 0
    private var jumpStart = 0L
    private var grabX = 0f
    private var grabY = 0f
    private var velocity: VelocityTracker? = null
    private var facingLeft = false
    private var lastTouch = SystemClock.uptimeMillis()
    private var shakenAt = 0L
    private var bubble: String? = null
    private var bubbleUntil = 0L
    private var emotion = "happy"
    private var downAt = 0L
    private var downX = 0f
    private var downY = 0f
    private var petCount = 0
    private var lastPet = 0L

    /** Перебежка на ПК: вызывается, когда персонажа утащили за правый край (S-24.11). */
    var onEdgeExit: (() -> Boolean)? = null

    fun attach() {
        params.x = screen.widthPixels - WIDTH
        params.y = floor
        host.add(this, params)
        setMode(Mode.WAVE, 2500)
        say(phrases.pick(greeting()) ?: "Привет!", "happy")
        postOnAnimation(::tick)
    }

    fun detach() = host.remove(this)

    /** Реплика в облачке над головой и эмоция на значке лица. */
    fun say(text: String, mood: String = emotion, ms: Long = 4500) {
        bubble = text
        emotion = mood
        bubbleUntil = SystemClock.uptimeMillis() + ms
        invalidate()
    }

    /** Слух услышал имя: персонаж поворачивается и «думает» (S-24.5). */
    fun attend() {
        setMode(Mode.REACT, 3000)
        say(phrases.pick("wake") ?: "Слушаю.", "thinking", 8000)
    }

    /** Встряска телефона (Shake): кружится голова. */
    fun dizzy() {
        shakenAt = SystemClock.uptimeMillis()
        setMode(Mode.DIZZY, 2500)
        say(phrases.pick("dizzy") ?: "Ой!", "surprised")
    }

    /** Персонаж прибежал с ПК: выпрыгивает из правого края. */
    fun arrive() {
        params.x = screen.widthPixels
        params.y = floor
        host.move(this, params)
        visibility = VISIBLE
        walkTo(screen.widthPixels - WIDTH * 2)
        say(phrases.pick("handoff_in") ?: "Я тут!", "happy")
    }

    private fun tick() {
        val now = SystemClock.uptimeMillis()
        when (mode) {
            Mode.WALK -> stepWalk()
            Mode.FALL -> stepFall()
            Mode.JUMP -> stepJump(now)
            Mode.CLING -> stepCling(now)
            Mode.PERCH -> if (now > modeUntil || perch?.let(Perches::stillThere) == false) drop()
            Mode.HELD, Mode.GONE -> Unit
            else -> if (now > modeUntil) decide(now)
        }
        if (bubble != null && now > bubbleUntil) bubble = null
        invalidate()
        postOnAnimation(::tick)
    }

    private fun decide(now: Long) {
        val idle = now - lastTouch
        when {
            idle > SLEEP_AFTER && mode == Mode.YAWN -> setMode(Mode.SLEEP, 60_000)
            idle > SLEEP_AFTER -> setMode(Mode.YAWN, 2500)
            Math.random() < 0.35 && Perches.pick(screen.widthPixels) != null ->
                jumpTo(Perches.pick(screen.widthPixels)!!)
            Math.random() < 0.45 -> walkTo((Math.random() * (screen.widthPixels - WIDTH)).toInt())
            Math.random() < 0.5 -> setMode(Mode.SIT, 8000 + (Math.random() * 8000).toLong())
            Math.random() < 0.5 -> setMode(Mode.LAY, 10_000)
            Math.random() < 0.15 -> setMode(Mode.DANCE, 6000)
            else -> idleRemark()
        }
    }

    private fun idleRemark() {
        setMode(Mode.IDLE, 7000)
        if (Math.random() < 0.3) phrases.pick("idle")?.let { say(it, "happy") }
    }

    private fun walkTo(x: Int) {
        targetX = x
        facingLeft = x < params.x
        setMode(Mode.WALK, 0)
    }

    private fun stepWalk() {
        val delta = targetX - params.x
        if (abs(delta) <= WALK_SPEED) return setMode(Mode.IDLE, 3000)
        params.x += if (delta > 0) WALK_SPEED else -WALK_SPEED
        host.move(this, params)
    }

    /** Полёт после броска: инерция, отскок от боков и от «пола» (затухает). */
    private fun stepFall() {
        vy += GRAVITY
        vx *= AIR_DRAG
        params.x = (params.x + vx).toInt()
        params.y = (params.y + vy).toInt()
        val right = screen.widthPixels - WIDTH
        if (params.x < 0 || params.x > right) {
            params.x = params.x.coerceIn(0, right)
            if (abs(vx) > CLING_SPEED) return cling(params.x == 0)
            vx = -vx * BOUNCE
        }
        if (params.y >= floor) land()
        host.move(this, params)
    }

    private fun land() {
        params.y = floor
        if (vy > MIN_BOUNCE) {
            vy = -vy * BOUNCE
            return
        }
        vx = 0f
        setMode(Mode.IDLE, 2000)
    }

    /** Бросили в бок экрана — цепляется за край и медленно сползает (поза hang_side). */
    private fun cling(left: Boolean) {
        facingLeft = left
        vx = 0f
        vy = 0f
        setMode(Mode.CLING, 5000 + (Math.random() * 4000).toLong())
        host.move(this, params)
    }

    private fun stepCling(now: Long) {
        if (now > modeUntil || params.y >= floor) return drop()
        params.y += 1
        host.move(this, params)
    }

    /** Прыжок на опору (иконку, кнопку): дуга за JUMP_MS, потом сидит на её верхнем крае. */
    private fun jumpTo(spot: Rect) {
        perch = spot
        jumpFrom = params.x to params.y
        jumpTo = (spot.centerX() - WIDTH / 2).coerceIn(0, screen.widthPixels - WIDTH) to
            (spot.top - HEIGHT + SEAT_FROM_BOTTOM)
        jumpStart = SystemClock.uptimeMillis()
        facingLeft = jumpTo.first < params.x
        setMode(Mode.JUMP, 0)
    }

    private fun stepJump(now: Long) {
        val t = ((now - jumpStart).toFloat() / JUMP_MS).coerceAtMost(1f)
        val arc = JUMP_HEIGHT * 4 * t * (1 - t)
        params.x = (jumpFrom.first + (jumpTo.first - jumpFrom.first) * t).toInt()
        params.y = (jumpFrom.second + (jumpTo.second - jumpFrom.second) * t - arc).toInt()
        host.move(this, params)
        if (t >= 1f) setMode(Mode.PERCH, 8000 + (Math.random() * 10_000).toLong())
    }

    /** Опора пропала (листнули экран, сменилось приложение) или надоело — падает вниз. */
    private fun drop() {
        perch = null
        vx = 0f
        vy = 0f
        setMode(Mode.FALL, 0)
    }

    /** Поворот экрана: ширина и высота меняются — возвращаем персонажа в пределы экрана. */
    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        post {
            params.x = params.x.coerceIn(0, maxOf(0, screen.widthPixels - WIDTH))
            params.y = params.y.coerceIn(0, maxOf(0, floor))
            host.move(this, params)
            if (mode != Mode.HELD && mode != Mode.GONE) drop()
        }
    }

    private fun setMode(next: Mode, ms: Long) {
        mode = next
        modeUntil = SystemClock.uptimeMillis() + ms
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // Касание мимо персонажа — не наше (на экране блокировки его ждёт LockActivity).
        if (event.actionMasked == MotionEvent.ACTION_OUTSIDE) return false
        lastTouch = SystemClock.uptimeMillis()
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> touchDown(event)
            MotionEvent.ACTION_MOVE -> touchMove(event)
            MotionEvent.ACTION_UP -> touchUp(event)
        }
        return true
    }

    private fun touchDown(event: MotionEvent) {
        downAt = event.eventTime
        downX = event.rawX
        downY = event.rawY
        // Держим за то место, где взяли, — без рывка окна под палец.
        grabX = event.rawX - params.x
        grabY = event.rawY - params.y
        velocity?.recycle()
        velocity = VelocityTracker.obtain().also { it.addMovement(event) }
    }

    private fun touchMove(event: MotionEvent) {
        if (mode == Mode.GONE) return
        if (mode != Mode.HELD && abs(event.rawX - downX) + abs(event.rawY - downY) < DRAG_SLOP) return
        velocity?.addMovement(event)
        if (mode != Mode.HELD) say(phrases.pick("thrown") ?: "Ой!", "surprised")
        setMode(Mode.HELD, 0)
        params.x = (event.rawX - grabX).toInt()
        params.y = (event.rawY - grabY).toInt()
        host.move(this, params)
        if (event.rawX > screen.widthPixels - EDGE && onEdgeExit?.invoke() == true) leave()
    }

    private fun touchUp(event: MotionEvent) {
        if (mode == Mode.GONE) return
        if (mode == Mode.HELD) return throwFrom(event)
        if (event.eventTime - downAt > LONG_PRESS) poke() else pet()
    }

    private fun throwFrom(event: MotionEvent) {
        val tracker = velocity ?: return setMode(Mode.FALL, 0)
        tracker.addMovement(event)
        tracker.computeCurrentVelocity(FRAME_UNITS, MAX_THROW)
        vx = tracker.xVelocity * THROW_POWER
        vy = tracker.yVelocity * THROW_POWER
        setMode(Mode.FALL, 0)
    }

    private fun leave() {
        say(phrases.pick("handoff_out") ?: "Бегу!", "happy", 1500)
        setMode(Mode.GONE, 0)
        visibility = INVISIBLE
    }

    /** Возврат с ПК подтверждён — спутник снова живёт здесь. */
    fun resume() {
        if (mode == Mode.GONE) arrive()
    }

    private fun poke() {
        setMode(Mode.POKE, 1500)
        say(phrases.pick("poke") ?: "Эй!", "surprised")
    }

    private fun pet() {
        val now = SystemClock.uptimeMillis()
        petCount = if (now - lastPet < PET_SERIES) petCount + 1 else 1
        lastPet = now
        val sleeping = mode == Mode.SLEEP || mode == Mode.LAY
        val shaken = now - shakenAt < SHAKE_MEMORY
        setMode(Mode.PET, 1800)
        val section = phrases.petSection(petCount, sleeping, shaken) ?: return
        val mood = if (petCount >= 10) "angry" else "happy"
        phrases.pick(section)?.let { say(it, mood) }
    }

    override fun onDraw(canvas: Canvas) {
        val now = SystemClock.uptimeMillis()
        val step = (now / FRAME_MS).toInt()
        val blink = mode != Mode.SLEEP && (now / 100) % BLINK_EVERY == 0L
        val sprite = pack.frame(mode.pose, step, blink)
        val breath = 1f + 0.012f * sin(now / 600.0).toFloat()
        val scale = SPRITE_H / sprite.height
        val matrix = Matrix().apply {
            postScale(if (facingLeft) -scale else scale, scale * breath)
            postTranslate(if (facingLeft) (WIDTH + sprite.width * scale) / 2 else (WIDTH - sprite.width * scale) / 2,
                HEIGHT - sprite.height * scale * breath)
        }
        canvas.drawBitmap(sprite, matrix, null)
        bubble?.let { drawBubble(canvas, it) }
    }

    private fun drawBubble(canvas: Canvas, text: String) {
        val layout = StaticLayout.Builder.obtain(text, 0, text.length, textPaint, WIDTH - 160)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL).build()
        val box = RectF(8f, 8f, WIDTH - 8f, 40f + maxOf(layout.height, 96).toFloat())
        canvas.drawRoundRect(box, 28f, 28f, bubblePaint)
        pack.head(emotion)?.let { canvas.drawBitmap(it, null, RectF(20f, 20f, 116f, 116f), null) }
        canvas.save()
        canvas.translate(130f, 24f)
        layout.draw(canvas)
        canvas.restore()
    }

    private fun greeting(): String {
        val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        return if (hour in 5..11) "morning" else if (hour >= 22 || hour < 5) "night" else "idle"
    }

    private enum class Mode(val pose: String) {
        IDLE("stand"), WALK("walk"), SIT("sit_edge"), LAY("laydown"), SLEEP("sleep"), HELD("held"),
        FALL("float"), POKE("poke"), PET("pet"), DIZZY("dizzy"), REACT("stand"),
        JUMP("float"), CLING("hang_side"), PERCH("sit_edge"),
        WAVE("wave"), YAWN("yawn"), DANCE("dance"), GONE("stand"),
    }

    private companion object {
        const val WIDTH = 520
        const val HEIGHT = 720
        const val SPRITE_H = 520f
        const val WALK_SPEED = 4
        const val GRAVITY = 2.2f
        const val DRAG_SLOP = 10f
        const val FRAME_UNITS = 16 // скорость пальца в пикселях за кадр (~60 Гц)
        const val MAX_THROW = 90f
        const val THROW_POWER = 1.35f
        const val AIR_DRAG = 0.985f
        const val BOUNCE = 0.45f
        const val MIN_BOUNCE = 9f
        const val CLING_SPEED = 14f
        const val JUMP_MS = 700f
        const val JUMP_HEIGHT = 220f
        const val SEAT_FROM_BOTTOM = 198 // SPRITE_H × (1 − 0.62): сиденье позы sit_edge, как ANCHORS в pack.ts
        const val EDGE = 12
        const val LONG_PRESS = 450L
        const val PET_SERIES = 3000L
        const val SHAKE_MEMORY = 20_000L
        const val SLEEP_AFTER = 180_000L
        const val FRAME_MS = 160L
        const val BLINK_EVERY = 45L
        val textPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 34f; color = Color.rgb(30, 30, 40) }
        val bubblePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(235, 255, 255, 255) }
    }
}
