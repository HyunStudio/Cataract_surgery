"""Bounded frame-time statistics for the *experimental* 3D renderer.

Measures CPU-observed wall-clock intervals only. Because OpenGL commands run
asynchronously and buffer swaps may wait for vertical sync, these numbers are
not GPU execution times. They support the GL08 checklist row (mean/P95 at
1920x1080) but never by themselves establish Windows hardware validation,
4K readability or clinical training value.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from typing import Iterable

TARGET_FRAME_MS = 1000. / 60.
MAX_SAMPLE_MS = 10_000.
DEFAULT_CAPACITY = 7200
SECTIONS = ("frame", "probe", "render")
# Renderer strings of common software rasterizers. A match means the run
# cannot count as physical GPU evidence regardless of the measured numbers.
SOFTWARE_RENDERERS = ("llvmpipe", "softpipe", "swrast", "lavapipe",
                      "microsoft basic render", "gdi generic")
GL08_MIN_SIZE = (1920, 1080)
GL08_MIN_SECONDS = 60.


def _sample(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Frame time must be a real number of milliseconds")
    try:
        ms = float(value)
    except OverflowError as exc:
        raise ValueError("Frame time out of range") from exc
    if not math.isfinite(ms) or not 0. <= ms <= MAX_SAMPLE_MS:
        raise ValueError("Frame time out of range")
    return ms


def percentile(ordered: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already ascending sample list."""
    if not ordered:
        raise ValueError("Percentile of an empty sample")
    if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0 <= q <= 100:
        raise ValueError("Percentile must be within 0..100")
    position = (len(ordered) - 1) * q / 100.
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


@dataclass(frozen=True, slots=True)
class FrameStats:
    """Summary of one bounded window of millisecond samples."""
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    over_target_fraction: float

    @property
    def mean_fps(self) -> float:
        return 1000. / self.mean_ms if self.mean_ms > 0. else math.inf

    def as_dict(self) -> dict[str, float | int]:
        return {
            "count": self.count,
            "mean_ms": round(self.mean_ms, 3),
            "p50_ms": round(self.p50_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "over_target_fraction": round(self.over_target_fraction, 4),
        }


def summarize(samples: Iterable[float],
              target_ms: float = TARGET_FRAME_MS) -> FrameStats:
    values = sorted(_sample(s) for s in samples)
    if not values:
        raise ValueError("No frame samples recorded")
    target = _sample(target_ms)
    return FrameStats(
        count=len(values),
        mean_ms=math.fsum(values) / len(values),
        p50_ms=percentile(values, 50),
        p95_ms=percentile(values, 95),
        p99_ms=percentile(values, 99),
        min_ms=values[0],
        max_ms=values[-1],
        over_target_fraction=sum(v > target for v in values) / len(values),
    )


class FrameProfiler:
    """Fixed-capacity rolling samples per named section.

    Each section is a ring buffer of C doubles allocated (and touched) up
    front, so recording never grows process memory: otherwise the profiler
    itself would show up as "memory growth" in GL07 runs. Once full, the
    oldest samples are overwritten. Unknown section names are rejected.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 1_000_000:
            raise ValueError("Profiler capacity must be a bounded integer")
        self.capacity = capacity
        self._samples = {name: array("d", bytes(8 * capacity))
                         for name in SECTIONS}
        self._counts = dict.fromkeys(SECTIONS, 0)
        self._next = dict.fromkeys(SECTIONS, 0)

    def _check(self, section: object) -> None:
        if section not in self._samples:
            raise ValueError(f"Unknown profiler section: {section!r}")

    def record(self, section: str, ms: object) -> None:
        self._check(section)
        value = _sample(ms)
        slot = self._next[section]
        self._samples[section][slot] = value
        self._next[section] = (slot + 1) % self.capacity
        self._counts[section] = min(self._counts[section] + 1, self.capacity)

    def count(self, section: str = "frame") -> int:
        self._check(section)
        return self._counts[section]

    def stats(self, section: str = "frame") -> FrameStats | None:
        self._check(section)
        count = self._counts[section]
        # Order is irrelevant to the statistics; only filled slots count.
        return summarize(self._samples[section][:count]) if count else None

    def reset(self) -> None:
        for name in SECTIONS:
            self._counts[name] = 0
            self._next[name] = 0

    def report(self) -> dict[str, dict[str, float | int] | None]:
        result = {}
        for name in SECTIONS:
            stats = self.stats(name)
            result[name] = stats.as_dict() if stats is not None else None
        return result


def is_software_renderer(renderer: object) -> bool:
    """Unknown or missing renderer strings are treated as non-hardware."""
    if not isinstance(renderer, str) or not renderer.strip():
        return True
    lowered = renderer.strip().lower()
    return lowered == "unknown" or any(name in lowered for name in SOFTWARE_RENDERERS)


def gl08_assessment(frame: FrameStats | None, size: tuple[int, int],
                    seconds: float, renderer: object) -> dict[str, object]:
    """Classify evidence for the GL08 row; a human still signs the checklist.

    ``INSUFFICIENT_EVIDENCE`` covers software GL, short runs and resolutions
    below 1920x1080. Otherwise the measured mean and P95 are compared with a
    60 fps frame budget, yielding a *candidate* result, never a final PASS.
    """
    reasons = []
    if frame is None:
        reasons.append("no frames measured")
    if is_software_renderer(renderer):
        reasons.append("software or unknown OpenGL renderer")
    width, height = size
    if width < GL08_MIN_SIZE[0] or height < GL08_MIN_SIZE[1]:
        reasons.append("window smaller than 1920x1080")
    if not math.isfinite(seconds) or seconds < GL08_MIN_SECONDS:
        reasons.append(f"measured duration below {GL08_MIN_SECONDS:.0f} s")
    within = (frame is not None and frame.mean_ms <= TARGET_FRAME_MS
              and frame.p95_ms <= TARGET_FRAME_MS)
    if reasons:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "CANDIDATE_WITHIN_60FPS" if within else "CANDIDATE_BELOW_60FPS"
    return {"status": status, "reasons": reasons,
            "target_frame_ms": round(TARGET_FRAME_MS, 3),
            "mean_and_p95_within_target": within,
            "requires_human_signoff": True}


# --- GL07: process memory over long runs ---------------------------------
GL07_MIN_SECONDS = 300.
# Triage heuristics for the report only; a person still decides GL07.
GL07_MAX_GROWTH_MB = 16.
GL07_MAX_SLOPE_MB_PER_MIN = 1.


def _rss_linux(path: str = "/proc/self/statm") -> float | None:
    import os
    try:
        with open(path, encoding="ascii") as handle:
            resident_pages = int(handle.read().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE") / 2**20
    except (OSError, ValueError, IndexError):
        return None


def _rss_windows() -> float | None:
    try:
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        kernel32 = ctypes.WinDLL("kernel32")
        psapi = ctypes.WinDLL("psapi")
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(),
                                          ctypes.byref(counters), counters.cb):
            return None
        return counters.WorkingSetSize / 2**20
    except (AttributeError, ImportError, OSError):
        return None


def process_rss_mb(platform_name: str | None = None) -> float | None:
    """Resident set / working set of this process in MiB, or None if unknown.

    Host memory only: textures and buffers held in dedicated GPU memory are
    not visible here, so GPU-side leaks need driver tools.
    """
    import sys
    name = sys.platform if platform_name is None else platform_name
    if name.startswith("linux"):
        return _rss_linux()
    if name == "win32":
        return _rss_windows()
    return None


@dataclass(frozen=True, slots=True)
class MemoryTrend:
    samples: int
    start_mb: float
    end_mb: float
    peak_mb: float
    growth_mb: float
    slope_mb_per_min: float
    # Second half of the run only: driver/allocator warm-up plateaus early,
    # whereas a leak keeps rising, so triage uses this slope.
    late_slope_mb_per_min: float

    def as_dict(self) -> dict[str, float | int]:
        return {"samples": self.samples,
                "start_mb": round(self.start_mb, 2),
                "end_mb": round(self.end_mb, 2),
                "peak_mb": round(self.peak_mb, 2),
                "growth_mb": round(self.growth_mb, 2),
                "slope_mb_per_min": round(self.slope_mb_per_min, 3),
                "late_slope_mb_per_min": round(self.late_slope_mb_per_min, 3)}


def memory_trend(samples: Iterable[tuple[float, float]]) -> MemoryTrend | None:
    """Least-squares slope and start/end/peak of (seconds, MiB) samples."""
    points = []
    for item in samples:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError("Memory samples must be (seconds, MiB) pairs")
        seconds, mb = item
        for value in item:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError("Memory sample out of range")
        points.append((float(seconds), float(mb)))
    if len(points) < 2:
        return None
    midpoint = (points[0][0] + points[-1][0]) / 2.
    late = [p for p in points if p[0] >= midpoint]
    return MemoryTrend(samples=len(points), start_mb=points[0][1],
                       end_mb=points[-1][1], peak_mb=max(m for _, m in points),
                       growth_mb=points[-1][1] - points[0][1],
                       slope_mb_per_min=_slope(points) * 60.,
                       late_slope_mb_per_min=_slope(late) * 60.)


def _slope(points: list[tuple[float, float]]) -> float:
    """Least-squares MiB per second; 0 for fewer than two distinct times."""
    if len(points) < 2:
        return 0.
    mean_t = math.fsum(t for t, _ in points) / len(points)
    mean_m = math.fsum(m for _, m in points) / len(points)
    spread = math.fsum((t - mean_t) ** 2 for t, _ in points)
    if spread <= 0.:
        return 0.
    return math.fsum((t - mean_t) * (m - mean_m) for t, m in points) / spread


def gl07_assessment(trend: MemoryTrend | None, seconds: float,
                    renderer: object) -> dict[str, object]:
    """Triage evidence for GL07 (5-minute run, no memory growth)."""
    reasons = []
    if trend is None:
        reasons.append("process memory not measurable on this platform")
    if is_software_renderer(renderer):
        reasons.append("software or unknown OpenGL renderer")
    if not math.isfinite(seconds) or seconds < GL07_MIN_SECONDS:
        reasons.append(f"measured duration below {GL07_MIN_SECONDS:.0f} s")
    stable = (trend is not None and trend.growth_mb <= GL07_MAX_GROWTH_MB
              and trend.late_slope_mb_per_min <= GL07_MAX_SLOPE_MB_PER_MIN)
    if reasons:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "CANDIDATE_NO_GROWTH" if stable else "CANDIDATE_GROWTH"
    return {"status": status, "reasons": reasons,
            "heuristic_max_growth_mb": GL07_MAX_GROWTH_MB,
            "heuristic_max_slope_mb_per_min": GL07_MAX_SLOPE_MB_PER_MIN,
            "within_heuristics": stable,
            "host_memory_only": True,
            "requires_human_signoff": True}
