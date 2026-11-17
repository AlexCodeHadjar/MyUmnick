package ru.umnick.pocket

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.PixelFormat
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
import kotlin.math.hypot
import kotlin.math.sin

/**
 * «Тело» спутника на телефоне (S-24.3, S-24.4): окно размером с персонажа поверх экрана, движение
 * (ходьба, прыжок по дуге, полёт после броска, лазанье по стене), отрисовка позы и облачка, касания.
 * Что делать дальше и как реагировать — решает `Life` (порт `brain.ts`/`triggers.ts` ПК).
 * Координаты — экранные: те же, что у рамок иконок от `PerchService`.
 */
class StageView(context: Context, private val host: Host) : View(context) {
    private val pack = Pack.get(context)
    val phrases = Phrases(pack.phrases)
    val mood = Mood(context)
    val life = Life(this, context)
    private val params = WindowManager.LayoutParams(
        WIDTH, HEIGHT, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.START
        // Координаты окна — от края экрана, а не от строки состояния: иначе на 144 px ниже иконок.
        if (android.os.Build.VERSION.SDK_INT >= 30) setFitInsetsTypes(0)
        if (android.os.Build.VERSION.SDK_INT >= 28) {
            layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
        }
    }
    val screen get() = Screen.of(context)
    /** «Пол» — над панелью навигации, ступни на её верхнем крае. */
    val floor get() = screen.let { it.heightPixels - it.bottomInset - HEIGHT }
    val x get() = params.x
    val y get() = params.y

    var mode = Mode.POSE
        private set
    var pose = "stand"
        private set
    private var until = 0L
    private var targetX = 0
    private var vx = 0f
    private var vy = 0f
    private var arcFrom = 0 to 0
    private var arcTo = 0 to 0
    private var arcStart = 0L
    private var arcPose = "sit_edge"
    private var arcHold = 0L
    private var climbLeft = false
    var facingLeft = false
    private var grabX = 0f
    private var grabY = 0f
    private var velocity: VelocityTracker? = null
    private var downAt = 0L
    private var downX = 0f
    private var downY = 0f
    private var bubble: String? = null
    private var bubbleUntil = 0L
    var emotion = "happy"
    var lastTouch = SystemClock.uptimeMillis()
        private set

    /** Перебежка на ПК: вызывается, когда персонажа утащили за правый край (S-24.11). */
    var onEdgeExit: (() -> Boolean)? = null

    /** Занят движением, которое нельзя прервать выбором нового занятия. */
    val moving get() = mode != Mode.POSE

    val expired get() = mode == Mode.POSE && SystemClock.uptimeMillis() > until

    fun attach() {
        params.x = screen.widthPixels - WIDTH
        params.y = floor
        host.add(this, params)
        life.attached()
        postOnAnimation(::tick)
    }

    fun detach() = host.remove(this)

    // ——— действия, которыми пользуется Life ———

    /** Поза на месте на `ms`; `atX`/`atY` — переставить (угол, стена). */
    fun act(pose: String, ms: Long, atX: Int? = null, atY: Int? = null) {
        this.pose = pose
        mode = Mode.POSE
        until = SystemClock.uptimeMillis() + ms
        if (atX != null || atY != null) place(atX ?: params.x, atY ?: params.y)
    }

    fun walkTo(x: Int) {
        targetX = x.coerceIn(minX(), maxX())
        facingLeft = targetX < params.x
        pose = "walk"
        mode = Mode.WALK
    }

    /** Прыжок по дуге в точку окна (`x`, `y`), там поза `then` на `hold` мс. */
    fun leap(x: Int, y: Int, then: String, hold: Long) {
        arcFrom = params.x to params.y
        arcTo = x to y
        arcStart = SystemClock.uptimeMillis()
        arcPose = then
        arcHold = hold
        facingLeft = x < params.x
        pose = "float"
        mode = Mode.JUMP
    }

    /** Падение вниз с текущей скоростью (после броска — с инерцией). */
    fun fall(withVx: Float = 0f, withVy: Float = 0f) {
        vx = withVx
        vy = withVy
        pose = "float"
        mode = Mode.FALL
    }

    /** Подойти вплотную к стене и лезть вверх (BEHAVIOR §9). */
    fun climb(left: Boolean) {
        climbLeft = left
        facingLeft = left
        pose = "climb"
        mode = Mode.CLIMB
        place(wallX("climb", left, CLIMB_CONTACT), params.y)
    }

    /** Висит на стене и сползает (бросили в бок). */
    fun cling(left: Boolean, ms: Long) {
        facingLeft = left
        act("climb", ms, wallX("climb", left, CLIMB_CONTACT), params.y)
        mode = Mode.CLING
    }

    fun hide() {
        mode = Mode.GONE
        visibility = INVISIBLE
    }

    fun show(atX: Int, atY: Int) {
        visibility = VISIBLE
        place(atX, atY)
        act("stand", 1500)
    }

    /** Реплика в облачке над головой и эмоция на значке лица. */
    fun say(text: String?, face: String = emotion, ms: Long = 4500) {
        text ?: return
        bubble = text
        emotion = face
        bubbleUntil = SystemClock.uptimeMillis() + ms
        invalidate()
    }

    /** Окно: x, при котором точка позы `pose` на доле `contact` ширины кадра касается стены. */
    fun wallX(pose: String, left: Boolean, contact: Float): Int {
        val bmp = pack.frame(pose, 0, false)
        val w = bmp.width * SPRITE_H / bmp.height
        val margin = (WIDTH - w) / 2
        return if (left) (-(margin + (1 - contact) * w)).toInt() else (screen.widthPixels - margin - contact * w).toInt()
    }

    /** Поля по бокам кадра позы в окне и ширина нарисованного кадра. */
    fun spriteSpan(pose: String): Pair<Int, Int> {
        val bmp = pack.frame(pose, 0, false)
        val w = (bmp.width * SPRITE_H / bmp.height).toInt()
        return (WIDTH - w) / 2 to w
    }

    fun attend() = life.attend()
    fun dizzy() = life.shaken()
    fun noteSaved() = life.noteSaved()

    /** Окно: y, при котором сиденье позы (доля высоты кадра) оказывается на линии `edgeY`. */
    fun seatY(edgeY: Int, seat: Float): Int = (edgeY - HEIGHT + SPRITE_H * (1 - seat)).toInt()

    fun minX() = -WIDTH / 4
    fun maxX() = screen.widthPixels - WIDTH * 3 / 4

    // ——— кадр ———

    private fun tick() {
        val now = SystemClock.uptimeMillis()
        when (mode) {
            Mode.WALK -> stepWalk()
            Mode.FALL -> stepFall()
            Mode.JUMP -> stepJump(now)
            Mode.CLIMB -> stepClimb()
            Mode.CLING -> stepCling(now)
            else -> Unit
        }
        life.tick(now)
        if (bubble != null && now > bubbleUntil) bubble = null
        invalidate()
        postOnAnimation(::tick)
    }

    private fun place(nx: Int, ny: Int) {
        params.x = nx
        params.y = ny
        host.move(this, params)
    }

    private fun stepWalk() {
        val delta = targetX - params.x
        if (abs(delta) <= WALK_SPEED) {
            act("stand", 1500)
            return life.arrived()
        }
        place(params.x + if (delta > 0) WALK_SPEED else -WALK_SPEED, floor)
    }

    /** Полёт: инерция, отскок от боков и «пола»; сильно в бок — цепляется. */
    private fun stepFall() {
        vy += GRAVITY
        vx *= AIR_DRAG
        var nx = (params.x + vx).toInt()
        var ny = (params.y + vy).toInt()
        if (nx < minX() || nx > maxX()) {
            nx = nx.coerceIn(minX(), maxX())
            if (abs(vx) > CLING_SPEED) return life.hitWall(nx == minX())
            vx = -vx * BOUNCE
        }
        if (ny >= floor) {
            ny = floor
            if (vy > MIN_BOUNCE) vy = -vy * BOUNCE else return landed()
        }
        place(nx, ny)
    }

    private fun landed() {
        place(params.x, floor)
        vx = 0f
        act("stand", 1500)
        life.landed()
    }

    private fun stepJump(now: Long) {
        val t = ((now - arcStart).toFloat() / JUMP_MS).coerceAtMost(1f)
        val lift = JUMP_HEIGHT * 4 * t * (1 - t)
        place(
            (arcFrom.first + (arcTo.first - arcFrom.first) * t).toInt(),
            (arcFrom.second + (arcTo.second - arcFrom.second) * t - lift).toInt(),
        )
        if (t >= 1f) act(arcPose, arcHold)
    }

    private fun stepClimb() {
        val top = seatY(screen.let { it.heightPixels / 30 + TOP_LEDGE }, 0.62f)
        if (params.y <= top) return life.reachedTop(climbLeft)
        place(params.x, params.y - CLIMB_SPEED)
    }

    private fun stepCling(now: Long) {
        if (now > until || params.y >= floor) return fall()
        place(params.x, params.y + 1)
    }

    /** Поворот экрана: ширина и высота меняются — возвращаем персонажа в пределы экрана. */
    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        post {
            place(params.x.coerceIn(minX(), maxX()), params.y.coerceIn(0, maxOf(0, floor)))
            if (mode != Mode.HELD && mode != Mode.GONE) fall()
            life.rotated()
        }
    }

    // ——— касания ———

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // Касание мимо персонажа — не наше (на экране блокировки его ждёт LockActivity).
        if (event.actionMasked == MotionEvent.ACTION_OUTSIDE || mode == Mode.GONE) return false
        lastTouch = SystemClock.uptimeMillis()
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> touchDown(event)
            MotionEvent.ACTION_MOVE -> touchMove(event)
            MotionEvent.ACTION_UP -> touchUp(event)
            MotionEvent.ACTION_CANCEL -> if (mode == Mode.HELD) fall()
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
        if (mode != Mode.HELD && abs(event.rawX - downX) + abs(event.rawY - downY) < DRAG_SLOP) return
        velocity?.addMovement(event)
        if (mode != Mode.HELD) life.grabbed()
        mode = Mode.HELD
        pose = "held"
        place((event.rawX - grabX).toInt(), (event.rawY - grabY).toInt())
        velocity?.let { tracker ->
            tracker.computeCurrentVelocity(1000)
            life.dragging(hypot(tracker.xVelocity, tracker.yVelocity))
        }
        if (event.rawX > screen.widthPixels - EDGE && onEdgeExit?.invoke() == true) life.leftForPc()
    }

    private fun touchUp(event: MotionEvent) {
        if (mode == Mode.HELD) return release(event)
        if (event.eventTime - downAt > LONG_PRESS) life.poked() else life.petted()
    }

    private fun release(event: MotionEvent) {
        val tracker = velocity ?: return fall()
        tracker.addMovement(event)
        tracker.computeCurrentVelocity(FRAME_UNITS, MAX_THROW)
        val tx = tracker.xVelocity * THROW_POWER
        val ty = tracker.yVelocity * THROW_POWER
        // Отпустили у самого бока — сразу цепляется за край, без броска.
        when {
            event.rawX < SIDE_GRAB -> life.hitWall(true)
            event.rawX > screen.widthPixels - SIDE_GRAB -> life.hitWall(false)
            else -> {
                fall(tx, ty)
                life.thrown(hypot(tx, ty))
            }
        }
    }

    // ——— отрисовка ———

    override fun onDraw(canvas: Canvas) {
        val now = SystemClock.uptimeMillis()
        val step = (now / FRAME_MS).toInt()
        val blink = pose != "sleep" && (now / 100) % BLINK_EVERY == 0L
        val talking = bubble != null && pose in TALKING_POSES && (now / 140) % 2 == 0L
        val sprite = pack.frame(if (talking) "${pose}_talk" else pose, step, blink, fallback = pose)
        val breath = 1f + 0.012f * sin(now / 600.0).toFloat()
        val scale = SPRITE_H / sprite.height
        val matrix = Matrix().apply {
            postScale(if (facingLeft) -scale else scale, scale * breath)
            postTranslate(
                if (facingLeft) (WIDTH + sprite.width * scale) / 2 else (WIDTH - sprite.width * scale) / 2,
                HEIGHT - sprite.height * scale * breath,
            )
        }
        canvas.drawBitmap(sprite, matrix, null)
        bubble?.let { drawBubble(canvas, it) } ?: drawMoodBadge(canvas)
    }

    /** Без реплики настроение видно по значку лица над головой: грусть, усталость, удивление. */
    private fun drawMoodBadge(canvas: Canvas) {
        if (emotion == "happy" || pose == "sleep") return
        val head = pack.head(emotion) ?: return
        val cx = WIDTH / 2f + 120f
        val cy = HEIGHT - SPRITE_H - 10f
        canvas.drawCircle(cx, cy, 50f, bubblePaint)
        canvas.drawBitmap(head, null, RectF(cx - 44f, cy - 44f, cx + 44f, cy + 44f), null)
    }

    private fun drawBubble(canvas: Canvas, text: String) {
        // Окно у края частично за экраном — облачко рисуем только в видимой его части.
        val visibleLeft = maxOf(8, -params.x + 8)
        val visibleRight = minOf(WIDTH - 8, screen.widthPixels - params.x - 8)
        var left = visibleLeft.toFloat()
        var right = visibleRight.toFloat()
        if (right - left < MIN_BUBBLE) {
            if (visibleLeft > 8) right = minOf(WIDTH - 8f, left + MIN_BUBBLE) else left = maxOf(8f, right - MIN_BUBBLE)
        }
        val layout = StaticLayout.Builder.obtain(text, 0, text.length, textPaint, (right - left - 140).toInt())
            .setAlignment(Layout.Alignment.ALIGN_NORMAL).build()
        val box = RectF(left, 8f, right, 40f + maxOf(layout.height, 96).toFloat())
        canvas.drawRoundRect(box, 28f, 28f, bubblePaint)
        pack.head(emotion)?.let { canvas.drawBitmap(it, null, RectF(left + 12f, 20f, left + 108f, 116f), null) }
        canvas.save()
        canvas.translate(left + 122f, 24f)
        layout.draw(canvas)
        canvas.restore()
    }

    enum class Mode { POSE, WALK, JUMP, FALL, CLIMB, CLING, HELD, GONE }

    companion object {
        const val WIDTH = 520
        const val HEIGHT = 720
        const val SPRITE_H = 520f
        private const val WALK_SPEED = 4
        private const val CLIMB_SPEED = 3
        private const val TOP_LEDGE = 60
        private const val GRAVITY = 2.2f
        private const val DRAG_SLOP = 10f
        private const val FRAME_UNITS = 16 // скорость пальца в пикселях за кадр (~60 Гц)
        private const val MAX_THROW = 90f
        private const val THROW_POWER = 1.35f
        private const val AIR_DRAG = 0.985f
        private const val BOUNCE = 0.45f
        private const val MIN_BOUNCE = 9f
        private const val CLING_SPEED = 6f
        private const val SIDE_GRAB = 90
        private const val JUMP_MS = 700f
        private const val JUMP_HEIGHT = 220f
        private const val EDGE = 12
        private const val MIN_BUBBLE = 330f
        private const val LONG_PRESS = 450L
        private const val FRAME_MS = 160L
        private const val BLINK_EVERY = 45L
        /** Кисти у стены в кадре climb — доля ширины (bbox 409 из 526). */
        const val CLIMB_CONTACT = 0.78f
        private val TALKING_POSES = setOf("stand", "sit_edge", "laydown", "sing")
        private val textPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 34f; color = Color.rgb(30, 30, 40) }
        private val bubblePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(235, 255, 255, 255) }
    }
}
