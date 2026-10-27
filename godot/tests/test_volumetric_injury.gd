extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for id in ["patient","side","equipment"]: app.prepare_check(id)
	app.begin_operation(); app.choose_tool("knife"); app.grip_down=true
	for i in range(101):
		app._set_tip(0,Vector3(1.32,.80,-.25+.005*i)); app._physics_process(1./60.)
	app.release_controls()
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.2,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.grip_down=true; app._set_tip(0,Vector3(.30,-.8,0)); app._physics_process(1./60.)
	check(app.injury.metrics().posterior_breached,"dimensioned wrong-depth blade punctures actual posterior bag")
	check(app.lens.metrics().rupture_outflow>0.,"actual dimensioned posterior aperture drives boundary outflow")
	check(app.director.snapshot().alert=="tissue_injury" and not app.grip_down,"dimensioned structural injury stops actions")
	app.acknowledge(); check(not app.finish_case(),"assessment cannot erase dimensioned structural injury")
	if DisplayServer.get_name()!="headless":
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/volumetric-injury.png")
	app.new_case("small_pupil")
	check(not app.injury.metrics().posterior_breached and app.lens.rupture_leak==0.,"new dimensioned case restores posterior surface and flow")
	check(absf(app.pupil_radius-.60)<.0001,"small-pupil case regenerates actual dimensioned iris")
	app.queue_free(); await process_frame
	print("Volumetric injury: ",failures," failures"); quit(1 if failures else 0)
