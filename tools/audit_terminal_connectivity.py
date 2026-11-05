"""Locate a retained geometric path from central tissue to the anchored rim."""
import argparse
from collections import deque
import json
import math
from pathlib import Path

from native_build_provenance import sha256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('capture', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.capture.resolve() == args.output.resolve():
    raise SystemExit('Audit output must not overwrite the terminal capture')
if args.output.exists():
    raise SystemExit('Audit output already exists; choose a new evidence path')
data = json.loads(args.capture.read_text(encoding='utf-8'))
xyz, rest = data['xyz'], data['rest']
anchored, removed, triangles = data['anchored'], data['removed'], data['triangles']
n = len(anchored)
if not n or len(xyz) != n * 3 or len(rest) != n * 3 or len(removed) != n or len(triangles) % 3:
    raise SystemExit('Misaligned terminal topology arrays')
if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in xyz + rest):
    raise SystemExit('Nonfinite terminal coordinates')
if any(v not in (0, 1) for v in anchored + removed):
    raise SystemExit('Invalid vertex flags')
if any(not isinstance(v, (int, float)) or not math.isfinite(v) or int(v) != v or v < 0 or v >= n for v in triangles):
    raise SystemExit('Invalid triangle indices')
triangles = list(map(int, triangles))
center = int(data['central_vertex'])
if center != data['central_vertex'] or center < 0 or center >= n or removed[center]:
    raise SystemExit('Invalid central vertex')
neighbors = [set() for _ in range(n)]
for i in range(0, len(triangles), 3):
    face = triangles[i:i + 3]
    if any(removed[v] for v in face):
        raise SystemExit('Retained triangles reference removed vertices')
    for a, b in zip(face, face[1:] + face[:1]):
        neighbors[a].add(b)
        neighbors[b].add(a)
queue = deque([center])
parent = {center: None}
anchor = None
while queue:
    vertex = queue.popleft()
    if anchored[vertex] and anchor is None:
        anchor = vertex
    for other in sorted(neighbors[vertex]):
        if other not in parent:
            parent[other] = vertex
            queue.append(other)
path = []
vertex = anchor
while vertex is not None:
    path.append(vertex)
    vertex = parent[vertex]
path.reverse()
declared_detached = any(center in piece['vertices'] for piece in data['components'])
if declared_detached != (anchor is None):
    raise SystemExit('Independent face connectivity disagrees with declared detached components')
report = {'qualified': False, 'scope': 'Independent face-edge connectivity only; no mechanics, cutting correctness, clinical or release qualification.',
          'capture_sha256': sha256(args.capture), 'auditor_sha256': sha256(Path(__file__)),
          'central_vertex': center, 'central_component_vertices': len(parent),
          'central_detached': anchor is None, 'agrees_with_declared_component': True,
          'anchored_vertices_in_central_component': sum(bool(anchored[v]) for v in parent),
          'shortest_edge_path_to_anchor': path,
          'path_coordinates': [{'vertex': v, 'rest': rest[v * 3:v * 3 + 3], 'current': xyz[v * 3:v * 3 + 3]} for v in path]}
args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({key: report[key] for key in ['central_vertex', 'central_component_vertices', 'central_detached', 'anchored_vertices_in_central_component']}))
