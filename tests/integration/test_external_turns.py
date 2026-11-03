"""Реплики зрителей → ходы: по одной, не перебивая речь, с показом в чате UI."""

import asyncio
from collections.abc import AsyncGenerator

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from tests.fakes.conversation import make_conversation
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory, TurnHints
from vtuber.application.pipeline import ChunkerConfig, ReplyPipeline, Voice
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    CancelReason,
    IncomingMessage,
    Persona,
    viewer_line,
)
from vtuber.gateway import ExternalTurns, InputBargeIn, InputFinal, OutboundMessage
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

FMT = AudioFormat(sample_rate=1000)
SPEECH_S = 0.1


class _ShortTTS:
    """Голос: на каждую фразу — ровно `SPEECH_S` секунд звука, мгновенно."""

    @property
    def audio_format(self) -> AudioFormat:
        return FMT

    async def synthesize(self, text: str) -> AsyncGenerator[AudioChunk]:
        yield AudioChunk(FMT, b"\x00" * int(SPEECH_S * FMT.bytes_per_second))


def _voiced_service() -> ConversationService:
    bus = EventBus()
    voice = Voice(_ShortTTS(), ChunkerConfig(first_min_words=4, next_min_words=10, max_words=25))
    pipeline = ReplyPipeline(
        FakeLLM("Привет."), GenerationParams(32, 0.5), Telemetry(bus, FakeClock()), voice
    )
    persona = Persona(name="Мика", language="русский", description="", speech_style="", rules=())
    budget = ContextBudget(
        ContextConfig(
            max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
        )
    )
    return ConversationService(pipeline, PromptBuilder(persona), ShortTermMemory(budget), bus)


def _turns(
    llm: FakeLLM, *, client: bool = True
) -> tuple[ConversationService, list[OutboundMessage], ExternalTurns]:
    bus = EventBus()
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    async def send_bytes(_: bytes) -> None:
        await asyncio.sleep(0)

    return service, sent, ExternalTurns(service, send, send_bytes, lambda: client)


async def _two_viewers() -> AsyncGenerator[IncomingMessage]:
    yield IncomingMessage("fake", "аня", "привет")
    yield IncomingMessage("fake", "боря", "пока")


async def test_messages_become_turns_one_by_one() -> None:
    llm = FakeLLM("Ок")
    _, sent, turns = _turns(llm)

    await turns.run(_two_viewers)

    assert [m for m in sent if isinstance(m, InputFinal)] == [
        InputFinal.of("аня: привет"),
        InputFinal.of("боря: пока"),
    ]
    assert [call[0][-1].text for call in llm.calls] == [
        viewer_line("аня", "привет"),
        viewer_line("боря", "пока"),
    ]


async def test_external_turn_gets_no_tools_or_memory_and_teaches_no_facts() -> None:
    llm = FakeLLM("Ок")
    service, _, turns = _turns(llm)
    asked: list[str] = []

    async def hints(text: str) -> TurnHints:
        asked.append(text)
        return TurnHints(context=("секрет ведущего",))

    service.use_tools(hints)
    service.use_memory(hints)

    await turns.run(_two_viewers)
    await service.handle("вопрос ведущего", RecordingSink())
    await service.wait_idle()

    assert asked == ["вопрос ведущего", "вопрос ведущего"]
    assert all("секрет" not in call[0][-1].text for call in llm.calls[:2])
    assert "секрет ведущего" in llm.calls[2][0][-1].text


async def test_without_ui_messages_are_lost_not_answered() -> None:
    llm = FakeLLM("Ок")
    _, sent, turns = _turns(llm, client=False)

    await turns.run(_two_viewers)

    assert sent == []
    assert llm.calls == []


async def test_broken_source_is_contained() -> None:
    _, _, turns = _turns(FakeLLM("Ок"))

    async def broken() -> AsyncGenerator[IncomingMessage]:
        yield IncomingMessage("fake", "а", "б")
        raise RuntimeError

    await turns.run(broken)


async def test_wait_silent_lasts_until_sound_of_turn_ends() -> None:
    service = _voiced_service()
    loop = asyncio.get_running_loop()

    await service.handle("привет", RecordingSink())
    await service.wait_idle()
    started = loop.time()
    await service.wait_silent()

    # Ход закончился раньше звука: тишина наступает примерно через его длительность.
    assert loop.time() - started >= SPEECH_S / 2


async def test_cancel_means_silence_at_once() -> None:
    service = _voiced_service()
    loop = asyncio.get_running_loop()

    await service.handle("привет", RecordingSink())
    await service.wait_idle()
    await service.cancel(CancelReason.USER_STOP)
    started = loop.time()
    await service.wait_silent()

    assert loop.time() - started < SPEECH_S / 2


async def test_initiative_line_is_not_shown_as_a_message_and_stays_external() -> None:
    llm = FakeLLM("Как прошёл день?")
    service, sent, external = _turns(llm)
    await external.initiate("(заговори сама)")
    assert not [message for message in sent if isinstance(message, InputFinal)]
    assert not service.engaged
    assert llm.calls[-1][0][-1].text == "(заговори сама)"


async def test_host_input_is_reported_and_stops_only_external_speech() -> None:
    service, sent, external = _turns(FakeLLM("Да."))
    seen: list[str] = []
    service.observe_input(lambda: seen.append("ввод"))
    await external.initiate("(заговори сама)")
    assert seen == []

    service.typing("черновик")
    assert seen == ["ввод"]
    assert service.engaged, "недописанная реплика: заговаривать нельзя"
    await external.stop_initiative()
    assert [m for m in sent if isinstance(m, InputBargeIn)], "голос законченного хода глушит UI"

    sink = RecordingSink()
    await service.handle("Привет", sink)
    before = len([m for m in sent if isinstance(m, InputBargeIn)])
    await external.stop_initiative()
    await service.wait_idle()
    assert len([m for m in sent if isinstance(m, InputBargeIn)]) == before
