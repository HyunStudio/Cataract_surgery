"""Freeze actual temporal point bridge and owned180 step; never a full-route gate."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256,source_hashes,verify_sources
ROOT=Path(__file__).resolve().parents[1]
engine=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
artifact=ROOT/'.tools/native-godot/bin/membrane.dll'
manifest=json.loads(artifact.with_suffix('.build.json').read_text());verify_sources(manifest['sources'])
assert sha256(artifact)==manifest['artifact_sha256']
probe=Path(tempfile.mkdtemp(prefix='owned-temporal-',dir=ROOT/'.tools'))
intended={str(Path(name).relative_to('godot')):ROOT/name for name in subprocess.check_output(['git','ls-files','--','godot'],cwd=ROOT,text=True).splitlines() if (ROOT/name).is_file() and name!='godot/project.godot'}
intended.update({'project.godot':ROOT/'native/test_project.godot','bin/membrane.gdextension':ROOT/'native/membrane.gdextension','temporal_points_bridge.gd':ROOT/'native/tests/test_temporal_points_godot.gd','temporal_point_advance.gd':ROOT/'native/tests/test_temporal_point_advance_godot.gd','temporal_material_point.json':ROOT/'native/tests/fixtures/temporal_material_point.json'})
inputs=source_hashes([*intended.values(),Path(__file__),ROOT/'tools/native_build_provenance.py'])
for name,source in intended.items():
 target=probe/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
shutil.copyfile(artifact,probe/'bin/membrane.dll')
frozen={name:sha256(probe/name) for name in intended};frozen['bin/membrane.dll']=manifest['artifact_sha256']
report={'qualified':False,'owned_step_qualified':False,'scope':'Actual temporal point bridge and owned180 engine step only. No complete route/surgery, actual OS input, real-time/GPU or release qualification.','probe':str(probe),'inputs':inputs,'frozen_inputs':frozen,'build':manifest,'engine_sha256':sha256(engine),'stages':[]}
destination=ROOT/'godot/reports/owned180-temporal-validation.json'
stages=[('fresh_import',['--editor','--import','--quit-after','35','--frame-delay','1000'],None),('temporal_points_bridge',['--script','res://temporal_points_bridge.gd'],'Native temporal material points: 0 failures'),('temporal_point_advance',['--script','res://temporal_point_advance.gd'],'Temporal material point advance: 0 failures')]
for name,arguments,marker in stages:
 print('Owned temporal '+name+': '+str(probe),flush=True);log=probe/(name+'.log')
 with log.open('wb') as sink:completed=subprocess.run([str(engine),'--headless','--path',str(probe),*arguments],stdout=sink,stderr=subprocess.STDOUT)
 text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',log.read_text(encoding='utf-8',errors='replace'))
 passed=completed.returncode==0 and not re.search('ERROR:|SCRIPT ERROR|leaked at exit|resources still in use',text)
 if marker is not None:passed=passed and marker in text
 else:
  done=set(re.findall(r'^\[ DONE \]\s+(\w+)',text,re.MULTILINE));started=set(re.findall(r'^\[[^\]]+\]\s+(\w+)\s+\|',text,re.MULTILINE))
  passed=passed and {'first_scan_filesystem','loading_editor_layout'}<=done and started<=done
 report['stages'].append({'name':name,'returncode':completed.returncode,'passed':passed,'log':str(log),'log_sha256':sha256(log)})
 destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
 if not passed:print(text,flush=True);break
verify_sources(inputs);verify_sources(manifest['sources'])
assert all(sha256(probe/name)==value for name,value in frozen.items())
assert sha256(engine)==report['engine_sha256']
report['owned_step_qualified']=len(report['stages'])==len(stages) and all(s['passed'] for s in report['stages'])
metrics=probe/'reports/owned180-temporal-metrics.json'
if metrics.exists():report['metrics']=json.loads(metrics.read_text());report['metrics_sha256']=sha256(metrics)
destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'owned_step_qualified':report['owned_step_qualified'],'report':str(destination),'probe':str(probe)}))
raise SystemExit(0 if report['owned_step_qualified'] else 1)
