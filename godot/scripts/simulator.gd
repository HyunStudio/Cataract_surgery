extends Control
## Research numerical workbench. No phase timer, target completion, or game score.
const Capsule = preload("res://scripts/capsule_solver.gd")
const Lens = preload("res://scripts/lens_fluid_solver.gd")
const Rig = preload("res://scripts/instrument_rig.gd")
const World = preload("res://scripts/surgical_world.gd")
const UISkinSource = preload("res://scripts/main.gd")
const InputGate = preload("res://scripts/operative_input.gd")
const IDS := ["forceps","knife","phaco","ia","cannula","injector","manipulator"]
const LABELS := ["집게 / 견인","절개도 / 국소 절단","유화 프로브","관류·흡인","관류 캐뉼라","IOL 인젝터 (표시)","조작 기구"]
var capsule = Capsule.new()
var lens = Lens.new()
var rigs: Array = [Rig.new(),Rig.new()]
var hand_tools := ["forceps","phaco"]
var selected := 0
var grip_down := false
var pedal_down := false
var pedal_gate = InputGate.new()
var paused := false
var wireframe := false
var target_plane := .82
var world
var viewport_3d: SubViewport
var viewport_box: SubViewportContainer
var membrane: MeshInstance3D
var lens_display: MultiMeshInstance3D
var tool_models: Array = []
var diagnostics: Label
var tool_status: Label
var explanation: Label
var hand_button: Button
var capsule_material: StandardMaterial3D
var wire_display: MeshInstance3D
var slider_values: Dictionary = {}
var clock := 0.
var samples: Array = []

func _ready() -> void:
	# A slow research solver must not queue eight stale mechanical updates
	# before displaying fresh input. Simulation time remains explicit below.
	Engine.max_physics_steps_per_frame = 1
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var skin = UISkinSource.new()
	skin.build_theme()
	theme = skin.theme
	skin.free()
	rigs[1].portal = Vector3(-1.44,.86,.25)
	rigs[1].aim_at(Vector3(0,.68,0))
	rigs[0].aim_at(Vector3(0,.82,0))
	for rig in rigs: rig.set_insertion(.12)
	build_ui()
	build_physics_display()
	resized.connect(release_controls)

func text(value: String, size_px := 15, color := Color("e4edf0")) -> Label:
	var node := Label.new()
	node.text = value
	node.add_theme_font_size_override("font_size",size_px)
	node.add_theme_color_override("font_color",color)
	return node
func action(value: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = value
	b.custom_minimum_size.y = 42
	b.pressed.connect(callback)
	return b
func build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = Color("08151c")
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]: margin.add_theme_constant_override("margin_"+side,18)
	add_child(margin)
	var all := VBoxContainer.new()
	margin.add_child(all)
	all.add_child(text("OPHTHOSIM  /  SURGICAL SIMULATION",24,Color("82dfc2")))
	all.add_child(text("물리 기반 실험 모드 · 비보정 연구 모델 · 임상적 정확성 미검증",13,Color("edc38b")))
	var row := HBoxContainer.new()
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	all.add_child(row)
	var left := VBoxContainer.new()
	left.custom_minimum_size.x = 240
	row.add_child(left)
	left.add_child(text("INSTRUMENTS",12,Color("819da5")))
	hand_button = action("왼손 기구 선택  [Tab]",switch_hand)
	left.add_child(hand_button)
	for i in range(IDS.size()):
		var id: String = IDS[i]
		left.add_child(action("%d  %s" % [i+1,LABELS[i]],func(): release_controls(); hand_tools[selected]=id))
	left.add_child(HSeparator.new())
	add_slider(left,"inflow","관류 유입 (연구값)",0.)
	add_slider(left,"suction","흡인 (연구값)",.35)
	add_slider(left,"energy","유화 작용 (연구값)",.25)
	left.add_child(action("조직 모델 초기화  [R]",reset_simulation))
	left.add_child(action("모델 격자  [F2]",func(): wireframe=not wireframe))
	left.add_child(action("일시정지  [Esc]",func(): release_controls(); paused=not paused))
	left.add_child(action("수치 기록 저장  [S]",export_observations))
	var center := VBoxContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(center)
	viewport_box = SubViewportContainer.new()
	viewport_box.stretch = true
	viewport_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	viewport_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	viewport_box.mouse_filter = Control.MOUSE_FILTER_STOP
	center.add_child(viewport_box)
	viewport_3d = SubViewport.new()
	viewport_3d.size = Vector2i(900,700)
	viewport_3d.msaa_3d = Viewport.MSAA_2X
	viewport_box.add_child(viewport_3d)
	world = World.new()
	viewport_3d.add_child(world)
	world.build()
	world.set_room_view(false)
	world.update_state({"phase":"PHACO","tutorial":false,"eye":{"opacity":0.,"cortex":0.}},Vector3(.5,.5,0),"",false)
	world.find_child("CapsuleMembrane",true,false).hide()
	world.target.hide()
	tool_status = text("",14,Color("82dfc2"))
	center.add_child(tool_status)
	explanation = text("마우스: 기구 축 방향 · 휠: 삽입 깊이 · Q/E: 상하 각도\n왼쪽 누름: 집게 견인/절개 · Space: 유화·흡인 페달 · Shift+휠: 현미경 확대",13,Color("819da5"))
	center.add_child(explanation)
	var right := VBoxContainer.new()
	right.custom_minimum_size.x = 250
	row.add_child(right)
	right.add_child(text("NUMERICAL OBSERVATIONS",12,Color("819da5")))
	diagnostics = text("",15)
	right.add_child(diagnostics)
	var notes := text("진행률·게임 점수를 사용하지 않습니다.\n\n접촉·견인·변형률·파열과 파편 이동을 수치 모델에서 계산합니다.\n\n압력·유량 표시는 단일 구획 연구값이며 실제 안압이나 수술 장비 설정값이 아닙니다.\n\nIOL 재료역학·정밀 광학·조직 물성 보정은 아직 구현되지 않았습니다.",13,Color("819da5"))
	notes.custom_minimum_size.x = 245
	notes.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(notes)

func add_slider(parent: VBoxContainer, key: String, caption: String, value: float) -> void:
	parent.add_child(text(caption,13,Color("819da5")))
	var slider := HSlider.new()
	slider.min_value = 0.
	slider.max_value = 1.
	slider.step = .01
	slider.value = value
	parent.add_child(slider)
	slider_values[key] = value
	slider.value_changed.connect(func(v): slider_values[key]=v)

func build_physics_display() -> void:
	membrane = MeshInstance3D.new()
	membrane.name = "ComputedCapsuleSurface"
	capsule_material = StandardMaterial3D.new()
	capsule_material.albedo_color = Color(.78,.9,.92,.42)
	capsule_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	capsule_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	capsule_material.roughness = .22
	membrane.material_override = capsule_material
	world.add_child(membrane)
	wire_display = MeshInstance3D.new()
	var wire_mat := StandardMaterial3D.new()
	wire_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	wire_mat.albedo_color = Color("75d8bf")
	wire_display.material_override = wire_mat
	world.add_child(wire_display)
	lens_display = MultiMeshInstance3D.new()
	lens_display.name = "ComputedLensParticles"
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	var sphere := SphereMesh.new()
	sphere.radius = .12
	sphere.height = .24
	sphere.radial_segments = 12
	sphere.rings = 6
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("cbb074")
	mat.roughness = .48
	sphere.material = mat
	multi.mesh = sphere
	multi.instance_count = lens.particles.size()
	lens_display.multimesh = multi
	world.add_child(lens_display)
	for hand in range(2):
		var models := {}
		for id in IDS:
			var model: Node3D = world.tools[id].duplicate()
			model.visible = false
			world.add_child(model)
			models[id] = model
		tool_models.append(models)
	update_geometry()

func release_controls() -> void:
	grip_down = false
	pedal_down = false
	pedal_gate.block()
	capsule.release()
func handle_pedal(pressed: bool, echo: bool, inside: bool) -> void:
	if echo: return
	if pressed: pedal_gate.press(inside and not paused)
	else: pedal_gate.release()
	pedal_down = pedal_gate.allowed
func switch_hand() -> void:
	release_controls()
	selected = 1-selected
	hand_button.text = ("왼손" if selected==0 else "오른손")+" 기구 선택  [Tab]"
func reset_simulation() -> void:
	release_controls()
	capsule.reset()
	lens.reset()
	clock = 0.
	samples.clear()
	if membrane: update_geometry()

func _input(event: InputEvent) -> void:
	if not viewport_box: return
	if event is InputEventMouseMotion and viewport_box.get_global_rect().has_point(event.position):
		var local: Vector2 = event.position-viewport_box.global_position
		var origin: Vector3 = world.microscope.project_ray_origin(local)
		var direction: Vector3 = world.microscope.project_ray_normal(local)
		var hit = Plane(Vector3.UP,target_plane).intersects_ray(origin,direction)
		if hit!=null and not grip_down: rigs[selected].aim_at(hit)
		elif hit!=null: rigs[selected].aim_at(hit)
	elif event is InputEventMouseMotion:
		release_controls()
	if event is InputEventMouseButton:
		var inside: bool = viewport_box.get_global_rect().has_point(event.position)
		if event.button_index == MOUSE_BUTTON_LEFT:
			grip_down = event.pressed and inside
			if not grip_down: capsule.release()
		elif inside and event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			var sign_value := 1. if event.button_index == MOUSE_BUTTON_WHEEL_UP else -1.
			if event.shift_pressed: world.microscope.size = clampf(world.microscope.size-sign_value*.2,2.8,6.)
			else: rigs[selected].set_insertion(rigs[selected].insertion+sign_value*.025)
		elif event.button_index==MOUSE_BUTTON_RIGHT and event.pressed: release_controls()
	if event is InputEventKey:
		if event.keycode==KEY_SPACE:
			handle_pedal(event.pressed,event.echo,viewport_box.get_global_rect().has_point(get_global_mouse_position()))
			get_viewport().set_input_as_handled()
		if event.pressed and not event.echo:
			get_viewport().set_input_as_handled()
			match event.keycode:
				KEY_TAB: switch_hand()
				KEY_R: reset_simulation()
				KEY_ESCAPE: release_controls(); paused=not paused
				KEY_F2: wireframe=not wireframe
				KEY_S: export_observations()
				KEY_Q: rigs[selected].adjust_pitch(-.025)
				KEY_E: rigs[selected].adjust_pitch(.025)
				KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7:
					release_controls(); hand_tools[selected]=IDS[event.keycode-KEY_1]

func _notification(what: int) -> void:
	if what in [MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT,NOTIFICATION_WM_WINDOW_FOCUS_OUT]: release_controls()

func _physics_process(dt: float) -> void:
	if paused or not world: return
	var tip: Vector3 = rigs[selected].tip
	var id: String = hand_tools[selected]
	lens.inflow = slider_values.get("inflow",0.)
	lens.suction = slider_values.get("suction",.35)
	lens.energy = slider_values.get("energy",.25)
	lens.passive_tips = PackedVector3Array([rigs[1-selected].tip])
	lens.step(dt,tip,pedal_down and id=="phaco",pedal_down and id in ["phaco","ia"])
	capsule.pressure_load = .3*(float(lens.metrics().pressure)-1.)
	capsule.passive_tips = PackedVector3Array([rigs[1-selected].tip])
	capsule.step(dt,tip,.09,grip_down and id=="forceps",grip_down and id=="knife")
	clock += dt
	if samples.size()<18000 and (samples.is_empty() or clock-float(samples[-1].time)>=.1):
		samples.append({"time":clock,"tip":[tip.x,tip.y,tip.z],"capsule":capsule.metrics(),"lens":lens.metrics()})
	update_geometry()

func update_geometry() -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = capsule.positions
	arrays[Mesh.ARRAY_INDEX] = capsule.triangles
	var normals := PackedVector3Array()
	normals.resize(capsule.positions.size())
	normals.fill(Vector3.ZERO)
	for i in range(0,capsule.triangles.size(),3):
		var a: int = capsule.triangles[i]
		var b: int = capsule.triangles[i+1]
		var c: int = capsule.triangles[i+2]
		var area_normal: Vector3 = (capsule.positions[b]-capsule.positions[a]).cross(capsule.positions[c]-capsule.positions[a])
		normals[a] += area_normal
		normals[b] += area_normal
		normals[c] += area_normal
	for i in range(normals.size()): normals[i]=normals[i].normalized() if normals[i].length_squared()>.00000001 else Vector3.UP
	arrays[Mesh.ARRAY_NORMAL] = normals
	var surface := ArrayMesh.new()
	if capsule.triangles.size()>0: surface.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	membrane.mesh = surface
	wire_display.visible = wireframe
	if wireframe:
		var lines := ImmediateMesh.new()
		lines.surface_begin(Mesh.PRIMITIVE_LINES)
		for edge in capsule.edges:
			if edge.active:
				lines.surface_add_vertex(capsule.positions[edge.a]+Vector3(0,.003,0))
				lines.surface_add_vertex(capsule.positions[edge.b]+Vector3(0,.003,0))
		lines.surface_end()
		wire_display.mesh = lines
	for i in range(lens.particles.size()):
		var particle: Dictionary = lens.particles[i]
		var basis := Basis.IDENTITY if particle.active else Basis.IDENTITY.scaled(Vector3.ZERO)
		lens_display.multimesh.set_instance_transform(i,Transform3D(basis,particle.position))
	for hand in range(2):
		for id in tool_models[hand]:
			var model: Node3D = tool_models[hand][id]
			model.visible = id==hand_tools[hand]
			if model.visible:
				model.position = rigs[hand].tip
				# Existing models extend +X from their origin-tip. Rotate shaft
				# back along the actual constrained axis toward the incision.
				var toward_portal: Vector3 = -rigs[hand].axis
				var side := toward_portal.cross(Vector3.UP).normalized()
				if side.length()<.01: side=Vector3.FORWARD
				var shaft_frame := Basis(toward_portal,side.cross(toward_portal).normalized(),side)
				var local_shaft := Vector3(1.55,.52,.20).normalized()
				model.basis = shaft_frame*Basis(Quaternion(local_shaft,Vector3.RIGHT))
	var cm: Dictionary = capsule.metrics()
	var lm: Dictionary = lens.metrics()
	diagnostics.text = "전낭 막 정점  %d\n남은 삼각형  %d\n끊어진 연결  %d\n최대 인장 변형률  %.3f\n집게 접점  %s\n\n수정체 질량  %.3f\n흡인된 질량  %.3f\n분리 파편  %d\n\n전방 체적  %.3f\n구획 압력  %.3f\n유입 / 유출  %.3f / %.3f\n\n계산 시간  %.1f s" % [capsule.positions.size(),capsule.triangles.size()/3,cm.broken_edges,cm.max_strain,str(cm.grasped),lm.remaining_mass,lm.removed_mass,lm.fragments,lm.volume,lm.pressure,lm.inflow,lm.outflow,clock]
	tool_status.text = "%s  ·  %s  ·  삽입 %.3f  ·  팁 Y %.3f  ·  %s" % ["왼손" if selected==0 else "오른손",hand_tools[selected],rigs[selected].insertion,rigs[selected].tip.y,"일시정지" if paused else ("작동" if grip_down or pedal_down else "대기")]

func export_observations() -> void:
	var file := FileAccess.open("user://physics_observations.json",FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify({"model":"uncalibrated-research-1","samples":samples}))
		explanation.text = "수치 관측 기록: "+ProjectSettings.globalize_path("user://physics_observations.json")
