"""Reproduce the owned legacy physics topology failure; never a passing-case waiver."""
from collections import defaultdict
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from native_build_provenance import sha256,source_hashes,verify_sources
ROOT=Path(__file__).resolve().parents[1]
case=ROOT/'godot/tests/fixtures/legacy-physics-nonmanifold-state.bin'
inputs=source_hashes([*ROOT.joinpath('godot/scripts').glob('*.gd'),case,Path(__file__),ROOT/'tools/native_build_provenance.py'])
probe=Path(tempfile.mkdtemp(prefix='legacy-topology-',dir=ROOT/'.tools'))
shutil.copytree(ROOT/'godot/scripts',probe/'scripts');shutil.copyfile(case,probe/'case.bin')
(probe/'project.godot').write_text('[application]\nconfig/name="Owned legacy topology failure"\n',encoding='utf-8')
(probe/'replay.gd').write_text('''extends SceneTree
func _initialize()->void:
 var data:Dictionary=FileAccess.open("res://case.bin",FileAccess.READ).get_var()
 var cutter=load("res://scripts/membrane_cut.gd").new()
 var before:=var_to_bytes([data.points,data.indices,data.patch])
 var result:Dictionary=cutter.slice_triangle(data.points,data.indices,data.patch[0],data.patch[1],data.patch[2],data.max_vertices,data.max_triangles,data.material_partition)
 var out:={"vertices":data.points.size(),"current":Array(data.indices),"previous":Array(data.previous.indices),"previous_vertices":data.previous.points.size(),"reason":result.reason,"valid":result.valid,"unchanged":before==var_to_bytes([data.points,data.indices,data.patch])}
 FileAccess.open("res://topology.json",FileAccess.WRITE).store_string(JSON.stringify(out))
 print("Owned legacy topology: reproduced");quit()
''',encoding='utf-8')
frozen={str(p.relative_to(probe)):sha256(p) for p in probe.rglob('*') if p.is_file()}
engine=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe';engine_hash=sha256(engine);log=probe/'replay.log'
with log.open('wb') as sink:
 process=subprocess.run([str(engine),'--headless','--path',str(probe),'--script','res://replay.gd','--quit-after','5'],stdout=sink,stderr=subprocess.STDOUT)
text=log.read_text(encoding='utf-8',errors='replace')
assert process.returncode==0 and 'Owned legacy topology: reproduced' in text and 'ERROR' not in text,text
packet=json.loads((probe/'topology.json').read_text())
assert not packet['valid'] and packet['reason']=='nonmanifold_vertex' and packet['unchanged']
def audit(ids):
 faces=[tuple(ids[i:i+3]) for i in range(0,len(ids),3)];edges=defaultdict(list);incident=defaultdict(set)
 for i,face in enumerate(faces):
  for v in face:incident[v].add(i)
  for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))].append(i)
 boundary=defaultdict(int)
 for (a,b),fs in edges.items():
  assert len(fs) in (1,2)
  if len(fs)==1:boundary[a]+=1;boundary[b]+=1
 bad=[]
 for v,fs in incident.items():
  remaining=set(fs);components=0
  while remaining:
   stack=[remaining.pop()];components+=1
   while stack:
    for a in faces[stack.pop()]:
     if a==v:continue
     for f in edges[tuple(sorted((v,a)))]:
      if f in remaining:remaining.remove(f);stack.append(f)
  if boundary[v] not in (0,2) or components!=1:bad.append({'vertex':v,'boundary_degree':boundary[v],'fan_components':components})
 return faces,bad
old,before=audit(packet['previous']);new,after=audit(packet['current'])
assert not before and len(after)==4 and len(set(old)-set(new))==10 and not set(new)-set(old)
assert packet['vertices']==packet['previous_vertices']==295
verify_sources(inputs);assert sha256(engine)==engine_hash
assert all(sha256(probe/name)==value for name,value in frozen.items())
report={'qualified':False,'reproduced':True,'scope':'Owned legacy physics failure diagnosis only. Previous accepted cutter output has valid vertex links; subsequent physics removes10faces and creates4disconnected stars. Guard rejection is correct. No product fix, actual full case or release qualification.','inputs':inputs,'frozen_inputs':frozen,'probe':str(probe),'engine_sha256':engine_hash,'log_sha256':sha256(log),'packet_sha256':sha256(probe/'topology.json'),'previous_faces':len(old),'current_faces':len(new),'removed_faces':10,'bad_vertices':after,'reason':packet['reason'],'unchanged_cut_inputs':packet['unchanged']}
(ROOT/'godot/reports/legacy-topology-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['reproduced','previous_faces','current_faces','removed_faces','bad_vertices','reason']}))
