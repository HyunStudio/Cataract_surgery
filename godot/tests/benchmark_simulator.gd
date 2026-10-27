extends SceneTree
func _initialize() -> void: call_deferred("run")
func run() -> void:
	if DisplayServer.get_name()=="headless": quit(1); return
	root.size=Vector2i(1920,1080)
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app)
	await process_frame
	app.start_practice()
	var started:=Time.get_ticks_usec()
	var previous:=started
	var samples: Array[float]=[]
	while Time.get_ticks_usec()-started<30000000:
		await process_frame
		var now:=Time.get_ticks_usec()
		if now-started>2000000: samples.append((now-previous)/1000.)
		previous=now
	var total:=0.
	for value in samples: total+=value
	samples.sort()
	var report:={"scene":"Integrated microscope with live capsule/lens physics, dual tools, UI and monitor; no powered tissue removal","resolution":[1920,1080],"duration_seconds":30,"warmup_seconds":2,"adapter":RenderingServer.get_video_adapter_name(),"frames":samples.size(),"mean_frame_ms":total/samples.size(),"p95_frame_ms":samples[int(samples.size()*.95)],"mean_fps":1000.*samples.size()/total}
	var file:=FileAccess.open("res://reports/benchmark-simulator.json",FileAccess.WRITE); file.store_string(JSON.stringify(report,"  "))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://reports/professional-microscope.png")
	print(JSON.stringify(report)); app.queue_free(); await process_frame; quit()
