"""Source-bound numerical boundary qualification; not full surgical completion."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from native_build_provenance import sha256,source_hashes,verify_sources

ROOT=Path(__file__).resolve().parents[1]
ARTIFACTS=['material_point_probe','membrane_kernel','contact_distance','contact_guard','contact_merit_probe',
           'contact_step_probe','membrane_contact','membrane_fem','fp_environment_probe','contact_activity_probe']
PATTERNS=['test_fem_temporal_points.py','test_material_witness_batch.py','test_fine_geometry_guard.py','test_material_point_distance.py','test_fem_material_points.py','test_membrane_kernel.py','test_contact_distance.py','test_embedded_contact.py',
          'test_contact_guard.py','test_contact_merit_difference.py','test_point_merit_difference.py',
          'test_contact_step_model.py','test_coupled_contact.py','test_trajectory_contact.py',
          'test_anatomical_contact.py','test_membrane_fem.py','test_membrane_grasp.py',
          'test_fem_contact.py','test_fem_trajectory.py','test_fem_warm_trajectory.py','test_fem_polish_freshness.py','test_fp_environment.py','test_native_provenance.py','test_contact_activity.py','test_temporal_hull_cache.py','test_physical_zero_certificate.py','test_fem_precise_endpoint.py','test_material_witness.py']
builds={}
for name in ARTIFACTS:
    artifact=ROOT/'.tools/native'/f'{name}.dll';manifest_path=artifact.with_suffix('.build.json')
    if not artifact.exists() or not manifest_path.exists():raise SystemExit('Build missing numerical artifact: '+name)
    manifest=json.loads(manifest_path.read_text())
    if sha256(artifact)!=manifest['artifact_sha256']:raise SystemExit('Artifact/manifest mismatch: '+name)
    verify_sources(manifest['sources'])
    if str(Path('native/fp_environment.h')) not in manifest['sources']:raise SystemExit('Missing boundary dependency: '+name)
    builds[name]=manifest
sources=[*ROOT.joinpath('native/tests').glob('*.py'),*ROOT.joinpath('native/tests/fixtures').rglob('*.json'),ROOT/'docs/assets/operative-motion150-budget-case-2026-11-05.json',ROOT/'docs/assets/operative-motion156-native-case-2026-11-05.json',ROOT/'docs/assets/operative-motion167-native-case-2026-11-05.json',Path(__file__).resolve()]
inputs=source_hashes(sources)
probe=Path(tempfile.mkdtemp(prefix='fp-qualification-',dir=ROOT/'.tools'))
report={'qualified':False,'scope':'Native numerical boundary and component regressions only. Runtime enclosure, normal/early/exception/nested restoration, actual API bitwise results across64caller contexts with independent x87/SSE rounding, old/new numerical suites. No actual surgical/controller case, real-time/GPU throughput, clinical calibration or Windows release claim.',
        'probe':str(probe),'builds':builds,'inputs':inputs,'results':[]}
destination=ROOT/'godot/reports/fp-environment-validation.json';destination.parent.mkdir(parents=True,exist_ok=True)
for pattern in PATTERNS:
    print('Numerical boundary: '+pattern,flush=True)
    completed=subprocess.run([sys.executable,'-m','unittest','discover','-s','native/tests','-p',pattern,'-v'],cwd=ROOT,capture_output=True,text=True)
    output=completed.stdout+completed.stderr;log=probe/(pattern+'.log');log.write_text(output,encoding='utf-8')
    match=re.search(r'Ran (\d+) tests?',output)
    passed=completed.returncode==0 and match is not None and int(match[1])>0
    report['results'].append({'pattern':pattern,'returncode':completed.returncode,'passed':passed,'tests':int(match[1]) if match else 0,'log':str(log),'log_sha256':sha256(log),'output':output})
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not passed:print(output,flush=True)
verify_sources(inputs)
for name,manifest in builds.items():
    artifact=ROOT/'.tools/native'/f'{name}.dll'
    verify_sources(manifest['sources'])
    if sha256(artifact)!=manifest['artifact_sha256'] or json.loads(artifact.with_suffix('.build.json').read_text())!=manifest:
        raise SystemExit('Numerical build changed during qualification: '+name)
report['qualified']=all(r['passed'] for r in report['results'])
report['tests']=sum(r['tests'] for r in report['results'])
destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'qualified':report['qualified'],'tests':report['tests'],'report':str(destination)}))
raise SystemExit(0 if report['qualified'] else 1)
