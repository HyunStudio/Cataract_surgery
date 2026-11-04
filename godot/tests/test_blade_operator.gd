extends SceneTree
var failures:=0
class Trace extends RefCounted:
	var cut_calls:=0
	var step_calls:=0
	var patches:Array=[]
	var tools:Array=[]
class CuttingProbe:
	extends "res://scripts/capsule_solver.gd"
	var trace:=Trace.new()
	var reject:=false
	func incise_patches(value:Array)->Dictionary:
		trace.cut_calls+=1;trace.patches=value.duplicate(true)
		if reject:
			positions[0]+=Vector3(.03,.02,0)
			return {"valid":false,"changed":false,"reason":"injected_blade_failure"}
		return {"valid":true,"changed":false,"reason":""}
	func step_tools(_dt:float,value:Array[Dictionary])->void:
		trace.step_calls+=1;trace.tools=value.duplicate(true);native_failure={}
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func arm_blade(app,probe)->void:
	app.start_practice();probe.geometry=app.geometry;probe.reset();probe.tissue_boundary=app._flap_boundary;app.capsule=probe
	app.choose_tool("knife");app.grip_down=true
	app.targets[0]=app.rigs[0].tip+Vector3(.01,0,.005);app.target_valid[0]=true
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app);app.set_physics_process(false);app.set_process(false);await process_frame
	var accepted:=CuttingProbe.new();arm_blade(app,accepted)
	var before_clock:float=app.clock
	app._physics_process(1./60.)
	check(accepted.trace.cut_calls==1 and not accepted.trace.patches.is_empty(),"dimensioned active knife sends actual finite sharp-edge patches through the operator step")
	check(accepted.trace.step_calls==1 and accepted.trace.tools.size()==2,"accepted geometric cutting still performs one physical tool step")
	if accepted.trace.tools.size()==2:check(not accepted.trace.tools[0].cut,"geometric knife never also enables coarse face-deletion cutting")
	check(absf(app.clock-before_clock-1./60.)<1e-12,"accepted blade operation commits time exactly once")
	app.release_controls();app._physics_process(1./60.)
	check(accepted.trace.cut_calls==1,"releasing the knife cannot replay the previous swept stroke")
	var rejected:=CuttingProbe.new();rejected.reject=true;arm_blade(app,rejected)
	var before_positions:PackedVector3Array=rejected.positions.duplicate();var before_tip:Vector3=app.rigs[0].tip
	var before_history:Dictionary=app._body_poses[0].duplicate(true);var before_lens:Dictionary=app.lens.capture_state();before_clock=app.clock
	app._physics_process(1./60.)
	check(rejected.trace.cut_calls==1 and rejected.trace.step_calls==0,"failed blade batch rejects before physical integration")
	check(rejected.positions==before_positions and app.rigs[0].tip==before_tip and app._body_poses[0]==before_history,"failed dimensioned blade restores material and full tool pose history")
	check(app.clock==before_clock and app.lens.capture_state()==before_lens,"failed geometric cut cannot advance fluid/material or clock")
	check(app.paused and not app.grip_down and not app.target_valid[0],"failed blade disarms targets and pauses without automatic retry")
	app._physics_process(1./60.);check(rejected.trace.cut_calls==1,"paused failure cannot repeat cutting")
	app.toggle_pause();app._physics_process(1./60.)
	check(rejected.trace.cut_calls==1,"explicit resume requires a new blade action")
	app.free();await process_frame;print("Blade operator transaction: ",failures," failures");quit(1 if failures else 0)
