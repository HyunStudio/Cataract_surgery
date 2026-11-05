extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var response:Dictionary={"status":1,"values":PackedFloat64Array([0.,-.01,.25,0.,.25,.25,0.,.25,.5,.25,.25,0.,0.])}
	func material_witness_fem(_request:Dictionary)->Dictionary:return response.duplicate(true)
func _initialize()->void:
	var tissue=load("res://scripts/embedded_membrane.gd").new()
	tissue.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	check(tissue.has_method("material_witness"),"material selection needs independent static geometry validation including exact contact")
	if failures:quit(1);return
	var backend:=Backend.new();var before:Dictionary=tissue.snapshot();var segment:=PackedFloat64Array([.25,0.,.25,.25,0.,.25])
	var result:Dictionary=tissue.material_witness(0,segment,.01,backend)
	check(result.valid and result.distance_status==1 and not result.ambiguous and result.point==PackedFloat64Array([.25,0.,.25]),"exact surface point and its intersection status remain inspectable")
	check(result.barycentric==PackedFloat64Array([.5,.25,.25]) and result.events==before.events and result.steps==before.steps,"witness describes the current accepted face and material coordinates")
	backend.response.values[11]=.5;backend.response.values[12]=5.
	var crossing:Dictionary=tissue.material_witness(0,PackedFloat64Array([.25,.1,.25,.25,-.1,.25]),.01,backend)
	check(crossing.valid and crossing.ambiguous,"finite-axis intersection is not automatically a unique acquisition point")
	result.controls[0]=9.;result.weights[0]=9.;result.values[0]=9.
	check(tissue.snapshot()==before,"returned geometry cannot alias or modify accepted physical state")
	var regular:=PackedFloat64Array([.01,.09,.25,.1,.25,.25,0.,.25,.5,.25,.25,0.,0.]);backend.response={"status":0,"values":regular}
	segment=PackedFloat64Array([.25,.1,.25,.25,.1,.25]);result=tissue.material_witness(0,segment,.01,backend)
	check(result.valid and result.distance_status==0 and not result.ambiguous,"regular closest point independently reconstructs")
	backend.response.status=3;segment=PackedFloat64Array([.25,.1,.25,.5,.1,.25]);result=tissue.material_witness(0,segment,.01,backend)
	check(result.valid and result.ambiguous and result.distance_status==3,"a nonunique closest pair remains explicit geometry, never an implicit unique grasp")
	for bad in [{},{"status":2,"values":PackedFloat64Array()},{"status":1,"values":regular},{"status":0,"values":[]},{"status":0,"values":PackedFloat64Array([NAN])}]:
		backend.response=bad;check(not tissue.material_witness(0,segment,.01,backend).valid,"malformed/uncertified geometry cannot publish a witness")
	backend.response={"status":0,"values":PackedFloat64Array([.135,sqrt(.135)-.01,.25,.1,.25,0.,0.,0.,1.,0.,0.,0.,0.])}
	check(not tissue.material_witness(0,segment,.01,backend).valid,"independent closest-point KKT rejects a consistent but nonminimal returned surface point")
	check(not tissue.material_witness(0,segment,.01,RefCounted.new()).valid,"old backends cannot silently substitute a derivative query")
	check(not tissue.material_witness(-1,segment,.01,backend).valid and not tissue.material_witness(0,PackedFloat64Array(),.01,backend).valid,"invalid face/input rejects before native invocation")
	check(tissue.snapshot()==before,"all geometry queries leave topology, targets, physics histories and time unchanged")
	var collapsed:PackedFloat64Array=before.xyz.duplicate();collapsed[6]=.5;collapsed[8]=0.;tissue.set_motion(collapsed,collapsed)
	backend.response={"status":1,"values":PackedFloat64Array([0.,-.01,.25,0.,0.,.25,0.,0.,.75,.25,0.,0.,0.])}
	check(not tissue.material_witness(0,PackedFloat64Array([.25,0.,0.,.25,0.,0.]),.01,backend).valid,"an independent degenerate source check rejects a fabricated intersection")
	print("Material witness state: ",failures," failures");quit(1 if failures else 0)
