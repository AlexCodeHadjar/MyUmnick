# Карманный Умник (Android) — Этап 24, ADR-0050

Спутник поверх экрана телефона: позы и фразы как на ПК, тап — поглаживание, долгий тап — тык, перетаскивание и
бросок, встряска — кружится голова. Голос: «Умник, запиши …», «Умник, прочитай заметки». Стартует сам при
включении телефона.

## Подготовка
1. Кадры и фразы: `node ui/scripts/export-mobile-pack.ts` (из корня репозитория) → `app/src/main/assets/character/`.
2. Модель речи: распаковать `vosk-model-small-ru-0.22` в `app/src/main/assets/model/` и положить туда файл
   `uuid` с любой строкой (его требует `StorageService.unpack`).
3. JDK 17 (`winget install Microsoft.OpenJDK.17`) и Android SDK в `C:\Android\sdk` (platform 35, build-tools 35.0.0);
   `local.properties`: `sdk.dir=C:/Android/sdk`.
4. Сборка: `JAVA_HOME="C:\Program Files\Microsoft\jdk-17.0.21.21-hotspot"`, затем `./gradlew assembleDebug
   testDebugUnitTest` → `app/build/outputs/apk/debug/app-debug.apk` (~92 МБ, из них 45 — модель речи).

## Установка на телефон
- С отладкой по USB: `C:\Android\sdk\platform-tools\adb.exe install -r app/build/outputs/apk/debug/app-debug.apk`.
- Без отладки: скопировать APK в «Загрузки» телефона (режим «Передача файлов») и открыть его там.

## Первый запуск на телефоне
Шаги в окне приложения: «Поверх других окон», микрофон и уведомления, «Не выключать в фоне» (HiOS иначе
убивает службу), папка `Documents/UmNick` (создать в окне выбора). Затем «Запустить Умника».
