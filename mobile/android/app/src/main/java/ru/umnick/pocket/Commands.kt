package ru.umnick.pocket

/** Разбор запроса после имени (чистые функции, проверяются тестом `CommandsTest`). */
object Commands {
    sealed interface Command {
        data object Read : Command
        data class Write(val text: String) : Command
    }

    // Vosk small-ru слышит имя по-разному; всё до имени включительно («эй, умник») — не запрос.
    private val NAME = Regex("""^(.*?\s)?(умник[а-я]*|умничк[а-я]*|ум ник)(?=[\s,!.?]|$)[,!.?\s]*""")
    private val WRITE = Regex("""^(запиши|записать|добавь|заметка|в блокнот)(\s+(в блокнот|в заметки|заметку))?[:,\s]*""")
    private val READ = Regex("(прочитай|прочти|какие|покажи).*(замет|блокнот)")

    fun hasName(text: String): Boolean = NAME.containsMatchIn(text.trim().lowercase())

    fun stripName(text: String): String = text.trim().lowercase().replaceFirst(NAME, "").trim()

    /** «запиши купить молоко» → Write; «прочитай заметки» → Read; иначе — вся фраза и есть заметка. */
    fun parse(request: String): Command = when {
        READ.containsMatchIn(request) -> Command.Read
        else -> Command.Write(request.replace(WRITE, "").trim().ifEmpty { request })
    }
}
