extends SceneTree
const Anatomy=preload("res://scripts/anatomical_contact.gd")
const Operative=preload("res://scripts/operative_membrane.gd")
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
class Guard extends RefCounted:
 var calls:=0
 var hit:=false
 func guard_motion(value:Dictionary)->Dictionary:
  calls+=1
  if hit:return {"status":1,"stats":PackedFloat64Array([1,1,0,0,-.001,0,0,4]),"witness_t":.5}
  return {"status":0,"stats":PackedFloat64Array([0,value.triangles.size()/3,-1,-1,1,0,0,0])}
func _initialize()->void:
 var mesh:={"positions":PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)]),"triangles":PackedInt32Array([0,1,2])}
 var xyz:=PackedFloat64Array();xyz.resize(4103*3)
 for i in range(4103):xyz[3*i+1]=.1
 var query=Anatomy.new();check(query.configure(mesh),"small obstacle configures")
 check(not query.requests(xyz,xyz,PackedInt32Array([4102]),16384).valid,"unsupported moving geometry limit is rejected")
 check(not query.requests(xyz,xyz,PackedInt32Array([4102])).valid,"legacy moving geometry capacity remains4096")
 var model=load("res://scripts/capsule_solver.gd").new()
 model.anchored=PackedByteArray();model.anchored.resize(4103);model.anchored.fill(1);model.anchored[4102]=0
 model._removed=PackedByteArray();model._removed.resize(4103)
 model._outside=PackedByteArray();model._outside.resize(4103)
 model._embedded_state={"fine_point_limit":8192};model.embedded_surfaces={"obstacle":mesh}
 var guard:=Guard.new();model.embedded_guard=guard
 var answer:Dictionary=Operative.boundaries(model,xyz,xyz)
 check(answer.valid and guard.calls==1,"operative fine boundary inspects high-index point without truncation")
 guard.hit=true
 answer=Operative.boundaries(model,xyz,xyz)
 check(not answer.valid and answer.get("vertex",-1)==4102,"fine boundary still rejects and maps high-index contact")
 model._embedded_state.fine_point_limit=4096;guard.calls=0
 check(not Operative.boundaries(model,xyz,xyz).valid and guard.calls==0,"legacy state cannot silently opt into large anatomy input")
 model._embedded_state.fine_point_limit=8192;xyz[-1]=NAN;guard.calls=0
 check(not Operative.boundaries(model,xyz,xyz).valid and guard.calls==0,"all high-index coordinates are validated")
 xyz[-1]=0.
 if "--require-native" in OS.get_cmdline_user_args():check(ClassDB.class_exists("MembraneContactKernel"),"actual native anatomy regression must load its kernel")
 if ClassDB.class_exists("MembraneContactKernel"):
  var native_guard=ClassDB.instantiate("MembraneContactKernel")
  xyz[-2]=.1
  var clear:Dictionary=query.inspect(native_guard,xyz,xyz,PackedInt32Array([4102]),8192)
  check(clear.status==0,"actual legacy obstacle guard handles high-index moving point via bounded packets")
  xyz[-2]=0.
  var hit:Dictionary=query.inspect(native_guard,xyz,xyz,PackedInt32Array([4102]),8192)
  check(hit.status==1 and hit.vertex==4102,"actual native obstacle contact maps the high-index witness")
 print("Fine anatomy boundary: ",failures," failures");quit(1 if failures else 0)
