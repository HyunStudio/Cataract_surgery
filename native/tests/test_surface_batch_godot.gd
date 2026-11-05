extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var kernel=ClassDB.instantiate("MembraneFEMKernel")
 check(kernel!=null and kernel.has_method("material_witnesses_fem"),"actual kernel must provide complete bulk witness API")
 if failures:quit(1);return
 var query=load("res://scripts/material_surface_query.gd").new()
 var q:=PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.])
 var state:={"steps":7,"events":11,"xyz":q,"indices":PackedInt32Array([0,1,2,3,4,5]),"support":{"elements":PackedInt32Array([0,1,2,0,1,2]),"weights":PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.,.5,.5,0.,0.,.5,.5,.5,0.,.5])}}
 var capsules:=PackedFloat64Array([.25,.1,.25,.25,.1,.25,.01,.1,.1,.1,.6,.1,.1,.01,.25,.1,.25,.25,-.1,.25,.01])
 var before:=var_to_bytes([state,capsules]);var result:Dictionary=query.batch(state,capsules,kernel)
 check(result.valid,"actual complete batch passes independent original-material checks")
 if result.valid:
  for face in range(2):
   for body in range(3):
    var scalar:Dictionary=query.face(state,face,capsules.slice(body*7,body*7+6),capsules[body*7+6],kernel)
    var pair:int=face*3+body
    check(scalar.valid and scalar.distance_status==result.statuses[pair] and scalar.values.to_byte_array()==result.values.slice(pair*13,pair*13+13).to_byte_array(),"actual scalar and bulk retain every status/value bit, including intersecting finite axes")
  result.values[0]=9.;result.statuses[0]=-1
 check(var_to_bytes([state,capsules])==before,"actual batch owns material/body inputs and outputs")
 var bad:Dictionary=state.duplicate(true);bad.support.weights[-1]=NAN
 check(not query.batch(bad,capsules,kernel).valid,"actual late invalid material cannot yield a partial proposal")
 print("Native surface batch state: ",failures," failures");quit(1 if failures else 0)
