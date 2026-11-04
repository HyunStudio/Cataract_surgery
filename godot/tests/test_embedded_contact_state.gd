extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var last:Dictionary={}
	var result:Dictionary={"status":0,"values":PackedFloat64Array([.09,.2,.2,.3,.4,.2,0.,.4,.4,.2,.4,0.,-.24,0.,0.,-.12,0.,0.,-.24,0.,0.,0.]),"gradient":PackedFloat64Array([0.,-.24,0.,0.,-.12,0.,0.,-.24,0.]),"hessian":PackedFloat64Array()}
	func _init()->void:result.hessian.resize(81)
	func contact_fem(request:Dictionary)->Dictionary:
		last=request.duplicate(true);return result.duplicate(true)
func _initialize()->void:
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.has_method("contact_geometry") and model.has_method("contact_face"),"embedded state exports retained contact geometry and validates native query")
	if failures:quit(1);return
	var base:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK])
	model.initialize(base,PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	var saved:Dictionary=model.snapshot();var view:Dictionary=model.contact_geometry()
	check(view.valid and view.nodes.size()==3 and view.weights.size()==9 and view.triangles==saved.indices,"contact export contains actual fine topology and per-face material map")
	view.xyz[0]=7.;view.weights[0]=9.;view.triangles[0]=99
	check(model.snapshot()==saved,"exported collision arrays cannot mutate accepted tissue")
	var backend:=Backend.new();var segment:=PackedFloat64Array([.2,.3,.4,.2,.3,.4])
	var answer:Dictionary=model.contact_face(0,segment,.1,backend)
	check(answer.valid and answer.nodes==PackedInt32Array([0,1,2]) and answer.material_weights==PackedFloat64Array([.4,.2,.4]),"fine witness retains its continuous material point instead of selecting nearest vertex")
	check(backend.last.controls==saved.xyz and model.snapshot()==saved,"query reads accepted doubles and never advances the physical clock")
	var valid:=backend.result.duplicate(true)
	for failure in ["gap","surface","weights","gradient","hessian","status"]:
		backend.result=valid.duplicate(true)
		match failure:
			"gap":backend.result.values[1]+=.01
			"surface":backend.result.values[5]+=.01
			"weights":backend.result.values[8]=-1.
			"gradient":backend.result.gradient[0]=1.
			"hessian":backend.result.hessian=PackedFloat64Array([0.])
			"status":backend.result.status=3
		check(not model.contact_face(0,segment,.1,backend).valid and model.snapshot()==saved,"invalid native "+failure+" cannot publish a material contact")
	backend.result=valid
	for call in [[-1,segment,.1,backend],[1,segment,.1,backend],[0,PackedFloat64Array([0.]),.1,backend],[0,segment,NAN,backend],[0,segment,.1,null]]:
		check(not model.contact_face(call[0],call[1],call[2],call[3]).valid and model.snapshot()==saved,"malformed contact command preserves accepted state")
	print("Embedded contact state contract: ",failures," failures");quit(1 if failures else 0)
