"""Compare eight legacy cuts/transfers/supports against the pre-fix source."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '234d448'
inputs = source_hashes([*ROOT.joinpath('godot/scripts').glob('*.gd'), Path(__file__),
                       ROOT/'tools/native_build_provenance.py'])
probe = Path(tempfile.mkdtemp(prefix='legacy-material-compare-',dir=ROOT/'.tools'))
shutil.copytree(ROOT/'godot/scripts',probe/'scripts')
baseline_hashes = {}
for module in ('membrane_support','membrane_refinement'):
    raw = subprocess.check_output(['git','show',f'{BASELINE}:godot/scripts/{module}.gd'],cwd=ROOT)
    target = probe/f'legacy_{module}.gd';target.write_bytes(raw)
    baseline_hashes[module] = sha256(target)
(probe/'project.godot').write_text('[application]\nconfig/name="Legacy material compare"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
(probe/'compare.gd').write_text('''extends SceneTree
func _initialize()->void:
 var old=load("res://legacy_membrane_refinement.gd");var current=load("res://scripts/membrane_refinement.gd")
 var old_support=load("res://legacy_membrane_support.gd");var support=load("res://scripts/membrane_support.gd");var cutter=load("res://scripts/membrane_cut.gd").new()
 var points:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)]);var ids:=PackedInt32Array([0,1,2])
 var state:={"rest":points,"previous":points,"anchored":PackedByteArray([0,0,0]),"removed":PackedByteArray([0,0,0]),"outside":PackedByteArray([0,0,0]),"indices":ids,"face_areas":PackedFloat64Array([2.]),"grasps":{},"grasp_faces":{}}
 var count:=0
 for x in [-.75,-.5,-.25,0.,.25,.5,.75,2.]:
  var cut:Dictionary=cutter.slice_triangle(points,ids,Vector3(x,-.2,-2),Vector3(x,.2,-2),Vector3(x,0,2))
  if not cut.valid:push_error("legacy comparison cut invalid");quit(1);return
  var a:Dictionary=old.prepare(state,cut);var b:Dictionary=current.prepare(state,cut)
  if not a.valid or var_to_bytes(a)!=var_to_bytes(b):push_error("legacy preparation differs");quit(1);return
  if var_to_bytes(old.transfer(state,cut,1.))!=var_to_bytes(current.transfer(state,cut,1.)):push_error("legacy transfer differs");quit(1);return
  var ancestors:=PackedInt32Array();ancestors.resize(cut.indices.size()/3)
  var first:Dictionary=old_support.build(points,ids,a.rest,cut.indices,ancestors,a.face_areas,1.)
  var second:Dictionary=support.build(points,ids,b.rest,cut.indices,ancestors,b.face_areas,1.)
  if not first.valid or var_to_bytes(first)!=var_to_bytes(second):push_error("legacy support differs");quit(1);return
  count+=1
 print("Legacy material bitwise comparison: PASS cases=",count);quit()
''',encoding='utf-8')
frozen = {str(p.relative_to(probe)):sha256(p) for p in probe.rglob('*') if p.is_file()}
engine = ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe';engine_hash = sha256(engine)
log = probe/'compare.log'
with log.open('wb') as sink:
    tested = subprocess.run([str(engine),'--headless','--path',str(probe),'--script','res://compare.gd','--quit-after','5'],stdout=sink,stderr=subprocess.STDOUT)
output = log.read_text(encoding='utf-8',errors='replace')
assert tested.returncode == 0 and 'PASS cases=8' in output and 'ERROR' not in output, output
verify_sources(inputs)
assert sha256(engine) == engine_hash and all(sha256(probe/name) == digest for name,digest in frozen.items())
report = {'passed':True,'cases':8,'scope':'Legacy display cut preparation/transfer/support bitwise comparison only.',
          'baseline_commit':BASELINE,'baseline_hashes':baseline_hashes,'inputs':inputs,
          'probe':str(probe),'engine_sha256':engine_hash,'frozen_inputs':frozen,'log_sha256':sha256(log)}
(ROOT/'godot/reports/legacy-material-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'cases':8,'baseline':BASELINE}))
