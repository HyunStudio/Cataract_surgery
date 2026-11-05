"""Frozen alternating owned179 comparison; not real-time or full-case qualification."""
import json
from pathlib import Path
import re
import statistics
import subprocess
from native_build_provenance import sha256,source_hashes,verify_sources
ROOT=Path(__file__).resolve().parents[1]
report_path=ROOT/'godot/reports/operative-components-trajectory-curved-coupled-contact-embedded-grasp-validation.json'
source=json.loads(report_path.read_text());baseline=Path(source['probe']);candidate=ROOT/'.tools/material-face-candidate'
assert source['qualified']
engine=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
assert sha256(engine)==source['engine_sha256']
assert all(sha256(baseline/name)==value for name,value in source['frozen_inputs'].items())
changed=['scripts/material_surface_query.gd','scripts/material_normal_contact.gd']
expected=dict(source['frozen_inputs'])
for name in expected:
 if Path(name).as_posix() in changed:expected[name]=sha256(candidate/name)
assert all(sha256(candidate/name)==value for name,value in expected.items())
inputs=source_hashes([Path(__file__),ROOT/'tools/benchmark_material_face.gd',*[ROOT/'godot'/name for name in changed]])
runs=[]
for label in ['baseline','candidate','candidate','baseline','baseline','candidate']:
 probe=baseline if label=='baseline' else candidate
 log=candidate/f'comparison-{len(runs)}.log'
 with log.open('wb') as sink:
  process=subprocess.run([str(engine),'--headless','--path',str(probe),'--script',str(ROOT/'tools/benchmark_material_face.gd'),'--quit-after','10'],stdout=sink,stderr=subprocess.STDOUT)
 text=log.read_text(encoding='utf-8',errors='replace')
 assert process.returncode==0 and 'Material face owned179:' in text and not re.search('ERROR:|SCRIPT ERROR',text),text
 metrics=json.loads((probe/'reports/material-face-time.json').read_text())
 assert metrics['valid'] and metrics['force_inf']<=1e-8 and metrics['iterations']==37
 metrics.update(label=label,log_sha256=sha256(log));runs.append(metrics)
 print(json.dumps(metrics),flush=True)
assert len({r['state_sha256'] for r in runs})==1,'Owned state/result changed'
medians={label:statistics.median(r['elapsed_us'] for r in runs if r['label']==label) for label in ['baseline','candidate']}
verify_sources(inputs)
assert all(sha256(baseline/name)==value for name,value in source['frozen_inputs'].items())
assert all(sha256(candidate/name)==value for name,value in expected.items())
result={'qualified':False,'bitwise_parity':True,'scope':'Owned179 alternating time and exact result/state comparison only; no full route, real-time or release claim.','source_report_sha256':sha256(report_path),'engine_sha256':sha256(engine),'inputs':inputs,'baseline':str(baseline),'candidate':str(candidate),'candidate_frozen_inputs':expected,'runs':runs,'median_us':medians,'speedup':medians['baseline']/medians['candidate']}
(ROOT/'godot/reports/material-face-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'bitwise_parity':True,'median_us':medians,'speedup':result['speedup']}))
