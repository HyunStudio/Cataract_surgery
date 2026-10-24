# Licensed 3D models (optional)

The game draws a procedural eye. A real model replaces one part of it only when a
folder here contains **both** files:

```
assets/models/<part>/model.obj
assets/models/<part>/manifest.json
```

- `<part>` is one of `sclera`, `iris`, `lens` or `cornea`. The IOL keeps its procedural
  mesh, because its folding is done in the shader.
- `model.obj` is a UTF-8 Wavefront OBJ of at most 8 MB, 200 000 vertices and 400 000
  triangles.
  - Coordinates use the normalized model space of `ophthosim/geometry.py`: eye centre
    at the origin, viewer on +z, globe radius about 1, every coordinate within ±1.5.
  - Polygons are triangulated as fans.
  - Normals are recomputed from the faces. Texture coordinates and materials are
    ignored.
- `manifest.json` must name the part, its source, its author and an allowed licence:

```json
{"name": "iris", "source": "https://example.org/model-page",
 "author": "Model author", "license": "CC-BY-4.0"}
```

Allowed licences: `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `MIT`, `Apache-2.0`,
`BSD-2-Clause`, `BSD-3-Clause`, and `LicenseRef-OphthoSim-Original` for work made for
this repository. Non-commercial or no-derivatives licences are refused, so the
repository stays freely redistributable ([SAFETY](../../docs/SAFETY.md)).

A missing, unlicensed or malformed asset is refused with a reason, and the procedural
mesh stays in use. Models are visual only and never change the rules, scores or
replays.
