package ru.umnick.pocket

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Первый запуск (S-24.2): разрешения по шагам. После них приложение больше не открывают —
 * служба стартует сама при включении телефона (BootReceiver).
 */
class SetupActivity : Activity() {
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 96, 48, 48) }
        status = TextView(this).apply { textSize = 16f }
        root.addView(status)
        root.addView(button("1. Поверх других окон") { openOverlaySettings() })
        root.addView(button("2. Микрофон и уведомления") { askRuntime() })
        root.addView(button("3. Не выключать в фоне") { askBattery() })
        root.addView(button("4. Папка для обмена с ПК") { NotesFolder.pick(this) })
        root.addView(button("Запустить Умника") { launch() })
        setContentView(root)
    }

    override fun onResume() {
        super.onResume()
        status.text = buildString {
            appendLine("Оверлей: " + mark(Permissions.overlay(this@SetupActivity)))
            appendLine("Микрофон: " + mark(Permissions.microphone(this@SetupActivity)))
            appendLine("Папка обмена: " + mark(NotesFolder.ready(this@SetupActivity)))
        }
    }

    @Deprecated("SAF result")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        NotesFolder.onPicked(this, requestCode, data)
    }

    private fun button(text: String, action: () -> Unit) =
        Button(this).apply { this.text = text; setOnClickListener { action() } }

    private fun mark(ok: Boolean) = if (ok) "есть" else "нет"

    private fun openOverlaySettings() {
        startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
    }

    private fun askRuntime() {
        val wanted = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) wanted += Manifest.permission.POST_NOTIFICATIONS
        requestPermissions(wanted.toTypedArray(), 1)
    }

    private fun askBattery() {
        val power = getSystemService(PowerManager::class.java)
        if (power.isIgnoringBatteryOptimizations(packageName)) return
        startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
    }

    private fun launch() {
        if (!Permissions.ready(this)) return openOverlaySettings()
        CompanionService.start(this)
        finish()
    }
}
