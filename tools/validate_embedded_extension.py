"""Freeze and test the actual optional FEM Godot extension, not the default app."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bridge-only', action='store_true')
parser.add_argument('--grasp', action='store_true', help='Include exact material attachment contracts')
parser.add_argument('--contact', action='store_true', help='Include retained fine-face static contact contracts')
parser.add_argument('--coupled', action='store_true', help='Include simultaneous FEM/grasp/contact candidate bridge')
parser.add_argument('--curved', action='store_true', help='Include retained curved coupled dynamics and multi-body maps')
parser.add_argument('--trajectory', action='store_true', help='Include original-material trajectory bridge, scalar poses and exact captured core step')
parser.add_argument('--operative-components', action='store_true', help='Qualify operative component contracts, then run a long frozen route separately')
parser.add_argument('--operative-blade', action='store_true', help='Run the same application closed-blade route with original-material dynamics')
options = parser.parse_args()
if (options.operative_blade or options.operative_components) and options.bridge_only:parser.error('Operative contracts require the application probe')
if options.operative_blade:options.operative_components=True
if options.curved:
    if options.bridge_only:parser.error('--curved requires the full state probe')
    options.coupled=True
if options.trajectory and options.bridge_only:parser.error('--trajectory requires the full state probe')
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
    intended['material_witness_bridge.gd'] = ROOT/'native/tests/test_material_witness_godot.gd'
    intended['material_witness_batch_bridge.gd'] = ROOT/'native/tests/test_material_witness_batch_godot.gd'
if options.coupled:
    intended['coupled_bridge.gd'] = ROOT/'native/tests/test_fem_contact_godot.gd'
if options.trajectory:
    intended['trajectory_bridge.gd']=ROOT/'native/tests/test_fem_trajectory_godot.gd'
    intended['temporal_points_bridge.gd']=ROOT/'native/tests/test_temporal_points_godot.gd'
    intended['temporal_material_point.json']=ROOT/'native/tests/fixtures/temporal_material_point.json'
    intended['temporal_point_advance.gd']=ROOT/'native/tests/test_temporal_point_advance_godot.gd'
    intended['trajectory_advance.gd']=ROOT/'native/tests/test_trajectory_advance_godot.gd'
    intended['material_point_advance.gd']=ROOT/'native/tests/test_material_point_advance_godot.gd'
    intended['scripts/material_normal_contact.gd']=ROOT/'godot/scripts/material_normal_contact.gd'
if not options.bridge_only:
    intended['scripts/cut_geometry.gd']=ROOT/'godot/scripts/cut_geometry.gd'
    for name in subprocess.check_output(['git', 'ls-files', '--', 'godot'], cwd=ROOT, text=True).splitlines():
        source = ROOT/name
        if source.is_file() and name != 'godot/project.godot':
            intended[str(source.relative_to(ROOT/'godot'))] = source
    intended['embedded_native.gd'] = ROOT/'godot/tests/test_embedded_native.gd'
    if options.operative_components:
        intended['fine_geometry_state.gd']=ROOT/'native/tests/test_fine_geometry_godot.gd'
        for name in ['scripts/cut_geometry.gd','tests/test_binary64_incision.gd','scripts/operative_membrane.gd','tests/test_operative_embedded.gd','tests/test_operative_blade.gd','tests/test_operative_cut_geometry.gd','tests/test_material_edge_insertion.gd','tests/test_operative_resolution_native.gd','tests/fixtures/operative-blade-area.bin']:
            intended[name]=ROOT/'godot'/name
    if options.grasp:intended['embedded_grasp.gd'] = ROOT/'godot/tests/test_embedded_grasp_native.gd'
    if options.contact:intended['embedded_contact.gd'] = ROOT/'godot/tests/test_embedded_contact_native.gd'
    if options.contact:intended['material_witness_state.gd'] = ROOT/'godot/tests/test_material_witness_native.gd'
    if options.coupled:intended['embedded_coupled.gd'] = ROOT/'godot/tests/test_embedded_coupled_native.gd'
    if options.curved:intended['embedded_curved.gd'] = ROOT/'godot/tests/test_embedded_coupled_curved_native.gd'
    if options.trajectory:
        for name in ['scripts/cut_geometry.gd','tests/test_binary64_incision.gd','scripts/recorded_body_pose.gd','scripts/trajectory_seed.gd','tests/test_trajectory_seed.gd','tests/test_trajectory_pose.gd','tests/test_trajectory_transaction.gd','tests/fixtures/recorded-poses.json','tests/fixtures/operative-motion146-state.bin']:
            intended[name]=ROOT/'godot'/name
inputs = source_hashes([*intended.values(), Path(__file__).resolve(), ROOT/'tools/audit_material_reduction.py'])
for name, source in intended.items():
    destination = probe/name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(build/'membrane.dll', probe/'bin/membrane.dll')
expected = {name:sha256(probe/name) for name in intended}
expected['bin/membrane.dll'] = manifest['artifact_sha256']
engine = ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
report = {'scope':'Native bridge/core and optional original-material closed-blade engineering route only; no complete surgery, actual OS input, clinical, real-time, GPU or release qualification.',
          'qualified':False, 'probe':str(probe), 'inputs':inputs, 'frozen_inputs':expected,
          'build':manifest, 'engine_sha256':sha256(engine), 'stages':[]}
destination = ROOT/'godot/reports'/('grasp-bridge-validation.json' if options.bridge_only and options.grasp else 'fem-bridge-validation.json' if options.bridge_only else 'embedded-grasp-validation.json' if options.grasp else 'embedded-native-validation.json')
if options.contact:destination = destination.with_name('contact-'+destination.name)
if options.coupled:destination = destination.with_name('coupled-'+destination.name)
if options.curved:destination = destination.with_name('curved-'+destination.name)
if options.trajectory:destination = destination.with_name('trajectory-'+destination.name)
if options.operative_blade:destination = destination.with_name('operative-blade-'+destination.name)
elif options.operative_components:destination = destination.with_name('operative-components-'+destination.name)
destination.parent.mkdir(parents=True, exist_ok=True)
stages = [('fresh_import', ['--editor','--import','--quit-after','35','--frame-delay','1000'], None),
          ('legacy_bridge', ['--script','res://legacy_bridge.gd'], 'Native Godot bridge: 0 failures'),
          ('fem_bridge', ['--script','res://fem_bridge.gd'], 'Native FEM Godot bridge: 0 failures')]
if not options.bridge_only:
    stages.append(('embedded_native', ['--script','res://embedded_native.gd'], 'Embedded native dynamics: 0 failures'))
if options.grasp:
    stages.append(('grasp_bridge', ['--script','res://grasp_bridge.gd'], 'Native grasp Godot bridge: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_grasp', ['--script','res://embedded_grasp.gd'], 'Embedded native grasp: 0 failures'))
    if not options.bridge_only:stages.append(('material_attachment_native', ['--script','res://tests/test_material_attachment_native.gd'], 'Native material attachment: 0 failures'))
if options.contact:
    stages.append(('contact_bridge', ['--script','res://contact_bridge.gd'], 'Native embedded contact Godot bridge: 0 failures'))
    stages.append(('material_witness_bridge', ['--script','res://material_witness_bridge.gd'], 'Native material witness bridge: 0 failures'))
    stages.append(('material_witness_batch_bridge',['--script','res://material_witness_batch_bridge.gd'],'Native material witness batch: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_contact', ['--script','res://embedded_contact.gd'], 'Embedded native contact: 0 failures'))
    if not options.bridge_only:stages.append(('material_witness_state', ['--script','res://material_witness_state.gd'], 'Native material witness state: 0 failures'))
if options.coupled:
    stages.append(('coupled_bridge', ['--script','res://coupled_bridge.gd'], 'Native coupled FEM Godot bridge: 0 failures'))
    if not options.bridge_only:stages.append(('embedded_coupled', ['--script','res://embedded_coupled.gd'], 'Embedded native coupled step: 0 failures'))
if options.curved:stages.append(('embedded_curved', ['--script','res://embedded_curved.gd'], 'Embedded native curved coupled step: 0 failures'))
if options.trajectory:
    stages.append(('trajectory_bridge',['--script','res://trajectory_bridge.gd'],'Native trajectory FEM Godot bridge: 0 failures'))
    stages.append(('temporal_points_bridge',['--script','res://temporal_points_bridge.gd'],'Native temporal material points: 0 failures'))
    stages.append(('temporal_point_advance',['--script','res://temporal_point_advance.gd'],'Temporal material point advance: 0 failures'))
    stages.append(('trajectory_pose',['--script','res://tests/test_trajectory_pose.gd'],'Recorded trajectory pose: 0 failures'))
    stages.append(('trajectory_transaction',['--script','res://tests/test_trajectory_transaction.gd'],'Trajectory step transaction: 0 failures'))
    stages.append(('trajectory_seed',['--script','res://tests/test_trajectory_seed.gd'],'Trajectory numerical seed: 0 failures'))
    stages.append(('trajectory_advance',['--script','res://trajectory_advance.gd'],'Embedded trajectory advance: 0 failures'))
    stages.append(('material_point_advance',['--script','res://material_point_advance.gd'],'Material point native advance: 0 failures'))
if options.operative_components:
    stages.append(('fine_anatomy_boundary',['--script','res://tests/test_fine_anatomy.gd','--','--require-native'],'Fine anatomy boundary: 0 failures'))
    stages.append(('fine_geometry_state',['--script','res://fine_geometry_state.gd'],'Fine geometry native state: 0 failures'))
    stages.append(('material_orientation',['--script','res://tests/test_material_orientation.gd'],'Original material orientation: 0 failures'))
    stages.append(('exact_material',['--script','res://tests/test_exact_material.gd'],'Exact material predicates: 0 failures'))
    stages.append(('material_reduce',['--script','res://tests/test_material_reduce.gd'],'Conservative material reduction: 0 failures'))
    stages.append(('binary64_incision',['--script','res://tests/test_binary64_incision.gd'],'Binary64 incision geometry: 0 failures'))
    stages.append(('operative_contract',['--script','res://tests/test_operative_embedded.gd'],'Operative embedded contract: 0 failures'))
    stages.append(('operative_cut_geometry',['--script','res://tests/test_operative_cut_geometry.gd'],'Operative cut geometry: 0 failures'))
    stages.append(('material_edge_insertion',['--script','res://tests/test_material_edge_insertion.gd'],'Material edge insertion: 0 failures'))
    stages.append(('operative_resolution_native',['--script','res://tests/test_operative_resolution_native.gd'],'Operative resolution native: 0 failures'))
if options.operative_blade:
    stages.append(('operative_blade',['--script','res://tests/capture_operative_trajectory.gd'],'Closed blade result: 0 failures'))
for name, arguments, marker in stages:
    log = probe/f'{name}.log'
    print(f'FEM extension {name}: {probe}', flush=True)
    with log.open('wb') as output:
        process = subprocess.run([str(engine),'--headless','--path',str(probe),*arguments], stdout=output, stderr=subprocess.STDOUT)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log.read_text(encoding='utf-8', errors='replace'))
    passed = process.returncode == 0 and not re.search(r'ERROR:|SCRIPT ERROR|leaked at exit|resources still in use', text)
    completed = set(re.findall(r'^\[ DONE \]\s+(\w+)', text, re.MULTILINE))
    if marker is not None:passed = passed and marker in text
    if name == 'material_reduce' and passed:
        audited = subprocess.run([sys.executable,str(ROOT/'tools/audit_material_reduction.py'),str(probe/'reports/material-reduction.json')],cwd=ROOT,capture_output=True,text=True)
        text += audited.stdout+audited.stderr
        with log.open('a',encoding='utf-8') as sink:sink.write(audited.stdout+audited.stderr)
        passed = passed and audited.returncode == 0
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
    if options.curved:
        curved_metrics = probe/'reports/embedded-coupled-curved-metrics.json'
        report['curved_metrics'] = json.loads(curved_metrics.read_text())
        report['curved_metrics_sha256'] = sha256(curved_metrics)
    if options.trajectory:
        metrics=probe/'reports/trajectory-advance-metrics.json'
        report['trajectory_metrics']=json.loads(metrics.read_text())
        report['trajectory_metrics_sha256']=sha256(metrics)
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'qualified':report['qualified'], 'report':str(destination), 'stages':report['stages']}, indent=2))
raise SystemExit(0 if report['qualified'] else 1)
