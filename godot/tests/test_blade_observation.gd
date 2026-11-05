extends SceneTree
class ObservedCapsule:
	extends "res://scripts/capsule_solver.gd"
	var changed:=true
	var reject:=false
	var calls:=0
	func requires_physics_transaction()->bool:return true
	func incise_patches(_patches:Array)->Dictionary:
		calls+=1
		if changed:_incision_events+=1
		return {"valid":true,"changed":changed,"reason":""}
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		native_failure={"reason":"observation_rollback"} if reject else {}
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func roll(app)->void:
	var event:=InputEventKey.new();event.keycode=KEY_C;event.pressed=true;app._input(event)
	app._physics_process(1./60.);app.refresh_ui()
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app)
	app.set_physics_process(false);app.set_process(false);app.set_process_input(false)
	await process_frame;app.start_practice();app.choose_tool("knife")
	var model:=ObservedCapsule.new();model.geometry=app.geometry;model.reset();app.capsule=model
	app.grip_down=true;roll(app)
	check(model.calls==1 and app._last_capsule.get("blade_action","")=="new_cut","accepted finite sweep publishes actual changed cutter result")
	check(app.ui._telemetry.text.contains("새 절개 형성"),"active selected knife displays accepted incision observation")
	model.changed=false;roll(app)
	check(app._last_capsule.get("blade_action","")=="no_new_cut" and app.ui._telemetry.text.contains("새 절개 없음"),"unchanged sweep reports no new incision rather than inventing contact or completion")
	# Complete the queued bounded roll before testing a truly stationary tick.
	for i in range(4):app._physics_process(1./60.)
	var calls:int=model.calls;app._physics_process(1./60.);app.refresh_ui()
	check(model.calls==calls and app._last_capsule.get("blade_action","")=="stationary" and app.ui._telemetry.text.contains("이동 없음"),"stationary blade does not reuse prior incision result or invoke cutter")
	model.changed=true;model.reject=true
	var before:Dictionary=app._last_capsule.duplicate(true);var events:int=model._incision_events;var clock:float=app.clock
	roll(app)
	check(app.paused and model._incision_events==events and app.clock==clock and app._last_capsule==before,"later solver rejection cannot publish cut or observation from the rejected tick")
	check(not app.ui._telemetry.text.contains("칼날:"),"paused rejected tick suppresses stale operating observation")
	app.paused=false;model.reject=false;app.grip_down=true;roll(app)
	app.release_controls();app.refresh_ui()
	check(not app.ui._telemetry.text.contains("칼날:"),"release immediately suppresses last accepted action without waiting for another tick")
	app.free();await process_frame
	print("Blade observation: ",failures," failures");quit(1 if failures else 0)
