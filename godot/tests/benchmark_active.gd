extends SceneTree
## Actual powered, moving-tool workload; separate from idle microscope samples.
func _initialize()->void: call_deferred("run")
func run()->void:
	if DisplayServer.get_name()=="headless": quit(1); return
	root.size=Vector2i(1920,1080)
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app)
	app.set_physics_process(false); app.set_process_input(false)
	await process_frame; app.start_practice(); app.choose_tool("knife")
	for p in [Vector3(1.32,.84,0),Vector3(1.22,.847,0),Vector3(1.1,.864,0),Vector3(.9,.89,0),Vector3(0,.9,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.grip_down=true
	for i in range(100):
		var a:=TAU*i/99.
		app._set_tip(0,Vector3(.32*cos(a),.81,.32*sin(a))); app._physics_process(1./60.)
	app.release_controls(); app.choose_tool("phaco"); app._set_tip(0,Vector3(.32,.68,0)); app._physics_process(1./60.)
	app.set_preset("balanced"); app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	app.set_physics_process(true)
	var started:=Time.get_ticks_usec(); var previous:=started; var samples:Array[float]=[]
	while Time.get_ticks_usec()-started<30000000:
		var elapsed:=(Time.get_ticks_usec()-started)/1000000.
		app.targets[0]=Vector3(.3*cos(elapsed*.7),.68,.3*sin(elapsed*.7)); app.target_valid[0]=true
		await process_frame
		var now:=Time.get_ticks_usec()
		if now-started>2000000: samples.append((now-previous)/1000.)
		previous=now
	var total:=0.
	for value in samples: total+=value
	samples.sort()
	var report:={"scene":"Moving phaco tool with powered local fracture/aspiration, continuous anatomical contact, live membrane/lens and UI","resolution":[1920,1080],"duration_seconds":30,"warmup_seconds":2,"adapter":RenderingServer.get_video_adapter_name(),"frames":samples.size(),"mean_frame_ms":total/samples.size(),"p95_frame_ms":samples[int(samples.size()*.95)],"mean_fps":1000.*samples.size()/total,"lens":app.lens.metrics(),"energy_exposure":app.metrics.energy_exposure,"path_length":app.metrics.path_length}
	var file:=FileAccess.open("res://reports/benchmark-active.json",FileAccess.WRITE); file.store_string(JSON.stringify(report,"  "))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://reports/professional-active.png")
	print(JSON.stringify(report)); app.queue_free(); await process_frame; quit(0 if report.lens.finite else 1)
