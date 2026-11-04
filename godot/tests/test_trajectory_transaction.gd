extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var requests:Array=[]
	var cost:=3.
	var bad_force:=false
	var bad_penetration:=false
	var bad_comp:=false
	var fail_static:=false
	var failed_force:=7e-7
	var failed_penetration:=0.
	var failed_comp:=0.
	func solve_contact_fem(request:Dictionary)->Dictionary:return candidate(request,1)
	func solve_trajectory_fem(request:Dictionary)->Dictionary:return candidate(request,request.times.size())
	func candidate(request:Dictionary,layers:int)->Dictionary:
		requests.append(request.duplicate(true));var xyz:PackedFloat64Array=request.xyz.duplicate()
		if bad_force and layers>1:xyz[4]+=.001
		var stats:=PackedFloat64Array();stats.resize(16);stats[2]=cost
		if fail_static and layers==1:
			stats[1]=failed_force;stats[12]=failed_penetration;stats[13]=failed_comp
			return {"status":2,"xyz":xyz,"stats":stats,"reaction":PackedFloat64Array(),"dual":PackedFloat64Array()}
		if layers>1 and bad_penetration:stats[12]=1e-6
		if layers>1 and bad_comp:stats[13]=1e-6
		var dual:=PackedFloat64Array();dual.resize(layers)
		return {"status":0,"xyz":xyz,"stats":stats,"reaction":PackedFloat64Array(),"dual":dual}
class Guard extends RefCounted:
	var calls:=0
	var witness:=.5
	var repeat:=false
	var always_clear:=false
	func guard_motion(_request:Dictionary)->Dictionary:
		calls+=1
		return {"status":1 if not always_clear and (repeat or calls==1) else 0,"stats":PackedFloat64Array([1.,1.,0.,0.,-.01,0.,0.,0.]),"witness_t":witness}
func model():
	var value=load("res://scripts/embedded_membrane.gd").new()
	value.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	return value
func motion(guard)->Dictionary:
	var packet:=PackedFloat64Array();packet.resize(41)
	for off in [0,3,6,9]:packet[off]=.2;packet[off+1]=.3;packet[off+2]=.4
	packet[12]=.1
	return {"kinds":PackedInt32Array([0]),"packets":packet,"guard":guard}
func _initialize()->void:
	var value=model();var backend:=Backend.new();var guard:=Guard.new();var command:=motion(guard)
	var force:=PackedFloat64Array([.001,0.,0.,.001,0.,0.,.001,0.,0.]);var before:Dictionary=value.snapshot()
	var result:Dictionary=value.advance_contact(1./60.,force,backend,2.,3.,command,1.,20)
	check(result.valid,"guard witness triggers a staged trajectory retry instead of publishing/rejecting endpoint only: "+result.reason)
	if not result.valid:quit(1);return
	check(backend.requests.size()==2 and guard.calls==2,"one complete-motion witness causes exactly one retry")
	var first:Dictionary=backend.requests[0];var retry:Dictionary=backend.requests[1]
	check(first.xyz==retry.xyz and first.dt==retry.dt and retry.previous==before.xyz,"retry retains original inertial predictor, accepted old controls and physical dt")
	check(first.budget==20 and retry.budget==17 and retry.times==PackedFloat64Array([.5,1.]),"retries share total Newton budget and carry sorted material contact times")
	var after:Dictionary=value.snapshot()
	check(after.steps==1 and after.time==1./60. and after.previous==before.xyz and after.contacts.times==retry.times,"histories, clock and sampled multipliers commit once after the complete guard")
	for mode in ["duplicate","zero","nan","exhausted","bad_work","bad_force"]:
		value=model();backend=Backend.new();guard=Guard.new();before=value.snapshot()
		if mode=="duplicate":guard.repeat=true
		if mode=="zero":guard.witness=0.
		if mode=="nan":guard.witness=NAN
		if mode=="bad_work":backend.cost=21.
		if mode=="bad_force":backend.bad_force=true
		var answer:Dictionary=value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,3 if mode=="exhausted" else 20)
		check(not answer.valid and value.snapshot()==before,"failed trajectory work is atomic: "+mode)
		check(backend.requests.size()<=2,"invalid/duplicate witness never starts an unbounded solve loop")
	value=model();backend=Backend.new();backend.fail_static=true;guard=Guard.new();guard.always_clear=true;before=value.snapshot()
	var recovered:Dictionary=value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20)
	check(recovered.valid and backend.requests.size()==2 and guard.calls==1,"near-feasible static force failure retries the accurate temporal field before requiring a guard witness")
	if recovered.valid:
		check(backend.requests[0].xyz==backend.requests[1].xyz and backend.requests[1].budget==17 and recovered.trajectory_iterations==6,"numerical recovery keeps predictor and accounts for failed static work")
		check(value.snapshot().steps==1 and value.snapshot().previous==before.xyz,"numerical recovery commits one history step")
	value=model();backend=Backend.new();backend.fail_static=true;backend.failed_force=1.1889320067348663e-6;guard=Guard.new();guard.always_clear=true;before=value.snapshot()
	recovered=value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20)
	check(recovered.valid and backend.requests.size()==2 and guard.calls==1,"finite feasible endpoint force stall above the old heuristic cap still tries one accurate cold candidate")
	if recovered.valid:check(value.snapshot().steps==1 and backend.requests[1].xyz==backend.requests[0].xyz and recovered.trajectory_iterations==6,"larger endpoint residual cannot change the predictor, work budget or single publication")
	value=model();backend=Backend.new();backend.fail_static=true;backend.failed_force=1.1889320067348663e-6;backend.bad_force=true;guard=Guard.new();guard.always_clear=true;before=value.snapshot()
	check(not value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20).valid and backend.requests.size()==2 and value.snapshot()==before,"retry eligibility never waives the candidate independent physical force gate")
	value=model();backend=Backend.new();backend.fail_static=true;backend.failed_force=1.235052110692969e-6;backend.failed_penetration=3.6986404357918054e-8;backend.failed_comp=8.919789087559183e-8;guard=Guard.new();guard.always_clear=true;before=value.snapshot()
	recovered=value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20)
	check(recovered.valid and backend.requests.size()==2 and guard.calls==1,"finite unpublished endpoint penetration/COMP stall can try one accurate cold candidate")
	if recovered.valid:check(backend.requests[0].xyz==backend.requests[1].xyz and recovered.trajectory_iterations==6 and value.snapshot().steps==1,"infeasible failed iterate is discarded while original predictor/work/history remain")
	value=model();backend=Backend.new();backend.fail_static=true;backend.failed_penetration=3.6986404357918054e-8;backend.failed_comp=8.919789087559183e-8;backend.bad_force=true;guard=Guard.new();guard.always_clear=true;before=value.snapshot()
	check(not value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20).valid and backend.requests.size()==2 and value.snapshot()==before,"broader numerical retry never publishes a candidate failing the independent force gate")
	for mode in ["penetration","comp"]:
		value=model();backend=Backend.new();backend.fail_static=true;backend.failed_penetration=3.6986404357918054e-8;backend.failed_comp=8.919789087559183e-8;backend.bad_penetration=mode=="penetration";backend.bad_comp=mode=="comp";guard=Guard.new();guard.always_clear=true;before=value.snapshot()
		check(not value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20).valid and backend.requests.size()==2 and guard.calls==0 and value.snapshot()==before,"failed endpoint retry never waives final candidate "+mode+" limits")
	value=model();backend=Backend.new();backend.fail_static=true;backend.failed_force=INF;guard=Guard.new();before=value.snapshot()
	check(not value.advance_contact(1./60.,force,backend,2.,3.,motion(guard),1.,20).valid and backend.requests.size()==1 and value.snapshot()==before,"invalid static geometry/nonfinite residual cannot trigger numerical recovery")
	print("Trajectory step transaction: ",failures," failures");quit(1 if failures else 0)
