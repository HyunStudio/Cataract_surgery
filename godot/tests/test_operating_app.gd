extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures+=1; push_error(message)
func _initialize() -> void: call_deferred("run")
func place(app,hand: int,p: Vector3) -> void:
	app.rigs[hand].aim_at(p)
	app.rigs[hand].set_insertion(app.rigs[hand].portal.distance_to(p))
func enter_chamber(app,hand:int) -> void:
	# Route through the actual prepared corneal window and above the iris.
	for p in [Vector3(1.32,.84,0),Vector3(1.22,.847,0),Vector3(1.1,.864,0),Vector3(.9,.89,0),Vector3(0,.9,0)]:
		place(app,hand,p); app._physics_process(1./60.)
func open_capsule(app) -> void:
	app.choose_tool("knife"); enter_chamber(app,app.selected); app.grip_down=true
	for i in range(100):
		var angle:=TAU*i/99.
		place(app,app.selected,Vector3(.32*cos(angle),.81,.32*sin(angle))); app._physics_process(1./60.)
	app.release_controls()
func run() -> void:
	var source=load("res://scripts/simulator.gd")
	if not source.can_instantiate(): push_error("app does not load"); quit(1); return
	var app=source.new()
	root.add_child(app)
	app.set_physics_process(false)
	await process_frame
	if not app.has_method("begin_operation"):
		push_error("professional encounter controller missing")
		app.queue_free(); quit(1); return
	check(not app.begin_operation(),"cannot start unprepared encounter")
	for key in ["patient","side","equipment"]: app.prepare_check(key)
	check(app.begin_operation(),"preparation enables operating view")
	check(not app.room_view,"operation enters microscope")
	check(not app.finish_case(),"cannot finish untouched eye")
	app.choose_tool("knife")
	app.grip_down=true
	for i in range(41):
		place(app,0,Vector3(1.32,.84,-.1+.005*i))
		app._physics_process(1./60.)
	check(app.incision.opened[0],"actual continuous blade path opens entry")
	app.release_controls()
	app.choose_tool("forceps")
	enter_chamber(app,0)
	place(app,0,Vector3(0,.82,0))
	app.grip_down=true
	app._physics_process(1./60.)
	app.toggle_latch()
	app.switch_hand()
	app._physics_process(1./60.)
	check(app.capsule.metrics().grasps.has(0),"left grasp remains while right hand selected")
	app.release_controls()
	check(not app.latched[0],"context release clears latch")
	app.handle_pedal(true,false,true,1)
	check(app.pedal_stage==1,"independent irrigation pedal state")
	app.set_room_view(true)
	check(not app.pedal_down and app.pedal_stage==0,"camera switch disarms equipment")
	app.start_practice()
	check(app.practice and app.incision.opened[0],"practice supplies explicit prepared entry anatomy")
	open_capsule(app)
	app.choose_tool("cannula"); place(app,app.selected,Vector3(.32,.76,0)); app._physics_process(1./60.)
	place(app,app.selected,Vector3(.66,.76,0))
	app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true,1); app.handle_pedal(true,false,true,1)
	for i in range(40): app._physics_process(1./60.)
	check(app.lens.layered and app.lens.metrics().adhesion_released>0.,"active cannula couples local hydro release in actual app")
	app.choose_tool("phaco"); app._physics_process(1./60.)
	check(app.lens.hydro_flow==0.,"tool change cannot retain a hydro jet")
	app.choose_tool("injector")
	place(app,app.selected,Vector3(0,.72,0)); app.grip_down=true
	for i in range(15): app._physics_process(1./60.)
	var folded: Vector3=app.iol.positions[-1]
	var delivered: float=app.iol.metrics().delivered
	app.switch_hand(); app.choose_tool("forceps"); place(app,app.selected,Vector3(.3,.82,0))
	app._physics_process(1./60.)
	check(app.iol.positions[-1].distance_to(folded)<.00001,"cartridge stays with original injector after hand switch")
	check(app.iol.metrics().delivered==delivered,"other hand cannot advance plunger")
	app.toggle_help(); var stopped: float=app.clock
	app._physics_process(1./60.)
	check(app.clock==stopped and not app.pedal_down,"help freezes physics and disarms actions")
	app.toggle_help()
	app.update_geometry()
	app.recording.record(0.,app.display.capture_frame(),true)
	var live: PackedVector3Array=app.capsule.positions.duplicate()
	app.preview_frame(0)
	check(app.capsule.positions==live,"visual review never changes numerical tissue")
	var old_tool: String=app.hand_tools[app.selected]
	var key:=InputEventKey.new(); key.keycode=KEY_1; key.pressed=true
	app._input(key)
	check(app.hand_tools[app.selected]==old_tool,"review ignores instrument keyboard shortcuts")
	app.end_review()
	app.choose_tool("knife"); app.target_planes[app.selected]=.95
	app.new_case("motion")
	check(app.target_planes==[.82,.68],"new case restores each starting tool depth")
	app.start_practice(); app.switch_hand()
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	for i in range(220): app._physics_process(.05)
	check(app.director.snapshot().alert=="motion" and not app.pedal_down,"seeded adverse event freezes and disarms active equipment")
	var alert_clock: float=app.clock
	app._physics_process(.05)
	check(app.clock==alert_clock,"unacknowledged event cannot advance")
	app.acknowledge(); app._physics_process(.05)
	check(app.clock>alert_clock,"assessment enables deliberate continuation")
	app.set_sound(true); check(app._sound,"sound setting reaches equipment audio")
	app.set_sound(false)
	app.queue_free()
	await process_frame
	print("Operating app: ",failures," failures")
	quit(1 if failures else 0)
