"""Сообщения вне хода диалога: панель ресурсов (S-12.10) и мастер первого запуска (S-13.2)."""

from typing import Literal, Self

from vtuber.application.scheduler import ModelStatus, ResourceSnapshot
from vtuber.application.setup import InstallProgress, SetupCatalog, SetupState
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, EmptyData, ProtocolModel, Version


class WatchData(ProtocolModel):
    """Открыта ли панель ресурсов."""

    enabled: bool


class ResourcesWatch(ProtocolModel):
    """UI → Ядро: панель ресурсов открыли или закрыли; закрытая ничего не считает."""

    v: Version
    type: Literal["resources.watch"]
    data: WatchData


class InstallData(ProtocolModel):
    """Что выбрал пользователь в мастере."""

    item_ids: list[str]
    voice: str


class SetupInstall(ProtocolModel):
    """UI → Ядро: согласие на загрузку; без этого сообщения ничего не скачивается (S-13.2)."""

    v: Version
    type: Literal["setup.install"]
    data: InstallData


class SetupCancel(ProtocolModel):
    """UI → Ядро: прервать загрузку; скачанное продолжится при следующей попытке."""

    v: Version
    type: Literal["setup.cancel"]
    data: EmptyData


class PinnedModelData(ProtocolModel):
    """Закреплённая модель: основная LLM, распознавание речи."""

    name: str
    vram_mb: int


class ManagedModelData(ProtocolModel):
    """Модель под управлением менеджера; `waiting_reason` — почему ждёт."""

    name: str
    vram_mb: int
    priority: str
    state: str
    users: int
    waiting_reason: str | None


class ResourcesData(ProtocolModel):
    """Снимок видеопамяти: `limit_mb` учитывает другие программы, `capacity_mb` — только конфиг."""

    limit_mb: int
    capacity_mb: int
    free_mb: int
    pinned: list[PinnedModelData]
    models: list[ManagedModelData]


class ResourcesMessage(ProtocolModel):
    """Ядро → UI: снимок для панели ресурсов, только пока она открыта (S-12.10)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["resources.snapshot"] = "resources.snapshot"
    data: ResourcesData

    @classmethod
    def of(cls, snapshot: ResourceSnapshot) -> Self:
        """Сообщение из снимка менеджера."""
        return cls(
            data=ResourcesData(
                limit_mb=snapshot.limit_mb,
                capacity_mb=snapshot.capacity_mb,
                free_mb=snapshot.free_mb,
                pinned=[PinnedModelData(name=n, vram_mb=mb) for n, mb in snapshot.pinned],
                models=[_model_data(status) for status in snapshot.models],
            )
        )


def _model_data(status: ModelStatus) -> ManagedModelData:
    return ManagedModelData(
        name=status.spec.name,
        vram_mb=status.spec.vram_mb,
        priority=status.spec.priority.name.lower(),
        state=status.state.value,
        users=status.users,
        waiting_reason=status.waiting_reason,
    )


class SetupItemData(ProtocolModel):
    """Компонент в мастере; `license` пользователь видит до согласия."""

    id: str
    title: str
    license: str
    size: int
    required: bool
    recommended: bool
    installed: bool


class SetupData(ProtocolModel):
    """Состояние мастера: `gpu_total_mb` — None, если карта NVIDIA не найдена."""

    needed: bool
    gpu_total_mb: int | None
    voices: list[str]
    voice: str
    warnings: list[str]
    items: list[SetupItemData]


class SetupStateMessage(ProtocolModel):
    """Ядро → UI: нужен ли мастер и что он предлагает; приходит при подключении."""

    v: Version = PROTOCOL_VERSION
    type: Literal["setup.state"] = "setup.state"
    data: SetupData

    @classmethod
    def of(cls, state: SetupState, catalog: SetupCatalog) -> Self:
        """Сообщение из состояния мастера."""
        advice = state.recommendation
        items = [
            SetupItemData(
                id=item.id,
                title=item.title,
                license=item.license,
                size=item.size,
                required=item.required,
                recommended=item.id in advice.item_ids,
                installed=item.id in state.installed,
            )
            for item in catalog.items
        ]
        total = None if state.gpu is None else state.gpu.total_mb
        data = SetupData(
            needed=state.needed,
            gpu_total_mb=total,
            voices=list(catalog.voices),
            voice=advice.voice,
            warnings=list(advice.warnings),
            items=items,
        )
        return cls(data=data)


class ProgressData(ProtocolModel):
    """Сколько байт готово из общего числа и какой файл качается."""

    done: int
    total: int
    file: str


class SetupProgress(ProtocolModel):
    """Ядро → UI: ход загрузки."""

    v: Version = PROTOCOL_VERSION
    type: Literal["setup.progress"] = "setup.progress"
    data: ProgressData

    @classmethod
    def of(cls, progress: InstallProgress) -> Self:
        """Сообщение из хода установки."""
        return cls(data=ProgressData(done=progress.done, total=progress.total, file=progress.file))


class FinishedData(ProtocolModel):
    """Итог установки: `problem` — None, если всё поставлено."""

    problem: str | None


class SetupFinished(ProtocolModel):
    """Ядро → UI: установка закончена; после успеха приложение перезапускается."""

    v: Version = PROTOCOL_VERSION
    type: Literal["setup.finished"] = "setup.finished"
    data: FinishedData

    @classmethod
    def of(cls, problem: str | None) -> Self:
        """Итог; `problem` — текст для пользователя."""
        return cls(data=FinishedData(problem=problem))


class BlockedData(ProtocolModel):
    """Кто и что написал."""

    author: str
    text: str


class ViewerBlockedMessage(ProtocolModel):
    """Ядро → UI: реплика зрителя заблокирована как атака; ведущий решает, что делать (FR-31)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["viewer.blocked"] = "viewer.blocked"
    data: BlockedData

    @classmethod
    def of(cls, author: str, text: str) -> Self:
        """Сообщение о блокировке."""
        return cls(data=BlockedData(author=author, text=text))


class NoticeData(ProtocolModel):
    """Текст для пользователя."""

    text: str


class BackendNoticeMessage(ProtocolModel):
    """Ядро → UI: компонент упал, поднимается или снова работает (S-17.1)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["backend.notice"] = "backend.notice"
    data: NoticeData

    @classmethod
    def of(cls, text: str) -> Self:
        """Сообщение с текстом."""
        return cls(data=NoticeData(text=text))
