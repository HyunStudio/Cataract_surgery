"""Prove strict separation of exported sharp-edge patches from a pristine mesh."""
import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path

from native_build_provenance import sha256


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def separating_axis(a, b):
    """Sufficient exact separating-axis certificate; None means unproved."""
    for axis in range(3):
        if max(v[axis] for v in a) < min(v[axis] for v in b) or max(v[axis] for v in b) < min(v[axis] for v in a):
            return 'coordinate'
    ea = [sub(a[(i + 1) % 3], a[i]) for i in range(3)]
    eb = [sub(b[(i + 1) % 3], b[i]) for i in range(3)]
    na, nb = cross(ea[0], ea[1]), cross(eb[0], eb[1])
    # Extra in-plane axes cover coplanar triangles. Any strict projection gap
    # is independently sufficient; absence of a gap is never called a hit.
    axes = [na, nb] + [cross(x, y) for x in ea for y in eb]
    axes += [cross(na, edge) for edge in ea] + [cross(nb, edge) for edge in eb]
    for axis in axes:
        pa, pb = [dot(axis, v) for v in a], [dot(axis, v) for v in b]
        if max(pa) < min(pb) or max(pb) < min(pa):
            return 'rational_projection'
    return None


def vertices(flat):
    if not flat or len(flat) % 3 or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in flat):
        raise ValueError('Invalid packed coordinates')
    # JSON numbers round-trip the represented binary64 values. These rational
    # values prove separation of that exported geometry, not an ideal eye.
    return [tuple(Fraction(v) for v in flat[i:i + 3]) for i in range(0, len(flat), 3)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.capture.resolve() == args.output.resolve():
        raise SystemExit('Choose a new output path; evidence must not be overwritten')
    data = json.loads(args.capture.read_text(encoding='utf-8'))
    points = vertices(data['points'])
    ids = data['triangles']
    if len(ids) % 3 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or int(v) != v or v < 0 or v >= len(points) for v in ids):
        raise SystemExit('Invalid mesh indices')
    faces = [tuple(points[int(v)] for v in ids[i:i + 3]) for i in range(0, len(ids), 3)]
    results = []
    for row in data['rows']:
        if row['changed'] != 0:
            continue
        counts = Counter()
        if not row['packets'] or len(row['packets']) != row['patches']:
            raise SystemExit('Missing blade patch packets')
        for packet in row['packets']:
            patch = vertices(packet)
            if len(patch) != 3:
                raise SystemExit('Patch must be a finite triangle')
            for face in faces:
                kind = separating_axis(patch, face)
                if kind is None:
                    raise SystemExit('Claimed missing intersection not independently proved at interval ' + str(row['index']))
                counts[kind] += 1
        results.append({'interval': row['index'], 'patches': row['patches'], 'faces': len(faces), 'strict_separation_certificates': dict(counts)})
    if not results:
        raise SystemExit('No missing-intersection intervals to prove')
    report = {'qualified': False, 'geometric_proof_verified': True,
              'scope': 'Exact rational separating-axis proof for exported pristine fixed triangle mesh and sharp-edge patches only. No dynamic route, cutter acceptance, surgical or release qualification.',
              'capture_sha256': sha256(args.capture), 'verifier_sha256': sha256(Path(__file__)), 'results': results}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'strictly_disjoint_intervals': [row['interval'] for row in results], 'pairs_proved': sum(sum(row['strict_separation_certificates'].values()) for row in results)}))


if __name__ == '__main__':
    main()
