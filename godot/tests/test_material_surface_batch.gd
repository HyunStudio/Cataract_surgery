extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
 var fault:=""
 var calls:=0
 var scalar_calls:=0
 var saved:Dictionary={}
 func material_witness_fem(v:Dictionary)->Dictionary:
  scalar_calls+=1
  var x:float=v.segment[0];var y:float=v.segment[1];var z:float=v.segment[2]
  return {"status":0 if y!=0. else 1,"values":PackedFloat64Array([y*y,absf(y)-v.radius,x,y,z,x,0.,z,1.-x-z,x,z,0.,0.])}
 func material_witnesses_fem(v:Dictionary)->Dictionary:
  calls+=1
  var statuses:=PackedInt32Array();var values:=PackedFloat64Array()
  for face in range(v.controls.size()/9):
   for body in range(v.capsules.size()/7):
    var c:int=body*7;var x:float=v.capsules[c];var y:float=v.capsules[c+1];var z:float=v.capsules[c+2]
    statuses.append(0 if y!=0. else 1)
    values.append_array(PackedFloat64Array([y*y,absf(y)-v.capsules[c+6],x,y,z,x,0.,z,1.-x-z,x,z,0.,0.]))
  var out:={"status":0,"statuses":statuses,"values":values}
  if fault=="shape":out.values=PackedFloat64Array([0.])
  if fault=="aggregate":out.status=1
  if fault=="statuses":out.statuses=Array(statuses)
  if fault=="last_status":out.statuses[-1]=2
  if fault=="nan":out.values[-12]=NAN
  if fault=="distance":out.values[-13]=-1.
  if fault=="barycentric":out.values[-5]=2.
  if fault=="reconstruction":out.values[-8]+=1.
  if fault=="gap":out.values[-12]+=.01
  if fault=="minimum":
   var o:int=values.size()-13;var c:int=v.capsules.size()-7;var x:float=v.capsules[c];var y:float=v.capsules[c+1];var z:float=v.capsules[c+2]
   out.values[o]=x*x+y*y+z*z;out.values[o+1]=sqrt(out.values[o])-v.capsules[c+6]
   for k in range(3):out.values[o+5+k]=0.;out.values[o+8+k]=1. if k==0 else 0.
  if fault in ["mutate","forge"]:
   for face in range(v.controls.size()/9):
    for j in range(3):v.controls[face*9+j*3+1]=.05
   v.weights[0]=0.
   if fault=="forge":out.values[6]=.05
  saved=out.duplicate(true)
  return out
class NormalBackend extends Backend:
 var solves:=0
 func solve_trajectory_material_points_fem(v:Dictionary)->Dictionary:
  solves+=1
  var dual:=PackedFloat64Array();dual.resize(v.face_nodes.size()/3*v.kinds.size()*v.times.size())
  var stats:=PackedFloat64Array();stats.resize(16);stats[15]=1. if not dual.is_empty() else 0.
  return {"status":0,"xyz":v.xyz.duplicate(),"dual":dual,"stats":stats}
func _initialize()->void:
 var query=load("res://scripts/material_surface_query.gd").new()
 check(query.has_method("batch"),"runtime needs complete independently checked all-pair material witnesses")
 if failures:print("Material surface batch: ",failures," failures");quit(1);return
 var q:=PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]);q.append_array(q.duplicate())
 var weights:=PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.]);weights.append_array(weights.duplicate())
 var state:={"steps":7,"events":9,"xyz":q,"indices":PackedInt32Array([0,1,2,3,4,5]),"support":{"elements":PackedInt32Array([0,1,2,3,4,5]),"weights":weights}}
 var capsules:=PackedFloat64Array([.2,.1,.2,.2,.1,.2,.01,.25,.2,.25,.25,.2,.25,.02])
 var before:=var_to_bytes([state,capsules]);var backend:=Backend.new()
 var result:Dictionary=query.batch(state,capsules,backend)
 check(result.valid and result.values.size()==52 and result.statuses==PackedInt32Array([0,0,0,0]) and backend.calls==1 and backend.scalar_calls==0,"one typed batch returns every ordered pair")
 if result.valid:
  for face in range(2):
   for body in range(2):
    var scalar:Dictionary=query.face(state,face,capsules.slice(body*7,body*7+6),capsules[body*7+6],backend)
    check(scalar.valid and result.values.slice((face*2+body)*13,(face*2+body+1)*13).to_byte_array()==scalar.values.to_byte_array(),"independent bulk and scalar witness bits agree")
  var saved:=var_to_bytes(backend.saved);result.values[0]=9.;result.statuses[0]=-1
  check(var_to_bytes(backend.saved)==saved,"public batch results own backend packet memory")
 for fault in ["shape","aggregate","statuses","last_status","nan","distance","barycentric","reconstruction","gap","minimum","forge"]:
  backend=Backend.new();backend.fault=fault
  check(not query.batch(state,capsules,backend).valid and backend.scalar_calls==0,"invalid late bulk packet cannot fall back or publish: "+fault)
 backend=Backend.new();backend.fault="mutate"
 check(query.batch(state,capsules,backend).valid and var_to_bytes([state,capsules])==before,"request buffers cannot alias physical inputs or independent geometry")
 var bad:Dictionary=state.duplicate(true);bad.support.weights[-1]=NAN;backend=Backend.new()
 check(not query.batch(bad,capsules,backend).valid and backend.calls==0,"invalid later material face rejects before backend")
 backend=Backend.new();var empty:Dictionary=query.batch(state,PackedFloat64Array(),backend)
 check(empty.valid and empty.values.is_empty() and backend.calls==0,"zero bodies preserve vacuous inspection without native call")
 var too_many:=PackedFloat64Array();too_many.resize(65*7)
 check(not query.batch(state,too_many,backend).valid and backend.calls==0,"body capacity is checked before allocation or backend")
 var capped:Dictionary=state.duplicate(true);capped.indices.resize(8193*3)
 check(not query.batch(capped,capsules,backend).valid and backend.calls==0,"face capacity is checked before geometry allocation")
 check(not query.batch(state,capsules,RefCounted.new()).valid,"missing bulk capability is explicit")
 check(var_to_bytes([state,capsules])==before,"all batch paths preserve source positions/material/history and body packet")
 var packet:=PackedFloat64Array([.2,.1,.2,.2,.1,.2,.2,.1,.2,.2,.1,.2,.01]);packet.resize(41)
 var context:={"previous":q,"times":PackedFloat64Array([.5,1.]),"kinds":PackedInt32Array([0]),"packets":packet,"bodies":1}
 var request:={"xyz":q,"budget":10,"previous":q,"times":context.times,"kinds":context.kinds,"packets":packet}
 var normals=load("res://scripts/material_normal_contact.gd").new();var normal_backend:=NormalBackend.new()
 var solved:Dictionary=normals.solve_trajectory(state,request,context,normal_backend)
 check(solved.valid and normal_backend.calls==4 and normal_backend.scalar_calls==0,"all temporal layers use complete bulk inspection when available")
 normal_backend=NormalBackend.new();normal_backend.fault="last_status"
 check(not normals.solve_trajectory(state,request,context,normal_backend).valid and normal_backend.solves==0 and normal_backend.scalar_calls==0,"malformed full batch cannot be hidden by scalar fallback or solving")
 print("Material surface batch: ",failures," failures");quit(1 if failures else 0)
