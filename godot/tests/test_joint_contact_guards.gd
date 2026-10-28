extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class StaticKernel extends RefCounted:
	var gap:=.001
	func solve_contact(request:Dictionary)->Dictionary:
		return {"status":0,"xyz":request.initial.duplicate(),"stats":PackedFloat64Array([0,0,0,0,0,0,0,0,0,0,0,0])}
	func guard_motion(_request:Dictionary)->Dictionary:
		return {"status":0,"stats":PackedFloat64Array([1,1,-1,-1,gap,0,0,0])}
class RefineKernel extends StaticKernel:
	var guards:=0
	var trajectory_requests:Array[Dictionary]=[]
	var always_collision:=false
	var fail_solve:=false
	var forced_witness:Variant=null
	func guard_motion(_request:Dictionary)->Dictionary:
		guards+=1
		if guards==1 or always_collision:
			return {"status":1,"witness_t":pow(.5,guards) if forced_witness==null else forced_witness}
		return {"status":0,"stats":PackedFloat64Array([3,1,-1,-1,INF,0,0,0])}
	func solve_trajectory(request:Dictionary)->Dictionary:
		trajectory_requests.append(request.duplicate(true))
		return {"status":1} if fail_solve else solve_contact(request)
func _initialize()->void:
	var source=load("res://scripts/capsule_solver.gd")
	if not source or not source.can_instantiate(): quit(1); return
	for residual in [-.001,-INF,NAN]:
		var model=source.new(); model.anchored.fill(1)
		var kernel:=StaticKernel.new(); kernel.gap=residual; model.set_contact_backend(kernel)
		var saved:Dictionary=model._checkpoint()
		model.step(1./120.,Vector3(3,3,3),.018,false,false)
		check(model.native_failure.get("reason","")=="native_joint_body_residual","unchanged pinned geometry cannot hide swept contact residual "+str(residual))
		check(model._physical_xyz==saved._physical_xyz and model._physical_previous==saved._physical_previous and model.metrics().integration_steps==0,"residual rejection preserves physical state and time")
	var grip=source.new(); grip.set_contact_backend(StaticKernel.new())
	var saved:Dictionary=grip._checkpoint()
	grip.step(1./120.,grip.positions[0],.05,true,false)
	check(grip.native_failure.get("reason","")=="native_joint_requires_grasp_body","joint grip requires actual jaw geometry instead of an infeasible solid tip sphere")
	check(grip._physical_xyz==saved._physical_xyz and grip.metrics().grasped==-1 and grip.metrics().integration_steps==0,"unsupported tip-only acquisition is transactional")
	var refined=source.new(); refined.anchored.fill(1)
	var kernel:=RefineKernel.new(); refined.set_contact_backend(kernel)
	var before:Dictionary=refined._checkpoint()
	refined.step(1./120.,Vector3(3,3,3),.018,false,false)
	check(refined.native_failure.is_empty() and refined.metrics().integration_steps==1 and kernel.guards==2 and kernel.trajectory_requests.size()==1,"sampled collision adds a physical time constraint and requires a fresh complete guard")
	if not kernel.trajectory_requests.is_empty():
		check(kernel.trajectory_requests[0].times==PackedFloat64Array([.5,1.]) and kernel.trajectory_requests[0].previous==before._physical_xyz and kernel.trajectory_requests[0].predicted==before._physical_xyz,"refinement preserves original history and predictor")
	for mode in ["budget","failed","invalid","repeated"]:
		var model=source.new(); model.anchored.fill(1)
		var injection:=RefineKernel.new(); injection.always_collision=mode in ["budget","repeated"]
		injection.fail_solve=mode=="failed"
		if mode=="invalid": injection.forced_witness=NAN
		if mode=="repeated": injection.forced_witness=.5
		model.set_contact_backend(injection); var checkpoint:Dictionary=model._checkpoint()
		model.step(1./120.,Vector3(3,3,3),.018,false,false)
		check(not model.native_failure.is_empty() and model._physical_xyz==checkpoint._physical_xyz and model._physical_previous==checkpoint._physical_previous and model.metrics().integration_steps==0,"trajectory "+mode+" rejects atomically")
		if mode=="budget": check(injection.guards==8 and injection.trajectory_requests.size()==7,"trajectory refinement has an explicit eight-solve bound")
	print("Joint contact guards: ",failures," failures")
	quit(1 if failures else 0)
