extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	func solve_fem(_request:Dictionary)->Dictionary:return {"status":1}
	func solve_contact_fem(_request:Dictionary)->Dictionary:return {"status":1}
	func contact_fem(_request:Dictionary)->Dictionary:return {"status":1}
class Guard extends RefCounted:
	func guard_motion(_request:Dictionary)->Dictionary:return {"status":1}
class AcceptedStep:
	extends "res://scripts/embedded_membrane.gd"
	var active:=true
	func advance_contact(_dt:float,_force:PackedFloat64Array,_backend,_mu:float,_lambda:float,_motion:Dictionary,_damping:float=1.,_budget:int=100,_targets:Dictionary={})->Dictionary:
		_state.contacts={"dual":PackedFloat64Array([.01]) if active else PackedFloat64Array()}
		active=false
		var stats:=PackedFloat64Array();stats.resize(16);stats[12]=5e-10
		return {"valid":true,"elastic_energy":0.,"force_inf":0.,"maximum_strain":0.,"stats":stats}
func _initialize()->void:
	var model=load("res://scripts/capsule_solver.gd").new()
	check(model.has_method("set_embedded_backend"),"operative capsule exposes the retained-material backend")
	if failures:quit(1);return
	model.geometry=load("res://scripts/anterior_segment.gd").new();model.reset()
	var backend:=Backend.new();var guard:=Guard.new()
	check(model.set_embedded_backend(backend,guard),"pristine actual capsule configures the original-material backend")
	check(model.metrics().get("mechanics","")=="original_material_fem","operative telemetry identifies its actual mechanical authority")
	if failures:quit(1);return
	var start:Dictionary=model.capture_state();var initial:float=model.metrics().retained_area
	var r:=.4;var y:float=model.geometry.bag_front(r);var prior:=Vector3(r,y,0)
	for i in range(1,65):
		var next:=Vector3(r*cos(TAU*i/64.),y,r*sin(TAU*i/64.));var down:=Vector3.UP*.05
		var cut:Dictionary=model.incise_patches([PackedVector3Array([prior-down,next-down,next+down]),PackedVector3Array([prior-down,next+down,prior+down])])
		check(cut.valid,"operative mirror accepts retained incision: "+cut.reason)
		if not cut.valid:break
		prior=next
	check(absf(model.metrics().retained_area-initial)<1e-10 and model.detached_components().size()==1,"operative topology preserves mass and a genuine retained free flap")
	var saved:Dictionary=model.capture_state();var empty:Array[Dictionary]=[];model.step_tools(1./60.,empty)
	check(not model.native_failure.is_empty() and model.capture_state()._embedded_state==saved._embedded_state,"native failure cannot advance embedded positions histories topology or clock")
	model.restore_state(start);model.invalidate_solver_cache()
	check(model.capture_state()==start and model.positions.size()==217,"whole-model restoration owns embedded value state and render topology")
	check(not model.set_contact_backend(guard),"legacy and original-material authorities cannot be combined")
	var operator=load("res://scripts/operative_membrane.gd")
	for part in [{},{"a":Vector3.ZERO,"b":Vector3.RIGHT,"previous_a":Vector3.ZERO,"previous_b":Vector3.RIGHT,"radius":.01}]:
		var bad_tools:Array[Dictionary]=[{"hand":0,"tip":Vector3.ZERO,"radius":.01,"grip":false,"cut":false,"body":[part]}]
		var bad:Variant=operator.step(model,1./60.,bad_tools)
		check(bad is Dictionary and not bad.valid and bad.reason=="body_input","operative bodies reject incomplete or unrecorded poses without script errors")
	model._embedded_solver=AcceptedStep.new()
	var accepted:Dictionary=operator.step(model,1./60.,empty)
	check(accepted.valid and model.metrics().body_contacts==1 and model.metrics().body_projection_peak_residual==5e-10,"accepted original-material contacts publish physical contact count and accepted gap residual")
	accepted=operator.step(model,1./60.,empty)
	check(accepted.valid and model.metrics().body_contacts==0 and model.metrics().body_uncertain==0,"subsequent certified contact-free step clears prior contact telemetry")
	print("Operative embedded contract: ",failures," failures");quit(1 if failures else 0)
