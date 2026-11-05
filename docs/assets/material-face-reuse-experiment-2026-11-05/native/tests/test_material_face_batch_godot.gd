extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 check(ClassDB.class_exists("MembraneFEMKernel"),"actual native material face test requires its kernel")
 if failures:quit(1);return
 var backend=ClassDB.instantiate("MembraneFEMKernel");var guard=ClassDB.instantiate("MembraneContactKernel")
 var query=load("res://scripts/material_surface_query.gd").new()
 var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion179-state.bin",FileAccess.READ).get_var()
 var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
 var context:Dictionary=load("res://scripts/embedded_contact_step.gd").prepare(saved.state,motion)
 check(context.valid,"owned body context prepares")
 var old:=var_to_bytes(saved.state)
 for face in [0,100,2210,saved.state.indices.size()/3-1]:
  var batch:Dictionary=query.face_bodies(saved.state,face,context.capsules,backend)
  check(batch.valid and batch.witnesses.size()==context.bodies,"every actual finite body gets a witness")
  if not batch.valid:continue
  for body in range(context.bodies):
   var off:=body*7
   var scalar:Dictionary=query.face(saved.state,face,context.capsules.slice(off,off+6),context.capsules[off+6],backend)
   check(var_to_bytes(scalar)==var_to_bytes(batch.witnesses[body]),"actual scalar/batch witness parity includes status, geometry and material ownership")
 check(var_to_bytes(saved.state)==old,"actual native batches leave owned physics state unchanged")
 print("Native material face batch: ",failures," failures");quit(1 if failures else 0)
