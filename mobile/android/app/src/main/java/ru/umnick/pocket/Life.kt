package ru.umnick.pocket

import android.content.Context
import android.media.AudioManager
import android.os.BatteryManager
import android.os.SystemClock
import java.util.Calendar
import kotlin.random.Random

/**
 * «Жизнь» спутника на телефоне — порт `brain.ts`, `triggers.ts`, `remarks.ts`, `habits.ts` ПК
 * (BEHAVIOR §3–§11) под экран телефона. Окна ПК здесь — иконки и кнопки (`Perches`), рабочий стол —
 * лаунчер, плеер — любой звук музыки, «полный экран» — видео в альбомной ориентации.
 *
 * Триггеры (номера — BEHAVIOR §3): T3 поглаживание, T4 встряска, T5 бросок, T6 приветствие,
 * T7 «с возвращением», T10 таскают, T11 «мой дом!», T12 сменилось приложение, T13 рабочий стол,
 * T14 «смотрим вместе», T15 музыка, T16 ночь, T17 «разомнись», T18 скука; §9 лазанье по стенам.
 */
class Life(private val stage: StageView, context: Context) {
    private val phrases get() = stage.phrases
    private val mood get() = stage.mood
    private val audio = context.getSystemService(AudioManager::class.java)
    private val battery = context.getSystemService(BatteryManager::class.java)
    private val cooldowns = HashMap<String, Long>()
    private var lastCheck = 0L
    private var lastDrift = SystemClock.uptimeMillis()
    private var perch: Perches.Spot? = null
    private var perchScene = 0
    private var petCount = 0
    private var lastPet = 0L
    private var shakenAt = 0L
    private var singing = false
    private var watching = false
    private var seenApp = ""
    private val appSwitches = ArrayDeque<Long>()
    private val firstToday = HashSet<String>()
    private var activeSince = SystemClock.uptimeMillis()
    private var climbAfterWalk: Boolean? = null
    private var onTop = false
    private var dodging = false
    private var sleptAt = 0L
    private var lookedAt = 0L

    // ——— события от тела и службы ———

    fun attached() {
        stage.act("wave", 2500)
        say(phrases.pick("pc.triggers.greet.${timeOfDay()}") ?: phrases.pick("idle"), "happy")
    }

    /** T7: экран включили после долгого перерыва. */
    fun screenOn(offMs: Long) {
        activeSince = SystemClock.uptimeMillis()
        if (offMs < COMEBACK_MS || !ready("comeback", 10 * MIN)) return
        stage.act("wave", 2500)
        say(phrases.pick("pc.triggers.comeback"), "happy")
        mood.nudge(Mood.Event.WAKE)
    }

    fun attend() {
        mood.nudge(Mood.Event.TALK)
        stage.act("stand", 3000)
        say(phrases.pick("wake") ?: "Слушаю.", "thinking", 8000)
    }

    fun noteSaved() = mood.nudge(Mood.Event.NOTE)

    /** T4: встряхнули телефон. */
    fun shaken() {
        shakenAt = SystemClock.uptimeMillis()
        mood.nudge(Mood.Event.SHAKE)
        if (stage.moving) return
        stage.act("dizzy", 2500)
        say(phrases.pick("pc.triggers.dizzy") ?: phrases.pick("dizzy"), "surprised")
    }

    /** T3: поглаживание сериями (BEHAVIOR §7). */
    fun petted() {
        val now = SystemClock.uptimeMillis()
        petCount = if (now - lastPet < PET_SERIES) petCount + 1 else 1
        lastPet = now
        val sleeping = stage.pose == "sleep" || stage.pose == "laydown"
        stage.act("pet", 1800)
        mood.nudge(Mood.Event.PET)
        val section = phrases.petSection(petCount, sleeping, now - shakenAt < SHAKE_MEMORY) ?: return
        say(phrases.pick(section), if (petCount >= 10) "angry" else "happy")
    }

    fun poked() {
        mood.nudge(Mood.Event.POKE)
        stage.act("poke", 1500)
        say(phrases.pick("poke"), "surprised")
    }

    fun grabbed() {
        perch = null
        climbAfterWalk = null
        onTop = false
        say(phrases.pick("thrown") ?: "Ой!", "surprised", 2000)
    }

    /** T10: таскают слишком резво. */
    fun dragging(speed: Float) {
        if (speed > DRAG_FAST && ready("drag", MIN)) say(phrases.pick("pc.triggers.drag"), "surprised")
    }

    /** T5: бросили с размаху. */
    fun thrown(speed: Float) {
        mood.nudge(Mood.Event.THROW)
        if (speed > TOSS_FAST && ready("toss", 15_000)) say(phrases.pick("pc.triggers.toss"), "surprised")
    }

    fun landed() {
        if (cooldowns["toss"]?.let { SystemClock.uptimeMillis() - it < 4000 } == true) {
            say(phrases.pick("pc.triggers.back"), if (mood.joy > 0.5f) "happy" else "angry")
        }
    }

    fun hitWall(left: Boolean) {
        stage.cling(left, 5000 + Random.nextLong(4000))
        if (ready("cling", 30_000)) say(phrases.pick("pc.triggers.climb"), "surprised")
    }

    /** §9: долез до верха — садится на верхний край экрана в углу. */
    fun reachedTop(left: Boolean) {
        val y = stage.topY()
        stage.facingLeft = !left
        stage.act("perch_corner", 8000 + Random.nextLong(8000), stage.wallX("perch_corner", left, CORNER_CONTACT), y)
        onTop = true
    }

    fun rotated() {
        watching = false
    }

    fun leftForPc() {
        say(phrases.pick("handoff_out"), "happy", 1500)
        stage.hide()
    }

    // ——— каждый кадр ———

    fun tick(now: Long) {
        checkPerch()
        checkKeyboard()
        lookAtTouch()
        if (now - lastCheck >= CHECK_MS) {
            lastCheck = now
            checkTriggers(now)
        }
        if (stage.expired) decide(now)
    }

    /** T11: опора пропала (листнули страницу, сменилось приложение) — падает, «Мой дом!». */
    private fun checkPerch() {
        val spot = perch ?: return
        if (stage.moving || stage.pose != "sit_edge") return
        if (Perches.scene == perchScene && Perches.stillThere(spot)) return
        perch = null
        stage.fall()
        if (ready("homeless", MIN)) say(phrases.pick("pc.triggers.homeless"), "surprised")
    }

    /**
     * Клавиатура появилась и персонаж в её зоне (или ниже её верха) — отпрыгивает в верхний угол, чтобы
     * не закрывать поле ввода; клавиатура ушла — спрыгивает вниз.
     */
    private fun checkKeyboard() {
        val box = Perches.keyboard
        if (box == null) {
            if (dodging) {
                dodging = false
                if (!stage.moving) stage.fall()
            }
            return
        }
        if (dodging || stage.mode == StageView.Mode.HELD || stage.mode == StageView.Mode.GONE) return
        val feet = stage.y + StageView.HEIGHT
        if (feet < box.top) return
        dodging = true
        perch = null
        climbAfterWalk = null
        val left = stage.x < stage.screen.widthPixels / 2 - StageView.WIDTH / 2
        stage.facingLeft = !left
        stage.leap(stage.wallX("perch_corner", left, CORNER_CONTACT), stage.topY(), "perch_corner", KEYBOARD_HOLD)
        Trace.event("keyboard")
        if (ready("keyboard", MIN)) say(phrases.pick("keyboard"))
    }

    /** Нажали где-то на экране — поворачивается туда (если стоит, сидит или лежит, а не лезет и не летит). */
    private fun lookAtTouch() {
        val at = Perches.touchAt
        if (at == lookedAt) return
        lookedAt = at
        if (stage.moving || stage.pose !in TURNABLE) return
        val left = Perches.touchX < stage.x + StageView.WIDTH / 2
        if (left == stage.facingLeft) return
        stage.facingLeft = left
        Trace.event("look:${if (left) "left" else "right"}")
        if (stage.pose == "sleep" && Random.nextFloat() < 0.3f) stage.act("yawn", 2000)
    }

    private fun checkTriggers(now: Long) {
        if (stage.mode == StageView.Mode.HELD || stage.mode == StageView.Mode.GONE) return
        checkMusic()
        checkVideo()
        checkApp(now)
        checkClock(now)
    }

    /** T15: играет музыка — поёт стоя и не гуляет (радио, BEHAVIOR §8). */
    private fun checkMusic() {
        val playing = audio.isMusicActive && !watching
        if (playing == singing) return
        singing = playing
        Trace.event("music:$playing")
        if (!playing || stage.moving) return
        stage.act(if (Random.nextBoolean()) "sing" else "radio_idle", 20_000)
        if (ready("music", 5 * MIN)) say(phrases.pick("pc.remarks.music"), "happy")
    }

    /** T14: видео во весь экран (альбомная) — «смотрим вместе» в углу (BEHAVIOR §11.2). */
    private fun checkVideo() {
        val screen = stage.screen
        val video = screen.widthPixels > screen.heightPixels && Topics.of(Perches.app) == "video"
        if (video == watching) return
        watching = video
        Trace.event("watch:$video")
        perch = null
        if (video) {
            stage.facingLeft = true
            stage.act("watch", 60_000, stage.maxX(), stage.floor)
            say(phrases.pick("pc.watch.start"), "happy")
        } else {
            stage.fall()
            say(phrases.pick("pc.watch.end"), "happy")
        }
    }

    /** T12: сменилось приложение — фраза о нём; «первый раз за день», «долго сидим», «туда-сюда». */
    private fun checkApp(now: Long) {
        val app = Perches.app
        if (app.isEmpty() || app == seenApp) return checkLongApp(now)
        seenApp = app
        Trace.event("app:$app")
        appSwitches.addLast(now)
        while (appSwitches.isNotEmpty() && now - appSwitches.first() > MIN) appSwitches.removeFirst()
        val topic = Topics.of(app)
        when {
            appSwitches.size >= SWITCHING && ready("switching", 3 * MIN) -> say(phrases.pick("pc.habits.switching"))
            firstToday.add(topic) && phrases.has("pc.habits.first.$topic") -> say(phrases.pick("pc.habits.first.$topic"))
            ready("app", 45_000) && Random.nextFloat() < 0.4f -> say(phrases.pick("pc.remarks.$topic"))
        }
    }

    private fun checkLongApp(now: Long) {
        if (Perches.app.isEmpty() || now - Perches.appSince < LONG_APP) return
        if (ready("long", LONG_APP)) say(phrases.pick("pc.habits.long"))
    }

    /** T16 ночь, T17 «разомнись», батарея. */
    private fun checkClock(now: Long) {
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        if (hour in 1..4 && ready("night", 60 * MIN)) {
            stage.act("yawn", 2500)
            say(phrases.pick("pc.triggers.night"), "blink")
        }
        if (now - activeSince > STRETCH_AFTER && ready("stretch", STRETCH_AFTER)) {
            say(phrases.pick("pc.triggers.stretch"))
        }
        val level = battery.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        if (level in 1..15 && !battery.isCharging && ready("battery", 30 * MIN)) {
            say(phrases.pick("low_battery"), "sad")
        }
    }

    // ——— выбор следующего занятия (brain.ts) ———

    private fun decide(now: Long) {
        mood.drift((now - lastDrift) / 1000f, (now - stage.lastTouch) / 1000f)
        lastDrift = now
        stage.emotion = mood.face()
        if (singing) return stage.act(if (Random.nextFloat() < 0.2f) "dance" else "sing", 15_000)
        if (watching) return watchMore()
        val idle = now - stage.lastTouch
        // Спит недолго и не подряд: в 20-минутном прогоне без касаний он спал 70% времени (засыпал снова
        // сразу после пробуждения). Теперь: сон 1–2 мин, потом не меньше SLEEP_GAP бодрствует.
        val night = Calendar.getInstance().get(Calendar.HOUR_OF_DAY).let { it >= 23 || it < 6 }
        val sleepAfter = when {
            night -> SLEEP_AFTER / 5
            mood.tired -> SLEEP_AFTER / 2
            else -> SLEEP_AFTER
        }
        val rested = now - sleptAt > SLEEP_GAP
        when {
            idle > sleepAfter && rested && stage.pose == "yawn" -> {
                sleptAt = now
                stage.act("sleep", 60_000 + Random.nextLong(60_000), atY = stage.floor)
            }
            idle > sleepAfter && rested -> stage.act("yawn", 2500)
            onTop -> comeDown()
            else -> stage.act(pickActivity())
        }
        mood.save()
    }

    /** Насиделся наверху: прыгает на иконку пониже или спрыгивает на «пол». */
    private fun comeDown() {
        onTop = false
        hopOnIcon()?.let { return }
        stage.fall()
    }

    private fun watchMore() {
        stage.act("watch", 30_000)
        if (Random.nextFloat() < 0.3f) say(phrases.pick("pc.watch.during"))
    }

    /** Занятие с весами по настроению; часть занятий сама двигает тело и возвращает короткую паузу. */
    private fun pickActivity(): Activity {
        val desktop = Topics.of(Perches.app) == "desktop"
        val roll = Random.nextFloat()
        return when {
            mood.tired && roll < 0.4f -> rest()
            mood.cheerful && roll < 0.2f -> Activity("dance", 6000)
            roll < if (desktop) 0.45f else 0.25f -> hopOnIcon() ?: wander()
            roll < 0.5f -> wander()
            roll < 0.6f -> corner()
            roll < 0.65f -> leanOnWall()
            roll < 0.82f -> startClimb()
            roll < 0.87f -> peek()
            roll < 0.92f -> rest()
            else -> chatter()
        }
    }

    private fun wander(): Activity {
        stage.walkTo(Random.nextInt(stage.minX(), stage.maxX()))
        return Activity("walk", 0)
    }

    private fun rest() = Activity(if (Random.nextBoolean()) "laydown" else "sit_edge", 10_000 + Random.nextLong(8000))

    /** T13: прыжок на иконку/кнопку; иногда «тыкает» её (choosePoke ПК). */
    private fun hopOnIcon(): Activity? {
        val spot = Perches.pick(stage.screen.widthPixels) ?: return null
        perch = spot
        perchScene = Perches.scene
        val x = (spot.box.centerX() - StageView.WIDTH / 2).coerceIn(stage.minX(), stage.maxX())
        stage.leap(x, stage.seatY(spot.box.top, EDGE_SEAT), "sit_edge", 8000 + Random.nextLong(10_000))
        if (spot.label.isNotEmpty() && Random.nextFloat() < 0.5f) {
            val section = if (Random.nextFloat() < 0.6f) "pc.perch" else "pc.poke"
            say(phrases.pick(section, spot.label))
        } else if (Random.nextFloat() < 0.1f) {
            say(phrases.pick("pc.desktopFun.count", Perches.spots.size.toString()))
        }
        return Activity("float", 0)
    }

    /** Угол экрана: сидит, обняв колени (sit_corner). */
    private fun corner(): Activity {
        val left = Random.nextBoolean()
        stage.facingLeft = !left
        stage.act("sit_corner", 12_000, if (left) stage.minX() + 40 else stage.maxX() - 40, stage.floor)
        return Activity("sit_corner", 0)
    }

    /** Прислонился спиной к боку экрана (lean_side). */
    private fun leanOnWall(): Activity {
        val left = Random.nextBoolean()
        stage.facingLeft = left
        stage.act("lean_side", 9000, stage.wallX("lean_side", left, LEAN_CONTACT), stage.floor)
        return Activity("lean_side", 0)
    }

    /** §9: идёт к ближней стене пешком, у стены — лезет вверх (`arrived`). */
    private fun startClimb(): Activity {
        val left = stage.x < stage.screen.widthPixels / 2 - StageView.WIDTH / 2
        climbAfterWalk = left
        stage.walkTo(stage.wallX("climb", left, StageView.CLIMB_CONTACT))
        return Activity("walk", 0)
    }

    /** Дошёл, куда шёл: если шёл к стене — лезет. */
    fun arrived() {
        val left = climbAfterWalk ?: return
        climbAfterWalk = null
        stage.climb(left)
        if (ready("climb", 2 * MIN)) say(phrases.pick("pc.triggers.climb"))
    }

    /** Выглядывает из-за края экрана (peek). */
    private fun peek(): Activity {
        // В кадре peek голова высовывается из-за ЛЕВОГО края кадра: у левой стены — как есть, у правой — зеркально.
        val left = Random.nextBoolean()
        stage.facingLeft = !left
        val (margin, width) = stage.spriteSpan("peek")
        val x = if (left) -margin else stage.screen.widthPixels - margin - width
        stage.act("peek", 5000, x, Random.nextInt(stage.screen.heightPixels / 5, maxOf(stage.screen.heightPixels / 5 + 1, stage.floor)))
        if (Random.nextFloat() < 0.4f) say(phrases.pick("peek"))
        return Activity("peek", 0)
    }

    /** T18: скучает — комментарий о программе, времени суток или настроении. */
    private fun chatter(): Activity {
        val topic = Topics.of(Perches.app)
        val section = when {
            mood.joy < 0.3f -> if (Random.nextBoolean()) "pc.mood.low" else "lonely"
            mood.cheerful -> "pc.mood.high"
            Random.nextFloat() < 0.5f -> "pc.remarks.$topic"
            else -> "pc.remarks.${timeOfDay()}"
        }
        if (Random.nextFloat() < 0.5f) say(phrases.pick(section) ?: phrases.pick("idle"))
        return Activity("stand", 7000)
    }

    // ——— вспомогательное ———

    private fun say(text: String?, face: String = mood.face(), ms: Long = 4500) = stage.say(text, face, ms)

    private fun ready(key: String, cooldown: Long): Boolean {
        val now = SystemClock.uptimeMillis()
        if (cooldowns[key]?.let { now - it < cooldown } == true) return false
        cooldowns[key] = now
        Trace.event("trigger:$key")
        return true
    }

    private fun timeOfDay(): String = when (Calendar.getInstance().get(Calendar.HOUR_OF_DAY)) {
        in 5..11 -> "morning"
        in 12..17 -> "day"
        in 18..22 -> "evening"
        else -> "night"
    }

    /** Занятие: поза и сколько её держать; 0 — тело уже занято движением (ходьба, прыжок). */
    data class Activity(val pose: String, val ms: Long)

    private fun StageView.act(activity: Activity) {
        if (activity.ms > 0 && !moving) act(activity.pose, activity.ms)
    }

    private companion object {
        const val MIN = 60_000L
        /** Позы, в которых можно повернуться к касанию: у стены и в полёте разворот выглядел бы сломанным. */
        val TURNABLE = setOf("stand", "sit_edge", "sit_corner", "laydown", "sleep", "dance", "sing", "radio_idle", "watch", "wave", "yawn")
        /** Сидит наверху, пока клавиатура открыта; потом сам слезет (`checkKeyboard`). */
        const val KEYBOARD_HOLD = 10 * 60_000L
        const val CHECK_MS = 1000L
        const val PET_SERIES = 3000L
        const val SHAKE_MEMORY = 20_000L
        const val SLEEP_AFTER = 5 * MIN
        const val SLEEP_GAP = 4 * MIN
        const val COMEBACK_MS = 10 * MIN
        const val STRETCH_AFTER = 50 * MIN
        const val LONG_APP = 40 * MIN
        const val SWITCHING = 5
        const val DRAG_FAST = 2500f
        const val TOSS_FAST = 30f
        /** Сиденье позы sit_edge — доля высоты кадра от верха (ANCHORS в pack.ts). */
        const val EDGE_SEAT = 0.62f
        /** Край кадра perch_corner, прижатый к боку экрана (bbox 501 из 526). */
        const val CORNER_CONTACT = 0.95f
        /** Спина у стены в кадре lean_side — доля ширины (bbox 531 из 536). */
        const val LEAN_CONTACT = 0.97f
    }
}
