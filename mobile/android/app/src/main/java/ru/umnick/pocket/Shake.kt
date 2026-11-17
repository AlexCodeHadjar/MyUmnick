package ru.umnick.pocket

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.SystemClock
import kotlin.math.sqrt

/** Встряска телефона — аналог тряски мышью на ПК (T4): спутнику кружит голову. */
class Shake(context: Context, private val onShake: () -> Unit) : SensorEventListener {
    private val sensors = context.getSystemService(SensorManager::class.java)
    private var lastShake = 0L

    fun start() {
        val accel = sensors.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION) ?: return
        sensors.registerListener(this, accel, SensorManager.SENSOR_DELAY_UI)
    }

    fun stop() = sensors.unregisterListener(this)

    override fun onSensorChanged(event: SensorEvent) {
        val (x, y, z) = event.values
        val now = SystemClock.uptimeMillis()
        if (sqrt(x * x + y * y + z * z) < THRESHOLD || now - lastShake < COOLDOWN) return
        lastShake = now
        onShake()
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) = Unit

    private companion object {
        const val THRESHOLD = 14f
        const val COOLDOWN = 4000L
    }
}
