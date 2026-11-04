extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	var backend=ClassDB.instantiate("MembraneFEMKernel");var guard=ClassDB.instantiate("MembraneContactKernel")
	check(backend!=null and guard!=null,"actual native trajectory and full interval guard register")
	if failures:quit(1);return
	var metrics:Array=[]
	for number in [144,146,150]:metrics.append(run_case(number,backend,guard))
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/trajectory-advance-metrics.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"qualified":failures==0,"scope":"Exact captured144/146/150 core states only; not outer operative anatomy, full route, real-time or release qualification.","cases":metrics},"  ",true,true))
	print("Embedded trajectory advance: ",failures," failures");quit(1 if failures else 0)
func run_case(number:int,backend,guard)->Dictionary:
	var saved:Dictionary=FileAccess.open("res://tests/fixtures/operative-motion%s-state.bin"%number,FileAccess.READ).get_var()
	var model=load("res://scripts/embedded_membrane.gd").new();model._state=saved.state.duplicate(true)
	var before:Dictionary=model.snapshot();var motion:Dictionary=saved.motion.duplicate(true);motion.guard=guard
	check(model.physical_positions()==motion.previous,"captured original controls reproduce accepted fine positions exactly")
	var started:=Time.get_ticks_msec()
	var result:Dictionary=model.advance_contact(saved.dt,saved.force,backend,saved.mu,saved.lambda,motion,saved.damping,saved.budget,saved.targets)
	var elapsed:=Time.get_ticks_msec()-started
	check(result.valid,"actual captured%s core step passes native solve, independent engine force and full recorded motion: "%number+result.reason)
	if not result.valid:print(result);return {"qualified":false,"reason":result.reason}
	var after:Dictionary=model.snapshot()
	check(after.steps==before.steps+1 and after.previous==before.xyz and after.time==before.time+saved.dt,"only one accepted physical step and its actual history are published")
	check(result.trajectory_iterations<=saved.budget and after.contacts.times[-1]==1.,"actual witness/numerical retries share the original Newton budget and retain endpoint")
	if number==150:check(result.trajectory_retired_layers>0,"exact150 exchanges inactive layers instead of exceeding the dense pair budget")
	check(result.force_inf<=1e-8,"independent GDScript original material force remains strict")
	print("Captured trajectory ",number,": steps=",after.steps," force=",result.force_inf," elapsed_ms=",elapsed)
	return {"accepted_steps":after.steps,"times":after.contacts.times,"force_inf":result.force_inf,"iterations":result.trajectory_iterations,"retired_layers":result.trajectory_retired_layers,"elapsed_ms":elapsed}
