extends SceneTree
var failures:=0
var app
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func point(p:Vector3)->Vector2:
	return app.world.microscope.unproject_position(p)+app.viewport_box.global_position
func move(p:Vector3)->void:
	var event:=InputEventMouseMotion.new(); event.position=point(p); app._input(event)
func run()->void:
	app=load("res://scripts/simulator.gd").new(); root.add_child(app)
	app.set_physics_process(false); app.set_process_input(false)
	await process_frame
	app.start_practice()
	await process_frame
	var desired:Vector3=app.rigs[0].portal-app.rigs[0].axis*.4
	app.target_planes[0]=desired.y; move(desired)
	check(app.target_valid[0],"real microscope event queues motion")
	app.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	check(not app.target_valid[0],"focus loss cancels pending pointer motion")
	var before:Vector3=app.rigs[0].tip
	app._physics_process(1./60.)
	check(app.rigs[0].tip.distance_to(before)<1e-6,"focus loss holds the actual tool")
	app.targets[0]=before+Vector3(.1,0,0); app.target_valid[0]=true
	app.toggle_pause(); app.toggle_pause()
	check(not app.target_valid[0],"resume requires a fresh pointer command")
	app.targets[0]=before+Vector3(.1,0,0); app.target_valid[0]=true
	app.switch_hand()
	check(not app.target_valid[0],"hand switch cancels the previously controlled hand target")
	app.switch_hand(); app.set_assisted(false)
	var wheel:=InputEventMouseButton.new(); wheel.button_index=MOUSE_BUTTON_WHEEL_DOWN
	wheel.pressed=true; wheel.position=point(app.rigs[0].tip); app._input(wheel)
	before=app.rigs[0].tip
	move(before)
	check(app.target_valid[0] and app.targets[0].distance_to(before)<.0001,"exterior fixed-length aiming preserves the pointer hemisphere after wheel withdrawal")
	app._physics_process(1./60.)
	check(app.rigs[0].tip.distance_to(before)<.0001,"stationary exterior pointer does not command reinsertion")
	app.release_controls(); app._set_tip(0,app.capsule.positions[0])
	app.toggle_pause()
	var key:=InputEventKey.new(); key.keycode=KEY_G; key.pressed=true; app._input(key)
	check(not app.latched[0],"paused keyboard shortcut cannot queue tissue grasping")
	app.toggle_pause(); app.toggle_latch()
	check(app.latched[0],"fresh operative latch remains available")
	app.withdraw_tools()
	check(app.target_valid[0] and app.target_valid[1],"explicit withdrawal schedules new commands after disarming")
	app.queue_free(); await process_frame
	print("Control context: ",failures," failures"); quit(1 if failures else 0)
