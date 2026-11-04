"""Licensed model loader: OBJ parsing, licence gate, refusal of bad files."""
import json

import pytest

from ophthosim.assets import (ALLOWED_LICENSES, AssetError, REPLACEABLE, load_asset, parse_obj,
                              with_assets)
from ophthosim.geometry import anterior_eye_meshes

QUAD = """# unit quad in normalized model space
o iris
v -.5 -.5 .03
v  .5 -.5 .03
v  .5  .5 .03
v -.5  .5 .03
vt 0 0
vn 0 0 1
f 1/1/1 2/1/1 3/1/1 4/1/1
"""
GOOD = {"name": "iris", "source": "original work for this repository",
        "author": "OphthoSim contributors", "license": "CC-BY-4.0"}


def make(root, name="iris", obj=QUAD, manifest=GOOD):
    folder = root / name
    folder.mkdir(parents=True)
    if obj is not None:
        (folder / "model.obj").write_text(obj, encoding="utf-8")
    if manifest is not None:
        text = manifest if isinstance(manifest, str) else json.dumps(manifest)
        (folder / "manifest.json").write_text(text, encoding="utf-8")
    return folder


def test_quad_is_fan_triangulated_with_unit_normals():
    mesh = parse_obj(QUAD, "iris")
    assert mesh.faces == ((0, 1, 2), (0, 2, 3))
    assert all(abs(n[2] - 1) < 1e-9 for n in mesh.normals)


def test_negative_indices_and_comments():
    mesh = parse_obj("v 0 0 0\nv 1 0 0\nv 0 1 0 # tip\nf -3 -2 -1\n")
    assert mesh.faces == ((0, 1, 2),)


@pytest.mark.parametrize("text, reason", [
    ("", "no triangles"),
    ("v 0 0 0\nv 1 0 0\nf 1 2 3\n", "out of range"),
    ("v 0 0 nan\n", "outside"),
    ("v 0 0 9\n", "outside"),
    ("v 0 0\n", "x y z"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 x\n", "bad face"),
    ("v 0 0 0\nf 1 1 1\n", "no triangles"),
])
def test_bad_obj_is_refused(text, reason):
    with pytest.raises(AssetError, match=reason):
        parse_obj(text)


def test_valid_licensed_asset_loads(tmp_path):
    make(tmp_path)
    mesh, info = load_asset("iris", tmp_path)
    assert info.license == "CC-BY-4.0" and info.triangles == 2 and mesh.name == "iris"


def test_no_folder_means_procedural(tmp_path):
    assert load_asset("iris", tmp_path) is None
    meshes, report = with_assets(anterior_eye_meshes(), tmp_path)
    assert meshes == anterior_eye_meshes() and report == {"loaded": {}, "rejected": {}}


@pytest.mark.parametrize("manifest, reason", [
    (None, "manifest.json is missing"),
    ("{not json", "not valid JSON"),
    ([], "must be an object"),
    ({**GOOD, "license": ""}, "'license'"),
    ({k: v for k, v in GOOD.items() if k != "author"}, "'author'"),
    ({**GOOD, "license": "CC-BY-NC-4.0"}, "not an allowed"),
    ({**GOOD, "license": "proprietary"}, "not an allowed"),
    ({**GOOD, "name": "lens"}, "does not match"),
])
def test_missing_or_unlicensed_manifest_is_refused(tmp_path, manifest, reason):
    make(tmp_path, manifest=manifest)
    with pytest.raises(AssetError, match=reason):
        load_asset("iris", tmp_path)
    meshes, report = with_assets(anterior_eye_meshes(), tmp_path)
    assert meshes["iris"] == anterior_eye_meshes()["iris"]      # procedural kept
    assert reason.strip("'") in report["rejected"]["iris"]


def test_missing_obj_and_unknown_names_are_refused(tmp_path):
    make(tmp_path, obj=None)
    with pytest.raises(AssetError, match="model.obj is missing"):
        load_asset("iris", tmp_path)
    for name in ("iol", "../iris", "Iris", "", 7):
        with pytest.raises(AssetError):
            load_asset(name, tmp_path)


def test_with_assets_replaces_only_valid_models(tmp_path):
    make(tmp_path)                                    # good iris
    make(tmp_path, "lens", manifest={**GOOD, "name": "lens", "license": "unknown"})
    meshes, report = with_assets(anterior_eye_meshes(), tmp_path)
    assert len(meshes["iris"].faces) == 2
    assert meshes["lens"] == anterior_eye_meshes()["lens"]
    assert set(report["loaded"]) == {"iris"} and set(report["rejected"]) == {"lens"}


def test_policy_constants():
    assert "iol" not in REPLACEABLE
    assert not any("NC" in name or "ND" in name for name in ALLOWED_LICENSES)
