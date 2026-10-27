extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures+=1; push_error(message)
func _initialize() -> void: call_deferred("run")
func place(app, p: Vector3) -> void:
	app._set_tip(app.selected,p)
func tick(app, count: int) -> void:
	for i in range(count): app._physics_process(1./60.)
func run() -> void:
	var app=load("res://scripts/simulator.gd").new()
	root.add_child(app); app.set_physics_process(false)
	await process_frame
	for key in ["patient","side","equipment"]: app.prepare_check(key)
	check(app.begin_operation(),"prepared case begins")
	# Only instrument poses and normal user actions change; never mutate tissue/material.
	app.choose_tool("knife"); app.grip_down=true
	for i in range(41):
		place(app,Vector3(1.32,.84,-.1+.005*i)); tick(app,1)
	check(app.incision.opened[0],"continuous blade trace creates real entry")
	# Open the membrane through a local blade trace.
	for i in range(100):
		var angle:=TAU*i/99.
		place(app,Vector3(.32*cos(angle),.81,.32*sin(angle))); tick(app,1)
	check(app.capsule.metrics().broken_edges>0,"blade opening changes actual capsule topology")
	app.release_controls(); app.choose_tool("cannula"); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true,1); app.handle_pedal(true,false,true,1)
	for step in range(2500):
		var attached:=-1.; var hydro_tip:=Vector3(.66,.76,0)
		for i in range(app.lens.particles.size()):
			if app.lens.material.is_cortex(i) and app.lens.material.adhesion[i]>attached:
				attached=app.lens.material.adhesion[i]; hydro_tip=app.lens.particles[i].position+Vector3(0,.04,0)
		if attached<.1: break
		place(app,hydro_tip); app._physics_process(.05)
		if step%100==0: await process_frame
	check(app.lens.metrics().adhesion_released>.8,"cannula moves locally around cortical shell to release adhesion")
	app.release_controls(); app.choose_tool("phaco")
	app.set_machine("energy",1.); app.set_machine("suction",1.); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	var tip:=Vector3(.6,.68,0)
	var steps:=0
	for step in range(3000):
		var nearest:=INF
		var found:=false
		for particle in app.lens.particles:
			if not particle.active or particle.cortex: continue
			var distance: float=particle.position.distance_squared_to(tip)
			if distance<nearest: nearest=distance; tip=particle.position; found=true
		if not found: break
		place(app,tip); tick(app,1); steps+=1
		if step%200==0: await process_frame
	print("Encounter phaco steps: ",steps," removed: ",app.lens.metrics().removed_mass)
	check(app.lens.metrics().nucleus_remaining<.01,"phaco removes the nuclear material")
	app.release_controls(); app.choose_tool("ia")
	app.handle_pedal(false,false,true,2); app.handle_pedal(true,false,true,2)
	for step in range(1600):
		var nearest:=INF; var found:=false
		for particle in app.lens.particles:
			if not particle.active: continue
			var distance:float=particle.position.distance_squared_to(tip)
			if distance<nearest: nearest=distance; tip=particle.position; found=true
		if not found: break
		place(app,tip); tick(app,1)
		if step%200==0: await process_frame
	check(app.metrics.path_length>1.,"path metric includes instrument pose and insertion changes")
	check(app.lens.metrics().removed_mass>=.98,"full app can physically aspirate material")
	app.release_controls(); app.choose_tool("injector"); place(app,Vector3(0,.72,0)); app.grip_down=true
	tick(app,110); app.release_controls(); tick(app,180)
	check(app.iol.metrics().deployed,"user-driven IOL fully delivered and elastically unfolds")
	app.withdraw_tools(); tick(app,150)
	for key in ["residual","implant","wound"]: check(app.inspect(key),"measured final inspection: "+key)
	check(app.finish_case(),"full prepared case reaches completion through real model observations")
	check(app.director.snapshot().ending=="completed","completion is not a practice or safe-stop ending")
	var live: PackedVector3Array=app.capsule.positions.duplicate()
	app.preview_frame(0); tick(app,10)
	check(app.capsule.positions==live,"review cannot run or overwrite live physics")
	app.end_review()
	if DisplayServer.get_name()!="headless":
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/professional-results.png")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports"))
	var file:=FileAccess.open("res://reports/full-encounter.json" if DisplayServer.get_name()=="headless" else "res://reports/full-encounter-gpu.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"failures":failures,"steps":steps,"report":app.director.snapshot(),"lens":app.lens.metrics(),"iol":app.iol.metrics(),"frames":app.recording.frames.size()},"  "))
	app.queue_free(); await process_frame
	print("Full operating encounter: ",failures," failures")
	quit(1 if failures else 0)
