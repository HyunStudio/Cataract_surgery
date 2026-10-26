extends Control
## Application owns input/UI. ProcedureSession alone owns surgical progression.
const Session = preload("res://scripts/procedure_session.gd")
const World = preload("res://scripts/surgical_world.gd")
const InputGate = preload("res://scripts/operative_input.gd")
const Monitor = preload("res://scripts/monitor.gd")
const BG := Color("091219")
const PANEL := Color("10212a")
const TEXT := Color("e4edf0")
const DIM := Color("819da5")
const MINT := Color("82dfc2")
const GOLD := Color("edc38b")
const TOOL_IDS := ["knife","forceps","cannula","phaco","ia","injector","manipulator"]
const TOOL_NAMES := ["절개도", "전낭 집게", "수류분리 캐뉼라", "유화 핸드피스", "관류·흡인 도구", "IOL 인젝터", "위치 조정 도구"]
const STAGES := ["PREOP","PREP","ENTRY","CAPSULE","HYDRO","PHACO","CORTEX","IOL","ALIGN","CLOSE","RECOVERY"]
const NAMES := {"PREOP":"수술 전 확인", "PREP":"환자 및 수술 준비", "ENTRY":"각막 진입", "CAPSULE":"전낭 경로 형성", "HYDRO":"수정체 분리", "PHACO":"혼탁 수정체 제거", "CORTEX":"잔여 피질 정리", "IOL":"인공수정체 전달", "ALIGN":"인공수정체 정렬", "CLOSE":"최종 확인 및 인계", "RECOVERY":"수술 결과", "ABORTED":"안전 중단"}
const GOALS := {
	"PREOP":"가상 환자와 수술 부위를 확인하고 사례를 시작하세요.",
	"PREP":"준비 상태를 확인하고 현미경 시야로 진입하세요.",
	"ENTRY":"절개도를 선택하고 눈 오른쪽의 짧은 진입 경로를 따라 드래그하세요.",
	"CAPSULE":"전낭 집게로 원의 오른쪽 시작점부터 시계 방향으로 한 바퀴 드래그하세요. 놓거나 경로를 벗어나면 다시 시작합니다.",
	"HYDRO":"캐뉼라를 선택하고 표시된 분리 영역에서 작동을 유지하세요.",
	"PHACO":"유화 핸드피스로 혼탁한 각 영역을 직접 조준해 제거하세요.",
	"CORTEX":"관류·흡인 도구로 남아 있는 피질 영역을 정리하세요.",
	"IOL":"인젝터로 중앙 전달 영역에서 작동을 유지하세요.",
	"ALIGN":"위치 조정 도구를 중앙으로 이동해 렌즈를 정렬하세요.",
	"CLOSE":"렌즈 정렬·상처 상태·환자 인계 세 가지 항목을 확인하세요.",
	"RECOVERY":"전체 과정을 완료했습니다. 결과와 이벤트 기록을 확인하세요.",
	"ABORTED":"수술 조작이 종료되었습니다. 중단 사유와 기록을 확인하세요."}

var session = Session.new()
var input_gate = InputGate.new()
var world: Node3D
var viewport_3d: SubViewport
var viewport_box: SubViewportContainer
var tip := Vector3(.5,.5,.12)
var last_tip := tip
var room_view := true
var tutorial := true
var reduced_motion := false
var high_contrast := false
var audio_enabled := false
var previous_phase := "PREOP"
var selected_case := "normal"
var status_text := "가상 사례입니다. 실제 의료 훈련용으로 검증되지 않았습니다."
var phase_label: Label
var phase_number: Label
var goal_label: Label
var status_label: Label
var context_label: Label
var progress_bar: ProgressBar
var progress_label: Label
var advance_button: Button
var tool_buttons: Array[Button] = []
var check_buttons: Array[Button] = []
var monitor: Control
var depth_view: Control
var result_label: RichTextLabel
var result_panel: PanelContainer
var alert_panel: PanelContainer
var alert_label: Label
var mode_button: Button
var pause_button: Button
var top_state: Label
var case_picker: OptionButton
var view_title: Label
var footer: Label
var beep_player: AudioStreamPlayer
var beep_clock := 0.
var elapsed_frames := 0

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	build_theme()
	build_ui()
	world = World.new()
	viewport_3d.add_child(world)
	world.build()
	world.set_room_view(true)
	build_audio()
	refresh_ui()
	resized.connect(func(): input_gate.block(); session.end_stroke())

func build_theme() -> void:
	var ui_theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Malgun Gothic", "Arial"])
	ui_theme.default_font = font
	ui_theme.default_font_size = 15
	ui_theme.set_color("font_color","Label",TEXT)
	for kind in ["normal","hover","pressed","disabled","focus"]:
		var style := StyleBoxFlat.new()
		style.bg_color = Color("17343e") if kind == "hover" else Color("142a34")
		if kind == "pressed": style.bg_color = Color("245044")
		if kind == "disabled": style.bg_color = Color("101e26")
		style.border_color = Color("426770") if kind == "focus" else Color("2c4650")
		style.set_border_width_all(1)
		style.set_corner_radius_all(6)
		style.content_margin_left = 12
		style.content_margin_right = 12
		style.content_margin_top = 10
		style.content_margin_bottom = 10
		ui_theme.set_stylebox(kind,"Button",style)
	ui_theme.set_color("font_color","Button",TEXT)
	ui_theme.set_color("font_hover_color","Button",MINT)
	ui_theme.set_color("font_disabled_color","Button",Color("526974"))
	ui_theme.set_constant("separation","VBoxContainer",10)
	ui_theme.set_constant("separation","HBoxContainer",12)
	theme = ui_theme

func label(text: String, font_size := 15, color := TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size",font_size)
	l.add_theme_color_override("font_color",color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func button(text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size.y = 42
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.pressed.connect(action)
	return b

func panel(color := PANEL) -> PanelContainer:
	var p := PanelContainer.new()
	var s := StyleBoxFlat.new()
	s.bg_color = color
	s.set_corner_radius_all(10)
	s.border_color = Color("263c45")
	s.set_border_width_all(1)
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 16
	s.content_margin_bottom = 16
	p.add_theme_stylebox_override("panel",s)
	return p

func build_ui() -> void:
	var background := ColorRect.new()
	background.color = BG
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]: margin.add_theme_constant_override("margin_"+side,16)
	add_child(margin)
	var root := VBoxContainer.new()
	margin.add_child(root)
	var header := HBoxContainer.new()
	header.custom_minimum_size.y = 58
	root.add_child(header)
	var brand := VBoxContainer.new()
	brand.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(brand)
	brand.add_child(label("OPHTHOSIM",24,MINT))
	brand.add_child(label("CATARACT THEATRE    /    3D 수술 시뮬레이션",11,DIM))
	top_state = label("● 준비",13,MINT)
	header.add_child(top_state)
	mode_button = button("현미경 보기  [Tab]",func(): set_room_view(not room_view))
	header.add_child(mode_button)
	pause_button = button("일시정지  [Esc]",toggle_pause)
	header.add_child(pause_button)
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(body)
	var left_panel := panel()
	left_panel.custom_minimum_size.x = 266
	body.add_child(left_panel)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	left_panel.add_child(scroll)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(left)
	left.add_child(label("PROCEDURE",11,DIM))
	phase_number = label("01 / 10",13,MINT)
	left.add_child(phase_number)
	phase_label = label("수술 전 확인",21)
	left.add_child(phase_label)
	goal_label = label("",14,DIM)
	goal_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	goal_label.custom_minimum_size = Vector2(220,80)
	left.add_child(goal_label)
	progress_bar = ProgressBar.new()
	progress_bar.show_percentage = false
	progress_bar.custom_minimum_size.y = 5
	left.add_child(progress_bar)
	progress_label = label("",12,MINT)
	left.add_child(progress_label)
	left.add_child(HSeparator.new())
	left.add_child(label("가상 사례",12,DIM))
	case_picker = OptionButton.new()
	for title in ["표준 사례", "환자 움직임", "모니터 이상", "수정체낭 손상"]: case_picker.add_item(title)
	case_picker.item_selected.connect(func(index): start_case(["normal","movement","monitor","capsule"][index]))
	left.add_child(case_picker)
	advance_button = button("사례 확인 / 다음",advance)
	left.add_child(advance_button)
	left.add_child(HSeparator.new())
	left.add_child(label("INSTRUMENT TRAY",11,DIM))
	for i in range(TOOL_IDS.size()):
		var id: String = TOOL_IDS[i]
		var b := button("%d   %s" % [i+1,TOOL_NAMES[i]],func(): choose_tool(id))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size",14)
		b.custom_minimum_size.y = 40
		left.add_child(b)
		tool_buttons.append(b)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	left.add_child(spacer)
	left.add_child(button("새 사례 시작  [R]",func(): start_case(selected_case)))
	var center := VBoxContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(center)
	var view_head := HBoxContainer.new()
	center.add_child(view_head)
	view_title = label("OPERATING THEATRE",12,DIM)
	view_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	view_head.add_child(view_title)
	view_head.add_child(label("VIRTUAL CASE  ·  OS / LEFT EYE",11,DIM))
	viewport_box = SubViewportContainer.new()
	viewport_box.stretch = true
	viewport_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	viewport_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	viewport_box.custom_minimum_size = Vector2(360,300)
	viewport_box.mouse_filter = Control.MOUSE_FILTER_STOP
	center.add_child(viewport_box)
	viewport_3d = SubViewport.new()
	viewport_3d.size = Vector2i(900,650)
	viewport_3d.handle_input_locally = false
	viewport_3d.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport_3d.msaa_3d = Viewport.MSAA_2X
	viewport_box.add_child(viewport_3d)
	context_label = label("",13,MINT)
	context_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	context_label.custom_minimum_size.y = 32
	center.add_child(context_label)
	var depth_panel := panel(Color("0d1d26"))
	center.add_child(depth_panel)
	depth_view = Monitor.new()
	depth_view.depth_mode = true
	depth_view.custom_minimum_size.y = 154
	depth_panel.add_child(depth_view)
	var right_panel := panel()
	right_panel.custom_minimum_size.x = 248
	body.add_child(right_panel)
	var right_scroll := ScrollContainer.new()
	right_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	right_panel.add_child(right_scroll)
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right_scroll.add_child(right)
	monitor = Monitor.new()
	monitor.custom_minimum_size = Vector2(208,340)
	right.add_child(monitor)
	right.add_child(HSeparator.new())
	right.add_child(label("최종 확인",13,DIM))
	for i in range(3):
		var id: String = ["alignment","wound","handoff"][i]
		var b := button(["렌즈 정렬 확인","상처 상태 확인","환자 인계 확인"][i],func(): verify_check(id))
		b.add_theme_font_size_override("font_size",13)
		right.add_child(b)
		check_buttons.append(b)
	right.add_child(HSeparator.new())
	var tutorial_toggle := CheckButton.new()
	tutorial_toggle.text = "학습 가이드"
	tutorial_toggle.button_pressed = true
	tutorial_toggle.toggled.connect(func(value): tutorial = value)
	right.add_child(tutorial_toggle)
	var motion_toggle := CheckButton.new()
	motion_toggle.text = "움직임 최소화"
	motion_toggle.toggled.connect(func(value): reduced_motion = value)
	right.add_child(motion_toggle)
	var contrast_toggle := CheckButton.new()
	contrast_toggle.text = "고대비 표시"
	contrast_toggle.toggled.connect(func(value): high_contrast = value; refresh_ui())
	right.add_child(contrast_toggle)
	var sound_toggle := CheckButton.new()
	sound_toggle.text = "모니터 사운드"
	sound_toggle.toggled.connect(func(value): audio_enabled = value)
	right.add_child(sound_toggle)
	right.add_child(button("수술 안전 중단  [X]",func(): stop_input(); session.abort(); refresh_ui()))
	status_label = label("",12,DIM)
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(status_label)
	footer = label("도구 1–7   ·   왼쪽 드래그: 작동   ·   Shift+휠: 깊이   ·   휠: 확대   ·   Tab: 시점   ·   Space: 다음   ·   A: 경고 평가",12,DIM)
	root.add_child(footer)
	build_dialogs()

func build_dialogs() -> void:
	alert_panel = panel(Color("38272a"))
	alert_panel.custom_minimum_size = Vector2(510,225)
	alert_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	alert_panel.position -= alert_panel.custom_minimum_size*.5
	add_child(alert_panel)
	var av := VBoxContainer.new()
	alert_panel.add_child(av)
	av.add_child(label("!   PROCEDURE ON HOLD",13,GOLD))
	alert_label = label("",18)
	alert_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	alert_label.custom_minimum_size.x = 470
	av.add_child(alert_label)
	av.add_child(label("도구 작동이 잠겼습니다. 상태를 평가하세요.",14,DIM))
	av.add_child(button("상태 평가 / 도움 요청  [A]",assess_alert))
	av.add_child(button("안전 중단",func(): stop_input(); session.abort(); refresh_ui()))
	result_panel = panel(Color("102831"))
	result_panel.custom_minimum_size = Vector2(560,460)
	result_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	result_panel.position -= result_panel.custom_minimum_size*.5
	add_child(result_panel)
	var rv := VBoxContainer.new()
	result_panel.add_child(rv)
	rv.add_child(label("CASE DEBRIEF",12,MINT))
	result_label = RichTextLabel.new()
	result_label.bbcode_enabled = true
	result_label.custom_minimum_size = Vector2(520,330)
	result_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	rv.add_child(result_label)
	rv.add_child(button("세션 기록 저장  [S]",save_session))
	rv.add_child(button("수술 결과 관찰",func(): result_panel.hide()))
	rv.add_child(button("새 사례 시작  [R]",func(): start_case(selected_case)))

func start_case(id: String) -> void:
	stop_input()
	selected_case = id
	session.reset(id,7)
	previous_phase = session.phase
	tip = Vector3(.5,.5,.12)
	last_tip = tip
	status_text = "새 가상 사례를 시작했습니다. 수술 부위: 좌안."
	set_room_view(true)
	refresh_ui()

func stop_input() -> void:
	input_gate.block()
	session.end_stroke()

func set_room_view(value: bool) -> void:
	stop_input()
	room_view = value
	if world: world.set_room_view(value)
	if mode_button: mode_button.text = "현미경 보기  [Tab]" if value else "수술실 보기  [Tab]"
	if view_title: view_title.text = "OPERATING THEATRE" if value else "OPERATING MICROSCOPE  /  LIVE 3D"

func choose_tool(id: String) -> void:
	stop_input()
	if session.select_tool(id):
		status_text = "도구 선택: " + TOOL_NAMES[TOOL_IDS.find(id)]
	refresh_ui()

func advance() -> void:
	stop_input()
	if session.confirm():
		if session.phase == "ENTRY": set_room_view(false)
	else:
		status_text = "현재 단계의 작업과 필수 확인을 먼저 완료하세요."
	phase_changed()
	refresh_ui()

func verify_check(id: String) -> void:
	stop_input()
	if session.has_method("verify"):
		session.verify(id)
	phase_changed()
	refresh_ui()

func toggle_pause() -> void:
	stop_input()
	if session.alert.is_empty() and session.ending.is_empty():
		session.toggle_pause()
	refresh_ui()

func assess_alert() -> void:
	stop_input()
	session.assess()
	status_text = "상태 평가가 기록되었습니다. 새로 클릭해 작업을 재개하세요."
	phase_changed()
	refresh_ui()

func operative_rect() -> Rect2:
	return viewport_box.get_global_rect() if viewport_box else Rect2()

func pointer_inside(point: Vector2) -> bool:
	return operative_rect().has_point(point) and not room_view and not alert_panel.visible and not result_panel.visible

func pointer_tip(point: Vector2) -> Vector3:
	var local := point-viewport_box.global_position
	var camera: Camera3D = world.microscope
	var ray_origin := camera.project_ray_origin(local)
	var ray_direction := camera.project_ray_normal(local)
	var plane := Plane(Vector3.UP,.8+tip.z)
	var hit = plane.intersects_ray(ray_origin,ray_direction)
	if hit == null: return Vector3(-1,-1,tip.z)
	return world.world_to_normalized(hit)

func _input(event: InputEvent) -> void:
	if not is_instance_valid(world): return
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				input_gate.press(pointer_inside(event.position))
				if input_gate.allowed:
					tip = pointer_tip(event.position)
					last_tip = tip
					session.begin_stroke()
			else:
				input_gate.release()
				session.end_stroke()
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			stop_input()
		elif event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN] and event.pressed and operative_rect().has_point(event.position):
			stop_input()
			var direction := 1. if event.button_index == MOUSE_BUTTON_WHEEL_UP else -1.
			if event.shift_pressed:
				tip.z = clampf(tip.z+direction*.02,-.28,.28)
			else:
				world.microscope.size = clampf(world.microscope.size-direction*.3,2.8,6.4)
	if event is InputEventMouseMotion:
		if pointer_inside(event.position): tip = pointer_tip(event.position)
		else: stop_input()
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode in [KEY_ESCAPE,KEY_TAB,KEY_SPACE,KEY_R,KEY_X,KEY_A,KEY_S,KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7,KEY_Q,KEY_E]:
			get_viewport().set_input_as_handled()
		match event.keycode:
			KEY_ESCAPE: toggle_pause()
			KEY_TAB: set_room_view(not room_view)
			KEY_SPACE: advance()
			KEY_R: start_case(selected_case)
			KEY_X: stop_input(); session.abort(); refresh_ui()
			KEY_A: assess_alert()
			KEY_S: save_session()
			KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7:
				choose_tool(TOOL_IDS[event.keycode-KEY_1])
			KEY_Q: stop_input(); tip.z = clampf(tip.z-.02,-.28,.28)
			KEY_E: stop_input(); tip.z = clampf(tip.z+.02,-.28,.28)

func _notification(what: int) -> void:
	if what in [MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT,NOTIFICATION_WM_WINDOW_FOCUS_OUT] and is_instance_valid(session):
		stop_input()

func _physics_process(delta: float) -> void:
	if not world: return
	if input_gate.allowed and not room_view and not session.paused and session.alert.is_empty():
		var samples: Array[Vector3] = input_gate.sweep(last_tip,tip)
		for sample in samples:
			var old: String = session.phase
			session.act(sample,delta/maxi(samples.size(),1))
			if session.phase != old or not session.alert.is_empty():
				stop_input()
				break
	last_tip = tip
	session.tick(delta)
	phase_changed()
	beep_clock += delta
	if beep_clock > .81:
		beep_clock = 0.
		if audio_enabled and not session.paused: beep_player.play()
	refresh_ui()

func phase_changed() -> void:
	if previous_phase == session.phase: return
	stop_input()
	previous_phase = session.phase
	var depth: float = session.target_depth()
	tip.z = depth
	last_tip = tip
	status_text = "새 단계: %s. 도구와 깊이를 확인한 뒤 새로 클릭하세요." % NAMES.get(session.phase,session.phase)
	if not session.ending.is_empty(): result_panel.show()

func _process(_delta: float) -> void:
	if not world: return
	var snapshot: Dictionary = session.snapshot()
	snapshot["tutorial"] = tutorial
	snapshot["reduced_motion"] = reduced_motion
	snapshot["high_contrast"] = high_contrast
	world.update_state(snapshot,tip,session.tool,input_gate.allowed and not room_view)
	monitor.state = snapshot
	monitor.high_contrast = high_contrast
	monitor.queue_redraw()
	depth_view.state = snapshot
	depth_view.tip = tip
	depth_view.queue_redraw()
	elapsed_frames += 1

func refresh_ui() -> void:
	if not phase_label: return
	var snap: Dictionary = session.snapshot()
	var index: int = STAGES.find(session.phase)
	phase_number.text = "%02d / 10" % mini(index+1,10) if index >= 0 else "SAFE STOP"
	phase_label.text = NAMES.get(session.phase,session.phase)
	goal_label.text = GOALS.get(session.phase,"")
	progress_bar.value = clampf(float(snap.get("progress",0.))*100.,0.,100.)
	progress_label.text = "단계 진행  %d %%" % progress_bar.value
	status_label.text = status_text
	status_label.modulate = Color.WHITE if high_contrast else Color(.9,.95,1.)
	var expected: String = session.expected_tool()
	var expected_index := TOOL_IDS.find(expected)
	var expected_name: String = TOOL_NAMES[expected_index] if expected_index >= 0 else "준비 확인"
	var depth_ok := absf(tip.z-session.target_depth()) <= .035
	var current_name: String = TOOL_NAMES[TOOL_IDS.find(session.tool)] if session.tool in TOOL_IDS else "도구 미선택"
	if room_view:
		context_label.text = "수술실 관찰 중  ·  현미경 보기로 전환하면 도구를 조작할 수 있습니다."
	elif not session.ending.is_empty(): context_label.text = "수술 종료  ·  세션 기록과 조직 상태를 확인하세요."
	else:
		context_label.text = "%s  /  필요: %s  ·  깊이 %+.2f / %+.2f  %s" % [current_name,expected_name,tip.z,session.target_depth(),"✓" if depth_ok else "[깊이 조정]"]
	context_label.add_theme_color_override("font_color",MINT if depth_ok and session.tool == expected else GOLD)
	advance_button.visible = session.phase in ["PREOP","PREP","CLOSE"]
	advance_button.text = "수술 부위·사례 확인" if session.phase == "PREOP" else ("준비 완료 / 현미경 진입" if session.phase == "PREP" else "최종 확인 완료")
	case_picker.disabled = session.phase != "PREOP"
	for i in range(tool_buttons.size()):
		var selected: bool = TOOL_IDS[i] == session.tool
		tool_buttons[i].text = "%s%d   %s" % ["● " if selected else "",i+1,TOOL_NAMES[i]]
		tool_buttons[i].add_theme_color_override("font_color",MINT if selected else (GOLD if tutorial and TOOL_IDS[i] == expected else TEXT))
		tool_buttons[i].disabled = session.paused or not session.ending.is_empty()
	var checks: Dictionary = snap.get("final_checks",{})
	for i in range(check_buttons.size()):
		check_buttons[i].disabled = session.phase != "CLOSE" or checks.get(["alignment","wound","handoff"][i],false)
	alert_panel.visible = not session.alert.is_empty() and session.ending.is_empty()
	alert_label.text = {"movement":"환자 움직임 감지", "monitor":"환자 모니터 상태 변화", "capsule":"수정체낭 상태 변화"}.get(session.alert,session.alert)
	top_state.text = "● 안전 중단" if not session.ending.is_empty() and session.phase == "ABORTED" else ("Ⅱ 일시정지" if session.paused else "● " + ("수술 완료" if session.phase == "RECOVERY" else "실시간 가상 사례"))
	pause_button.text = "계속하기  [Esc]" if session.paused else "일시정지  [Esc]"
	if not session.ending.is_empty():
		var lines := "[font_size=28]%s[/font_size]\n\n" % ("수술 시뮬레이션 완료" if session.phase == "RECOVERY" else "안전 중단")
		lines += "[color=#82dfc2]게임 평가  %s / 100[/color]\n" % snap.get("score",0)
		lines += "진행 시간  %.1f 초   ·   조작 오류  %s\n\n" % [float(snap.get("tick",0))/60.,str(snap.get("errors",0))]
		var eye: Dictionary = snap.get("eye",{})
		lines += "혼탁 제거  %d %%\n피질 정리  %d %%\nIOL 중심 정렬  %d %%\n\n" % [roundi((1.-float(eye.get("opacity",1.)))*100.),roundi((1.-float(eye.get("cortex",1.)))*100.),roundi(float(eye.get("iol_alignment",0.))*100.)]
		lines += "단계 완료·잔여물·렌즈 정렬·조작 오류를 바탕으로 한 게임 내 평가입니다. 실제 술기 능력을 의미하지 않습니다.\n"
		lines += "\n기록 이벤트  %d개  /  버전 2 의미 입력 리플레이" % session.events.size()
		result_label.text = lines
	else: result_panel.hide()

func save_session() -> void:
	if session.ending.is_empty():
		status_text = "사례 종료 후 기록을 내보낼 수 있습니다."
		return
	var raw: String = session.export_log()
	if raw.is_empty():
		status_text = "기록 저장 불가: " + session.export_error
		refresh_ui()
		return
	var name := "user://case_%s_%d.jsonl" % [selected_case,Time.get_unix_time_from_system()]
	var file := FileAccess.open(name,FileAccess.WRITE)
	if file:
		file.store_string(raw)
		status_text = "저장 완료: " + ProjectSettings.globalize_path(name)
	else: status_text = "기록 저장 실패: 폴더 권한과 디스크 공간을 확인하세요."
	refresh_ui()

func build_audio() -> void:
	beep_player = AudioStreamPlayer.new()
	add_child(beep_player)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = 22050
	var bytes := PackedByteArray()
	bytes.resize(2205*2)
	for i in range(2205):
		var envelope := sin(float(i)/2205.*PI)
		var value := int(sin(float(i)/22050.*TAU*880.)*envelope*2200.)
		bytes.encode_s16(i*2,value)
	stream.data = bytes
	beep_player.stream = stream
