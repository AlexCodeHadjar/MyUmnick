package ru.umnick.pocket

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.provider.Settings

/** Что нужно спутнику для работы: оверлей обязателен, микрофон — только для голоса. */
object Permissions {
    fun overlay(context: Context): Boolean = Settings.canDrawOverlays(context)

    fun microphone(context: Context): Boolean =
        context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    fun ready(context: Context): Boolean = overlay(context)
}
