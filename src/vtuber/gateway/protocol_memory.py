"""Сообщения об управлении памятью: приватный режим, очистка, редактор (S-17.2, S-16.2)."""

from collections.abc import Sequence
from typing import Literal, Self

from vtuber.domain import Fact
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, EmptyData, ProtocolModel, Version


class PrivacySetData(ProtocolModel):
    """Включить или выключить приватный режим."""

    enabled: bool


class PrivacySet(ProtocolModel):
    """UI → Ядро: разговор не запоминается (S-17.2)."""

    v: Version
    type: Literal["privacy.set"]
    data: PrivacySetData


class EraseData(ProtocolModel):
    """`confirm` — пользователь подтвердил: без него очистка не выполняется."""

    confirm: bool


class MemoryErase(ProtocolModel):
    """UI → Ядро: удалить всю память."""

    v: Version
    type: Literal["memory.erase"]
    data: EraseData


class PrivacyStateData(ProtocolModel):
    """Режим и можно ли очистить память (она может быть выключена)."""

    enabled: bool
    erasable: bool


class PrivacyState(ProtocolModel):
    """Ядро → UI: состояние режима; приходит при подключении и после переключения."""

    v: Version = PROTOCOL_VERSION
    type: Literal["privacy.state"] = "privacy.state"
    data: PrivacyStateData

    @classmethod
    def of(cls, *, enabled: bool, erasable: bool) -> Self:
        """Сообщение о состоянии."""
        return cls(data=PrivacyStateData(enabled=enabled, erasable=erasable))


class ErasedData(ProtocolModel):
    """`problem` — None, если всё удалено."""

    problem: str | None


class MemoryErased(ProtocolModel):
    """Ядро → UI: итог очистки."""

    v: Version = PROTOCOL_VERSION
    type: Literal["memory.erased"] = "memory.erased"
    data: ErasedData

    @classmethod
    def of(cls, problem: str | None) -> Self:
        """Итог; `problem` — текст для пользователя."""
        return cls(data=ErasedData(problem=problem))


class MemoryList(ProtocolModel):
    """UI → Ядро: открыта панель памяти, нужен список."""

    v: Version
    type: Literal["memory.list"]
    data: EmptyData


class FactSaveData(ProtocolModel):
    """Новый текст факта."""

    note: str
    text: str


class MemoryFactSave(ProtocolModel):
    """UI → Ядро: исправить факт."""

    v: Version
    type: Literal["memory.fact_save"]
    data: FactSaveData


class FactDeleteData(ProtocolModel):
    """Какой факт удалить."""

    note: str


class MemoryFactDelete(ProtocolModel):
    """UI → Ядро: удалить факт."""

    v: Version
    type: Literal["memory.fact_delete"]
    data: FactDeleteData


class FactData(ProtocolModel):
    """Факт с его источником."""

    note: str
    text: str
    source: str
    importance: float
    created: str


class FactsData(ProtocolModel):
    """Список фактов; `problem` — что не удалось сделать."""

    facts: list[FactData]
    problem: str | None


class MemoryFacts(ProtocolModel):
    """Ядро → UI: факты памяти (S-16.2)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["memory.facts"] = "memory.facts"
    data: FactsData

    @classmethod
    def of(cls, facts: Sequence[Fact], problem: str | None) -> Self:
        """Список из фактов домена."""
        items = [
            FactData(
                note=fact.note,
                text=fact.text,
                source=fact.source.value,
                importance=fact.importance,
                created=fact.created_at.isoformat(),
            )
            for fact in facts
        ]
        return cls(data=FactsData(facts=items, problem=problem))


class MemoryTransfer(ProtocolModel):
    """UI → Ядро: перенести факты о пользователе в другое издание (S-20.10)."""

    v: Version
    type: Literal["memory.transfer"]
    data: EmptyData


class TransferredData(ProtocolModel):
    """Итог переноса: сколько фактов выгружено, или текст ошибки."""

    count: int | None
    problem: str | None


class MemoryTransferred(ProtocolModel):
    """Ядро → UI: перенос закончен (идёт в простое, поэтому — отдельным сообщением)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["memory.transferred"] = "memory.transferred"
    data: TransferredData

    @classmethod
    def of(cls, count: int | None, problem: str | None) -> Self:
        """Итог переноса."""
        return cls(data=TransferredData(count=count, problem=problem))
