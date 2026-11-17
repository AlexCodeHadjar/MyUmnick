package ru.umnick.pocket

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.KeyguardManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.IntentFilter
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

/**
 * Служба переднего плана (S-24.2): держит оверлей со спутником и слух. HiOS убивает фон —
 * поэтому уведомление постоянное и `START_STICKY`.
 */
class CompanionService : Service() {
    private var stage: StageView? = null
    private var ears: Ears? = null
    private var shake: Shake? = null

    /**
     * Экран погас — заранее поднимаем окно на экране блокировки, чтобы при включении спутник уже был
     * там; разблокировали — LockActivity закрывается сама, оверлей снова виден.
     */
    private val screen = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val locked = getSystemService(KeyguardManager::class.java).isKeyguardLocked
            when (intent.action) {
                Intent.ACTION_SCREEN_OFF -> showOnLock()
                Intent.ACTION_SCREEN_ON -> if (locked && Stages.lock == null) showOnLock()
                Intent.ACTION_USER_PRESENT -> Stages.overlay?.visibility = android.view.View.VISIBLE
            }
        }
    }

    private fun showOnLock() {
        Stages.overlay?.visibility = android.view.View.INVISIBLE
        runCatching { LockActivity.show(this) }.onFailure { CrashLog.write(this, "lock", it) }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        CrashLog.install(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        goForeground()
        if (stage == null) attachStage()
        syncFolder()
        if (ears == null && Permissions.microphone(this)) ears = Ears(this, Notebook(this), stage!!).also { it.start() }
        return START_STICKY
    }

    override fun onDestroy() {
        ears?.stop()
        runCatching { unregisterReceiver(screen) }
        shake?.stop()
        stage?.detach()
        super.onDestroy()
    }

    private fun attachStage() {
        val view = StageView(this, OverlayHost(getSystemService(android.view.WindowManager::class.java)))
        view.attach()
        Stages.overlay = view
        registerReceiver(screen, IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_USER_PRESENT)
        })
        shake = Shake(this) { view.dizzy() }.also { it.start() }
        stage = view
    }

    /** Заметки с ПК из `from_pc.jsonl` и зеркало блокнота для ПК (S-24.6); файлы маленькие — в фоне. */
    private fun syncFolder() = Thread {
        val notebook = Notebook(this)
        NotesFolder.importFromPc(this, notebook)
        NotesFolder.mirror(this, notebook)
    }.start()

    private fun goForeground() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "Умник", NotificationManager.IMPORTANCE_MIN))
        val note = Notification.Builder(this, CHANNEL)
            .setContentTitle("Умник рядом")
            .setContentText("Скажите «Умник, запиши…»")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build()
        val type = if (Permissions.microphone(this)) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
        else ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
        if (Build.VERSION.SDK_INT >= 29) startForeground(ID, note, type) else startForeground(ID, note)
    }

    companion object {
        private const val CHANNEL = "umnick"
        private const val ID = 1

        fun start(context: Context) {
            context.startForegroundService(Intent(context, CompanionService::class.java))
        }
    }
}
