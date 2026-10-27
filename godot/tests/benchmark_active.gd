extends SceneTree
## Actual powered, moving-tool workload; separate from idle microscope samples.
func _initialize()->void: call_deferred("run")
func run()->void:
	if DisplayServer.get_name()=="headless": quit(1); return
	root.size=Vector2i(1920,1080)
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app)
	app.set_physics_process(false); app.set_process_input(false)
	await process_frame; app.start_practice(); app.choose_tool("knife")
	for p in [Vector3(1.32,.80,0),Vector3(1.32,.65,0),Vector3(1.20,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.grip_down=true
	for i in range(100):
		var a:=TAU*i/99.
		app._set_tip(0,Vector3(.57*cos(a),app.geometry.bag_front(.57)-.005,.57*sin(a))); app._physics_process(1./60.)
	app.release_controls()
	for p in [Vector3(.57,.70,0),Vector3(1.32,.52,0),Vector3(1.32,.95,0),Vector3(1.95,.95,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.choose_tool("phaco")
	if app.hand_tools[0]!="phaco": push_error("active benchmark failed exterior tool exchange"); quit(1); return
	for p in [Vector3(1.32,.8,0),Vector3(1.32,.65,0),Vector3(.9,.68,0),Vector3(0,.75,0),Vector3(.57,.18,0)]:
		app._set_tip(0,p); app._physics_process(1./60.)
	app.set_preset("balanced"); app.set_machine("energy",1.); app.set_machine("suction",1.); app.set_machine("inflow",1.)
	app.handle_pedal(false,false,true); app.handle_pedal(true,false,true)
	app.set_physics_process(true)
	var physics_started:float=app.clock
	var started:=Time.get_ticks_usec(); var previous:=started; var samples:Array[float]=[]
	var sampled_physics_start:=0.; var sampled_wall_start:=0
	while Time.get_ticks_usec()-started<30000000:
		var elapsed:=(Time.get_ticks_usec()-started)/1000000.
		app.targets[0]=Vector3(.3*cos(elapsed*.7),.32*sin(elapsed*.5),.3*sin(elapsed*.7)); app.target_valid[0]=true
		await process_frame
		var now:=Time.get_ticks_usec()
		if now-started>2000000:
			if sampled_wall_start==0: sampled_wall_start=now; sampled_physics_start=app.clock
			samples.append((now-previous)/1000.)
		previous=now
	var total:=0.
	for value in samples: total+=value
	samples.sort()
	var report:={"controls":app.machine.duplicate(),"tip":[app.rigs[0].tip.x,app.rigs[0].tip.y,app.rigs[0].tip.z],"tissue_access":app.lens.tissue_access,"membrane_broken_edges":app.capsule.metrics().broken_edges,"retained_detached_area":app.capsule.metrics().retained_detached_area,"extracted_flaps":app.capsule.metrics().extracted_flaps,"case_alert":app.director.snapshot().alert,"scene":"Dimensioned volumetric eye, full corneal shell, moving powered phaco, continuous tip contact, live membrane/lens and UI","resolution":[1920,1080],"duration_seconds":30,"warmup_seconds":2,"adapter":RenderingServer.get_video_adapter_name(),"frames":samples.size(),"mean_frame_ms":total/samples.size(),"p95_frame_ms":samples[int(samples.size()*.95)],"mean_fps":1000.*samples.size()/total,"lens":app.lens.metrics(),"energy_exposure":app.metrics.energy_exposure,"path_length":app.metrics.path_length}
	report["simulated_seconds"]=app.clock-physics_started
	report["wall_seconds"]=(Time.get_ticks_usec()-started)/1000000.
	report["simulation_wall_ratio"]=report.simulated_seconds/report.wall_seconds
	report["physics_catchup_limit"]=Engine.max_physics_steps_per_frame
	report["sampled_simulation_wall_ratio"]=(app.clock-sampled_physics_start)/((previous-sampled_wall_start)/1000000.)
	var file:=FileAccess.open("res://reports/benchmark-active.json",FileAccess.WRITE); file.store_string(JSON.stringify(report,"  "))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://reports/professional-active.png")
	print(JSON.stringify(report)); app.queue_free(); await process_frame; quit(0 if report.lens.finite and report.lens.removed_mass>.01 and report.case_alert=="" and report.simulation_wall_ratio>.95 and report.sampled_simulation_wall_ratio>.98 else 1)
