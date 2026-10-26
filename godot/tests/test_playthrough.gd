extends SceneTree
## Exercises actual viewport projection, application input, instruments and endings.
var app
var failures := 0
var capture := false
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)
func _initialize() -> void:
	capture = "--capture" in OS.get_cmdline_user_args()
	call_deferred("run")
func frame(name: String) -> void:
	app.refresh_ui()
	app._process(1./60.)
	await process_frame
	await process_frame
	if capture:
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/"+name+".png")
func point(p: Vector3) -> Vector2:
	return app.world.microscope.unproject_position(app.world.normalized_to_world(p))+app.viewport_box.global_position
func press(p: Vector3) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = true
	e.position = point(p)
	app._input(e)
func release() -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = false
	e.position = app.viewport_box.global_position+Vector2(10,10)
	app._input(e)
func move(p: Vector3, frames := 1) -> void:
	var e := InputEventMouseMotion.new()
	e.position = point(p)
	app._input(e)
	for i in range(frames): app._physics_process(1./60.)
func hold(p: Vector3, frames: int) -> void:
	release()
	press(p)
	move(p,frames)
	release()
func run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://reports"))
	app = load("res://scripts/main.gd").new()
	root.add_child(app)
	app.set_physics_process(false)
	app.set_process(false)
	# Synthetic events below are the sole input source; real desktop movement
	# during GPU capture must not interrupt this controlled test session.
	app.set_process_input(false)
	await frame("01_theatre")
	app.advance()
	app.advance()
	await frame("02_microscope_entry")
	check(app.session.phase == "ENTRY" and not app.room_view,"preparation enters actual microscope")
	var probe := Vector3(.76,.5,.12)
	check(app.pointer_tip(point(probe)).distance_to(probe)<.001,"screen-to-tool mapping agrees with rendered camera")
	# Clicking a panel cannot operate, even with a correct instrument.
	var e := InputEventMouseButton.new()
	e.pressed = true
	e.button_index = MOUSE_BUTTON_LEFT
	e.position = Vector2(60,200)
	app._input(e)
	app._physics_process(1./60.)
	check(not app.input_gate.allowed and app.session.progress == 0.,"UI click blocked")
	release()
	press(Vector3(.76,.5,.12))
	for i in range(61): move(Vector3(.76+.15*i/60.,.5,.12))
	check(app.session.phase=="CAPSULE","viewport entry drag advances")
	release()
	app.choose_tool("forceps")
	press(Vector3(.72,.5,.04))
	for i in range(193):
		var angle := TAU*i/192.
		move(Vector3(.5+cos(angle)*.22,.5+sin(angle)*.22,.04))
	check(app.session.phase=="HYDRO","viewport continuous capsule drag advances")
	release()
	await frame("03_capsule_open")
	app.choose_tool("cannula")
	hold(Vector3(.68,.5,-.02),90)
	check(app.session.phase=="PHACO","hydro tool operates at actual target")
	app.choose_tool("phaco")
	var regions: Array = app.session.eye.regions.duplicate(true)
	for i in range(8):
		hold(Vector3(regions[i].x,regions[i].y,-.08),100)
		if i==3: await frame("04_lens_removal")
	check(app.session.phase=="CORTEX","local lens removal advances")
	app.choose_tool("ia")
	for region in regions: hold(Vector3(region.x,region.y,-.06),65)
	check(app.session.phase=="IOL","cortex removal advances")
	app.choose_tool("injector")
	press(Vector3(.5,.5,.02))
	move(Vector3(.5,.5,.02),40)
	await frame("05_iol_insertion")
	release()
	press(Vector3(.5,.5,.02))
	move(Vector3(.5,.5,.02),65)
	release()
	check(app.session.phase=="ALIGN","injector delivers IOL")
	app.choose_tool("manipulator")
	hold(Vector3(.5,.5,.02),100)
	check(app.session.phase=="CLOSE","manipulator aligns IOL")
	await frame("06_iol_aligned")
	for id in ["alignment","wound","handoff"]: app.verify_check(id)
	app.advance()
	check(app.session.phase=="RECOVERY","full viewport playthrough completes")
	check(app.session.replay_log(app.session.export_log()).get("ok",false),"integrated app session replays")
	await frame("07_results")
	if capture:
		var file := FileAccess.open("res://reports/playthrough.jsonl",FileAccess.WRITE)
		file.store_string(app.session.export_log())
	print("Playthrough tests: ",failures," failures; ending=",app.session.ending)
	app.queue_free()
	await process_frame
	quit(1 if failures else 0)
