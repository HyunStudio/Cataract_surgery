extends SceneTree
## A rejected precise tissue tick cannot advance the rest of the surgery.
class RejectingCapsule:
	extends "res://scripts/capsule_solver.gd"
	var before_rejection:Callable
	var release_probe:Callable
	func requires_physics_transaction()->bool: return true
	func release()->void:
		if release_probe.is_valid(): release_probe.call()
		super.release()
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		if before_rejection.is_valid(): before_rejection.call()
		native_failure={"reason":"injected_precise_step_failure","status":2}

class CacheSpy:
	extends RefCounted
	var invalidations:=0
	func invalidate_cache()->void: invalidations+=1

class AcceptingCapsule:
	extends "res://scripts/capsule_solver.gd"
	func requires_physics_transaction()->bool: return true
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		native_failure={}; _integration_steps+=1

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
	var cache=CacheSpy.new(); rejecting.stretch_backend=cache
	app.grip_down=true; app.pedal_down=true; app.pedal_stage=3
	var before_clock:float=app.clock
	var before_lens:Dictionary=app.lens.metrics().duplicate(true)
	var before_samples:int=app.samples.size()
	var before_recording:int=app.recording.frames.size()
	var before_adhesion:PackedFloat64Array=app.lens.material.adhesion.duplicate()
	var material_identity=app.lens.material
	var before_opened:Array=app.incision.opened.duplicate()
	var before_revision:int=app.injury.surfaces.cornea.revision
	var before_positions:PackedVector3Array=rejecting.positions.duplicate()
	var before_xyz:PackedFloat64Array=rejecting._physical_xyz.duplicate()
	var before_previous:PackedFloat64Array=rejecting._physical_previous.duplicate()
	var before_steps:int=rejecting.metrics().integration_steps
	var before_boundary:Dictionary=app._flap_boundary._cornea.duplicate(true)
	var before_iol:Dictionary=app.iol.metrics().duplicate(true)
	var call_trace:Array=[] # Outside model state: rollback must not erase the oracle.
	rejecting.release_probe=func()->void: call_trace.append("release")
	# Inject changes within the failed transaction, including a nested object
	# and the shared surface graph. Metrics alone cannot verify their rollback.
	rejecting.before_rejection=func()->void:
		call_trace.append("rejected")
		app.lens.material.adhesion[0]=.125
		app.incision.opened[0]=not app.incision.opened[0]
		app.injury.surfaces.cornea.revision+=1
		app._flap_boundary._cornea.height_cache[Vector2.ZERO]=999.
		app._rigid_body._cache["failed_geometry"]={"revision":999}
		# Partial earlier tissue work must roll back along with the other models.
		rejecting.positions[0]+=Vector3(.001,0,0)
		rejecting._physical_xyz[0]+=.001; rejecting._physical_previous[0]+=.001
		rejecting._integration_steps+=1
	app._physics_process(1./60.)
	check(call_trace==["rejected"],"injected tissue failure must actually run")
	check(rejecting.native_failure.get("reason","")=="injected_precise_step_failure","retain physical failure reason")
	check(app.clock==before_clock,"rejected tissue tick must not advance surgery clock")
	check(app.lens.metrics()==before_lens,"rejected tissue tick must not advance lens or fluid state")
	check(app.samples.size()==before_samples and app.recording.frames.size()==before_recording,"rejected tick must not publish an accepted sample or recording")
	check(app.lens.material.adhesion==before_adhesion,"rollback must restore nested material state")
	check(app.lens.material==material_identity and material_identity.adhesion==before_adhesion,"restore nested material into its original owned object")
	check(app.incision.opened==before_opened,"rollback must restore wound state")
	check(app.injury.surfaces.cornea.revision==before_revision,"rollback must restore anatomical surface revision")
	check(rejecting.positions==before_positions and rejecting._physical_xyz==before_xyz and rejecting._physical_previous==before_previous and rejecting.metrics().integration_steps==before_steps,"partial earlier tissue work must roll back both packed64 authority and presentation/history")
	check(app._flap_boundary._cornea==before_boundary and app._rigid_body._cache.is_empty(),"failed geometry must not survive in anatomical caches")
	check(cache.invalidations==1,"invalidate derived solver cache without erasing diagnostic identity")
	check(app.iol.metrics()==before_iol,"IOL update must wait until tissue acceptance")
	check(app.paused and not app.grip_down and not app.pedal_down and not app.target_valid[0] and not app.target_valid[1],"failure must pause and disarm stale input without a physical release")
	var stopped_clock:float=app.clock
	app._physics_process(1./60.)
	check(app.clock==stopped_clock and call_trace==["rejected"],"paused failed tick must not silently retry or release tissue")
	app.toggle_pause()
	check(not app.paused and call_trace==["rejected"],"explicit resume must not physically release the restored attachment")
	app._physics_process(1./60.)
	check(app.paused and app.clock==before_clock and call_trace==["rejected","rejected"] and cache.invalidations==2,"explicit retry must remain atomic when failure repeats")
	# Verify shared ownership by behavior rather than dictionary value equality.
	app.injury.surfaces.cornea["transaction_alias_probe"]=73
	check(app.anatomy.cornea.get("transaction_alias_probe",0)==73,"restored anatomy must share injury's authoritative surface")
	app.injury.surfaces.cornea.erase("transaction_alias_probe")
	rejecting.before_rejection=Callable(); rejecting.release_probe=Callable()
	app.new_case("standard"); app.start_practice()
	var accepting=AcceptingCapsule.new(); accepting.geometry=app.geometry; accepting.reset()
	app.capsule=accepting
	var accepted_clock:float=app.clock
	var accepted_lens:Dictionary=app.lens.metrics().duplicate(true)
	app._physics_process(1./60.)
	check(absf(app.clock-accepted_clock-1./60.)<1e-12 and not app.paused and accepting.metrics().integration_steps==1,"accepted precise tick must commit exactly once")
	check(app.lens.metrics()!=accepted_lens,"accepted precise tick must retain its lens and fluid evolution")
	app.queue_free(); await process_frame
	print("Precise whole-step transaction: ",failures," failures")
	quit(1 if failures else 0)
