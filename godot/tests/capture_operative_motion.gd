extends "res://tests/test_operative_blade.gd"
## Transparent first guard-rejection and final failed-frame observations.
## A guard rejection may be resolved within the same subsequently accepted tick.
class TraceBackend extends RefCounted:
	var inner:RefCounted
	var request:Dictionary={}
	var response:Dictionary={}
	func solve_fem(value:Dictionary)->Dictionary:return inner.solve_fem(value)
	func solve_grasp_fem(value:Dictionary)->Dictionary:return inner.solve_grasp_fem(value)
	func material_witness_fem(value:Dictionary)->Dictionary:return inner.material_witness_fem(value)
	func contact_fem(value:Dictionary)->Dictionary:return inner.contact_fem(value)
	func solve_precise_contact_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_precise_contact_fem(value);response=result.duplicate(true);return result
	func solve_material_points_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_material_points_fem(value);response=result.duplicate(true);return result
	func solve_contact_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_contact_fem(value);response=result.duplicate(true);return result
	func solve_trajectory_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_trajectory_fem(value);response=result.duplicate(true);return result
	func solve_seeded_trajectory_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_seeded_trajectory_fem(value);response=result.duplicate(true);return result
	func solve_trajectory_material_points_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_trajectory_material_points_fem(value);response=result.duplicate(true);return result
	func solve_seeded_trajectory_material_points_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var result:Dictionary=inner.solve_seeded_trajectory_material_points_fem(value);response=result.duplicate(true);return result
class TraceGuard extends RefCounted:
	var inner:RefCounted
	var backend:TraceBackend
	var captured:=false
	func guard_fine_motion(value:Dictionary)->Dictionary:return _guard(value,true)
	func guard_motion(value:Dictionary)->Dictionary:return _guard(value,false)
	func _guard(value:Dictionary,fine:bool)->Dictionary:
		var result:Dictionary=inner.guard_fine_motion(value) if fine else inner.guard_motion(value)
		if result.get("status",-1)!=0 and not captured:
			captured=true;DirAccess.make_dir_recursive_absolute("res://reports")
			var data:={"scope":"First complete-motion guard rejection only; may resolve within an accepted tick.","guard_request":value,"guard_response":result,"fem_request":backend.request,"fem_response":backend.response}
			var file:=FileAccess.open("res://reports/operative-motion-request.bin",FileAccess.WRITE)
			if file:file.store_var(data)
			file=FileAccess.open("res://reports/operative-motion-request.json",FileAccess.WRITE)
			if file:file.store_string(JSON.stringify(data,"  ",true,true))
		return result
class TraceState:
	extends "res://scripts/embedded_membrane.gd"
	func advance_contact(dt:float,force:PackedFloat64Array,backend,mu:float,lambda:float,motion:Dictionary,damping:float=1.,budget:int=100,targets:Dictionary={})->Dictionary:
		var before:=snapshot();var result:=super.advance_contact(dt,force,backend,mu,lambda,motion,damping,budget,targets)
		if not result.valid:
			var path:=motion.duplicate(true);path.erase("guard")
			DirAccess.make_dir_recursive_absolute("res://reports")
			var file:=FileAccess.open("res://reports/operative-motion-state.bin",FileAccess.WRITE)
			if file:file.store_var({"state":before,"dt":dt,"force":force,"mu":mu,"lambda":lambda,"motion":path,"damping":damping,"budget":budget,"targets":targets,"result":result})
		return result
func configure_capsule(app)->bool:
	if not super.configure_capsule(app):return false
	var backend:=TraceBackend.new();backend.inner=app.capsule.embedded_backend
	var guard:=TraceGuard.new();guard.inner=app.capsule.embedded_guard;guard.backend=backend
	app.capsule.embedded_backend=backend;app.capsule.embedded_guard=guard;app.capsule._embedded_solver=TraceState.new()
	return true
