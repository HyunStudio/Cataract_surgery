extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 var kernel=ClassDB.instantiate("MembraneFEMKernel")
 check(kernel!=null and kernel.has_method("material_witnesses_fem"),"actual kernel needs bounded all-pair witness API")
 if failures:print("Native material witness batch: ",failures," failures");quit(1);return
 var q:=PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]);var b:=PackedFloat64Array([1.,0.,0.,0.,1.,0.,0.,0.,1.])
 var controls:=q.duplicate();controls.append_array(q);var weights:=b.duplicate();weights.append_array(b)
 var capsules:=PackedFloat64Array([.25,0.,.25,.25,0.,.25,.01,.1,.1,.1,.6,.1,.1,.01,.25,.1,.25,.25,-.1,.25,.01])
 var request:={"controls":controls,"weights":weights,"capsules":capsules}
 var before:=var_to_bytes(request);var result:Dictionary=kernel.material_witnesses_fem(request)
 check(result.status==0 and result.statuses is PackedInt32Array and result.statuses.size()==6 and result.values is PackedFloat64Array and result.values.size()==78,"typed bulk bridge publishes every ordered pair")
 if result.status==0:
  for face in range(2):
   for body in range(3):
    var scalar:Dictionary=kernel.material_witness_fem({"controls":q,"weights":b,"segment":capsules.slice(body*7,body*7+6),"radius":capsules[body*7+6]})
    var pair:=face*3+body
    check(result.statuses[pair]==scalar.status and result.values.slice(pair*13,pair*13+13).to_byte_array()==scalar.values.to_byte_array(),"typed scalar status and every value bit remain unchanged")
  result.values[0]=9.;result.statuses[0]=-1
 check(var_to_bytes(request)==before,"typed batch owns its returned arrays and cannot mutate requests")
 for bad in [{"controls":[]},{"weights":PackedFloat64Array([NAN])},{"capsules":PackedFloat64Array([0.])}]:
  var changed:Dictionary=request.duplicate(true);changed.merge(bad,true)
  var rejected:Dictionary=kernel.material_witnesses_fem(changed)
  check(rejected.status==-1 and rejected.values.is_empty() and rejected.statuses.is_empty(),"malformed bulk input publishes no partial pair")
 var bad:Dictionary=request.duplicate(true);bad.weights[-1]=NAN
 check(kernel.material_witnesses_fem(bad).status==-1,"invalid final material input cannot hide behind earlier valid faces")
 bad=request.duplicate(true);bad.weights=PackedFloat64Array([1.,0.,0.,1.,0.,0.,1.,0.,0.]);bad.controls=q
 var inconclusive:Dictionary=kernel.material_witnesses_fem(bad)
 check(inconclusive.status==2 and inconclusive.values.is_empty() and inconclusive.statuses.is_empty(),"degenerate source preserves scalar failure without partial publication")
 print("Native material witness batch: ",failures," failures");quit(1 if failures else 0)
