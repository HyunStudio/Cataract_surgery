"""Foldable synthetic IOL visualization: geometry, timing and dirty inputs."""
import math
import random

import pytest

from ophthosim.engine import Game, Phase
from ophthosim.geometry import Mesh
from ophthosim.gl_preview import AnatomyAppearance, VERTEX_SHADER, atlas_meshes, pack_mesh
from ophthosim.iol3d import foldable_iol_mesh, iol_visual_deployment


def _reach_iol():
    game = Game(seed=17)
    assert game.action("confirm")
    assert game.action("prepare")
    for x, y in game._entry_target:
        assert game.action("touch", x, y)
    assert game.phase == Phase.CAPSULE
    for n in range(24):
        a = (n+.5)*math.tau/24
        game.action("trace", .5+.28*math.cos(a), .5+.28*math.sin(a))
    assert game.phase == Phase.PHACO
    while game.phase in (Phase.PHACO, Phase.CORTEX):
        assert game.action("remove",.5,.5)
    assert game.phase == Phase.IOL
    return game


def test_synthetic_iol_mesh_cached_valid_and_has_curved_supports():
    m = foldable_iol_mesh()
    assert m is foldable_iol_mesh()
    assert isinstance(m, Mesh)
    m.validate()
    assert len(m.vertices) > 450
    assert len(m.faces) > 650
    assert min(v[0] for v in m.vertices) < -.55
    assert max(v[0] for v in m.vertices) > .55
    assert all(math.isfinite(v) for point in m.vertices for v in point)
    data, idx, count = pack_mesh(m)
    assert len(data) == len(m.vertices)*24
    assert len(idx) == count*4


def test_atlas_uses_folding_visual_mesh_only_for_iol():
    pre = atlas_meshes("CATARACT")
    post = atlas_meshes("IOL")
    assert post["lens"] == foldable_iol_mesh()
    assert pre["lens"] != post["lens"]
    assert "u_iol_fold" in VERTEX_SHADER
    assert "u_iol_mode" in VERTEX_SHADER
    for m in post.values():
        m.validate()


def test_iol_deployment_follows_simulation_not_wall_time():
    g = _reach_iol()
    assert iol_visual_deployment(g) == 0.
    assert g.action("place",.5,.5)
    assert g.phase == Phase.CLOSE
    assert iol_visual_deployment(g) == 0.
    for _ in range(15):
        g.tick(.05)
    midpoint = iol_visual_deployment(g)
    assert midpoint == pytest.approx(.5, abs=.002)
    g.action("pause")
    for _ in range(100):
        g.tick(.05)
    assert iol_visual_deployment(g) == midpoint
    g.action("pause")
    for _ in range(15):
        g.tick(.05)
    assert iol_visual_deployment(g) == 1.
    for check in ("alignment","wound","handoff"):
        assert g.action("verify",check)
    assert g.phase == Phase.RECOVERY
    assert iol_visual_deployment(g) == 1.


def test_iol_deployment_does_not_mutate_or_score_game():
    g = _reach_iol()
    original = g.snapshot()
    original_events = g.export_jsonl()
    for _ in range(20):
        assert iol_visual_deployment(g) == 0.
    assert original == g.snapshot()
    assert original_events == g.export_jsonl()


def test_aborted_case_never_automatically_unfolds():
    g = _reach_iol()
    assert iol_visual_deployment(g) == 0.
    assert g.action("abort")
    assert g.phase == Phase.ABORTED
    assert iol_visual_deployment(g) == 1.  # No implant visualized in ABORTED mode.


def test_synthetic_appearance_rejects_dirty_fold_parameter():
    for value in (None, True, "bad", float("nan"), float("inf"),
                  -0.1, 1.1, 10**400):
        with pytest.raises(ValueError):
            AnatomyAppearance(iol_deployment=value).check()


@pytest.mark.parametrize("value", [None, True, "bad", float("nan"),
                                   float("inf"), -.1, 31, 10**400])
def test_bad_visual_animation_duration_rejected(value):
    with pytest.raises(ValueError):
        iol_visual_deployment(_reach_iol(), duration_s=value)


def test_timeline_with_different_duration_and_random_ticks():
    g = _reach_iol()
    assert g.action("place",.5,.5)
    rng = random.Random(314)
    prev = 0.
    for _ in range(200):
        g.tick(rng.uniform(0,.05))
        fraction = iol_visual_deployment(g, duration_s=2.)
        assert 0. <= prev <= fraction <= 1.
        prev = fraction
    assert iol_visual_deployment(g, duration_s=2.) == 1.
