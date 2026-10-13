"""Synthetic capsule appearance: scene state, safety and adversarial tests."""
import math

import pytest

from ophthosim.capsule3d import (_ring, capsule_indicator_meshes,
                                 capsule_display_state, capsule_visible)
from ophthosim.engine import Game, Phase
from ophthosim.gl_preview import AnatomyAppearance, pack_mesh


def reach_phaco(game):
    assert game.action("confirm")
    assert game.action("prepare")
    for x,y in game._entry_target:
        assert game.action("touch",x,y)
    assert game.phase == Phase.CAPSULE
    for i in range(24):
        angle=(i+.5)*math.tau/24
        game.action("trace",.5+.28*math.cos(angle),.5+.28*math.sin(angle))
    assert game.phase == Phase.PHACO


def test_capsule_visual_meshes_cache_contain_true_open_arc():
    a=capsule_indicator_meshes()
    b=capsule_indicator_meshes()
    assert a is b and set(a)=={"intact","damaged"}
    for mesh in a.values():
        mesh.validate()
        vertices,indices,count=pack_mesh(mesh)
        assert len(vertices)==24*len(mesh.vertices)
        assert len(indices)==count*4
        assert all(.20 <= math.hypot(x,y) <= .25 for x,y,z in mesh.vertices)
        assert all(abs(z-.067)<1e-9 for x,y,z in mesh.vertices)
    left,right=a["damaged"].vertices[0],a["damaged"].vertices[-2]
    assert math.dist(left,right) > .1
    assert len(a["intact"].faces)==len(a["damaged"].faces)
    assert max(math.dist(a["intact"].vertices[i],a["damaged"].vertices[i])
               for i in range(len(a["intact"].vertices))) > .1


def test_capsule_state_only_visible_at_relevant_stages():
    g=Game()
    assert capsule_display_state(g)==(False,0.)
    g.action("confirm")
    g.action("prepare")
    assert capsule_display_state(g)==(False,0.)
    for x,y in g._entry_target:
        g.action("touch",x,y)
    assert g.phase==Phase.CAPSULE
    assert capsule_display_state(g)==(True,0.)
    assert capsule_visible(g)
    before=g.snapshot()
    for _ in range(100):
        capsule_display_state(g)
    assert g.snapshot()==before


def test_seeded_capsule_integrity_alert_maps_to_red_indicator_without_mutation():
    g=Game("capsule",seed=17)
    reach_phaco(g)
    assert g.patient.alert=="CAPSULE INTEGRITY" and g.paused
    assert g.eye.capsule_integrity == pytest.approx(.55)
    before=g.snapshot()
    assert capsule_display_state(g)==(True,.45)
    assert g.snapshot()==before
    assert g.action("assess")
    assert g.phase==Phase.ABORTED
    assert capsule_display_state(g)==(True,.45)


def test_normal_safe_abort_never_fabricates_capsule_injury():
    g=Game("normal")
    reach_phaco(g)
    assert capsule_display_state(g)==(True,0.)
    assert g.action("abort")
    assert capsule_display_state(g)==(False,0.)


def test_schematic_depth_layer_and_uniform_validation():
    appearance=AnatomyAppearance(capsule_damage=.45,capsule_present=True)
    appearance.check()
    assert appearance.capsule_damage == .45
    for damage in (0.,.14,.15,.55,1.):
        AnatomyAppearance(capsule_damage=damage,capsule_present=True).check()


@pytest.mark.parametrize("bad",[None,True,False,"1",float("nan"),
                                float("inf"),-1.,1.2,10**400,[],{}])
def test_dirty_capsule_damage_rejected_by_gpu_presentation(bad):
    with pytest.raises(ValueError):
        AnatomyAppearance(capsule_damage=bad).check()


@pytest.mark.parametrize("bad",[0,1,"yes",None,[],{}])
def test_nonboolean_visibility_rejected(bad):
    with pytest.raises(ValueError):
        AnatomyAppearance(capsule_present=bad).check()


@pytest.mark.parametrize("bad",[None,True,False,"x",float("nan"),
                                float("inf"),-1.,2.,10**400])
def test_corrupted_game_capsule_state_fails_closed(bad):
    g=Game()
    g.eye.capsule_integrity=bad
    with pytest.raises(ValueError):
        capsule_display_state(g)


@pytest.mark.parametrize("bad",[None,True,"x",float("nan"),
                                float("inf"),-.1,1.,10**400])
def test_invalid_gap_values_rejected(bad):
    with pytest.raises(ValueError):
        _ring("damaged_capsule",gap=bad)


@pytest.mark.parametrize("bad",[None,True,1,11,257,10**400,8.3])
def test_invalid_segment_counts_rejected(bad):
    with pytest.raises(ValueError):
        _ring("damaged_capsule",segments=bad)
