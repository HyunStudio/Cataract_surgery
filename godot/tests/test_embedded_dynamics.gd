extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var request:Dictionary
	var mode:="predictor"
	func solve_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true)
		var xyz:PackedFloat64Array=value.xyz.duplicate();var stats:=PackedFloat64Array();stats.resize(8)
		if mode=="failure":return {"status":1,"xyz":xyz,"stats":stats}
		if mode=="malformed":return {"status":0,"xyz":[],"stats":stats}
		if mode=="false_success":xyz[4]+=.1
		if mode=="false_stats":stats[1]=1.
		return {"status":0,"xyz":xyz,"stats":stats}
func _initialize()->void:
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.has_method("advance"),"embedded state advances actual control histories through a bounded implicit backend")
	if failures:quit(1);return
	var points:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]);var ids:=PackedInt32Array([0,2,1])
	model.initialize(points,ids,PackedByteArray([0,0,0]),1.)
	var state:Dictionary=model.snapshot();var previous:PackedFloat64Array=state.xyz.duplicate()
	for node in range(3):
		for axis in range(3):previous[node*3+axis]-=.001*(axis+1)
	model.set_motion(state.xyz,previous)
	var before:Dictionary=model.snapshot();var force:=PackedFloat64Array();force.resize(9)
	var backend:=Backend.new();var dt:=1./60.
	var accepted:Dictionary=model.advance(dt,force,backend,2.,3.)
	check(accepted.valid,"rigid predictor with zero internal force accepts its implicit step")
	var after:Dictionary=model.snapshot()
	check(after.previous==before.xyz and after.steps==1 and absf(after.time-dt)<1e-15,"accepted native candidate advances history and time exactly once")
	for i in range(9):check(absf(after.xyz[i]-(2.*before.xyz[i]-before.previous[i]))<1e-15,"backward Euler predictor retains existing control velocity")
	check(backend.request.force_tolerance==1e-8 and backend.request.budget==100 and backend.request.dt==dt,"state adapter retains the strict force/work/time contract")
	for mode in ["failure","malformed","false_success","false_stats"]:
		backend.mode=mode;var saved:Dictionary=model.snapshot()
		var rejected:Dictionary=model.advance(dt,force,backend,2.,3.)
		check(not rejected.valid and model.snapshot()==saved,"rejected or falsely converged backend cannot publish histories, time or material state: "+mode)
	backend.mode="predictor"
	var saved:Dictionary=model.snapshot()
	var bad_force:=force.duplicate();bad_force[0]=NAN
	for bad_dt in [0.,.2,NAN]:check(not model.advance(bad_dt,force,backend,2.,3.).valid,"invalid step interval rejects before mutation")
	check(not model.advance(dt,bad_force,backend,2.,3.).valid and not model.advance(dt,force,null,2.,3.).valid,"invalid force or unavailable native backend rejects")
	check(model.snapshot()==saved,"all invalid step inputs preserve accepted state")
	var acceleration:=PackedFloat64Array([.1,-.2,.3]);var load:=force.duplicate()
	for node in range(3):
		for axis in range(3):load[node*3+axis]=after.support.mass[node]*acceleration[axis]
	check(model.advance(dt,load,backend,2.,3.).valid,"mass-proportional external load admits a rigid accelerated predictor")
	for node in range(3):
		for axis in range(3):check(absf(backend.request.xyz[node*3+axis]-(2.*saved.xyz[node*3+axis]-saved.previous[node*3+axis]+dt*dt*acceleration[axis]))<1e-15,"actual operator forces enter prediction using their original support masses")
	print("Embedded dynamics contract: ",failures," failures");quit(1 if failures else 0)
