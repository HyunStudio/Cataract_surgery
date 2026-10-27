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
	wheel.pressed=true; wheel.position=point(app.rigs[0].tip)
	before=app.rigs[0].tip; app._input(wheel)
	check(app.rigs[0].tip.distance_to(before)<1e-6,"wheel queues intent without changing the accepted pose before collision validation")
	for i in range(10): app._input(wheel)
	check(app.rigs[0].tip.distance_to(before)<1e-6,"wheel burst cannot teleport the accepted tool")
	app._physics_process(1./60.)
	check(app.rigs[0].tip.distance_to(before)<=.0251,"queued wheel movement obeys the normal per-tick speed bound")
	for i in range(20): app._physics_process(1./60.)
	before=app.rigs[0].tip
	move(before)
	check(app.target_valid[0] and app.targets[0].distance_to(before)<.0001,"exterior fixed-length aiming preserves the pointer hemisphere after wheel withdrawal")
	app._physics_process(1./60.)
	check(app.rigs[0].tip.distance_to(before)<.0001,"stationary exterior pointer does not command reinsertion")
	var pitch:=InputEventKey.new(); pitch.keycode=KEY_Q; pitch.pressed=true
	before=app.rigs[0].tip
	for i in range(10): app._input(pitch)
	check(app.rigs[0].tip.distance_to(before)<1e-6,"pitch burst queues intent without publishing an unchecked pose")
	app._physics_process(1./60.)
	check(app.rigs[0].tip.distance_to(before)<=.0251,"pitch command obeys normal bounded movement")
	app.release_controls(); app._set_tip(0,app.capsule.positions[0])
	app.toggle_pause()
	var key:=InputEventKey.new(); key.keycode=KEY_G; key.pressed=true; app._input(key)
	check(not app.latched[0],"paused keyboard shortcut cannot queue tissue grasping")
	app.toggle_pause(); app.toggle_latch()
	check(app.latched[0],"fresh operative latch remains available")
	app.withdraw_tools()
	check(app.target_valid[0] and app.target_valid[1],"explicit withdrawal schedules new commands after disarming")
	app.start_practice(); app.rigs[0].set_insertion(0.)
	app.previous_tips[0]=app.rigs[0].tip
	app._body_poses[0]={"tip":app.rigs[0].tip,"axis":app.rigs[0].axis,"grip":false}
	var old_axis:Vector3=app.rigs[0].axis
	app._input(pitch)
	var proposed_axis:Vector3=old_axis
	var reference=load("res://scripts/instrument_rig.gd").new()
	reference.axis=old_axis; reference.adjust_pitch(-.02); proposed_axis=reference.axis
	check(app.rigs[0].axis.is_equal_approx(old_axis),"pivot orientation is not published before certification")
	app._physics_process(1./60.)
	check(app.rigs[0].axis.is_equal_approx(proposed_axis),"clear zero-insertion pitch retains and certifies orientation intent")
	app._input(pitch)
	reference.adjust_pitch(-.02)
	wheel.button_index=MOUSE_BUTTON_WHEEL_UP; wheel.position=point(app.rigs[0].tip); app._input(wheel)
	check(app.target_valid[0] and (app.targets[0]-app.rigs[0].portal).normalized().is_equal_approx(reference.axis),"wheel after queued pivot pitch preserves the proposed axis")
	app.release_controls()
	var portal:Vector3=app.rigs[0].portal
	app.anatomy.iris={"positions":PackedVector3Array([portal+Vector3(-.01,-.1,-.1),portal+Vector3(-.01,.1,-.1),portal+Vector3(-.01,0,.1)]),"triangles":PackedInt32Array([0,1,2]),"revision":0}
	old_axis=app.rigs[0].axis
	app._input(pitch); app._physics_process(1./60.)
	check(app.rigs[0].axis.is_equal_approx(old_axis),"uncertified pivot rotation near tissue retains the accepted axis")
	app.queue_free(); await process_frame
	print("Control context: ",failures," failures"); quit(1 if failures else 0)
