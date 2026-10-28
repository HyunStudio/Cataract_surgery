extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class StaticKernel extends RefCounted:
	func solve_contact(request:Dictionary)->Dictionary:
		return {"status":0,"xyz":request.initial.duplicate(),"stats":PackedFloat64Array([0,0,0,0,0,0,0,0,0,0,0,0])}
class ResidualBody extends RefCounted:
	var residual:=.001
	var inner=load("res://scripts/membrane_contact.gd").new()
	func valid_body(body:Array)->bool: return inner.valid_body(body)
	func begin_substep(_mode:bool)->void: pass
	func project(points,_faces,_inverse,_body,_previous)->Dictionary:
		return {"valid":true,"positions":points.duplicate(),"contacts":1,"residual":residual,"uncertain":0}
func _initialize()->void:
	var source=load("res://scripts/capsule_solver.gd")
	if not source or not source.can_instantiate(): quit(1); return
	for residual in [.001,INF,NAN]:
		var model=source.new(); model.anchored.fill(1)
		model.set_contact_backend(StaticKernel.new())
		var body:=ResidualBody.new(); body.residual=residual; model._face_contact=body
		var saved:Dictionary=model._checkpoint()
		model.step(1./120.,Vector3(3,3,3),.018,false,false)
		check(model.native_failure.get("reason","")=="native_joint_body_residual","unchanged pinned geometry cannot hide swept contact residual "+str(residual))
		check(model._physical_xyz==saved._physical_xyz and model._physical_previous==saved._physical_previous and model.metrics().integration_steps==0,"residual rejection preserves physical state and time")
	var grip=source.new(); grip.set_contact_backend(StaticKernel.new())
	var saved:Dictionary=grip._checkpoint()
	grip.step(1./120.,grip.positions[0],.05,true,false)
	check(grip.native_failure.get("reason","")=="native_joint_requires_grasp_body","joint grip requires actual jaw geometry instead of an infeasible solid tip sphere")
	check(grip._physical_xyz==saved._physical_xyz and grip.metrics().grasped==-1 and grip.metrics().integration_steps==0,"unsupported tip-only acquisition is transactional")
	print("Joint contact guards: ",failures," failures")
	quit(1 if failures else 0)
