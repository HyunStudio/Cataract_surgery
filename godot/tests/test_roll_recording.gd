extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func run()->void:
	var display=load("res://scripts/surgical_display.gd").new();root.add_child(display);display.build()
	var capsule=load("res://scripts/capsule_solver.gd").new()
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	var iol=load("res://scripts/iol_dynamics.gd").new()
	var rig=load("res://scripts/instrument_rig.gd").new();rig.roll=.7
	var second=load("res://scripts/instrument_rig.gd").new();second.roll=-.4
	display.apply(capsule,lens,iol,[rig,second],["forceps","phaco"],0,[{},{}],{"dimensioned":true})
	var expected:Basis=display.tool_models[0].forceps.basis
	var frame:Dictionary=display.capture_frame()
	check(frame.rigs[0].get("roll",-1.)==.7 and frame.rigs[1].get("roll",-1.)==-.4,"recorded visual poses preserve both accepted axial orientations")
	rig.roll=0.;display.apply(capsule,lens,iol,[rig,second],["forceps","phaco"],0,[{},{}],{"dimensioned":true})
	display.apply_frame(frame)
	check(display.tool_models[0].forceps.basis.is_equal_approx(expected),"review replays physical axial orientation rather than current live pose")
	for data in frame.rigs:data.erase("roll")
	display.apply_frame(frame)
	var profile=load("res://scripts/instrument_profile.gd")
	check(display.tool_models[0].forceps.basis.is_equal_approx(profile.frame(rig.axis)),"old visual recordings default to zero roll without script errors")
	display.free();await process_frame
	print("Roll recording: ",failures," failures");quit(1 if failures else 0)
