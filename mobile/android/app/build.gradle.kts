// Карманный Умник (Этап 24, ADR-0050). Зависимости — только AndroidX и Vosk.
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ru.umnick.pocket"
    compileSdk = 35
    defaultConfig {
        applicationId = "ru.umnick.pocket"
        minSdk = 26
        targetSdk = 35
        versionCode = 8
        versionName = "0.8"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    androidResources { noCompress += listOf("webp", "json") }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("com.alphacephei:vosk-android:0.3.47")
    testImplementation("junit:junit:4.13.2")
}
