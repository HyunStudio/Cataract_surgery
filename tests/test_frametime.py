"""Frame-time statistics and scripted 3D benchmark workload (no GPU needed).

The numbers are CPU wall-clock diagnostics; these tests never claim Windows
GPU validation. The workload must stay read-only for the synthetic Game.
"""
import argparse
import math
import random
import statistics

import pytest

import ophthosim.gl_benchmark as bench
import ophthosim.surface_probe3d as probes
from ophthosim.frametime import (FrameProfiler, TARGET_FRAME_MS, gl08_assessment,
                                 is_software_renderer, percentile, summarize)
from ophthosim.gl_preview import View
from ophthosim.gl_surgery import SurgeryHUD


def test_percentile_matches_stdlib_inclusive_interpolation():
    rng = random.Random(41)
    for _ in range(200):
        values = sorted(rng.uniform(0., 50.) for _ in range(rng.randint(2, 90)))
        cuts = statistics.quantiles(values, n=100, method="inclusive")
        for q in (1, 50, 95, 99):
            assert percentile(values, q) == pytest.approx(cuts[q-1], abs=1e-9)
        assert percentile(values, 0) == values[0]
        assert percentile(values, 100) == values[-1]
    assert percentile([7.], 95) == 7.


def test_percentile_rejects_empty_and_bad_rank():
    with pytest.raises(ValueError):
        percentile([], 50)
    for q in (-1, 101, True, "95", math.nan):
        with pytest.raises(ValueError):
            percentile([1., 2.], q)


def test_summary_of_known_samples():
    stats = summarize([10., 10., 10., 10., 30.])
    assert stats.count == 5
    assert stats.mean_ms == pytest.approx(14.)
    assert stats.p50_ms == 10.
    assert stats.min_ms == 10. and stats.max_ms == 30.
    assert stats.p95_ms == pytest.approx(26.)
    assert stats.over_target_fraction == pytest.approx(.2)
    assert stats.mean_fps == pytest.approx(1000. / 14.)
    data = stats.as_dict()
    assert data["count"] == 5 and data["p95_ms"] == 26.
    assert "mean_fps" not in data  # only meaningful for whole frames


def test_zero_mean_has_infinite_fps_not_division_error():
    assert math.isinf(summarize([0., 0.]).mean_fps)


@pytest.mark.parametrize("bad", [True, None, "16", math.nan, math.inf, -0.1,
                                 10_000.01, 10**400, [1.]])
def test_invalid_samples_are_rejected(bad):
    profiler = FrameProfiler(4)
    with pytest.raises(ValueError):
        profiler.record("frame", bad)
    with pytest.raises(ValueError):
        summarize([1., bad])
    assert profiler.count() == 0


def test_profiler_capacity_is_bounded_and_sections_are_closed():
    profiler = FrameProfiler(capacity=10)
    for i in range(1000):
        profiler.record("frame", float(i % 40))
    assert profiler.count("frame") == 10
    assert profiler.stats("frame").min_ms == 30.  # oldest samples dropped
    assert profiler.stats("probe") is None
    report = profiler.report()
    assert set(report) == {"frame", "probe", "render"}
    assert report["probe"] is None and report["frame"]["count"] == 10
    for name in ("hud", "", None):
        with pytest.raises(ValueError):
            profiler.record(name, 1.)
        with pytest.raises(ValueError):
            profiler.stats(name)
    profiler.reset()
    assert profiler.count() == 0 and profiler.stats() is None
    for capacity in (0, -1, True, 1.5, 10**7):
        with pytest.raises(ValueError):
            FrameProfiler(capacity)


@pytest.mark.parametrize("renderer,software", [
    ("llvmpipe (LLVM 20.1.2, 256 bits)", True),
    ("Microsoft Basic Render Driver", True),
    ("GDI Generic", True),
    ("", True), ("unknown", True), (" Unknown ", True), (None, True), (42, True),
    ("AMD Radeon RX 7800 XT", False),
    ("NVIDIA GeForce RTX 4070/PCIe/SSE2", False),
])
def test_software_renderer_detection(renderer, software):
    assert is_software_renderer(renderer) is software


def test_gl08_never_passes_on_software_short_or_small_runs():
    fast = summarize([5.] * 100)
    result = gl08_assessment(fast, (960, 640), 2., "llvmpipe")
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert len(result["reasons"]) == 3
    assert result["requires_human_signoff"] is True
    assert gl08_assessment(None, (1920, 1080), 90., "AMD Radeon")["status"] == (
        "INSUFFICIENT_EVIDENCE")
    assert gl08_assessment(fast, (1920, 1080), math.nan, "AMD Radeon")["status"] == (
        "INSUFFICIENT_EVIDENCE")


def test_gl08_hardware_candidates_use_both_mean_and_p95():
    within = gl08_assessment(summarize([10.] * 100), (1920, 1080), 61., "AMD Radeon")
    assert within["status"] == "CANDIDATE_WITHIN_60FPS" and not within["reasons"]
    # Mean is fine but the 95th percentile exceeds the 60 fps budget.
    spiky = summarize([8.] * 90 + [40.] * 10)
    assert spiky.mean_ms < TARGET_FRAME_MS < spiky.p95_ms
    below = gl08_assessment(spiky, (3840, 2160), 120., "AMD Radeon")
    assert below["status"] == "CANDIDATE_BELOW_60FPS"
    assert below["mean_and_p95_within_target"] is False


def test_camera_path_stays_inside_view_limits():
    view = View()
    for index in range(0, 20000, 7):
        view.yaw, view.pitch = bench.camera_at(index)
        view.check()
    for bad in (-1, 1.0, True, None):
        with pytest.raises(ValueError):
            bench.camera_at(bad)
        with pytest.raises(ValueError):
            bench.hover_at(bad)


@pytest.mark.parametrize("size", [(960, 640), (1920, 1080), (3840, 2160)])
def test_workload_probes_every_frame_without_mutating_game(size):
    controller = bench.prepare_controller(seed=11)
    hud = SurgeryHUD(controller)
    snapshot = controller.game.snapshot()
    journal = controller.game.export_replay_jsonl()
    profiler = FrameProfiler(capacity=500)
    for index in range(400):
        frame = bench.prepare_frame(controller, hud, index, *size, profiler)
        assert frame.tool_pose is not None
        assert frame.proximity is not None and frame.proximity.face_index >= 0
        assert hud.frame_proximity is frame.proximity
    assert profiler.count("probe") == 400 and profiler.count("frame") == 0
    assert controller.game.snapshot() == snapshot
    assert controller.game.export_replay_jsonl() == journal


def test_workload_runs_exactly_one_proximity_query_per_frame(monkeypatch):
    controller = bench.prepare_controller()
    hud = SurgeryHUD(controller)
    calls = []
    actual = probes.probe_surface
    def counted(*args, **kwargs):
        calls.append(1)
        return actual(*args, **kwargs)
    monkeypatch.setattr(bench, "probe_surface", counted)
    for index in range(25):
        bench.prepare_frame(controller, hud, index, 1280, 720)
    assert len(calls) == 25


def test_report_shape_is_honest_about_scope():
    profiler = FrameProfiler(100)
    for _ in range(50):
        profiler.record("frame", 9.)
        profiler.record("probe", .3)
        profiler.record("render", 8.)
    env = bench.environment(None)
    assert env["software_renderer"] is True and env["gl_renderer"] == "unknown"
    report = bench.build_report(profiler, size=(1920, 1080), seconds=3.,
                                warmup=5, env=env, state_unchanged=True, probes=50)
    assert report["frames_measured"] == 50
    assert report["mean_fps"] == pytest.approx(111.11)
    assert report["gl08"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["vsync_controlled"] is False
    assert report["clinical_validation"] is False
    assert "not GPU time" in report["timing_basis"]
    empty = bench.build_report(FrameProfiler(4), size=(1920, 1080), seconds=0.,
                               warmup=0, env=env, state_unchanged=True, probes=0)
    assert empty["mean_fps"] is None and empty["sections"]["frame"] is None


def test_environment_reads_context_info():
    class Ctx:
        info = {"GL_RENDERER": "AMD Radeon", "GL_VENDOR": "ATI",
                "GL_VERSION": "4.6"}
    env = bench.environment(Ctx())
    assert env["gl_renderer"] == "AMD Radeon"
    assert env["software_renderer"] is False


def test_size_and_argument_validation():
    assert bench._size("1920x1080") == (1920, 1080)
    assert bench._size("3840X2160") == (3840, 2160)
    for bad in ("1920", "axb", "100x100", "9000x9000", "1920x1080x1"):
        with pytest.raises(argparse.ArgumentTypeError):
            bench._size(bad)
    for argv in (["--frames", "0"], ["--seconds", "0"], ["--seconds", "nan"],
                 ["--warmup", "-1"], ["--frames", "5", "--seconds", "5"]):
        with pytest.raises(SystemExit) as error:
            bench.main(argv)
        assert error.value.code == 2


def test_f3_perf_label_is_display_only():
    pygame = pytest.importorskip("pygame")
    pygame.init()
    try:
        controller = bench.prepare_controller()
        hud = SurgeryHUD(controller)
        surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        font = pygame.font.SysFont("segoeui", 20)
        large = pygame.font.SysFont("segoeui", 28, bold=True)
        snapshot = controller.game.snapshot()

        def region():
            surf.fill((0, 0, 0, 0))
            hud.draw(pygame, surf, controller.view, 1280, 720, font, large)
            return pygame.image.tobytes(surf.subsurface((860, 620, 400, 26)), "RGBA")

        hidden = region()
        hud.show_perf = True
        measuring = region()
        hud.perf = summarize([12., 14., 30.])
        measured = region()
        assert len({hidden, measuring, measured}) == 3
        assert controller.game.snapshot() == snapshot
    finally:
        pygame.quit()
