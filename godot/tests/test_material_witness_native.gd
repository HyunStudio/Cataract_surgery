extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 check(ClassDB.class_exists("MembraneFEMKernel"),"material state query needs actual native kernel")
 if failures:quit(1);return
 var kernel=ClassDB.instantiate("MembraneFEMKernel");var model=load("res://scripts/embedded_membrane.gd").new()
 model.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
 var cut:Dictionary=model._incise_one(PackedVector3Array([Vector3(.25,-.2,-1),Vector3(.25,.2,-1),Vector3(.25,0,2)]))
 check(cut.valid and cut.changed,"actual retained cut provides nonidentity material faces")
 if not cut.valid:quit(1);return
 var before:Dictionary=model.snapshot();var physical:PackedFloat64Array=model.physical_positions();var point:=PackedFloat64Array([0.,0.,0.])
 for corner in range(3):
  var vertex:int=before.indices[corner]
  for axis in range(3):point[axis]+=physical[vertex*3+axis]/3.
 var probe:=PackedFloat64Array();probe.append_array(point);probe.append_array(point)
 var witness:Dictionary=model.material_witness(0,probe,.01,kernel)
 check(witness.valid and witness.distance_status==1 and witness.values.size()==13,"actual exact contact on refined material can be inspected without a smooth branch")
 check(not model.contact_face(0,probe,.01,kernel).valid,"legacy derivative query keeps its original no-intersection force contract")
 check(model.snapshot()==before,"actual native witness and validation do not advance physics or change topology")
 if witness.valid:
  check(model.grasp_material(0,0,witness.barycentric).valid,"validated face coordinates can describe a material point without a nearest display vertex shortcut")
  var target:PackedFloat64Array=model.snapshot().grasps[0].target
  for axis in range(3):check(absf(target[axis]-witness.point[axis])<1e-11,"registered material point reconstructs the actual geometry witness")
 var identity=load("res://scripts/embedded_membrane.gd").new();identity.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
 witness=identity.material_witness(0,PackedFloat64Array([.1,.1,.1,.6,.1,.1]),.01,kernel)
 check(witness.valid and witness.distance_status==3 and witness.ambiguous,"actual nonunique closest geometry remains explicitly ambiguous")
 witness=identity.material_witness(0,PackedFloat64Array([-.1,0.,.2,.7,0.,.2]),.01,kernel)
 check(witness.valid and witness.distance_status==1 and witness.ambiguous,"actual coplanar intersection interval cannot masquerade as a unique grasp")
 print("Native material witness state: ",failures," failures");quit(1 if failures else 0)
