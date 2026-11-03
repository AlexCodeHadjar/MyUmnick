"""Адаптеры долговременной памяти: эмбеддеры и хранилища (ADR-0015)."""

from vtuber.adapters.memory.e5_embedder import E5Config, E5Embedder
from vtuber.adapters.memory.obsidian_vault import ObsidianVault
from vtuber.adapters.memory.sqlite_vec import SqliteVecStore

__all__ = ["E5Config", "E5Embedder", "ObsidianVault", "SqliteVecStore"]
