extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var saved_fps:=Engine.max_fps; Engine.max_fps=30
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app)
	await process_frame; app.start_practice()
	var started:=Time.get_ticks_usec(); var initial:float=app.clock
	while Time.get_ticks_usec()-started<3000000: await process_frame
	var wall:float=(Time.get_ticks_usec()-started)/1000000.
	var elapsed:float=app.clock-initial
	print("30fps cap: wall=",wall," simulated=",elapsed)
	check(absf(elapsed/wall-1.)<.1,"fixed-step surgery keeps real time under a 30fps render cap")
	app.toggle_pause(); var paused_clock:float=app.clock
	for i in range(20): await process_frame
	check(app.clock==paused_clock,"pause does not accumulate surgery time")
	app.toggle_pause(); started=Time.get_ticks_usec(); initial=app.clock
	while Time.get_ticks_usec()-started<1200000: await process_frame
	wall=(Time.get_ticks_usec()-started)/1000000.; elapsed=app.clock-initial
	check(absf(elapsed/wall-1.)<.1,"resume advances current fixed steps without replaying paused time")
	check(app.capsule.metrics().finite and app.lens.metrics().finite,"runtime fixed-step state remains finite")
	app.queue_free(); Engine.max_fps=saved_fps; await process_frame
	print("Real-time clock: ",failures," failures"); quit(1 if failures else 0)
