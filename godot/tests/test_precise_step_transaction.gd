extends SceneTree
## A rejected precise tissue tick cannot advance the rest of the surgery.
class RejectingCapsule:
	extends "res://scripts/capsule_solver.gd"
	var before_rejection:Callable
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		if before_rejection.is_valid(): before_rejection.call()
		native_failure={"reason":"injected_precise_step_failure","status":2}

var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new()
	root.add_child(app); app.set_physics_process(false); app.set_process(false)
	await process_frame
	app.start_practice()
	var rejecting=RejectingCapsule.new()
	rejecting.geometry=app.geometry; rejecting.reset()
	app.capsule=rejecting
	var before_clock:float=app.clock
	var before_lens:Dictionary=app.lens.metrics().duplicate(true)
	var before_samples:int=app.samples.size()
	var before_recording:int=app.recording.frames.size()
	var before_adhesion:PackedFloat64Array=app.lens.material.adhesion.duplicate()
	var before_opened:Array=app.incision.opened.duplicate()
	var before_revision:int=app.injury.surfaces.cornea.revision
	var call_trace:Array=[] # Outside model state: rollback must not erase the oracle.
	# Inject changes within the failed transaction, including a nested object
	# and the shared surface graph. Metrics alone cannot verify their rollback.
	rejecting.before_rejection=func()->void:
		call_trace.append("rejected")
		app.lens.material.adhesion[0]=.125
		app.incision.opened[0]=not app.incision.opened[0]
		app.injury.surfaces.cornea.revision+=1
	app._physics_process(1./60.)
	check(call_trace==["rejected"],"injected tissue failure must actually run")
	check(rejecting.native_failure.get("reason","")=="injected_precise_step_failure","retain physical failure reason")
	check(app.clock==before_clock,"rejected tissue tick must not advance surgery clock")
	check(app.lens.metrics()==before_lens,"rejected tissue tick must not advance lens or fluid state")
	check(app.samples.size()==before_samples and app.recording.frames.size()==before_recording,"rejected tick must not publish an accepted sample or recording")
	check(app.lens.material.adhesion==before_adhesion,"rollback must restore nested material state")
	check(app.incision.opened==before_opened,"rollback must restore wound state")
	check(app.injury.surfaces.cornea.revision==before_revision,"rollback must restore anatomical surface revision")
	# Verify shared ownership by behavior rather than dictionary value equality.
	app.injury.surfaces.cornea["transaction_alias_probe"]=73
	check(app.anatomy.cornea.get("transaction_alias_probe",0)==73,"restored anatomy must share injury's authoritative surface")
	app.injury.surfaces.cornea.erase("transaction_alias_probe")
	app.queue_free(); await process_frame
	print("Precise whole-step transaction: ",failures," failures")
	quit(1 if failures else 0)
