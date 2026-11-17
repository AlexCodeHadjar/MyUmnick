package ru.umnick.pocket

import android.app.Activity
import android.app.KeyguardManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
import android.view.MotionEvent
import android.view.WindowManager

/**
 * Спутник на экране блокировки (просьба пользователя: «включаю телефон — он уже тут»). Окно
 * размером с персонажа, `FLAG_NOT_TOUCH_MODAL` — касания мимо него уходят экрану блокировки.
 * После разблокировки закрывается, спутник снова живёт в оверлее.
 */
class LockActivity : Activity() {
    private var stage: StageView? = null
    private val unlocked = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) = finish()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setShowWhenLocked(true)
        window.addFlags(
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
        )
        window.clearFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND)
        stage = StageView(this, LockHost(this)).also {
            it.attach()
            Stages.lock = it
        }
        registerReceiver(unlocked, IntentFilter(Intent.ACTION_USER_PRESENT))
    }

    /**
     * Пока окно на экране блокировки, Android считает блокировку «перекрытой» и не показывает ввод
     * пароля и не слушает отпечаток (баг 0.3). Любое касание мимо спутника или «назад» — просим
     * систему показать разблокировку и уходим.
     */
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_OUTSIDE) unlock()
        return super.onTouchEvent(event)
    }

    @Deprecated("Activity back")
    override fun onBackPressed() = unlock()

    private fun unlock() {
        if (isFinishing) return
        val keyguard = getSystemService(KeyguardManager::class.java)
        keyguard.requestDismissKeyguard(this, null)
        finish()
    }

    override fun onDestroy() {
        unregisterReceiver(unlocked)
        if (Stages.lock === stage) Stages.lock = null
        Stages.overlay?.visibility = android.view.View.VISIBLE
        super.onDestroy()
    }

    companion object {
        fun enabled(context: Context): Boolean =
            context.getSharedPreferences("settings", 0).getBoolean("on_lock", true)

        fun setEnabled(context: Context, on: Boolean) =
            context.getSharedPreferences("settings", 0).edit().putBoolean("on_lock", on).apply()

        fun show(context: Context) {
            if (!enabled(context)) return
            val intent = Intent(context, LockActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
            context.startActivity(intent)
        }
    }
}

/** Какой спутник сейчас на виду: слух говорит через него. */
object Stages {
    var overlay: StageView? = null
    var lock: StageView? = null

    fun current(): StageView? = lock ?: overlay
}
