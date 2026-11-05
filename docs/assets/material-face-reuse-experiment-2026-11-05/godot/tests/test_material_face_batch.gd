extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
 var calls:=0
 var fail_call:=-1
 func material_witness_fem(value:Dictionary)->Dictionary:
  calls+=1
  if calls==fail_call:return {"status":0,"values":PackedFloat64Array([NAN])}
  var y:float=value.segment[1]
  return {"status":0,"values":PackedFloat64Array([y*y,y-value.radius,.25,y,.25,.25,0.,.25,.5,.25,.25,0.,0.])}
class MutatingBackend extends Backend:
 func material_witness_fem(value:Dictionary)->Dictionary:
  var answer:=super.material_witness_fem(value)
  value.controls[0]=9.;value.weights[0]=9.
  return answer
func _initialize()->void:
 var query=load("res://scripts/material_surface_query.gd").new()
 check(query.has_method("face_bodies"),"multiple bodies need a locally prepared face query")
 if failures:print("Material face batch: ",failures," failures");quit(1);return
 var tissue=load("res://scripts/embedded_membrane.gd").new()
 tissue.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
 var state:Dictionary=tissue.snapshot();var capsules:=PackedFloat64Array([.25,.1,.25,.25,.1,.25,.01,.25,.2,.25,.25,.2,.25,.02])
 var backend:=Backend.new();var old:=var_to_bytes([state,capsules])
 var batch:Dictionary=query.face_bodies(state,0,capsules,backend)
 check(batch.valid and batch.witnesses.size()==2 and backend.calls==2,"local reuse still queries every ordered body")
 for body in range(2):
  var scalar:Dictionary=query.face(state,0,capsules.slice(body*7,body*7+6),capsules[body*7+6],Backend.new())
  check(var_to_bytes(scalar)==var_to_bytes(batch.witnesses[body]),"every body retains exact scalar geometry and independent checks")
 batch.witnesses[0].controls[0]=9.;batch.witnesses[1].values[0]=9.
 check(batch.witnesses[1].controls[0]==0.,"one returned body cannot mutate another body geometry")
 check(var_to_bytes([state,capsules])==old,"batch results cannot mutate source state or body arrays")
 var owned:Dictionary=query.face_bodies(state,0,capsules,MutatingBackend.new())
 check(owned.valid and owned.witnesses[0].controls[0]==0. and owned.witnesses[1].weights[0]==1.,"backend request edits cannot poison later geometry or published witness ownership")
 var bad:=capsules.duplicate();bad[-1]=NAN
 check(not query.face_bodies(state,0,bad,Backend.new()).valid,"a malformed last body cannot publish partial success")
 backend=Backend.new();backend.fail_call=2
 check(not query.face_bodies(state,0,capsules,backend).valid and backend.calls==2,"later native corruption rejects the whole inspection")
 var changed:Dictionary=state.duplicate(true);changed.xyz[1]=.05;changed.xyz[4]=.05;changed.xyz[7]=.05
 check(not query.face_bodies(changed,0,capsules,Backend.new()).valid,"new positions cannot reuse an old accepted surface reconstruction")
 changed=state.duplicate(true);changed.support.weights[0]=NAN
 check(not query.face_bodies(changed,0,capsules,Backend.new()).valid,"new material topology is independently revalidated")
 check(not query.face_bodies(state,0,PackedFloat64Array([0.]),Backend.new()).valid,"partial body packet is rejected")
 print("Material face batch: ",failures," failures");quit(1 if failures else 0)
