"""Replay the owned incision, then independently audit every exact material face."""
import base64
from fractions import Fraction as Q
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from native_build_provenance import sha256, source_hashes, verify_sources

ROOT = Path(__file__).resolve().parents[1]
case = ROOT/'godot/tests/fixtures/operative-fine-orientation-state.bin'
sources = [*ROOT.joinpath('godot/scripts').glob('*.gd'), case,
           Path(__file__).resolve(), ROOT/'tools/native_build_provenance.py']
inputs = source_hashes(sources)
engine = ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
engine_hash = sha256(engine)
probe = Path(tempfile.mkdtemp(prefix='material-orientation-audit-', dir=ROOT/'.tools'))
shutil.copytree(ROOT/'godot/scripts', probe/'scripts')
shutil.copyfile(case, probe/'case.bin')
(probe/'project.godot').write_text('[application]\nconfig/name="Owned material audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf-8')
(probe/'audit.gd').write_text('''extends SceneTree
func _initialize()->void:
 var packet:Dictionary=FileAccess.open("res://case.bin",FileAccess.READ).get_var()
 var tissue=load("res://scripts/embedded_membrane.gd").new();tissue._state=packet.state.duplicate(true)
 var before:Dictionary=tissue.snapshot();var result:Dictionary=tissue._incise_one(packet.patch)
 if not result.valid or not result.changed:push_error("owned incision rejected: "+str(result));quit(1);return
 var after:Dictionary=tissue.snapshot()
 var data:={"weights_le":Marshalls.raw_to_base64(after.support.weights.to_byte_array()),"areas_le":Marshalls.raw_to_base64(after.areas.to_byte_array()),"before_areas_le":Marshalls.raw_to_base64(before.areas.to_byte_array()),"steps":[before.steps,after.steps],"events":[before.events,after.events],"time":[before.time,after.time],"vertices":after.rest.size(),"triangles":after.indices.size()/3}
 var file:=FileAccess.open("res://candidate.json",FileAccess.WRITE);file.store_string(JSON.stringify(data,"",true,true))
 print("Owned material audit replay: PASS");quit()
''', encoding='utf-8')
frozen = {str(p.relative_to(probe)):sha256(p) for p in probe.rglob('*') if p.is_file()}
log = probe/'replay.log'
with log.open('wb') as sink:
    process = subprocess.run([str(engine),'--headless','--path',str(probe),
                              '--script','res://audit.gd','--quit-after','5'], stdout=sink, stderr=subprocess.STDOUT)
text = log.read_text(encoding='utf-8',errors='replace')
assert process.returncode == 0 and 'Owned material audit replay: PASS' in text and 'ERROR' not in text, text
candidate = json.loads((probe/'candidate.json').read_text(encoding='utf-8'))


def values(encoded):
    raw = base64.b64decode(encoded)
    return struct.unpack('<'+'d'*(len(raw)//8),raw)


weights = values(candidate['weights_le'])
assert len(weights) == candidate['triangles']*9
minimum = None
for off in range(0,len(weights),9):
    a,b,c = [list(map(Q,weights[off+3*j:off+3*j+3])) for j in range(3)]
    determinant = (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])
                   + a[2]*(b[0]*c[1]-b[1]*c[0]))
    assert determinant > 0, (off//9,determinant)
    minimum = determinant if minimum is None else min(minimum,determinant)
areas = values(candidate['areas_le']);old_areas = values(candidate['before_areas_le'])
assert len(areas) == candidate['triangles'] and all(a > 0 for a in areas)
area_error = sum(map(Q,areas))-sum(map(Q,old_areas))
assert abs(area_error) < Q(1e-10)
assert candidate['steps'][0] == candidate['steps'][1] and candidate['time'][0] == candidate['time'][1]
assert candidate['events'][1] == candidate['events'][0]+1
assert candidate['vertices'] <= 4096 and candidate['triangles'] <= 8192
verify_sources(inputs)
assert sha256(engine) == engine_hash and all(sha256(probe/name) == value for name,value in frozen.items())
report = {'passed':True,'scope':'Owned incision exact Fraction audit only; no whole route, surgical, real-time or release qualification.',
          'inputs':inputs,'probe':str(probe),'engine_sha256':engine_hash,'frozen_inputs':frozen,
          'candidate_sha256':sha256(probe/'candidate.json'),'log_sha256':sha256(log),
          'positive_faces':candidate['triangles'],'vertices':candidate['vertices'],
          'minimum_material_determinant':float(minimum),'area_error':float(area_error)}
destination = ROOT/'godot/reports/owned-material-orientation-audit.json'
destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ('passed','positive_faces','vertices','minimum_material_determinant','area_error')}))
