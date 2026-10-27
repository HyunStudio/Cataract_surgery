extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame; app.start_practice()
	check(app.has_method("_present_frame"),"runtime separates presentation from fixed tissue steps")
	if failures: app.queue_free(); await process_frame; quit(1); return
	var before:Dictionary=app.display.capture_frame()
	app.set_physics_process(true)
	for p in [Vector3(1.32,.8,0),Vector3(1.32,.65,0),Vector3(.9,.68,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	check(app.clock>.049 and app.display.capture_frame()==before,"multiple fixed steps advance tissue while retaining last presented frame")
	var live_clock:float=app.clock
	app._process(0.)
	check(app.clock==live_clock,"presentation never integrates another tissue step")
	check(app.display.capture_frame().rigs[0].tip==app.rigs[0].tip,"one presentation applies the latest resolved tool pose")
	check(app.recording.frames[-1].time==app.clock,"sample timestamp matches the captured latest state")
	app._physics_process(1./60.); app.preview_frame(0)
	var reviewed:Dictionary=app.display.capture_frame()
	app._process(0.)
	check(app.display.capture_frame()==reviewed,"pending live presentation cannot overwrite review geometry")
	app.end_review(); app.set_physics_process(false)
	app._physics_process(1./60.)
	check(app.display.capture_frame().capsule.positions==app.capsule.positions,"explicit manual steps still publish current numerical state")
	app.queue_free(); await process_frame
	print("Presentation clock: ",failures," failures"); quit(1 if failures else 0)
