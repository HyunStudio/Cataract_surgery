extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var source = load("res://scripts/simulator.gd")
	if source == null:
		push_error("numerical simulation scene missing")
		quit(1)
		return
	var app = source.new()
	root.add_child(app)
	app.set_physics_process(false)
	await process_frame
	app.start_practice()
	check(app.capsule.positions.size()>100,"actual deformable membrane in simulation")
	check(app.rigs.size()==2,"independent two instrument poses")
	var grip_world: Vector3 = app.tool_models[0]["forceps"].to_global(Vector3(1.55,.52,.20))
	check((grip_world-app.rigs[0].tip).cross(app.rigs[0].axis).length()<.001,"rendered instrument shaft follows incision-constrained axis")
	var other: Vector3 = app.rigs[1].tip
	app.rigs[0].aim_at(Vector3(.2,.8,.2))
	check(app.rigs[1].tip==other,"switching selected tool does not teleport other hand")
	app.grip_down = true
	app.pedal_down = true
	app.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	check(not app.grip_down and not app.pedal_down,"focus loss releases simulated pedal and jaws")
	check(app.has_method("handle_pedal"),"pedal context gate exists")
	if app.has_method("handle_pedal"):
		app.handle_pedal(true,false,true)
		app.switch_hand()
		app.handle_pedal(true,true,true)
		check(not app.pedal_down,"held key echo cannot rearm pedal after hand switch")
		app.handle_pedal(false,false,true)
		app.handle_pedal(true,false,true)
		check(app.pedal_down,"release and fresh pedal press can rearm")
	var count: int = app.capsule.positions.size()
	app.reset_simulation()
	check(app.capsule.positions.size()==count and app.capsule.metrics().broken_edges==0,"reset restores actual topology")
	for i in range(5): app._physics_process(1./60.)
	check(app.capsule.metrics().finite and app.lens.metrics().finite,"coupled scene finite")
	app.queue_free()
	await process_frame
	print("Numerical simulator integration: ",failures," failures")
	quit(1 if failures else 0)
