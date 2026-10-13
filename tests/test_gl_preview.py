"""GL renderer boundary and dirty tests that need no display or GPU."""
from array import array
import json
import math
import subprocess
import sys
import pytest

from ophthosim.gl_preview import (
    View, AnatomyAppearance, pack_mesh, atlas_meshes, bounded_float, offline_check,
    VERTEX_SHADER, FRAGMENT_SHADER, UI_VERTEX_SHADER, UI_FRAGMENT_SHADER,
)
from ophthosim.geometry import ellipsoid


def test_gpu_mesh_buffers_are_correctly_interleaved():
    mesh = ellipsoid("test", (1,1,1), slices=8, stacks=4)
    vertices, indices, count = pack_mesh(mesh)
    floats = array("f")
    floats.frombytes(vertices)
    tris = array("I")
    tris.frombytes(indices)
    assert len(floats) == len(mesh.vertices)*6
    assert count == len(mesh.faces)*3 == len(tris)
    assert all(i < len(mesh.vertices) for i in tris)
    assert floats[:6] == pytest.approx((*mesh.vertices[0], *mesh.normals[0]))


def test_model_switch_and_asset_budget():
    opaque, implanted = atlas_meshes("CATARACT"), atlas_meshes("IOL")
    assert set(opaque) == set(implanted) == {"sclera", "iris", "lens", "cornea"}
    assert opaque["lens"] != implanted["lens"]
    for mesh in opaque.values():
        vb, ib, count = pack_mesh(mesh)
        assert count and len(vb) < 1_000_000 and len(ib) < 1_000_000


def test_atlas_offline_does_not_claim_gpu_check():
    d = offline_check()
    assert d["status"] == "cpu-geometry-ok"
    assert d["gpu_tested"] is False
    assert d["meshes"]["cornea"]["triangles"] > 0


def test_atlas_offline_check_cli():
    p = subprocess.run([sys.executable, "-m", "ophthosim.gl_preview", "--check"],
                       capture_output=True, text=True, check=True)
    assert json.loads(p.stdout)["gpu_tested"] is False


def test_view_camera_limits_under_10000_events():
    v = View()
    for _ in range(10000):
        for k in ("up","right","zoom_in"):
            v.key(k)
    assert v.pitch == .8 and v.yaw == 1.2 and v.zoom == 2.6
    v.check()
    for _ in range(10000):
        for k in ("down","left","zoom_out"):
            v.key(k)
    assert v.pitch == -.8 and v.yaw == -1.2 and v.zoom == 5.0
    v.check()


def test_view_switch_and_invalid_state_rejected():
    v = View()
    v.key("toggle")
    assert v.phase == "IOL"
    v.key("toggle")
    assert v.phase == "CATARACT"
    v.phase = "SURGERY"
    with pytest.raises(ValueError):
        v.check()
    with pytest.raises(ValueError):
        atlas_meshes("unknown")


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"),
                                  -float("inf"), 10**400, -10**400, "0", [], {}])
def test_invalid_float_rejected(value):
    with pytest.raises(ValueError):
        bounded_float(value, -1, 1)


def test_shader_contracts_have_versions_and_draw_interface():
    for shader in (VERTEX_SHADER, FRAGMENT_SHADER,
                   UI_VERTEX_SHADER, UI_FRAGMENT_SHADER):
        assert "#version 330" in shader
        assert "void main()" in shader
    for name in ("u_yaw", "u_pitch", "u_aspect", "u_zoom"):
        assert name in VERTEX_SHADER
    assert "in_normal" in VERTEX_SHADER
    assert "u_tint" in FRAGMENT_SHADER
    assert "u_hud" in UI_FRAGMENT_SHADER


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -3, 7, 10**400])
def test_view_invalid_zoom_fails_closed(bad):
    v = View()
    v.zoom = bad
    with pytest.raises(ValueError):
        v.check()


def test_synthetic_appearance_defaults_and_valid_extremes():
    for values in ((1.,1.,1.),(0.,0.,0.),(.3,.6,.9)):
        AnatomyAppearance(*values).check()


@pytest.mark.parametrize("bad",[float("nan"),float("inf"),-1.,1.1,10**400,None,True,"0.5"])
def test_synthetic_appearance_dirty_values_fail_closed(bad):
    for which in range(3):
        values=[.5,.5,.5]
        values[which]=bad
        with pytest.raises(ValueError):
            AnatomyAppearance(*values).check()


def test_shader_has_declared_model_translation_for_iol():
    assert "uniform vec3 u_offset;" in VERTEX_SHADER
    # The shader now deforms only the IOL local position before translating
    # it by the existing world-space offset. Avoid pinning the old expression.
    assert "vec3 local_pos = in_position;" in VERTEX_SHADER
    assert "local_pos + u_offset" in VERTEX_SHADER
    assert "u_iol_mode" in VERTEX_SHADER
    assert "u_iol_fold" in VERTEX_SHADER
