"""Мастер первого запуска (S-13.2): что нужно этой машине и установка с проверкой сумм."""

from vtuber.application.setup.catalog import (
    CatalogFile,
    CatalogItem,
    Recommendation,
    SetupCatalog,
    recommend,
)
from vtuber.application.setup.installer import Installer, InstallProgress, ProgressSink
from vtuber.application.setup.wizard import SetupChoice, SetupState, SetupWizard

__all__ = [
    "CatalogFile",
    "CatalogItem",
    "InstallProgress",
    "Installer",
    "ProgressSink",
    "Recommendation",
    "SetupCatalog",
    "SetupChoice",
    "SetupState",
    "SetupWizard",
    "recommend",
]
