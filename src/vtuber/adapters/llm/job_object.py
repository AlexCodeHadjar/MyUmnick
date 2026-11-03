"""Дочерний процесс умирает вместе с ядром (S-17.1): Windows Job Object с KILL_ON_JOB_CLOSE.

Штатный выход останавливает llama-server сам, но при жёстком завершении ядра сервер остался бы
держать видеопамять и порт. Система закрывает описатель задания при смерти процесса, а вместе с ним
и сервер.
"""

import sys

from vtuber.kernel import get_logger

_log = get_logger(__name__)


class ChildBinding:
    """Держит описатель задания: пока ядро живо, задание открыто; на других системах пусто."""

    def __init__(self) -> None:
        self._handle: int | None = None

    def bind(self, pid: int) -> None:
        """Привязать процесс; неудача — только предупреждение: сервер всё равно работает."""
        if sys.platform != "win32":
            return
        try:
            self._handle = _assign(self._handle, pid)
        except OSError as exc:
            _log.warning("llama_server.not_bound_to_core", problem=str(exc))


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _KILL_ON_JOB_CLOSE = 0x2000
    _PROCESS_SET_QUOTA = 0x0100
    _PROCESS_TERMINATE = 0x0001

    class _BasicLimits(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _IoCounters(ctypes.Structure):
        _fields_ = tuple((name, ctypes.c_uint64) for name in ("r", "w", "o", "rb", "wb", "ob"))

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _BasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    def _new_job(kernel32: ctypes.WinDLL) -> int:
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
        done = kernel32.SetInformationJobObject(
            wintypes.HANDLE(job),
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )
        if not done:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(job)

    def _assign(job: int | None, pid: int) -> int:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        current = _new_job(kernel32) if job is None else job
        kernel32.OpenProcess.restype = wintypes.HANDLE
        process = kernel32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, 0, pid)
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not kernel32.AssignProcessToJobObject(
                wintypes.HANDLE(current), wintypes.HANDLE(process)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(wintypes.HANDLE(process))
        return current
