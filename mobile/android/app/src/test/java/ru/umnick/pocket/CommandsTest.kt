package ru.umnick.pocket

import org.junit.Assert.assertEquals
import org.junit.Test

class CommandsTest {
    @Test fun writesDictation() {
        assertEquals(Commands.Command.Write("купить молоко"), Commands.parse(Commands.stripName("Умник, запиши купить молоко")))
        assertEquals(Commands.Command.Write("позвонить маме"), Commands.parse("добавь в заметки позвонить маме"))
        assertEquals(Commands.Command.Write("забрать посылку"), Commands.parse("забрать посылку"))
    }

    @Test fun readsNotes() {
        assertEquals(Commands.Command.Read, Commands.parse("прочитай заметки"))
        assertEquals(Commands.Command.Read, Commands.parse("какие у меня заметки"))
    }
}
