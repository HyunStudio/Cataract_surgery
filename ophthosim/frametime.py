"""Bounded frame-time statistics for the *experimental* 3D renderer.

Measures CPU-observed wall-clock intervals only. Because OpenGL commands run
asynchronously and buffer swaps may wait for vertical sync, these numbers are
not GPU execution times. They support the GL08 checklist row (mean/P95 at
1920x1080) but never by themselves establish Windows hardware validation,
4K readability or clinical training value.
"""
from __future__ import annotations

from collections import deque
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

    Memory stays bounded during long sessions: older samples are discarded.
    Unknown section names are rejected instead of silently creating buckets.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 1_000_000:
            raise ValueError("Profiler capacity must be a bounded integer")
        self.capacity = capacity
        self._samples = {name: deque(maxlen=capacity) for name in SECTIONS}

    def record(self, section: str, ms: object) -> None:
        if section not in self._samples:
            raise ValueError(f"Unknown profiler section: {section!r}")
        self._samples[section].append(_sample(ms))

    def count(self, section: str = "frame") -> int:
        if section not in self._samples:
            raise ValueError(f"Unknown profiler section: {section!r}")
        return len(self._samples[section])

    def stats(self, section: str = "frame") -> FrameStats | None:
        if section not in self._samples:
            raise ValueError(f"Unknown profiler section: {section!r}")
        samples = self._samples[section]
        return summarize(samples) if samples else None

    def reset(self) -> None:
        for samples in self._samples.values():
            samples.clear()

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
