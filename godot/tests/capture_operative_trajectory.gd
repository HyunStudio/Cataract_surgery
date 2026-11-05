extends "res://tests/test_operative_blade.gd"
class BackendProxy extends RefCounted:
	var inner:RefCounted
	var history:Array=[]
	func solve_fem(value:Dictionary)->Dictionary:return inner.solve_fem(value)
	func solve_grasp_fem(value:Dictionary)->Dictionary:return inner.solve_grasp_fem(value)
	func material_witness_fem(value:Dictionary)->Dictionary:return inner.material_witness_fem(value)
	func contact_fem(value:Dictionary)->Dictionary:return inner.contact_fem(value)
	func solve_contact_fem(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.solve_contact_fem(value);history.append({"kind":"static","request":value.duplicate(true),"response":result.duplicate(true)});return result
	func solve_precise_contact_fem(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.solve_precise_contact_fem(value);history.append({"kind":"precise_endpoint","request":value.duplicate(true),"response":result.duplicate(true)});return result
	func solve_material_points_fem(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.solve_material_points_fem(value);history.append({"kind":"material_points","request":value.duplicate(true),"response":result.duplicate(true)});return result
	func solve_trajectory_fem(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.solve_trajectory_fem(value);history.append({"kind":"trajectory","request":value.duplicate(true),"response":result.duplicate(true)});return result
	func solve_seeded_trajectory_fem(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.solve_seeded_trajectory_fem(value);history.append({"kind":"seeded","request":value.duplicate(true),"response":result.duplicate(true)});return result
class GuardProxy extends RefCounted:
	var inner:RefCounted
	var history:Array=[]
	func guard_motion(value:Dictionary)->Dictionary:
		var result:Dictionary=inner.guard_motion(value);history.append({"request":value.duplicate(true),"response":result.duplicate(true)});return result
class TraceState:
	extends "res://tests/test_operative_blade.gd".CaptureState
	func advance_contact(dt:float,force:PackedFloat64Array,backend,mu:float,lambda:float,motion:Dictionary,damping:float=1.,budget:int=100,targets:Dictionary={})->Dictionary:
		backend.history=[];motion.guard.history=[]
		var before:=snapshot();var answer:=super.advance_contact(dt,force,backend,mu,lambda,motion,damping,budget,targets)
		if not answer.valid:
			var path:=motion.duplicate(true);path.erase("guard")
			var data:={"state":before,"dt":dt,"force":force,"mu":mu,"lambda":lambda,"motion":path,"damping":damping,"budget":budget,"targets":targets,"result":answer,"native_history":backend.history,"guard_history":motion.guard.history}
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/next-operative-motion.bin",FileAccess.WRITE);file.store_var(data)
			file=FileAccess.open("res://reports/next-operative-motion.json",FileAccess.WRITE);file.store_string(JSON.stringify(data,"  ",true,true))
			print("Captured next original state: steps=",before.steps," events=",before.events," native_requests=",backend.history.size()," reason=",answer.reason)
		return answer
func configure_capsule(app)->bool:
	if not super.configure_capsule(app):return false
	var backend:=BackendProxy.new();backend.inner=app.capsule.embedded_backend
	var guard:=GuardProxy.new();guard.inner=app.capsule.embedded_guard
	app.capsule.embedded_backend=backend;app.capsule.embedded_guard=guard;app.capsule._embedded_solver=TraceState.new()
	return true
