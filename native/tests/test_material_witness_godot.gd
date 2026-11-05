extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
 if not ok:failures+=1;push_error(message)
func _initialize()->void:
 check(ClassDB.class_exists("MembraneFEMKernel"),"read-only material witness needs the real native kernel")
 if failures:quit(1);return
 var kernel=ClassDB.instantiate("MembraneFEMKernel")
 check(kernel.has_method("material_witness_fem"),"real extension exposes a separate contact-position witness without requiring smooth derivatives")
 if failures:quit(1);return
 var request:={"controls":PackedFloat64Array([0.,0.,0.,1.,0.,0.,0.,0.,1.]),"weights":PackedFloat64Array([.8,.1,.1,.3,.6,.1,.3,.1,.6]),"segment":PackedFloat64Array([.25,0.,.25,.25,0.,.25]),"radius":.01}
 var saved:=request.duplicate(true);var result:Dictionary=kernel.material_witness_fem(request)
 check(result.status==1 and result.values.size()==13 and result.values[0]==0.,"actual point on a fine face returns intersection geometry")
 check(not result.has("gradient") and not result.has("hessian"),"geometry selection cannot be mistaken for a force/Hessian result")
 if result.values.size()==13:
  check(absf(result.values[8]-.4)<1e-12 and absf(result.values[9]-.3)<1e-12 and absf(result.values[10]-.3)<1e-12,"fine material barycentrics reconstruct the actual contact point")
 check(request==saved,"typed witness leaves caller geometry untouched")
 var crossing:=request.duplicate(true);crossing.segment=PackedFloat64Array([.25,.1,.25,.25,-.1,.25]);result=kernel.material_witness_fem(crossing)
 check(result.status==1 and result.values.size()==13,"finite crossing remains explicit geometry status1")
 var degenerate:=request.duplicate(true);degenerate.weights=PackedFloat64Array([1.,0.,0.,1.,0.,0.,1.,0.,0.]);result=kernel.material_witness_fem(degenerate)
 check(result.status==2 and result.values.is_empty(),"degenerate geometry cannot publish a selection witness")
 for bad in [{},request.merged({"weights":[]},true),request.merged({"weights":PackedFloat64Array([1.])},true),request.merged({"segment":PackedFloat64Array([0.,0.,0.])},true),request.merged({"radius":".01"},true),request.merged({"radius":NAN},true)]:
  result=kernel.material_witness_fem(bad);check(result.status==-1 and result.values.is_empty(),"malformed typed geometry is rejected without publication")
 print("Native material witness bridge: ",failures," failures");quit(1 if failures else 0)
