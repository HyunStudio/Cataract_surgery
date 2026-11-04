"""Independent exact-rational replay of every fine boundary edge collapse."""
import argparse
import base64
from collections import Counter, defaultdict
from fractions import Fraction as Q
import json
from pathlib import Path
import struct


def values(encoded):
    raw = base64.b64decode(encoded)
    return struct.unpack('<'+'d'*(len(raw)//8), raw)


def determinant(a, b, c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def faces(state, sources=None):
    weights = values(state['weights_le'])
    result = []
    for f, ancestor in enumerate(state['ancestors']):
        ids = state['indices'][3*f:3*f+3]
        if sources is not None:
            ids = [sources[v] for v in ids]
        result.append({'ids':ids, 'ancestor':ancestor,
                       'chart':tuple(state['elements'][3*f:3*f+3]),
                       'rows':[tuple(map(Q, weights[9*f+3*j:9*f+3*j+3])) for j in range(3)]})
    return result


def topology(mesh):
    incident, edges, neighbors = defaultdict(list), defaultdict(list), defaultdict(set)
    for f, face in enumerate(mesh):
        for j, v in enumerate(face['ids']):
            u = face['ids'][(j+1)%3]
            assert v != u
            incident[v].append(f)
            edges[tuple(sorted((v,u)))].append(f)
            neighbors[v].add(u); neighbors[u].add(v)
    assert all(len(fs) in (1,2) for fs in edges.values())
    boundary = defaultdict(set)
    for (v,u), fs in edges.items():
        if len(fs) == 1:
            boundary[v].add(u); boundary[u].add(v)
    return incident, edges, neighbors, boundary


def signature(face):
    # Retain orientation and exact row values, allowing only cyclic order.
    pairs = list(zip(face['ids'], face['rows']))
    rotations = [tuple(pairs[j:]+pairs[:j]) for j in range(3)]
    return face['ancestor'], face['chart'], min(rotations)


def audit(packet):
    mesh = faces(packet['before'])
    original_area = sum(values(packet['before']['areas_le']))
    for proof in packet['certificates']:
        v, target = proof['vertex'], proof['target']
        incident, edges, neighbors, boundary = topology(mesh)
        star = incident[v]
        assert star and len(boundary[v]) == 2 and target in boundary[v]
        assert all(not packet['before'][flag][v] for flag in ('anchored','removed','outside'))
        charts = {(mesh[f]['ancestor'], mesh[f]['chart']) for f in star}
        assert len(charts) == 1
        # Build actual current B rows independently of the submitted proof.
        rows = {}
        for f in star:
            for node, row in zip(mesh[f]['ids'],mesh[f]['rows']):
                if node in rows:
                    assert rows[node] == row
                rows[node] = row
        a, c = proof['boundary']
        assert boundary[v] == {a,c}
        A, B, C = rows[a], rows[v], rows[c]
        proof_values = values(proof['rows_le'])
        assert tuple(x for row in (A,B,C) for x in row) == tuple(map(Q,proof_values))
        ab, bc = [B[j]-A[j] for j in range(3)], [C[j]-B[j] for j in range(3)]
        assert all(ab[j]*bc[(j+1)%3] == ab[(j+1)%3]*bc[j] for j in range(3))
        assert any(ab[j]*bc[j] > 0 for j in range(3))
        edge_faces = edges[tuple(sorted((v,target)))]
        assert len(edge_faces) == 1
        deleted = edge_faces[0]
        assert neighbors[v] & neighbors[target] == set(mesh[deleted]['ids'])-{v,target}
        for f in star:
            if f == deleted:
                continue
            at = mesh[f]['ids'].index(v)
            mesh[f]['ids'][at] = target
            mesh[f]['rows'][at] = rows[target]
            assert determinant(*mesh[f]['rows']) > 0
        mesh.pop(deleted)
    actual = faces(packet['after'],packet['point_sources'])
    assert Counter(map(signature,mesh)) == Counter(map(signature,actual))
    topology(actual)
    areas = values(packet['after']['areas_le'])
    assert all(a > 0 for a in areas)
    assert abs(sum(areas)-original_area) < 1e-10
    assert len(packet['certificates']) == packet['removed']
    return {'passed':True, 'exact_collapses':len(packet['certificates']),
            'remaining_vertices':packet['after_vertices'], 'area_error':sum(areas)-original_area,
            'scope':'Independent exact-rational boundary/link/B replay only; not complete surgery or real-time.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', nargs='?', type=Path, default=Path('godot/reports/material-reduction.json'))
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.report.read_text(encoding='utf-8')))))
