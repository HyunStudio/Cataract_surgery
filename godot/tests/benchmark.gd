extends SceneTree
## Reproducible 300-second actual Windows rendering sample, never a headless FPS claim.
var app
var samples: Array[float] = []
var started := 0
var seconds := 300.0
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("Benchmark requires a real graphics context")
		quit(1)
		return
	root.size = Vector2i(1920,1080)
	app = load("res://scripts/main.gd").new()
	root.add_child(app)
	await process_frame
	app.advance(); app.advance()
	# The input-heavy rendered playthrough is separately verified. Keep the full
	# cloudy anatomy, instruments, monitors, UI and deterministic clock running.
	app.choose_tool("knife")
	started = Time.get_ticks_usec()
	var previous := started
	while (Time.get_ticks_usec()-started)/1000000. < seconds:
		await process_frame
		var now := Time.get_ticks_usec()
		if now-started > 2000000:
			samples.append(float(now-previous)/1000.)
		previous = now
		app.tip = Vector3(.5+.2*sin(float(now-started)/1400000.),.5,.12)
	var sum := 0.
	for value in samples: sum += value
	samples.sort()
	var mean := sum/maxi(samples.size(),1)
	var report := {"engine":Engine.get_version_info().string,"adapter":RenderingServer.get_video_adapter_name(),"display":DisplayServer.get_name(),"resolution":[root.size.x,root.size.y],"duration_seconds":(Time.get_ticks_usec()-started)/1000000.,"warmup_seconds":2,"frames":samples.size(),"mean_frame_ms":mean,"p95_frame_ms":samples[mini(samples.size()-1,int(samples.size()*.95))],"mean_fps":1000./mean,"scene":"microscope ENTRY: full anatomy, idle instrument, live UI/monitor; no automated surgery","draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)}
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports"))
	var file := FileAccess.open("res://reports/benchmark.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print(JSON.stringify(report))
	app.queue_free()
	await process_frame
	quit()
