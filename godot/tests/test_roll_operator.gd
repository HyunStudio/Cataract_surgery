extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app)
	app.set_physics_process(false);app.set_process(false);app.set_process_input(false)
	await process_frame;app.start_practice();await process_frame
	var event:=InputEventKey.new();event.keycode=KEY_C;event.pressed=true
	var before:Vector3=app.rigs[0].tip
	for i in range(10):app._input(event)
	check(app.rigs[0].roll==0.,"key burst queues roll without publishing an unchecked pose")
	app._physics_process(1./60.)
	check(app.rigs[0].roll>0. and app.rigs[0].roll<=.020001,"operative axial rotation obeys1.2radian/second fixed-tick limit")
	check(app.rigs[0].tip.distance_to(before)<1e-6,"axial key input does not advance the tip")
	app.update_geometry(false)
	var profile=load("res://scripts/instrument_profile.gd")
	check(app.tool_models[0].forceps.basis.is_equal_approx(profile.frame(app.rigs[0].axis,app.rigs[0].roll)),"display uses accepted physical roll")
	var accepted:float=app.rigs[0].roll
	app.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT);app._physics_process(1./60.)
	check(app.rigs[0].roll==accepted,"focus loss cancels residual roll intent")
	app.toggle_pause();app._input(event);app.toggle_pause();app._physics_process(1./60.)
	check(app.rigs[0].roll==accepted,"paused roll does not queue a later surprise rotation")
	app._input(event);app.switch_hand();app._physics_process(1./60.)
	check(app.rigs[0].roll==accepted,"hand change cancels old hand rotation intent")
	app.start_practice();check(app.rigs[0].roll==0. and app.rigs[1].roll==0.,"new practice resets both axial orientations")
	app.free();await process_frame
	print("Roll operator: ",failures," failures");quit(1 if failures else 0)
