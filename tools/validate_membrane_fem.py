"""Source-bound FEM/grasp/static contact candidates; no CCD/app/FPS claim."""
import importlib.util
import json
from pathlib import Path
import statistics
import re
import subprocess
import sys
import time
import numpy as np
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
artifact = ROOT/'.tools/native/membrane_fem.dll'
manifest_path = artifact.with_name('membrane_fem.build.json')
manifest = json.loads(manifest_path.read_text())
artifact_hash = sha256(artifact)
if artifact_hash != manifest['artifact_sha256']:
    raise SystemExit('Native FEM artifact differs from its build manifest')
verify_sources(manifest['sources'])
fixture_path = ROOT/'native/tests/fixtures/embedded_membrane_reference.json'
fixture = json.loads(fixture_path.read_text())
for ref, expected in fixture['sources'].items():
    if sha256(ROOT/'godot'/ref.removeprefix('res://')) != expected:
        raise SystemExit(f'Regenerate Godot FEM reference: source changed: {ref}')
test_inputs = source_hashes([ROOT/'native/tests/test_membrane_fem.py', ROOT/'native/tests/test_membrane_grasp.py', ROOT/'native/tests/test_fem_contact.py', fixture_path, Path(__file__).resolve()])
test_output = '';test_count = 0
for pattern in ['test_membrane_fem.py', 'test_membrane_grasp.py', 'test_fem_contact.py']:
    tested = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'native/tests',
                             '-p', pattern, '-v'], cwd=ROOT, text=True, capture_output=True)
    output = tested.stdout+tested.stderr
    print(output, end='');test_output += output
    if tested.returncode:raise SystemExit(tested.returncode)
    matched = re.search(r'Ran (\d+) tests?', output)
    if matched is None:raise SystemExit('Missing native test completion count')
    test_count += int(matched.group(1))
spec = importlib.util.spec_from_file_location('fem_contract', ROOT/'native/tests/test_membrane_fem.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
contract.MembraneFEMTests.setUpClass()
case = contract.MembraneFEMTests()
nodes = np.array([cell['nodes'] for cell in fixture['cells']], dtype=np.int32)
basis = np.array([cell['gradients'] for cell in fixture['cells']]).reshape(-1, 2, 3)
areas = np.array([cell['area'] for cell in fixture['cells']])
predicted = np.array(fixture['rest']).reshape(-1, 3)
predicted[0, 1] += .0005
inverse = 1/np.array(fixture['mass'])
fixed = np.array(fixture['fixed'], dtype=bool)
inverse[fixed] = 0.
measurements = []
for mu in [2., 1e4]:
    samples, residuals, iterations = [], [], []
    for repeat in range(6):
        started = time.perf_counter()
        code, result, stats = case.run_solve(predicted, inverse, nodes, basis, areas, mu=mu, lam=1.5*mu)
        elapsed = (time.perf_counter()-started)*1000
        residual = np.zeros_like(result)
        for ids, shape, area in zip(nodes, basis, areas):
            f = result[ids].T@shape.T
            c = f.T@f
            log_j = .5*np.linalg.slogdet(c)[1]
            p = mu*f+(1.5*mu*log_j-mu)*f@np.linalg.inv(c)
            residual[ids] += (area*p@shape).T
        free = inverse>0
        residual[free] += (result[free]-predicted[free])/(inverse[free, None]*(1/60)**2)
        force = float(np.max(np.abs(residual[free])))
        if code != 0 or force>1e-8 or not np.array_equal(result[fixed], predicted[fixed]):
            raise SystemExit('FEM measured candidate did not pass its independent force/pin gate')
        samples.append(elapsed);residuals.append(force);iterations.append(int(stats[2]))
    measurements.append({'mu':mu, 'lambda':1.5*mu, 'samples_ms':samples,
                         'median_ms':statistics.median(samples), 'max_ms':max(samples),
                         'independent_force_inf':max(residuals), 'iterations':iterations})
verify_sources(manifest['sources']);verify_sources(test_inputs)
if sha256(artifact) != artifact_hash or json.loads(manifest_path.read_text()) != manifest:
    raise SystemExit('Native FEM artifact/manifest changed during qualification')
report = {'scope':'Standalone retained curved energy/implicit candidates, exact linear attachments and static coupled fine-face contact candidates. Contact KKT uses an independent NumPy active-simplex/finite-axis oracle. No CCD, engine coupled time step, operator case, active FPS or clinical calibration.',
          'qualified':True, 'controls':len(predicted), 'cells':len(areas), 'tests':test_count,
          'test_output':test_output, 'build':manifest, 'test_inputs':test_inputs,
          'godot_reference_sources':fixture['sources'], 'measurements':measurements}
destination = ROOT/'godot/reports/fem-core-validation.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'controls':len(predicted), 'cells':len(areas), 'measurements':measurements}, indent=2))
