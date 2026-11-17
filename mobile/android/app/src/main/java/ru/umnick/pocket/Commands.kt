package ru.umnick.pocket

/** Разбор запроса после имени (чистые функции, проверяются тестом `CommandsTest`). */
object Commands {
    sealed interface Command {
        data object Read : Command
        data class Write(val text: String) : Command
    }

    private val NAME = Regex("""^(умник|умничка)[,!.\s]*""")
    private val WRITE = Regex("""^(запиши|записать|добавь|заметка|в блокнот)(\s+(в блокнот|в заметки|заметку))?[:,\s]*""")
    private val READ = Regex("(прочитай|прочти|какие|покажи).*(замет|блокнот)")

    fun stripName(text: String): String = text.trim().lowercase().replace(NAME, "").trim()

    /** «запиши купить молоко» → Write; «прочитай заметки» → Read; иначе — вся фраза и есть заметка. */
    fun parse(request: String): Command = when {
        READ.containsMatchIn(request) -> Command.Read
        else -> Command.Write(request.replace(WRITE, "").trim().ifEmpty { request })
    }
}
