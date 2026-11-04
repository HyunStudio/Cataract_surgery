"""Frozen focused engine regressions; not full default-app qualification."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
SUITES = ['test_embedded_coupled_state','test_embedded_contact_state','test_embedded_weights','test_embedded_grasp','test_embedded_dynamics',
          'test_fem_reference','test_material_affine','test_embedded_state',
          'test_embedded_cut_route','test_membrane_support','test_embedded_failure',
          'test_membrane_energy','test_membrane_cut_patch','test_blade_sweep',
          'test_blade_incisions','test_blade_operator','test_blade_actual','test_membrane_cut',
          'test_instrument_profile','test_instrument_path','test_surgical_display',
          'test_precise_step_transaction','test_control_context','test_physical_instrument_path',
          'test_body_app','test_rigid_body_app','test_presentation_clock','test_capsule_solver',
          'test_capsule_surface','test_membrane_normal','test_flap_boundary','test_capsule_extraction']
probe = Path(tempfile.mkdtemp(prefix='embedded-regressions-', dir=ROOT/'.tools'))
sources = [ROOT/name for name in subprocess.check_output(['git','ls-files','--','godot'], cwd=ROOT, text=True).splitlines()]
sources = sorted({p for p in sources if p.is_file()} | {ROOT/'godot/tests'/f'{name}.gd' for name in SUITES})
inputs = source_hashes([*sources, Path(__file__).resolve()])
for source in sources:
    target = probe/source.relative_to(ROOT/'godot');target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
frozen = {str(p.relative_to(ROOT/'godot')):sha256(p) for p in sources}
engine = ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
report = {'qualified':False,'scope':'32 focused frozen engine regressions only. Default closed-blade/mass-resolution and fine-traction failures are not covered or waived; no whole-case/contact/GPU/release claim.',
          'probe':str(probe),'engine_sha256':sha256(engine),'inputs':inputs,'frozen_inputs':frozen,'results':[]}
destination = ROOT/'godot/reports/embedded-precision-regression.json'
destination.parent.mkdir(parents=True, exist_ok=True)
stages = [('fresh_import',['--editor','--import','--quit-after','35','--frame-delay','1000'])]
stages += [(name,['--script',f'res://tests/{name}.gd']) for name in SUITES]
for name, arguments in stages:
    print(f'Frozen regression {name}: {probe}', flush=True)
    log = probe/f'{name}.log'
    with log.open('wb') as stream:
        result = subprocess.run([str(engine),'--headless','--path',str(probe),*arguments], stdout=stream, stderr=subprocess.STDOUT)
    output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log.read_text(encoding='utf-8', errors='replace'))
    passed = result.returncode == 0 and not re.search(r'ERROR:|SCRIPT ERROR|leaked at exit|resources still in use', output)
    if name == 'fresh_import':
        completed = set(re.findall(r'^\[ DONE \]\s+(\w+)', output, re.MULTILINE))
        started = set(re.findall(r'^\[[^\]]+\]\s+(\w+)\s+\|', output, re.MULTILINE))
        passed = passed and {'first_scan_filesystem','loading_editor_layout'} <= completed and started <= completed
    else:passed = passed and bool(re.search(r'(?m)^.+: (?:0 failures|0 failure|PASS)(?:[; ].*)?$', output))
    report['results'].append({'test':name,'returncode':result.returncode,'passed':passed,'log':str(log),'log_sha256':sha256(log),'output':output})
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not passed:
        print(output, flush=True);break
verify_sources(inputs)
for name, expected in frozen.items():
    if sha256(probe/name) != expected:raise SystemExit('Frozen regression source changed: '+name)
report['qualified'] = len(report['results']) == len(stages) and all(r['passed'] for r in report['results'])
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'qualified':report['qualified'],'suites':len(report['results'])-1,'report':str(destination)}))
raise SystemExit(0 if report['qualified'] else 1)
