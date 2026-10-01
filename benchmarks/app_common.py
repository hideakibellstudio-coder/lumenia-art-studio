"""Helpers shared by the application-level benchmark scenarios."""

from __future__ import annotations

import json
import statistics
import sys
import time
from typing import Callable


def summary(samples_ms: list[float]) -> dict[str, float]:
    """Median, 95th percentile and maximum of a list of timings in milliseconds."""
    ordered = sorted(samples_ms)
    p95 = ordered[max(0, min(len(ordered) - 1, round((len(ordered) - 1) * 0.95)))]
    return {
        "samples": len(ordered),
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(ordered[-1], 3),
    }


def repeat_ms(action: Callable[[], object], repeats: int) -> list[float]:
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000.0)
    return samples


def parse_sizes(text: str) -> list[tuple[int, int]]:
    """Parse "1920x1080,3840x2160" into [(1920, 1080), (3840, 2160)]."""
    sizes = []
    for item in text.split(","):
        width, height = item.lower().split("x")
        sizes.append((int(width), int(height)))
    return sizes


def peak_memory_mb() -> float | None:
    """Peak resident memory of this process in MB, or None where it cannot be read.

    Monotonic over the process lifetime: the growth caused by one operation is
    the difference between two readings, and only shows when the operation
    raised the peak.
    """
    if sys.platform == "win32":
        return _peak_working_set_windows()
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0
    return round(peak / divisor, 1)


def _peak_working_set_windows() -> float | None:
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return round(counters.PeakWorkingSetSize / (1024.0 * 1024.0), 1)


def emit(result: dict) -> None:
    """Scenarios print their result as the last line of stdout, as JSON."""
    print(json.dumps(result))
