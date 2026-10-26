extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		push_error(message)
func hazard_setup(id: String) -> void:
	app.start_case(id)
	app.advance(); app.advance()
	var s = app.session
	s.end_stroke(); s.select_tool("knife"); s.begin_stroke()
	for i in range(31): s.act(Vector3(.76+.15*i/30.,.5,.12),1./60.)
	s.end_stroke(); s.select_tool("forceps"); s.begin_stroke()
	for i in range(97):
		var a := TAU*i/96.
		s.act(Vector3(.5+cos(a)*.22,.5+sin(a)*.22,.04),1./60.)
	s.end_stroke(); s.select_tool("cannula"); s.begin_stroke()
	for i in range(90): s.act(Vector3(.68,.5,-.02),1./60.)
	app.phase_changed()
	app.refresh_ui()
var app
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var script = load("res://scripts/main.gd")
	if script == null:
		push_error("game application missing")
		quit(1)
		return
	app = script.new()
	root.add_child(app)
	await process_frame
	check(app.session.phase == "PREOP", "app starts with preoperative case review")
	check(app.viewport_3d.get_child_count() > 0, "operative viewport contains actual 3D world")
	app.advance_button.grab_focus()
	var shortcut := InputEventKey.new()
	shortcut.keycode = KEY_SPACE
	shortcut.pressed = true
	Input.parse_input_event(shortcut)
	await process_frame
	check(app.session.phase == "PREP", "Space shortcut advances exactly once despite focused button")
	app.start_case("normal")
	for child in app.find_children("*", "Button", true, false):
		if child.text.begins_with("새 사례 시작"):
			child.grab_focus()
	Input.parse_input_event(shortcut)
	shortcut = shortcut.duplicate()
	shortcut.pressed = false
	Input.parse_input_event(shortcut)
	await process_frame
	check(app.session.phase == "PREP", "Space release must not activate a focused restart button")
	app.input_gate.press(true)
	app.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	check(not app.input_gate.allowed, "application focus loss disarms surgery")
	app.input_gate.release()
	app.start_case("movement")
	check(app.session.case_id == "movement", "case selector selects real scenario")
	app.input_gate.press(true)
	app.set_room_view(false)
	check(not app.input_gate.allowed, "camera switching clears held operation")
	app.toggle_pause()
	check(app.session.paused, "pause stops procedure")
	check(not app.input_gate.allowed, "pause clears held operation")
	check(app.get_viewport_rect().size.x > 0, "application lays out in viewport")
	for hazard in ["movement","monitor","capsule"]:
		hazard_setup(hazard)
		check(app.alert_panel.visible,"hazard shows blocking UI: "+hazard)
		check(not app.pointer_inside(app.operative_rect().get_center()),"hazard UI blocks operative input")
		app.assess_alert()
		check(app.session.ending == "safe_abort" if hazard=="capsule" else app.session.alert.is_empty(),"assessment routes real hazard: "+hazard)
		if hazard=="capsule": check(app.result_panel.visible,"safe abort shows debrief")
	app.queue_free()
	await process_frame
	print("Integration tests: ", failures, " failures")
	quit(1 if failures else 0)
