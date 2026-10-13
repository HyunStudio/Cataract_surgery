"""CPU/GPU synthetic IOL folding parity for read-only triangle inspection."""
import math
import random
from types import SimpleNamespace

import pytest

from ophthosim.gl_preview import (AnatomyAppearance, GPUEyePreview, View,
                                  VERTEX_SHADER, atlas_meshes)
from ophthosim.iol3d import foldable_iol_mesh
from ophthosim.iol_pick3d import deformed_iol_mesh, iol_vertex_position
from ophthosim.mesh_raycast import build_index, pick_indexed
from ophthosim.picking3d import project_point, _rotate
from ophthosim.vision3d import VisualFeedback

W,H=1280,720


def preview_without_opengl():
    """The exact selection method can run without a graphics driver."""
    p=object.__new__(GPUEyePreview)
    p.pg=SimpleNamespace(display=SimpleNamespace(
        get_window_size=lambda: (W,H)))
    meshes=atlas_meshes("IOL")
    p.mesh_indexes={k:build_index(meshes[k]) for k in ("iris","lens")}
    p._dynamic_iol_signature=None
    p._dynamic_iol_index=None
    p.selection=None
    p.selection_pixel=None
    return p


def test_deformation_matches_declared_glsl_vertex_equations():
    src=VERTEX_SHADER
    assert "mix(0.24 * in_position.x, in_position.x, u_iol_fold)" in src
    assert "(1.0 - u_iol_fold) * 0.30 * abs(in_position.x)" in src
    assert "local_pos + u_offset" in src
    vertex=(.36,.10,-.19)
    assert iol_vertex_position(vertex,0,1)==pytest.approx(
        (.0864,.10,-.082))
    assert iol_vertex_position(vertex,.5,1)==pytest.approx(
        (.2232,.10,-.136))
    assert iol_vertex_position(vertex,1,0)==pytest.approx(
        (.54,.10,-.19))
    assert iol_vertex_position(vertex,1,1)==pytest.approx(vertex)


def test_deformed_mesh_stays_bounded_indexed_and_source_immutable():
    source=foldable_iol_mesh()
    original=source.vertices
    full=deformed_iol_mesh(1.,1.)
    folded=deformed_iol_mesh(0.,1.)
    intermediate=deformed_iol_mesh(.5,1.)
    shifted=deformed_iol_mesh(1.,0.)
    assert source.vertices==original
    assert full.vertices==source.vertices
    assert full.faces is source.faces
    assert full.normals is source.normals
    assert all(math.isfinite(v) for p in folded.vertices for v in p)
    assert all(p[0]==pytest.approx(q[0]+.18)
               for p,q in zip(shifted.vertices,full.vertices))
    assert full!=folded!=intermediate
    for mesh in (folded,intermediate,shifted):
        mesh.validate()
        build_index(mesh)


def test_deformed_mesh_caches_only_16_bounded_combinations():
    deformed_iol_mesh.cache_clear()
    a=deformed_iol_mesh(.5,.9)
    assert a is deformed_iol_mesh(.5,.9)
    for j in range(32):
        deformed_iol_mesh(j/32.,1.)
    assert deformed_iol_mesh.cache_info().currsize<=16


def test_atlas_click_selects_fully_unfolded_optic_but_not_folded_same_pixel():
    atlas=preview_without_opengl()
    view=View(yaw=0,pitch=0,zoom=3.6,phase="IOL")
    point=project_point((.25,0,-.19),W,H,0,0,3.6)
    selected=atlas.select(point,view)
    assert selected is not None and selected.name=="IOL"
    unfolded_index=atlas._dynamic_iol_index
    assert atlas.select(point,view) is not None
    assert atlas._dynamic_iol_index is unfolded_index
    view.key("fold")
    assert view.iol_deployment==0.
    folded=atlas.select(point,view)
    assert folded is None
    assert atlas._dynamic_iol_index is not unfolded_index
    view.key("fold")
    assert view.iol_deployment==.5
    assert atlas.select((639.5,359.5),view).name=="IOL"
    view.key("fold")
    assert view.iol_deployment==1.


def test_alignment_offset_and_scene_motion_follow_glsl_coordinate_frame():
    atlas=preview_without_opengl()
    view=View(yaw=.43,pitch=-.21,zoom=4.2,phase="IOL")
    appearance=AnatomyAppearance(iol_deployment=.42,iol_alignment=.65)
    scene=VisualFeedback(motion_x=.035,motion_y=-.019)
    # On a 3D surface: GPU first deforms, then shifts lens in model space,
    # rotates, then applies visual camera-plane movement.
    pos=iol_vertex_position((.25,0,-.19),.42,.65)
    rx,ry,rz=_rotate(pos,view.yaw,view.pitch)
    depth=view.zoom-rz
    x_ndc=2.3*(rx+scene.motion_x)/(depth*(W/H))
    y_ndc=2.3*(ry+scene.motion_y)/depth
    px=(x_ndc+1)*W/2-.5
    py=(1-y_ndc)*H/2-.5
    hit=atlas.select((px,py),view,appearance=appearance,vision=scene)
    assert hit and hit.name=="IOL"
    assert hit.distance>0
    assert atlas._dynamic_iol_signature==(.42,.65)
    assert all(math.isfinite(x) for x in hit.position)


def test_cache_signature_changes_only_on_visual_parameters():
    atlas=preview_without_opengl()
    view=View(phase="IOL")
    px=(639.5,359.5)
    atlas.select(px,view,appearance=AnatomyAppearance(iol_deployment=.3))
    index=atlas._dynamic_iol_index
    atlas.select(px,view,appearance=AnatomyAppearance(iol_deployment=.3))
    assert atlas._dynamic_iol_index is index
    atlas.select(px,view,appearance=AnatomyAppearance(iol_deployment=.3,
                                                       iol_alignment=.8))
    assert atlas._dynamic_iol_index is not index


def test_original_scene_phase_inspection_is_unchanged():
    atlas=preview_without_opengl()
    view=View(yaw=0,pitch=0,phase="CATARACT")
    result=atlas.select((639.5,359.5),view)
    assert result and result.name=="cloudy lens"
    assert atlas._dynamic_iol_index is None


@pytest.mark.parametrize("bad",[None,True,False,"1",float("nan"),
                                float("inf"),-1.,1.1,10**400,[],{}])
def test_untrusted_fold_and_alignment_rejected(bad):
    with pytest.raises(ValueError):
        deformed_iol_mesh(bad,1.)
    with pytest.raises(ValueError):
        deformed_iol_mesh(1.,bad)
    with pytest.raises(ValueError):
        iol_vertex_position((.1,.2,.3),bad)
    with pytest.raises(ValueError):
        iol_vertex_position((.1,.2,.3),1.,bad)


@pytest.mark.parametrize("bad",[None,True,"0",float("nan"),
                                float("inf"),10**400,[],{}])
def test_bad_shader_vertex_input_rejected(bad):
    with pytest.raises(ValueError):
        iol_vertex_position((bad,.1,.2),.5)
    with pytest.raises(ValueError):
        iol_vertex_position(bad,.5)


def test_pointer_invalid_dynamic_state_fails_before_opengl_driver():
    atlas=preview_without_opengl()
    view=View(phase="IOL")
    for bad in (True,1,[],{},object()):
        with pytest.raises(ValueError):
            atlas.select((639.5,359.5),view,appearance=bad)
        with pytest.raises(ValueError):
            atlas.select((639.5,359.5),view,vision=bad)
    view.iol_deployment=float("nan")
    with pytest.raises(ValueError):
        atlas.select((639.5,359.5),view)


def test_seeded_300_deformation_and_alignment_parameters_safe():
    atlas=preview_without_opengl()
    rng=random.Random(913)
    view=View(yaw=.28,pitch=.15,phase="IOL")
    for _ in range(300):
        appearance=AnatomyAppearance(iol_deployment=rng.random(),
                                     iol_alignment=rng.random())
        hit=atlas.select((639.5,359.5),view,appearance=appearance)
        if hit:
            assert hit.name in {"IOL","iris"}
            assert math.isfinite(hit.distance)
            assert 0<=hit.face_index<20000
            assert sum(hit.barycentric)==pytest.approx(1.,abs=1e-8)
