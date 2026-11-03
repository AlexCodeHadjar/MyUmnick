"""Опрос видеокарты для менеджера ресурсов (ADR-0018)."""

from vtuber.adapters.gpu.nvidia_smi import NvidiaSmiConfig, NvidiaSmiProbe, parse_memory

__all__ = ["NvidiaSmiConfig", "NvidiaSmiProbe", "parse_memory"]
