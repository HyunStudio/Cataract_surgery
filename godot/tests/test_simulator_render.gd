extends SceneTree
var app
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures+=1; push_error(message)
func _initialize() -> void: call_deferred("run")
func show_frame(name: String) -> void:
	app.update_geometry()
	await process_frame
	await process_frame
	if DisplayServer.get_name()!="headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/"+name+".png")
func place(p: Vector3) -> void:
	app.rigs[app.selected].aim_at(p)
	app.rigs[app.selected].set_insertion(app.rigs[app.selected].portal.distance_to(p))
func enter_chamber(side:float,z:float) -> void:
	for p in [Vector3(side*1.32,.84,z),Vector3(side*1.22,.847,z),Vector3(side*1.1,.864,z),Vector3(side*.9,.885,z),Vector3(0,.9,0)]:
		place(p); app._physics_process(1./60.)
func run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports"))
	app=load("res://scripts/simulator.gd").new()
	app.anatomical=false
	root.add_child(app)
	app.set_process_input(false)
	app.set_physics_process(false)
	app.start_practice()
	await show_frame("physics_01_intact")
	app.wireframe=true
	enter_chamber(1.,0.)
	place(Vector3(0,.82,0))
	app.grip_down=true
	app._physics_process(1./60.)
	check(app.capsule.metrics().grasped>=0,"constrained tool attaches at actual tissue contact")
	for i in range(12):
		place(Vector3(.012*i,minf(.89,.82+.018*i),0))
		app._physics_process(1./60.)
	await show_frame("physics_02_traction")
	for i in range(12,40):
		place(Vector3(.012*i,minf(.89,.82+.018*i),0))
		app._physics_process(1./60.)
	check(app.capsule.metrics().broken_edges>0,"actual constrained traction tears capsule")
	await show_frame("physics_03_rupture")
	app.release_controls()
	app.selected=1
	app.hand_tools[1]="phaco"
	enter_chamber(-1.,.25)
	# Prepare a local physical opening for this hand; do not bypass the membrane.
	app.choose_tool("knife"); app.grip_down=true
	for i in range(40):
		place(Vector3(.42,.81,-.10+.005*i)); app._physics_process(1./60.)
	app.release_controls(); app.choose_tool("phaco")
	place(Vector3(.42,.70,0)); app._physics_process(1./60.)
	app.slider_values.energy=1.
	app.slider_values.suction=1.
	place(Vector3(.42,.68,0))
	app.handle_pedal(false,false,true,3)
	app.handle_pedal(true,false,true,3)
	for i in range(180): app._physics_process(1./60.)
	check(app.lens.metrics().removed_mass>0.,"coupled workbench aspiration transports material into tool")
	check(app.lens.metrics().remaining_mass>.5,"local aspiration does not clear global field")
	await show_frame("physics_04_local_aspiration")
	var file:=FileAccess.open("res://reports/physics-kernel-observation.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"capsule":app.capsule.metrics(),"lens":app.lens.metrics(),"model":"uncalibrated research","adapter":RenderingServer.get_video_adapter_name()},"  "))
	print("Numerical GPU scene: ",failures," failures; ",JSON.stringify(app.lens.metrics()))
	app.queue_free()
	await process_frame
	quit(1 if failures else 0)
