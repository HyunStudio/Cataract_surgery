"""Optional licensed 3D model assets for the synthetic eye.

The procedural meshes in geometry.py are always available. A real model
replaces one of them only when ``assets/models/<name>/`` holds BOTH a
``model.obj`` and a ``manifest.json`` that documents its source, author and a
redistributable licence (docs/SAFETY.md: every anatomical asset must have a
verified creator, licence and redistribution right). Anything else is
rejected with a reason and the procedural mesh stays in use, so a missing or
broken asset can never stop the game or change its rules: models are visual
only and never touch the Game, scoring or replays.

The OBJ must be authored in the normalized model space of geometry.py
(eye centre at the origin, viewer on +z, globe radius about 1).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path
import re

from .geometry import Mesh

ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "models"
# Meshes a model may replace. The IOL is not here: its folding is a shader
# deformation of the procedural mesh.
REPLACEABLE = ("sclera", "iris", "lens", "cornea")
# Redistributable licences (SPDX ids). Non-commercial or no-derivatives
# licences are refused: the repository must stay freely redistributable.
ALLOWED_LICENSES = frozenset({
    "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT", "Apache-2.0",
    "BSD-2-Clause", "BSD-3-Clause", "LicenseRef-OphthoSim-Original",
})
MANIFEST_FIELDS = ("name", "source", "author", "license")
MAX_OBJ_BYTES = 8_000_000
MAX_MANIFEST_BYTES = 16_000
MAX_VERTICES = 200_000
MAX_TRIANGLES = 400_000
COORDINATE_LIMIT = 1.5
_NAME = re.compile(r"^[a-z][a-z_]{0,31}$")


class AssetError(ValueError):
    """A present asset that may not be used (reason in the message)."""


@dataclass(frozen=True, slots=True)
class AssetInfo:
    name: str
    source: str
    author: str
    license: str
    vertices: int
    triangles: int


def _folder(name: str, root: Path) -> Path:
    if not isinstance(name, str) or not _NAME.match(name) or name not in REPLACEABLE:
        raise AssetError(f"Unknown asset name: {name!r}")
    base = Path(root).resolve()
    folder = (base / name).resolve()
    if folder.parent != base:
        raise AssetError("Asset path escapes the asset folder")
    return folder


def read_manifest(path: Path, name: str) -> dict[str, str]:
    if not path.is_file():
        raise AssetError("manifest.json is missing (source, author and licence are required)")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise AssetError("manifest.json is too large")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetError(f"manifest.json is not valid JSON: {exc.__class__.__name__}") from exc
    if not isinstance(data, dict):
        raise AssetError("manifest.json must be an object")
    for field in MANIFEST_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 500:
            raise AssetError(f"manifest.json field '{field}' is missing or empty")
    if data["name"] != name:
        raise AssetError(f"manifest name {data['name']!r} does not match folder {name!r}")
    if data["license"] not in ALLOWED_LICENSES:
        raise AssetError(f"licence {data['license']!r} is not an allowed redistributable licence")
    return {field: data[field].strip() for field in MANIFEST_FIELDS}


def _index(token: str, count: int, line: int) -> int:
    try:
        raw = int(token.split("/")[0])
    except ValueError as exc:
        raise AssetError(f"OBJ line {line}: bad face index") from exc
    index = raw - 1 if raw > 0 else count + raw
    if raw == 0 or not 0 <= index < count:
        raise AssetError(f"OBJ line {line}: face index out of range")
    return index


def parse_obj(text: str, name: str = "asset") -> Mesh:
    """Positions and faces of a Wavefront OBJ (polygons fan-triangulated).

    Texture coordinates, materials and groups are ignored; smooth vertex
    normals are recomputed from the faces so every vertex has one normal.
    """
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        parts = raw.split("#", 1)[0].split()
        if not parts:
            continue
        if parts[0] == "v":
            if len(parts) < 4:
                raise AssetError(f"OBJ line {number}: vertex needs x y z")
            try:
                xyz = tuple(float(v) for v in parts[1:4])
            except ValueError as exc:
                raise AssetError(f"OBJ line {number}: bad vertex") from exc
            if not all(math.isfinite(v) and abs(v) <= COORDINATE_LIMIT for v in xyz):
                raise AssetError(f"OBJ line {number}: vertex outside normalized model space")
            vertices.append(xyz)
            if len(vertices) > MAX_VERTICES:
                raise AssetError("OBJ has too many vertices")
        elif parts[0] == "f":
            if len(parts) < 4:
                raise AssetError(f"OBJ line {number}: face needs three vertices")
            ids = [_index(token, len(vertices), number) for token in parts[1:]]
            for k in range(1, len(ids) - 1):
                tri = (ids[0], ids[k], ids[k + 1])
                if len(set(tri)) == 3:
                    faces.append(tri)
            if len(faces) > MAX_TRIANGLES:
                raise AssetError("OBJ has too many triangles")
    if not vertices or not faces:
        raise AssetError("OBJ has no triangles")
    sums = [[0., 0., 0.] for _ in vertices]
    for a, b, c in faces:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = vertices[a], vertices[b], vertices[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)   # area-weighted
        for i in (a, b, c):
            sums[i][0] += n[0]; sums[i][1] += n[1]; sums[i][2] += n[2]
    normals = []
    for x, y, z in sums:
        length = math.sqrt(x * x + y * y + z * z)
        normals.append((x / length, y / length, z / length) if length > 1e-12 else (0., 0., 1.))
    mesh = Mesh(name, tuple(vertices), tuple(normals), tuple(faces))
    mesh.validate()
    return mesh


def load_asset(name: str, root: Path | str = ASSET_ROOT) -> tuple[Mesh, AssetInfo] | None:
    """The licensed model for `name`, None when there is no asset folder,
    or AssetError when an asset is present but may not be used."""
    folder = _folder(name, Path(root))
    if not folder.exists():
        return None
    obj = folder / "model.obj"
    manifest = read_manifest(folder / "manifest.json", name)
    if not obj.is_file():
        raise AssetError("model.obj is missing")
    if obj.stat().st_size > MAX_OBJ_BYTES:
        raise AssetError("model.obj is too large")
    try:
        text = obj.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AssetError("model.obj is not UTF-8 text") from exc
    mesh = parse_obj(text, name)
    return mesh, AssetInfo(name, manifest["source"], manifest["author"], manifest["license"],
                           len(mesh.vertices), len(mesh.faces))


def with_assets(meshes: dict[str, Mesh], root: Path | str = ASSET_ROOT,
                *, allowed: tuple[str, ...] = REPLACEABLE) -> tuple[dict[str, Mesh], dict]:
    """Replace procedural meshes by valid licensed models. Never raises for a
    bad asset: the report says what was loaded and why others were refused."""
    result = dict(meshes)
    report: dict[str, dict] = {"loaded": {}, "rejected": {}}
    for name in allowed:
        if name not in meshes:
            continue
        try:
            found = load_asset(name, root)
        except (AssetError, OSError) as exc:
            report["rejected"][name] = str(exc)
            continue
        if found is not None:
            mesh, info = found
            result[name] = mesh
            report["loaded"][name] = {"source": info.source, "author": info.author,
                                      "license": info.license, "triangles": info.triangles}
    return result, report


@lru_cache(maxsize=4)
def default_assets(phase: str) -> tuple[tuple[tuple[str, Mesh], ...], str]:
    """Cached replacement for the GPU atlas (asset files are read once)."""
    from .geometry import anterior_eye_meshes
    base = anterior_eye_meshes()
    allowed = REPLACEABLE if phase == "CATARACT" else tuple(n for n in REPLACEABLE if n != "lens")
    meshes, report = with_assets({n: base[n] for n in allowed}, ASSET_ROOT, allowed=allowed)
    loaded = tuple((n, m) for n, m in meshes.items() if n in report["loaded"])
    return loaded, json.dumps(report, sort_keys=True)
