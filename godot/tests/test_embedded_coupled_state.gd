extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var mode:="clear"
	var request:Dictionary
	func solve_contact_fem(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var xyz:PackedFloat64Array=value.xyz.duplicate();var stats:=PackedFloat64Array();stats.resize(16)
		var dual:=PackedFloat64Array([0.]);var reaction:=PackedFloat64Array();reaction.resize(value.targets.size())
		if mode=="force":xyz[4]+=.001
		if mode=="negative":dual[0]=-1.
		if mode=="nonfinite":dual[0]=NAN
		if mode=="active":dual[0]=1.
		if mode=="shape":dual=PackedFloat64Array()
		var result:={"status":0,"xyz":xyz,"stats":stats,"reaction":reaction,"dual":dual}
		if mode=="ghost_model":result["normal_rows"]=[];result.dual=PackedFloat64Array()
		return result
class Guard extends RefCounted:
	var status:=0
	var malformed:=false
	var bad_index:=4
	var bad_value:=NAN
	var request:Dictionary
	func guard_motion(value:Dictionary)->Dictionary:
		request=value.duplicate(true);var stats:=PackedFloat64Array([0.,0.,-1.,-1.,INF,0.,0.,0.])
		if malformed:stats[bad_index]=bad_value
		return {"status":status,"stats":stats,"witness_t":-1.}
func _initialize()->void:
	var model=load("res://scripts/embedded_membrane.gd").new()
	check(model.has_method("advance_contact"),"embedded state offers guarded coupled time integration")
	if failures:quit(1);return
	model.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	var backend:=Backend.new();var guard:=Guard.new();var packet:=PackedFloat64Array();packet.resize(41)
	for off in [0,3,6,9]:packet[off]=.2;packet[off+1]=.3;packet[off+2]=.4
	packet[12]=.1
	var motion:={"kinds":PackedInt32Array([0]),"packets":packet,"guard":guard}
	var force:=PackedFloat64Array();force.resize(9)
	var before:Dictionary=model.snapshot();var result:Dictionary=model.advance_contact(1./60.,force,backend,2.,3.,motion)
	check(result.valid,"stationary clear coupled candidate accepts only with a complete interval guard: "+result.reason)
	var after:Dictionary=model.snapshot()
	check(after.steps==1 and after.previous==before.xyz and after.contacts.dual==PackedFloat64Array([0.]),"accepted positions histories reactions and clock publish together")
	check(backend.request.capsules==PackedFloat64Array([.2,.3,.4,.2,.3,.4,.1]),"solver capsule endpoints/radius derive from the same physical motion packet as the guard")
	check(guard.request.previous==model.physical_positions() and guard.request.current==model.physical_positions() and guard.request.gap_tolerance==1e-9,"guard receives double fine geometry and the original full path tolerance")
	for status in [1,2,-1]:
		guard.status=status;var saved:Dictionary=model.snapshot()
		check(not model.advance_contact(1./60.,force,backend,2.,3.,motion).valid and model.snapshot()==saved,"collision or uncertain/invalid interval cannot commit any candidate")
	guard.status=0;guard.malformed=true
	check(not model.advance_contact(1./60.,force,backend,2.,3.,motion).valid and model.snapshot()==after,"nonfinite guard diagnostics reject atomically")
	for pair in [[4,-INF],[0,INF],[7,NAN]]:
		guard.bad_index=pair[0];guard.bad_value=pair[1]
		check(not model.advance_contact(1./60.,force,backend,2.,3.,motion).valid and model.snapshot()==after,"only the documented unsampled positive gap infinity is permitted")
	guard.malformed=false
	for mode in ["force","negative","nonfinite","active","shape","ghost_model"]:
		backend.mode=mode
		check(not model.advance_contact(1./60.,force,backend,2.,3.,motion).valid and model.snapshot()==after,"fabricated candidate/dual cannot bypass original force/contact checks: "+mode)
	backend.mode="clear"
	for malformed in [{},motion.merged({"guard":null},true),motion.merged({"packets":PackedFloat64Array([0.])},true),motion.merged({"kinds":PackedInt32Array([9])},true)]:
		check(not model.advance_contact(1./60.,force,backend,2.,3.,malformed).valid and model.snapshot()==after,"invalid motion command never advances tissue")
	print("Embedded coupled state contract: ",failures," failures");quit(1 if failures else 0)
