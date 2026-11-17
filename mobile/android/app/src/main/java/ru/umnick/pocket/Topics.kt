package ru.umnick.pocket

/**
 * Тема приложения по имени пакета — как `topicOf` в `remarks.ts` ПК (там — по имени процесса):
 * от неё зависят фразы «о программе» (T12) и «смотрим вместе» (T14).
 */
object Topics {
    private val RULES: List<Pair<String, List<String>>> = listOf(
        "video" to listOf("youtube", "netflix", "twitch", "vk.video", "kinopoisk", "ivi", "okko", "videoplayer", "mxtech", "vlc", "rutube", "tiktok"),
        "music" to listOf("music", "spotify", "yandex.music", "zvuk", "soundcloud", "deezer", "boom", "player"),
        "chat" to listOf("telegram", "whatsapp", "discord", "viber", "messag", "vkontakte", "slack", "teams"),
        "browser" to listOf("chrome", "firefox", "browser", "opera", "edge", "brave", "yandex.searchapp"),
        "game" to listOf("game", "games", "supercell", "mihoyo", "hoyoverse", "roblox", "mojang", "unity"),
        "office" to listOf("docs", "office", "word", "excel", "sheets", "notion", "obsidian", "keep", "notes", "mail", "gmail"),
        "code" to listOf("termux", "github", "acode", "code"),
        "files" to listOf("files", "filemanager", "documentsui", "explorer", "gallery", "photos"),
        "desktop" to listOf("launcher", "nexuslauncher", "hilauncher", "home"),
    )

    fun of(pkg: String): String {
        val name = pkg.lowercase()
        if (name.isEmpty()) return "other"
        return RULES.firstOrNull { (_, keys) -> keys.any { it in name } }?.first ?: "other"
    }
}
