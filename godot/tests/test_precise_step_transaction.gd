extends SceneTree
## A rejected precise tissue tick cannot advance the rest of the surgery.
class RejectingCapsule:
	extends "res://scripts/capsule_solver.gd"
	var rejected:=0
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		rejected+=1
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
	app._physics_process(1./60.)
	check(rejecting.rejected==1,"injected tissue failure must actually run")
	check(rejecting.native_failure.get("reason","")=="injected_precise_step_failure","retain physical failure reason")
	check(app.clock==before_clock,"rejected tissue tick must not advance surgery clock")
	check(app.lens.metrics()==before_lens,"rejected tissue tick must not advance lens or fluid state")
	check(app.samples.size()==before_samples and app.recording.frames.size()==before_recording,"rejected tick must not publish an accepted sample or recording")
	app.queue_free(); await process_frame
	print("Precise whole-step transaction: ",failures," failures")
	quit(1 if failures else 0)
