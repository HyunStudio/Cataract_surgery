"""Freeze and test the actual optional FEM Godot extension, not the default app."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bridge-only', action='store_true')
parser.add_argument('--grasp', action='store_true', help='Include exact material attachment contracts')
parser.add_argument('--contact', action='store_true', help='Include retained fine-face static contact contracts')
parser.add_argument('--coupled', action='store_true', help='Include simultaneous FEM/grasp/contact candidate bridge')
options = parser.parse_args()
build = ROOT/'.tools/native-godot/bin'
manifest = json.loads((build/'membrane.build.json').read_text())
if sha256(build/'membrane.dll') != manifest['artifact_sha256']:
    raise SystemExit('FEM extension differs from build manifest')
verify_sources(manifest['sources'])
probe = Path(tempfile.mkdtemp(prefix='fem-extension-', dir=ROOT/'.tools'))
intended = {'project.godot':ROOT/'native/test_project.godot',
            'bin/membrane.gdextension':ROOT/'native/membrane.gdextension',
            'legacy_bridge.gd':ROOT/'native/tests/test_godot_bridge.gd',
            'fem_bridge.gd':ROOT/'native/tests/test_fem_godot.gd',
            'refined_flap.json':ROOT/'native/tests/fixtures/refined_flap.json',
            'local_jaw_contact.json':ROOT/'native/tests/fixtures/local_jaw_contact.json'}
if options.grasp:
    intended['grasp_bridge.gd'] = ROOT/'native/tests/test_grasp_godot.gd'
if options.contact:
    intended['contact_bridge.gd'] = ROOT/'native/tests/test_embedded_contact_godot.gd'
if options.coupled:
    intended['coupled_bridge.gd'] = ROOT/'native/tests/test_fem_contact_godot.gd'
if not options.bridge_only:
    for name in subprocess.check_output(['git', 'ls-files', '--', 'godot'], cwd=ROOT, text=True).splitlines():
        source = ROOT/name
        if source.is_file() and name != 'godot/project.godot':
            intended[str(source.relative_to(ROOT/'godot'))] = source
    intended['embedded_native.gd'] = ROOT/'godot/tests/test_embedded_native.gd'
    if options.grasp:intended['embedded_grasp.gd'] = ROOT/'godot/tests/test_embedded_grasp_native.gd'
    if options.contact:intended['embedded_contact.gd'] = ROOT/'godot/tests/test_embedded_contact_native.gd'
    if options.coupled:intended['embedded_coupled.gd'] = ROOT/'godot/tests/test_embedded_coupled_native.gd'
inputs = source_hashes([*intended.values(), Path(__file__).resolve()])
for name, source in intended.items():
    destination = probe/name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(build/'membrane.dll', probe/'bin/membrane.dll')
expected = {name:sha256(probe/name) for name in intended}
expected['bin/membrane.dll'] = manifest['artifact_sha256']
engine = ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
report = {'scope':'Isolated real Godot FEM bridge and optional embedded state; no app/contact/full operation qualification.',
          'qualified':False, 'probe':str(probe), 'inputs':inputs, 'frozen_inputs':expected,
          'build':manifest, 'engine_sha256':sha256(engine), 'stages':[]}
destination = ROOT/'godot/reports'/('grasp-bridge-validation.json' if options.bridge_only and options.grasp else 'fem-bridge-validation.json' if options.bridge_only else 'embedded-grasp-validation.json' if options.grasp else 'embedded-native-validation.json')
if options.contact:destination = destination.with_name('contact-'+destination.name)
if options.coupled:destination = destination.with_name('coupled-'+destination.name)
destination.parent.mkdir(parents=True, exist_ok=True)
stages = [('fresh_import', ['--editor','--import','--quit-after','35','--frame-delay','1000'], None),
          ('legacy_bridge', ['--script','res://legacy_bridge.gd'], 'Native Godot bridge: 0 failures'),
          ('fem_bridge', ['--script','res://fem_bridge.gd'], 'Native FEM Godot bridge: 0 failures')]
if not options.bridge_only:
    stages.append(('embedded_native', ['--script','res://embedded_native.gd'], 'Embedded native dynamics: 0 failures'))
if options.grasp:
    stages.append(('grasp_bridge', ['--script','res://grasp_bridge.gd'], 'Native grasp Godot bridge: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_grasp', ['--script','res://embedded_grasp.gd'], 'Embedded native grasp: 0 failures'))
if options.contact:
    stages.append(('contact_bridge', ['--script','res://contact_bridge.gd'], 'Native embedded contact Godot bridge: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_contact', ['--script','res://embedded_contact.gd'], 'Embedded native contact: 0 failures'))
if options.coupled:
    stages.append(('coupled_bridge', ['--script','res://coupled_bridge.gd'], 'Native coupled FEM Godot bridge: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_coupled', ['--script','res://embedded_coupled.gd'], 'Embedded native coupled step: 0 failures'))
for name, arguments, marker in stages:
    log = probe/f'{name}.log'
    print(f'FEM extension {name}: {probe}', flush=True)
    with log.open('wb') as output:
        process = subprocess.run([str(engine),'--headless','--path',str(probe),*arguments], stdout=output, stderr=subprocess.STDOUT)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log.read_text(encoding='utf-8', errors='replace'))
    passed = process.returncode == 0 and not re.search(r'ERROR:|SCRIPT ERROR|leaked at exit|resources still in use', text)
    completed = set(re.findall(r'^\[ DONE \]\s+(\w+)', text, re.MULTILINE))
    if marker is not None:passed = passed and marker in text
    if name == 'fresh_import':
        started = set(re.findall(r'^\[[^\]]+\]\s+(\w+)\s+\|', text, re.MULTILINE))
        passed = passed and {'first_scan_filesystem','loading_editor_layout'} <= completed and started <= completed
    report['stages'].append({'name':name, 'arguments':arguments, 'returncode':process.returncode,
                             'passed':passed, 'log':str(log), 'log_sha256':sha256(log)})
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not passed:
        print(text, flush=True)
        break
verify_sources(manifest['sources']);verify_sources(inputs)
if any(sha256(probe/name) != value for name, value in expected.items()):
    raise SystemExit('Frozen FEM validation inputs changed during run')
report['qualified'] = len(report['stages']) == len(stages) and all(stage['passed'] for stage in report['stages'])
if report['qualified'] and not options.bridge_only:
    metrics = probe/'reports/embedded-native-metrics.json'
    report['metrics'] = json.loads(metrics.read_text())
    report['metrics_sha256'] = sha256(metrics)
    if options.grasp:
        grasp_metrics = probe/'reports/embedded-grasp-metrics.json'
        report['grasp_metrics'] = json.loads(grasp_metrics.read_text())
        report['grasp_metrics_sha256'] = sha256(grasp_metrics)
    if options.contact:
        contact_metrics = probe/'reports/embedded-contact-metrics.json'
        report['contact_metrics'] = json.loads(contact_metrics.read_text())
        report['contact_metrics_sha256'] = sha256(contact_metrics)
    if options.coupled:
        coupled_metrics = probe/'reports/embedded-coupled-metrics.json'
        report['coupled_metrics'] = json.loads(coupled_metrics.read_text())
        report['coupled_metrics_sha256'] = sha256(coupled_metrics)
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'qualified':report['qualified'], 'report':str(destination), 'stages':report['stages']}, indent=2))
raise SystemExit(0 if report['qualified'] else 1)
