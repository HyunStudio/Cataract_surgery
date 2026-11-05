"""Reproduce the owned cut299 capacity failure without another surgical prefix."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256,source_hashes,verify_sources

ROOT=Path(__file__).resolve().parents[1]
fixture=ROOT/'godot/tests/fixtures/operative-cut299-vertex-state.bin'
inputs=source_hashes([*ROOT.joinpath('godot/scripts').glob('*.gd'),fixture,Path(__file__),ROOT/'tools/native_build_provenance.py'])
probe=Path(tempfile.mkdtemp(prefix='cut299-budget-',dir=ROOT/'.tools'))
shutil.copytree(ROOT/'godot/scripts',probe/'scripts')
shutil.copyfile(fixture,probe/'case.bin')
(probe/'project.godot').write_text('[application]\nconfig/name="Owned cut capacity replay"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
(probe/'replay.gd').write_text('''extends SceneTree
func _initialize()->void:
 var saved:Dictionary=FileAccess.open("res://case.bin",FileAccess.READ).get_var()
 var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
 var before:Dictionary=model.snapshot();var used:Dictionary={}
 for vertex in before.indices:used[vertex]=true
 var reducer=load("res://scripts/embedded_material_reduce.gd")
 var topology:Dictionary=reducer._topology(before);var single_chart_interior:=0
 if topology.valid:
  for vertex in range(before.rest.size()):
   if topology.boundary.has(vertex) or before.anchored[vertex]!=0 or before.removed[vertex]!=0 or before.outside[vertex]!=0:continue
   var star:Array=topology.incident.get(vertex,[])
   if star.is_empty():continue
   var first:Dictionary=topology.faces[star[0]];var same:=true
   for f in star:
    if topology.faces[f].chart!=first.chart or topology.faces[f].ancestor!=first.ancestor:same=false
   if same:single_chart_interior+=1
 var reduced:Dictionary=reducer.simplify(before,128)
 var answer:Dictionary=model._incise_one(saved.patch)
 var summary:={"scope":"Failed cut and current exact boundary reduction only; captured event298 is an intermediate staged cut, not a whole-frame publication.","steps":before.steps,"staged_events":before.events,"vertices":before.rest.size(),"used_vertices":used.size(),"faces":before.indices.size()/3,"controls":before.support.controls.size(),"boundary_vertices":topology.get("boundary",{}).size(),"single_chart_interior_vertices":single_chart_interior,"saved_reason":saved.result.reason,"replayed_reason":answer.reason,"cut_valid":answer.valid,"unchanged_state":var_to_bytes(before)==var_to_bytes(model.snapshot()),"reduction_valid":reduced.valid,"reduction_changed":reduced.get("changed",false),"removed_vertices":reduced.get("removed_vertices",0)}
 FileAccess.open("res://summary.json",FileAccess.WRITE).store_string(JSON.stringify(summary,"  ",true,true))
 print("CUT_REPLAY_COMPLETE");quit()
''',encoding='utf-8')
frozen={str(p.relative_to(probe)):sha256(p) for p in probe.rglob('*') if p.is_file()}
engine=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
engine_hash=sha256(engine);log=probe/'replay.log'
print('Frozen cut299 replay: '+str(probe),flush=True)
with log.open('wb') as output:
    completed=subprocess.run([str(engine),'--headless','--path',str(probe),'--script','res://replay.gd','--quit-after','5'],stdout=output,stderr=subprocess.STDOUT)
output=log.read_text(encoding='utf-8',errors='replace')
assert completed.returncode==0 and 'CUT_REPLAY_COMPLETE' in output and 'ERROR' not in output,output
result=json.loads((probe/'summary.json').read_text(encoding='utf-8'))
assert result['saved_reason']==result['replayed_reason']=='vertex_budget'
assert not result['cut_valid'] and result['unchanged_state']
verify_sources(inputs);assert sha256(engine)==engine_hash
assert all(sha256(probe/name)==value for name,value in frozen.items())
report={'qualified':False,'reproduced':True,'scope':'Exact failed cut reproduction only; no fixed-cut, full route, full surgery or release qualification.',
        'probe':str(probe),'inputs':inputs,'frozen_inputs':frozen,'engine_sha256':engine_hash,
        'log':str(log),'log_sha256':sha256(log),'result':result}
destination=ROOT/'godot/reports/owned-cut299-budget-replay.json'
destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
