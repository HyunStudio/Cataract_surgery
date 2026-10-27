extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func place(app,target:Vector3,until_injury:=false)->void:
	app.targets[0]=target; app.target_valid[0]=true
	for i in range(300):
		var before:Vector3=app.rigs[0].tip
		app._physics_process(1./60.)
		check(app.rigs[0].tip.distance_to(before)<=.0251,"adverse case preserves normal control speed")
		if until_injury and app.injury.metrics().posterior_breached: return
		if app.rigs[0].tip.distance_to(target)<.001: return
		if app.director.snapshot().alert!="": break
	check(false,"adverse route blocked before intended posterior contact: "+str(app.rigs[0].tip))
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for id in ["patient","side","equipment"]: app.prepare_check(id)
	app.begin_operation(); app.choose_tool("knife"); place(app,Vector3(1.32,.95,-.25)); app.grip_down=true
	for i in range(101):
		place(app,Vector3(1.32,.80,-.25+.005*i))
	app.release_controls()
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.2,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0)]:
		place(app,p)
	place(app,Vector3(-.5,.65,0))
	app.grip_down=true; place(app,Vector3(-.5,-.8,0),true)
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
