"""Точка входа собранного ядра (ADR-0019): то же, что `python -m vtuber`."""

from vtuber.bootstrap.main import run

raise SystemExit(run())
