package ru.umnick.pocket

import android.app.KeyguardManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.service.wallpaper.WallpaperService
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.MotionEvent
import android.view.SurfaceHolder
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.sin
import kotlin.random.Random

/**
 * Живые обои с Умником — единственный честный способ показать его на экране блокировки: окно поверх
 * блокировки «перекрывает» её и ломает пароль и отпечаток (убрано в 0.7), а обои система рисует сама.
 * На рабочем столе персонаж на обоях не рисуется, если работает обычный спутник поверх приложений
 * (двух Умников сразу не нужно), — только фон. Фон — фото пользователя (`WallpaperBackground`) или градиент.
 */
class UmnickWallpaper : WallpaperService() {
    override fun onCreateEngine(): Engine = LiveEngine()

    private inner class LiveEngine : Engine() {
        private val handler = Handler(Looper.getMainLooper())
        /**
         * Кадры грузятся секунды (122 штуки): в главном потоке обои после обновления приложения
         * оставались чёрными. Фон рисуем сразу, персонажа — когда пакет догрузился в фоне.
         */
        @Volatile private var pack: Pack? = null
        private var phrases: Phrases? = null

        init {
            Thread {
                val loaded = Pack.get(this@UmnickWallpaper)
                handler.post {
                    pack = loaded
                    phrases = Phrases(loaded.phrases)
                    drawnKey = ""
                    if (visible) greet()
                }
            }.start()
        }
        private val keyguard = getSystemService(KeyguardManager::class.java)
        private var visible = false
        private var width = 0
        private var height = 0
        private var background: Bitmap? = null
        private var pose = "stand"
        private var until = 0L
        private var x = 0f
        private var targetX = 0f
        private var facingLeft = false
        private var bubble: String? = null
        private var bubbleUntil = 0L
        private val drawLoop = Runnable { frame() }
        private var drawnKey = ""
        private var plain: Bitmap? = null

        override fun onSurfaceChanged(holder: SurfaceHolder, format: Int, w: Int, h: Int) {
            width = w
            height = h
            plain = null
            drawnKey = ""
            background = WallpaperBackground.load(this@UmnickWallpaper, w, h)
            x = (w - SPRITE_W) / 2f
            targetX = x
            frame()
        }

        override fun onVisibilityChanged(visible: Boolean) {
            this.visible = visible
            if (visible) {
                background = WallpaperBackground.load(this@UmnickWallpaper, width, height) ?: background
                greet()
                frame()
            } else {
                handler.removeCallbacks(drawLoop)
            }
        }

        override fun onDestroy() {
            handler.removeCallbacks(drawLoop)
            super.onDestroy()
        }

        /** Касание обоев (на рабочем столе — по пустому месту): машет и отвечает. */
        override fun onTouchEvent(event: MotionEvent) {
            val phrases = phrases ?: return
            if (event.actionMasked != MotionEvent.ACTION_UP || !characterShown()) return
            if (abs(event.x - (x + SPRITE_W / 2)) > SPRITE_W) return
            act("wave", 2500)
            say(phrases.pick("pet.first"))
        }

        /** Экран включили — машет и здоровается по времени суток (T6 ПК). */
        private fun greet() {
            if (night()) return act("sleep", 60_000)
            act("wave", 2500)
            say(phrases?.pick("pc.triggers.greet.${timeOfDay()}"))
        }

        private fun characterShown(): Boolean =
            pack != null && (keyguard.isKeyguardLocked || Stages.current() == null || isPreview)

        private fun frame() {
            handler.removeCallbacks(drawLoop)
            if (!visible) return
            val now = SystemClock.uptimeMillis()
            live(now)
            // Перерисовка только при изменении: полный экран программно 10–30 раз в секунду занимал
            // 81% CPU эмулятора и подвешивал System UI.
            val bubbleText = bubble?.takeIf { now < bubbleUntil }
            val key = "$pose|${now / ANIM_MS}|${x.toInt()}|$facingLeft|$bubbleText|${characterShown()}"
            if (key != drawnKey) {
                drawnKey = key
                draw(now)
            }
            handler.postDelayed(drawLoop, if (pose == "walk") WALK_FRAME_MS else FRAME_MS)
        }

        /** Простая жизнь без касаний: стоит, гуляет, садится, ложится; ночью спит. */
        private fun live(now: Long) {
            if (pose == "walk") {
                val step = if (targetX > x) WALK_STEP else -WALK_STEP
                if (abs(targetX - x) <= WALK_STEP) act("stand", 3000) else x += step
                return
            }
            if (now < until) return
            if (night()) return act("sleep", 60_000)
            val roll = Random.nextFloat()
            when {
                roll < 0.35f -> {
                    targetX = Random.nextFloat() * (width - SPRITE_W).coerceAtLeast(1f)
                    facingLeft = targetX < x
                    pose = "walk"
                }
                roll < 0.55f -> act("sit_edge", 10_000)
                roll < 0.7f -> act("laydown", 12_000)
                roll < 0.8f -> act("dance", 5000)
                else -> act("stand", 6000)
            }
        }

        private fun act(next: String, ms: Long) {
            pose = next
            until = SystemClock.uptimeMillis() + ms
        }

        private fun say(text: String?) {
            text ?: return
            bubble = text
            bubbleUntil = SystemClock.uptimeMillis() + 5000
        }

        private fun draw(now: Long) {
            val holder = surfaceHolder
            // Через видеокарту, где можно: программный холст на весь экран слишком дорог.
            val canvas = runCatching { holder.lockHardwareCanvas() }.getOrNull()
                ?: runCatching { holder.lockCanvas() }.getOrNull() ?: return
            try {
                drawBackground(canvas)
                if (characterShown()) drawCharacter(canvas, now)
            } catch (error: RuntimeException) {
                CrashLog.write(this@UmnickWallpaper, "wallpaper", error)
            } finally {
                holder.unlockCanvasAndPost(canvas)
            }
        }

        private fun drawBackground(canvas: Canvas) {
            val image = background ?: plain ?: gradientBitmap().also { plain = it }
            canvas.drawBitmap(image, 0f, 0f, null)
        }

        /** Градиент один раз в картинку, а не заново на каждом кадре. */
        private fun gradientBitmap(): Bitmap {
            val bitmap = Bitmap.createBitmap(maxOf(width, 1), maxOf(height, 1), Bitmap.Config.RGB_565)
            gradient.shader = LinearGradient(
                0f, 0f, 0f, height.toFloat(), Color.rgb(18, 22, 40), Color.rgb(8, 30, 52), Shader.TileMode.CLAMP,
            )
            Canvas(bitmap).drawRect(0f, 0f, width.toFloat(), height.toFloat(), gradient)
            return bitmap
        }

        private fun drawCharacter(canvas: Canvas, now: Long) {
            val blink = pose != "sleep" && (now / 100) % 45 == 0L
            val sprite = (pack ?: return).frame(pose, (now / 160).toInt(), blink)
            val scale = SPRITE_H / sprite.height
            val breath = 1f + 0.012f * sin((now / ANIM_MS * ANIM_MS) / 600.0).toFloat()
            // Ниже часов и уведомлений, выше ярлыков экрана блокировки.
            val feetY = height * FEET_LINE
            val left = x + (SPRITE_W - sprite.width * scale) / 2
            val matrix = Matrix().apply {
                postScale(if (facingLeft) -scale else scale, scale * breath)
                postTranslate(if (facingLeft) left + sprite.width * scale else left, feetY - sprite.height * scale * breath)
            }
            canvas.drawBitmap(sprite, matrix, null)
            val text = bubble?.takeIf { now < bubbleUntil } ?: return
            drawBubble(canvas, text, feetY - SPRITE_H * 0.85f)
        }

        /**
         * Облачко — сбоку от персонажа на уровне головы, а не над ним: над ним большие часы экрана
         * блокировки, облачко на них наезжало.
         */
        private fun drawBubble(canvas: Canvas, text: String, top: Float) {
            val boxWidth = (width * 0.46f).toInt()
            val layout = StaticLayout.Builder.obtain(text, 0, text.length, textPaint, boxWidth - 40)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL).build()
            val onRight = x + SPRITE_W / 2 < width / 2
            val left = if (onRight) (x + SPRITE_W - 20).coerceAtMost(width - boxWidth - 12f)
            else (x - boxWidth + 20).coerceAtLeast(12f)
            canvas.drawRoundRect(RectF(left, top, left + boxWidth, top + layout.height + 32), 28f, 28f, bubblePaint)
            canvas.save()
            canvas.translate(left + 20, top + 16)
            layout.draw(canvas)
            canvas.restore()
        }

        private fun night(): Boolean = Calendar.getInstance().get(Calendar.HOUR_OF_DAY).let { it >= 23 || it < 6 }

        private fun timeOfDay(): String = when (Calendar.getInstance().get(Calendar.HOUR_OF_DAY)) {
            in 5..11 -> "morning"
            in 12..17 -> "day"
            in 18..22 -> "evening"
            else -> "night"
        }
    }

    private companion object {
        const val SPRITE_H = 440f
        const val SPRITE_W = 300f
        /** Ступни — ниже больших часов экрана блокировки, выше значка замка и ярлыков. */
        const val FEET_LINE = 0.86f
        const val FRAME_MS = 100L
        const val ANIM_MS = 200L
        const val WALK_FRAME_MS = 50L
        const val WALK_STEP = 6f
        val gradient = Paint()
        val textPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 38f; color = Color.rgb(30, 30, 40) }
        val bubblePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(235, 255, 255, 255) }
    }
}

/** Фото пользователя для фона обоев (выбирается в настройке, доступ через SAF сохраняется). */
object WallpaperBackground {
    private const val PREFS = "wallpaper"
    private const val KEY = "background"

    fun save(context: Context, uri: Uri) {
        context.getSharedPreferences(PREFS, 0).edit().putString(KEY, uri.toString()).apply()
    }

    /** Фото, обрезанное по центру под экран, или `null` — тогда градиент. */
    fun load(context: Context, width: Int, height: Int): Bitmap? {
        if (width <= 0 || height <= 0) return null
        val saved = context.getSharedPreferences(PREFS, 0).getString(KEY, null) ?: return null
        val uri = Uri.parse(saved)
        // Фото с камеры — до 50 Мп: сначала узнаём размер и декодируем уменьшенным (иначе нехватка памяти).
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        runCatching { context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) } }
        var sample = 1
        while (bounds.outWidth / (sample * 2) >= width && bounds.outHeight / (sample * 2) >= height) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        val source = runCatching {
            context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
        }.getOrNull() ?: return null
        val scale = maxOf(width.toFloat() / source.width, height.toFloat() / source.height)
        val scaled = Bitmap.createScaledBitmap(source, (source.width * scale).toInt(), (source.height * scale).toInt(), true)
        return Bitmap.createBitmap(scaled, (scaled.width - width) / 2, (scaled.height - height) / 2, width, height)
    }
}
