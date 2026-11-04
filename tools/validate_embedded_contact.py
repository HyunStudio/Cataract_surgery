"""Source-bound static retained-face derivatives; no coupled contact/CCD claim."""
import json
from pathlib import Path
import re
import subprocess
import sys
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
artifact = ROOT/'.tools/native/contact_distance.dll'
manifest_path = artifact.with_name('contact_distance.build.json')
manifest = json.loads(manifest_path.read_text())
artifact_hash = sha256(artifact)
if artifact_hash != manifest['artifact_sha256']:
    raise SystemExit('Contact artifact differs from build manifest')
verify_sources(manifest['sources'])
inputs = source_hashes([ROOT/'native/tests/test_contact_distance.py',
                       ROOT/'native/tests/test_embedded_contact.py', Path(__file__).resolve()])
count = 0;output = ''
for pattern in ('test_contact_distance.py', 'test_embedded_contact.py'):
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'native/tests',
                             '-p', pattern, '-v'], cwd=ROOT, text=True, capture_output=True)
    part = result.stdout+result.stderr;print(part, end='');output += part
    if result.returncode:raise SystemExit(result.returncode)
    matched = re.search(r'Ran (\d+) tests?', part)
    if not matched:raise SystemExit('Missing terminal test count')
    count += int(matched.group(1))
verify_sources(manifest['sources']);verify_sources(inputs)
if sha256(artifact) != artifact_hash or json.loads(manifest_path.read_text()) != manifest:
    raise SystemExit('Contact artifact/manifest changed during qualification')
report = {'qualified':True, 'tests':count, 'build':manifest, 'test_inputs':inputs, 'test_output':output,
          'scope':'Static retained fine-face squared distance, smooth-feature exact Hessian and affine control pullback only. No coupled equilibrium, continuous guard, cut-remap certificate, actual input, active GPU FPS or clinical calibration.'}
destination = ROOT/'godot/reports/embedded-contact-core-validation.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'qualified':True, 'tests':count}))
