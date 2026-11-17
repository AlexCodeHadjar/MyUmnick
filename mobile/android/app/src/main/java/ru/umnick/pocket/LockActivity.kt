package ru.umnick.pocket

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
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
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        )
        window.clearFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND)
        stage = StageView(this, LockHost(this)).also {
            it.attach()
            Stages.lock = it
        }
        registerReceiver(unlocked, IntentFilter(Intent.ACTION_USER_PRESENT))
    }

    override fun onDestroy() {
        unregisterReceiver(unlocked)
        if (Stages.lock === stage) Stages.lock = null
        Stages.overlay?.visibility = android.view.View.VISIBLE
        super.onDestroy()
    }

    companion object {
        fun show(context: Context) {
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
