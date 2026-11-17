package ru.umnick.pocket

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Автозапуск при включении телефона (S-24.2): служба поднимается сама, без открытия приложения. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Permissions.ready(context)) CompanionService.start(context)
    }
}
