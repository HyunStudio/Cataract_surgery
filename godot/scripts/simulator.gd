extends Control
## Specialist simulation game: numerical tissue, instrument constraints and evidence-based cases.
const FlapBoundary=preload("res://scripts/flap_boundary.gd")
var _flap_boundary:RefCounted
var _flap_revision:=-1
const Segment=preload("res://scripts/anterior_segment.gd")
var anatomical:=true
var geometry:RefCounted
const Capsule = preload("res://scripts/capsule_solver.gd")
const Lens = preload("res://scripts/lens_fluid_solver.gd")
const Rig = preload("res://scripts/instrument_rig.gd")
const IOL = preload("res://scripts/iol_dynamics.gd")
const Director = preload("res://scripts/case_director.gd")
const Injury=preload("res://scripts/tissue_injury.gd")
const Contact = preload("res://scripts/anatomy_contact.gd")
const ToolPath=preload("res://scripts/instrument_path.gd")
const BladeSweep=preload("res://scripts/blade_sweep.gd")
const RigidBody=preload("res://scripts/pivot_body_contact.gd")
var _rigid_body=RigidBody.new()
var _body_poses:Array=[{},{}]
var _resolved_grips:=[false,false]
const TIP_RADIUS:=.01
const Incision = preload("res://scripts/incision_model.gd")
const Recording = preload("res://scripts/case_recording.gd")
const Display = preload("res://scripts/surgical_display.gd")
const Interface = preload("res://scripts/simulation_ui.gd")
const InputGate = preload("res://scripts/operative_input.gd")
const PhysicsTransaction=preload("res://scripts/surgical_transaction.gd")
const IDS := ["knife","forceps","cannula","phaco","ia","injector","manipulator"]
const PLANES := {"knife":.84,"forceps":.82,"cannula":.76,"phaco":.68,"ia":.68,"injector":.72,"manipulator":.72}
var capsule = Capsule.new()
var lens = Lens.new()
var iol = IOL.new()
var director = Director.new()
var incision = Incision.new()
var anatomy=Contact.new()
var injury=Injury.new()
var _contact_records:=[[],[]]
var _last_injury:Dictionary={}
var last_contacts:=[[],[]]
var recording = Recording.new()
var rigs: Array = [Rig.new(),Rig.new()]
var hand_tools := ["forceps","phaco"]
var selected := 0
var latched := [false,false]
var grip_down := false
var pedal_down := false
var pedal_stage := 0
var pedal_gate = InputGate.new()
var paused := false
var wireframe := false
var assisted := true
var high_contrast := false
var reduced_motion := false
var room_view := true
var practice := false
var case_active := false
var reviewing := false
var review_index := 0
var implant_hand := -1
var implant_nozzle := Vector3(0,.72,0)
var case_id := "standard"
var pupil_radius := .98
var clock := 0.
var status := "증례와 수술 준비를 확인하세요."
var machine := {"inflow":.35,"suction":.35,"energy":.25,"focus":1.,"illumination":1.}
var slider_values: Dictionary = machine
var samples: Array = []
var metrics := {"path_length":0.,"energy_exposure":0.,"iris_contacts":0.,"posterior_contacts":0.,"capsule_contacts":0.,"cornea_contacts":0.}
var targets := [Vector3.ZERO,Vector3.ZERO]
var target_valid := [false,false]
var _command_axes := [Vector3.ZERO,Vector3.ZERO]
var _command_rolls:Array=[null,null]
var previous_tips := [Vector3.ZERO,Vector3.ZERO]
var target_planes := [.82,.68]
var display
var ui
var world
var viewport_3d: SubViewport
var viewport_box: SubViewportContainer
var membrane: MeshInstance3D
var lens_display: MeshInstance3D
var tool_models: Array = []
var diagnostics: Label
var explanation: Label
var hand_button: Button
var _last_lens: Dictionary = {}
var _last_capsule: Dictionary = {}
var _last_iol: Dictionary = {}
var _ui_accum := 0.
var _sample_accum := 0.
var _audio: AudioStreamPlayer
var _audio_clock := 0.
var _sound := false
var _presentation_pending:=false

func _ready() -> void:
	# Retain fixed tissue ticks below 60fps; publish geometry once per rendered frame.
	Engine.max_physics_steps_per_frame=8
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui=Interface.new(); add_child(ui); ui.build(self)
	viewport_box=ui.viewport_box; viewport_3d=ui.viewport_3d
	explanation=ui.explanation; diagnostics=ui.diagnostics; hand_button=ui.hand_button
	display=Display.new(); viewport_3d.add_child(display); display.build()
	world=display.world; membrane=display.membrane; lens_display=display.lens_display; tool_models=display.tool_models
	var optics := ShaderMaterial.new()
	optics.shader=load("res://assets/microscope.gdshader"); viewport_box.material=optics
	_build_audio()
	new_case("standard")
	resized.connect(release_controls)

func new_case(id: String) -> void:
	release_controls()
	case_id=id if id in ["standard","dense","small_pupil","motion"] else "standard"
	director.reset(case_id,7)
	geometry=Segment.new() if anatomical else null
	capsule.geometry=geometry; lens.geometry=geometry; iol.geometry=geometry; incision.geometry=geometry; anatomy.geometry=geometry
	capsule.reset(); lens.reset(); iol.reset(); incision.reset(); recording.reset()
	injury.reset({"cornea":geometry.cornea(),"posterior":geometry.posterior()} if geometry else {})
	display.reset_lens_geometry()
	anatomy.cornea=injury.surfaces.cornea; anatomy.posterior=injury.surfaces.posterior
	_contact_records=[[],[]]
	_command_axes=[Vector3.ZERO,Vector3.ZERO]
	_command_rolls=[null,null]
	_resolved_grips=[false,false]
	lens.layered=true
	lens.hardness=.8 if case_id=="dense" else .4
	selected=0; hand_tools=["forceps","phaco"]; latched=[false,false]
	target_planes=[_plane("forceps"),_plane("phaco")]
	rigs[0].portal=incision.portals[0]; rigs[1].portal=incision.portals[1]
	for hand in range(2):
		rigs[hand].allow_withdrawal=geometry!=null
		rigs[hand].roll=0.
		rigs[hand].aim_at(Vector3(0,.65 if geometry else .8,0)); rigs[hand].set_insertion(-.2 if geometry else .12)
		targets[hand]=rigs[hand].tip; previous_tips[hand]=rigs[hand].tip; target_valid[hand]=false
		_body_poses[hand]={"tip":rigs[hand].tip,"axis":rigs[hand].axis,"roll":rigs[hand].roll,"grip":false}
	pupil_radius=geometry.pupil_radius(case_id=="small_pupil") if geometry else (.74 if case_id=="small_pupil" else .98)
	anatomy.set_pupil(pupil_radius); last_contacts=[[],[]]
	_flap_boundary=FlapBoundary.new() if geometry else null; _flap_revision=-1
	if _flap_boundary:
		_flap_boundary.portals=geometry.portals.duplicate(); _flap_boundary.wound_radius=geometry.wound_radius
		_flap_boundary.configure(anatomy.cornea,anatomy.iris); _flap_revision=anatomy.cornea.revision
	capsule.tissue_boundary=_flap_boundary
	implant_hand=-1; implant_nozzle=Vector3(0,_plane("injector"),0)
	clock=0.; samples=[]; _sample_accum=0.; _ui_accum=0.
	_presentation_pending=false
	metrics={"path_length":0.,"energy_exposure":0.,"iris_contacts":0.,"posterior_contacts":0.,"capsule_contacts":0.,"cornea_contacts":0.}
	case_active=false; practice=false; paused=false; reviewing=false; room_view=true
	status="증례 선택 → 환자·부위·장비 확인 → 집도 시작"
	_cache_metrics(); update_geometry()

func prepare_check(id: String) -> void:
	director.prepare(id); refresh_ui()

func begin_operation() -> bool:
	if not director.ready():
		status="환자·수술 부위·장비의 세 가지 준비 확인이 필요합니다."
		refresh_ui(); return false
	case_active=true; room_view=false; paused=false
	status="현미경 진입. 절개도로 진입부를 만들거나 도움말에서 조작을 확인하세요."
	update_geometry(); return true

func start_practice() -> void:
	new_case(case_id)
	for check_id in ["patient","side","equipment"]: director.prepare(check_id)
	practice=true; case_active=true; room_view=false
	incision.opened=[true,true]; incision.lengths=[.18,.18]
	incision.paths=[[Vector3(1.32,.80,-.25),Vector3(1.32,.80,.25)],[Vector3(-1.32,.80,0),Vector3(-1.32,.80,.5)]] if geometry else [[Vector3(1.32,.84,-.1),Vector3(1.32,.84,.1)],[Vector3(-1.32,.84,.15),Vector3(-1.32,.84,.35)]]
	status="자유 술기 연습: 미리 준비된 진입부에서 조직과 장비 반응을 연습합니다."
	update_geometry()

func _radius(hand:int)->float:
	return geometry.tip_radius(hand_tools[hand]) if geometry else TIP_RADIUS

func _plane(id:String)->float:
	return geometry.planes[id] if geometry else PLANES[id]

func choose_tool(id: String) -> void:
	if id not in IDS: return
	if geometry and id!=hand_tools[selected] and (rigs[selected].insertion>0. or rigs[selected].tip.distance_to(previous_tips[selected])>.001):
		_disarm_actions(); status="열린 통로로 현재 기구를 완전히 인출한 뒤 교체하세요."; refresh_ui(); return
	if selected==implant_hand and iol.metrics().delivered<1. and id!="injector":
		status="부분 전달 중인 인젝터를 유지하세요. 다른 손은 Tab으로 선택할 수 있습니다."; refresh_ui(); return
	if id!=hand_tools[selected]:
		_resolved_grips[selected]=false; _body_poses[selected].grip=false
	_disarm_actions(); latched[selected]=false; capsule.release_hand(selected)
	hand_tools[selected]=id; target_planes[selected]=_plane(id); target_valid[selected]=false
	_command_axes[selected]=Vector3.ZERO
	_command_rolls[selected]=null
	status="%s 기구: %s" % ["왼손" if selected==0 else "오른손",id]
	update_geometry()

func _disarm_actions() -> void:
	grip_down=false; pedal_down=false; pedal_stage=0; pedal_gate.block()

func release_controls() -> void:
	_disarm_actions(); latched=[false,false]; capsule.release()
	target_valid=[false,false]
	_command_axes=[Vector3.ZERO,Vector3.ZERO]
	_command_rolls=[null,null]
	for hand in range(2): incision.cut(hand,rigs[hand].tip,false)

func switch_hand() -> void:
	_disarm_actions()
	target_valid=[false,false]
	_command_axes=[Vector3.ZERO,Vector3.ZERO]
	_command_rolls=[null,null]
	if not latched[selected]: capsule.release_hand(selected)
	selected=1-selected
	status="%s 조작. G로 접촉한 집게의 파지를 유지할 수 있습니다." % ("왼손" if selected==0 else "오른손")
	refresh_ui()

func toggle_latch() -> void:
	if not _can_operate(): return
	if hand_tools[selected]!="forceps":
		status="파지 유지는 집게에서 사용할 수 있습니다."; refresh_ui(); return
	if latched[selected]:
		latched[selected]=false; capsule.release_hand(selected)
	else:
		var near := false
		for p in capsule.positions:
			if p.distance_to(rigs[selected].tip)<.08: near=true; break
		if near: latched[selected]=true
		else: status="조직과 접촉한 뒤 G를 누르세요."
	refresh_ui()

func handle_pedal(pressed: bool, echo: bool, inside: bool, stage := 3) -> void:
	if echo: return
	if pressed: pedal_gate.press(inside and _can_operate())
	else: pedal_gate.release()
	pedal_down=pedal_gate.allowed
	pedal_stage=clampi(stage,1,3) if pedal_down else 0

func _can_operate() -> bool:
	return case_active and not paused and not reviewing and not room_view and director.snapshot().ending=="" and director.snapshot().alert=="" and not ui._help.visible

func set_room_view(value: bool) -> void:
	release_controls(); room_view=value; update_geometry()
func toggle_help() -> void:
	release_controls(); ui._help.visible=not ui._help.visible
func toggle_pause() -> void:
	if not paused: release_controls()
	else:
		# A failed physical tick may pause while preserving a held attachment.
		_disarm_actions(); target_valid=[false,false]; _command_axes=[Vector3.ZERO,Vector3.ZERO]
		_command_rolls=[null,null]
	paused=not paused; refresh_ui()
func set_assisted(value: bool) -> void:
	release_controls(); assisted=value; target_valid=[false,false]; refresh_ui()
func set_high_contrast(value: bool) -> void:
	high_contrast=value; _apply_optics(); refresh_ui()
func set_reduced_motion(value: bool) -> void:
	reduced_motion=value; refresh_ui()
func set_sound(value: bool) -> void:
	_sound=value
	if not value: _audio.stop()
	refresh_ui()
func toggle_debug() -> void:
	wireframe=not wireframe; update_geometry()
func set_machine(key: String, value: float) -> void:
	if machine.has(key) and is_finite(value):
		machine[key]=clampf(value,.5,1.5) if key=="illumination" else clampf(value,0.,1.)
	_apply_optics(); refresh_ui()
func set_preset(name: String) -> void:
	var presets := {"balanced":[.35,.35,.25],"gentle":[.25,.20,.15],"dense":[.42,.48,.55]}
	var values: Array=presets.get(name,presets.balanced)
	for i in range(3): machine[["inflow","suction","energy"][i]]=values[i]
	status="장비 프리셋: "+name+" · 시뮬레이터 상대값"; refresh_ui()

func withdraw_tools() -> void:
	release_controls()
	for hand in range(2):
		if geometry:
			targets[hand]=rigs[hand].portal-rigs[hand].axis*.35; target_valid[hand]=true
		else:
			rigs[hand].set_insertion(.06); target_valid[hand]=false
	status="기구 인출 중. 열린 절개창에 맞춘 경로인지 확인하세요."
	update_geometry()

func acknowledge() -> void:
	release_controls(); director.acknowledge(); status="상태 확인 기록. 페달과 마우스를 놓은 뒤 재개하세요."; refresh_ui()
func inspect(id: String) -> bool:
	var accepted: bool=director.inspect(id)
	status="확인 기록: "+id if accepted else "현재 조직 상태가 확인 조건을 충족하지 않습니다: "+id
	refresh_ui(); return accepted
func finish_case() -> bool:
	if practice:
		abort_case("술기 연습 종료"); return true
	if not director.finish():
		status="구조 손상 증례는 정상 완료로 처리하지 않습니다. 기록 검토 또는 안전 중단을 선택하세요." if director.snapshot().metrics.get("structural_injury",false) else "잔여물·IOL 전달/정렬·기구 인출 후 진입부 상태와 세 최종 검사를 확인하세요."
		refresh_ui(); return false
	_end_encounter(); return true
func abort_case(reason := "사용자 안전 중단") -> void:
	director.abort(reason); _end_encounter()
func _end_encounter() -> void:
	release_controls(); reviewing=false; room_view=false
	update_geometry(); recording.record(clock,display.capture_frame(),true); refresh_ui()

func reset_simulation() -> void:
	if practice: start_practice()
	else: new_case(case_id)

func _command_rig():
	# Input edits a proposed pose. Only the fixed simulation tick may
	# publish movement after speed, pivot and tissue contact constraints.
	var command=Rig.new()
	command.portal=rigs[selected].portal
	command.allow_withdrawal=rigs[selected].allow_withdrawal
	command.axis=rigs[selected].axis; command.insertion=rigs[selected].insertion
	command.roll=rigs[selected].roll if _command_rolls[selected]==null else _command_rolls[selected]
	if target_valid[selected]:
		var delta:Vector3=targets[selected]-command.portal
		var inward:=Vector3(-signf(command.portal.x),0,0)
		var side:=-1. if command.allow_withdrawal and delta.dot(inward)<0. else 1.
		if delta==Vector3.ZERO or (delta.normalized()*side).dot(inward)>=.28:
			command.place_tip(targets[selected])
			if delta==Vector3.ZERO and _command_axes[selected]!=Vector3.ZERO: command.axis=_command_axes[selected]
	return command

func _queue_command(command)->void:
	targets[selected]=command.tip; target_valid[selected]=true
	_command_axes[selected]=command.axis
	_command_rolls[selected]=command.roll
	target_planes[selected]=command.tip.y

func _input(event: InputEvent) -> void:
	if not viewport_box: return
	if reviewing:
		if event is InputEventKey and event.pressed and not event.echo:
			if event.keycode==KEY_ESCAPE: end_review(); get_viewport().set_input_as_handled()
			elif event.keycode==KEY_S: save_session(); get_viewport().set_input_as_handled()
		return
	if ui._help.visible:
		if event is InputEventKey and event.keycode==KEY_ESCAPE and event.pressed:
			toggle_help(); get_viewport().set_input_as_handled()
		return
	if event is InputEventMouseMotion:
		if _pointer_inside(event.position) and _can_operate():
			var local: Vector2=event.position-viewport_box.global_position
			var origin: Vector3=world.microscope.project_ray_origin(local)
			var ray: Vector3=world.microscope.project_ray_normal(local)
			var hit=Plane(Vector3.UP,target_planes[selected]).intersects_ray(origin,ray)
			if hit!=null:
				if assisted: targets[selected]=hit
				else:
					var length:float=targets[selected].distance_to(rigs[selected].portal) if target_valid[selected] else absf(rigs[selected].insertion)
					targets[selected]=rigs[selected].portal+(hit-rigs[selected].portal).normalized()*length
				target_valid[selected]=true
				_command_axes[selected]=Vector3.ZERO
		elif grip_down or pedal_down: _disarm_actions()
	if event is InputEventMouseButton:
		var inside: bool=_pointer_inside(event.position)
		if event.button_index==MOUSE_BUTTON_LEFT:
			grip_down=event.pressed and inside and _can_operate()
			if not grip_down and not latched[selected]: capsule.release_hand(selected)
		elif event.button_index==MOUSE_BUTTON_RIGHT and event.pressed: release_controls()
		elif event.pressed and inside and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			var direction:=1. if event.button_index==MOUSE_BUTTON_WHEEL_UP else -1.
			if event.shift_pressed: world.microscope.size=clampf(world.microscope.size-direction*.2,2.8,6.4)
			elif _can_operate():
				var command=_command_rig()
				command.set_insertion(command.insertion+direction*.03); _queue_command(command)
	if event is InputEventKey:
		if event.keycode==KEY_SPACE:
			var stage:=1 if event.ctrl_pressed else (2 if event.shift_pressed else 3)
			handle_pedal(event.pressed,event.echo,_pointer_inside(get_global_mouse_position()),stage)
			get_viewport().set_input_as_handled()
		if event.pressed and not event.echo:
			if event.keycode in [KEY_TAB,KEY_G,KEY_R,KEY_ESCAPE,KEY_F2,KEY_S,KEY_Q,KEY_E,KEY_Z,KEY_C,KEY_A,KEY_X,KEY_V,KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7]: get_viewport().set_input_as_handled()
			match event.keycode:
				KEY_TAB: switch_hand()
				KEY_G: toggle_latch()
				KEY_R: reset_simulation()
				KEY_ESCAPE: toggle_pause()
				KEY_F2: toggle_debug()
				KEY_S: save_session()
				KEY_A: acknowledge()
				KEY_X: abort_case()
				KEY_V: set_room_view(not room_view)
				KEY_Q,KEY_E:
					if _can_operate():
						var command=_command_rig()
						command.adjust_pitch(-.02 if event.keycode==KEY_Q else .02); _queue_command(command)
				KEY_Z,KEY_C:
					if _can_operate():
						var command=_command_rig()
						command.adjust_roll(-.04 if event.keycode==KEY_Z else .04);_queue_command(command)
				KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7: choose_tool(IDS[event.keycode-KEY_1])

func _pointer_inside(point: Vector2) -> bool:
	return viewport_box.get_global_rect().has_point(point) and not ui.briefing.visible and not ui.debrief.visible and not ui.alert_popup.visible and not ui._help.visible

func _notification(what: int) -> void:
	if what in [MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT,NOTIFICATION_WM_WINDOW_FOCUS_OUT]: release_controls()

func _set_tip(hand: int, target: Vector3) -> void:
	rigs[hand].place_tip(target)

func _advance_motion(dt: float) -> float:
	var distance:=0.
	_contact_records=[[],[]]
	for hand in range(2):
		if target_valid[hand]: rigs[hand].advance_toward(targets[hand],dt*1.5)
		if _command_rolls[hand]!=null:
			rigs[hand].roll=rotate_toward(rigs[hand].roll,_command_rolls[hand],dt*1.2)
		# Finish retraction before rotating at the pivot. This creates a
		# separate zero-to-zero rotation interval for body certification.
		if target_valid[hand] and targets[hand]==rigs[hand].portal and previous_tips[hand]==rigs[hand].portal and rigs[hand].insertion==0. and _command_axes[hand]!=Vector3.ZERO:
			var angle:float=rigs[hand].axis.angle_to(_command_axes[hand])
			if angle>0.: rigs[hand].axis=rigs[hand].axis.slerp(_command_axes[hand],minf(1.,dt*1.2/angle)).normalized()
		if not incision.opened[hand] and hand_tools[hand]!="knife": rigs[hand].set_insertion(minf(.05 if geometry else .12,rigs[hand].insertion))
		var wounds:Array=_open_wounds()
		var contact:Dictionary=anatomy.resolve(previous_tips[hand],rigs[hand].tip,_radius(hand),hand_tools[hand],hand==selected and grip_down,capsule,wounds,hand,geometry!=null)
		_set_tip(hand,contact.position if contact.valid else previous_tips[hand])
		if geometry:
			var prior:Dictionary=_body_poses[hand]
			var requested_grip:bool=hand_tools[hand]=="forceps" and (latched[hand] or (hand==selected and grip_down))
			var surfaces:={"iris":anatomy.iris,"posterior":anatomy.posterior}
			var body:Dictionary=_rigid_body.resolve(rigs[hand].portal,previous_tips[hand],prior.axis,rigs[hand].tip,rigs[hand].axis,hand_tools[hand],_radius(hand),prior.grip,surfaces,prior.grip,prior.get("roll",0.),rigs[hand].roll)
			_resolved_grips[hand]=prior.grip
			if not body.valid:
				rigs[hand].axis=prior.axis;rigs[hand].roll=prior.get("roll",0.); _set_tip(hand,previous_tips[hand])
				contact.contacts=[]; contact.records=[]
				status="기구 몸통 경로를 확인할 수 없습니다: "+body.reason
			else:
				rigs[hand].axis=body.axis;rigs[hand].roll=body.roll; _set_tip(hand,body.tip)
				if body.fraction<1.: contact.contacts=[]; contact.records=[]
				if requested_grip!=prior.grip:
					var transition:Dictionary=_rigid_body.resolve(rigs[hand].portal,rigs[hand].tip,rigs[hand].axis,rigs[hand].tip,rigs[hand].axis,hand_tools[hand],_radius(hand),requested_grip,surfaces,prior.grip,rigs[hand].roll,rigs[hand].roll)
					if transition.valid and transition.fraction==1. and transition.contacts.is_empty(): _resolved_grips[hand]=requested_grip
					else:
						for candidate in transition.contacts:
							if candidate.get("time",0.)>0.: candidate.conservative=true; candidate.load=0.
						body.contacts.append_array(transition.contacts)
						status="집게 턱이 조직과 접촉합니다. 기구 위치를 조절하세요."
				for record in body.contacts:
					if record.surface not in contact.contacts: contact.contacts.append(record.surface)
					contact.records.append(record)
		for surface in contact.contacts:
			metrics[surface+"_contacts"]+=dt
		if not contact.contacts.is_empty() and contact.contacts!=last_contacts[hand]:
			var labels:={"capsule":"전낭","cornea":"각막","iris":"홍채","posterior":"후낭"}
			status="기구 접촉: "+str(labels.get(contact.contacts[0],contact.contacts[0]))+" · 깊이와 진입 경로를 확인하세요."
		last_contacts[hand]=contact.contacts.duplicate()
		_contact_records[hand]=contact.records.duplicate(true)

		distance+=previous_tips[hand].distance_to(rigs[hand].tip)
		previous_tips[hand]=rigs[hand].tip
	return distance

func _physics_process(dt: float) -> void:
	if not display or not _can_operate(): return
	if not is_finite(dt) or dt<=0 or dt>.05: return
	var geometric_blade:bool=geometry!=null and hand_tools[selected]=="knife" and grip_down
	var blade_action:=""
	var saved:Dictionary=PhysicsTransaction.capture(self) if capsule.requires_physics_transaction() or geometric_blade else {}
	var movement:=_advance_motion(dt)
	metrics.path_length+=movement
	_update_injury(dt)
	var tip: Vector3=rigs[selected].tip
	var tool: String=hand_tools[selected]
	for hand in range(2): incision.cut(hand,rigs[hand].tip,hand==selected and grip_down and hand_tools[hand]=="knife")
	incision.update(dt,[rigs[0].insertion,rigs[1].insertion])
	if geometric_blade:
		var prior:Dictionary=_body_poses[selected]
		blade_action="stationary" if prior.tip==rigs[selected].tip and prior.axis==rigs[selected].axis and prior.get("roll",0.)==rigs[selected].roll else "no_new_cut"
		var sweep:Dictionary=BladeSweep.build("knife",prior.tip,prior.axis,rigs[selected].tip,rigs[selected].axis,true,prior.get("roll",0.),rigs[selected].roll)
		if not sweep.valid:
			_reject_physics_tick(saved,{"reason":"blade_"+sweep.reason,"status":-1});return
		if not sweep.patches.is_empty():
			var incision_result:Dictionary=capsule.incise_patches(sweep.patches)
			if not incision_result.valid:
				_reject_physics_tick(saved,{"reason":"blade_"+incision_result.reason,"status":-1});return
			# No new incision can also mean an already-open bank; it is not a
			# contact or completion claim. Publish only after the whole tick.
			blade_action="new_cut" if incision_result.changed else "no_new_cut"
	var flow_active:=pedal_down and tool in ["phaco","ia","cannula"]
	var aspirating:=flow_active and pedal_stage>=2 and tool in ["phaco","ia"]
	var powered:=flow_active and pedal_stage==3 and tool=="phaco"
	lens.inflow=machine.inflow if flow_active else 0.
	lens.suction=machine.suction; lens.energy=machine.energy
	lens.tissue_access=anatomy.lens_access(tip,capsule,_radius(selected)) if flow_active else true
	lens.hydro_flow=1. if flow_active and tool=="cannula" and lens.tissue_access else 0.
	lens.wound_leak=clampf(incision.metrics().leak+_last_injury.get("corneal_conductance",0.),0.,1.)
	lens.rupture_leak=_last_injury.get("rupture_conductance",0.)
	lens.passive_tips=PackedVector3Array([rigs[1-selected].tip])
	lens.step(dt,tip,powered,aspirating)
	_last_lens=lens.metrics()
	capsule.pressure_load=.3*(float(_last_lens.pressure)-1.)
	var tools: Array[Dictionary]=[]
	for hand in range(2):
		var cutting:bool=hand_tools[hand]=="knife" and hand==selected and grip_down
		tools.append({"hand":hand,"tip":rigs[hand].tip,"radius":.065,"contact_radius":_radius(hand),"grip":hand_tools[hand]=="forceps" and _actual_grip(hand) and (latched[hand] or (hand==selected and grip_down)),"cut":cutting and geometry==null})
		if geometry:
			var prior:Dictionary=_body_poses[hand]
			tools[-1]["body"]=ToolPath.build(hand_tools[hand],_radius(hand),prior.tip,prior.axis,prior.grip,rigs[hand].tip,rigs[hand].axis,_actual_grip(hand),cutting,prior.get("roll",0.),rigs[hand].roll)
	if _flap_boundary:
		_flap_boundary.wounds=_open_wounds()
		if anatomy.cornea.revision!=_flap_revision:
			_flap_boundary.configure(anatomy.cornea,anatomy.iris); _flap_revision=anatomy.cornea.revision
	if capsule.embedded_backend:capsule.embedded_surfaces={"iris":anatomy.iris,"posterior":anatomy.posterior}
	capsule.step_tools(dt,tools)
	if not capsule.native_failure.is_empty():
		var failure:Dictionary=capsule.native_failure.duplicate(true)
		_reject_physics_tick(saved,failure)
		return
	for hand in range(2): _body_poses[hand]={"tip":rigs[hand].tip,"axis":rigs[hand].axis,"roll":rigs[hand].roll,"grip":hand_tools[hand]=="forceps" and _actual_grip(hand)}
	var injecting: bool=tool=="injector" and grip_down and incision.opened[selected] and (implant_hand==-1 or implant_hand==selected)
	if injecting and implant_hand==-1: implant_hand=selected
	if implant_hand>=0 and hand_tools[implant_hand]=="injector": implant_nozzle=rigs[implant_hand].tip
	iol.step(dt,implant_nozzle,injecting,tip,tool=="manipulator" and grip_down)
	clock+=dt; metrics.energy_exposure+=(machine.energy*dt if powered else 0.)
	_cache_metrics()
	if geometric_blade:
		_last_capsule["blade_action"]=blade_action
		_last_capsule["blade_hand"]=selected
	director.observe(dt,_observation(movement,machine.energy if powered else 0.))
	if director.snapshot().alert!="":
		release_controls(); status="조직 형상 손상 기록. 상태를 확인하고 기록 검토 또는 안전 중단을 선택하세요." if director.snapshot().alert=="tissue_injury" else "환자 움직임. 기구·페달을 멈추고 상태를 평가하세요."
	_sample_accum+=dt; _ui_accum+=dt
	if _sample_accum>=.25 and samples.size()<12000:
		_sample_accum=0.; samples.append({"time":clock,"capsule":_last_capsule.duplicate(),"lens":_last_lens.duplicate(),"iol":_last_iol.duplicate(),"metrics":metrics.duplicate()})
	_presentation_pending=true
	if not is_physics_processing(): _present_frame()
	_audio_clock+=dt
	if _sound and _audio_clock>.81: _audio_clock=0.; _audio.play()

func _reject_physics_tick(saved:Dictionary,failure:Dictionary)->void:
	if not saved.is_empty():PhysicsTransaction.restore(self,saved)
	capsule.native_failure=failure
	# Disarm input without releasing restored physical grasps or cut history.
	_disarm_actions();target_valid=[false,false];_command_axes=[Vector3.ZERO,Vector3.ZERO]
	_command_rolls=[null,null]
	paused=true
	status="조직 계산을 완료하지 못했습니다. 조작을 멈추고 상태를 확인하세요: "+str(failure.get("reason","native_failure"))
	refresh_ui()

func _process(_dt:float)->void:
	if _presentation_pending: _present_frame()

func _present_frame()->void:
	_presentation_pending=false
	if not display or reviewing: return
	update_geometry(false)
	if recording.frames.is_empty() or clock-float(recording.frames[-1].time)>=recording.INTERVAL: recording.record(clock,display.capture_frame())
	if _ui_accum>=.1: _ui_accum=0.; refresh_ui()

func _open_wounds()->Array:
	return [incision.paths[0] if incision.opened[0] else [],incision.paths[1] if incision.opened[1] else []]

func _update_injury(dt:float)->void:
	var records:Array=[]
	for hand in range(2):
		var powered:bool=hand==selected and hand_tools[hand]=="phaco" and pedal_down and pedal_stage==3
		var local:Array=_contact_records[hand].duplicate(true)
		if powered:
			for current in anatomy.stationary(rigs[hand].tip,_radius(hand),_open_wounds()):
				var duplicate:=false
				for moving in local:
					if not moving.get("conservative",false) and moving.surface==current.surface and moving.triangle==current.triangle and moving.revision==current.revision and moving.get("part","working_tip")=="working_tip": duplicate=true; break
				if not duplicate: local.append(current)
		var energy_contacts:=0
		for record in local:
			if not record.get("conservative",false) and (not record.has("part") or record.get("energy",false)==true): energy_contacts+=1
		for record in local:
			if record.get("conservative",false): continue
			var cutting_part:bool=not record.has("part") or record.get("cutting",false)==true
			var energy_part:bool=not record.has("part") or record.get("energy",false)==true
			record["tool"]=hand_tools[hand]; record["cutting"]=cutting_part and hand==selected and grip_down and hand_tools[hand]=="knife"
			record["energy"]=machine.energy/maxi(1,energy_contacts) if powered and energy_part else 0.
			records.append(record)
	injury.step(dt,records); _last_injury=injury.metrics()

func _anatomy_state()->Dictionary:
	var state:Dictionary={}
	for id in injury.surfaces:
		if geometry or injury.surfaces[id].revision>0: state[id]=injury.surfaces[id]
	if geometry: state["iris"]=anatomy.iris
	return state

func _observation(movement:=0.,energy:=0.) -> Dictionary:
	return {"capsule_extraction_required":geometry!=null,"capsule":_last_capsule,"lens":_last_lens,"iol":_last_iol,"injury":_last_injury,"wound":incision.metrics().sealed and not _last_injury.get("corneal_breached",false) and not _last_injury.get("posterior_breached",false),"energy":energy,"movement":movement,"tool":hand_tools[selected]}

func _cache_metrics() -> void:
	_last_capsule=capsule.metrics(); _last_lens=lens.metrics(); _last_iol=iol.metrics(); _last_injury=injury.metrics()

func _actual_grip(hand:int)->bool:
	return _resolved_grips[hand] if geometry and hand_tools[hand]=="forceps" else latched[hand] or (grip_down and hand==selected)

func update_geometry(update_ui:=true) -> void:
	if not display: return
	var actions: Array=[]
	for hand in range(2): actions.append({"grip":_actual_grip(hand),"pedal":pedal_stage if hand==selected else 0})
	display.apply(capsule,lens,iol,rigs,hand_tools,selected,actions,{"dimensioned":geometry!=null,"room":room_view,"wireframe":wireframe,"pupil_radius":pupil_radius,"wounds":incision.paths,"anatomy":_anatomy_state(),"injury":_last_injury})
	tool_models=display.tool_models
	_apply_optics()
	if update_ui: _cache_metrics(); refresh_ui()

func _apply_optics() -> void:
	if not viewport_box or not viewport_box.material: return
	viewport_box.material.set_shader_parameter("focus",machine.focus)
	viewport_box.material.set_shader_parameter("illumination",machine.illumination)
	viewport_box.material.set_shader_parameter("vignette_strength",.12 if room_view else .55)
	viewport_box.material.set_shader_parameter("high_contrast",high_contrast)

func refresh_ui() -> void:
	if not ui: return
	var state: Dictionary=director.snapshot()
	var objective: String=state.objective
	if case_active and state.ending=="" and state.alert=="":
		if incision.metrics().entry_count==0: objective="절개도로 진입부 형성 · 각막 주변의 짧은 연속 경로"
		elif _last_capsule.get("broken_edges",0)==0 and _last_lens.get("remaining_mass",1.)>.98: objective="집게·절개도로 전낭 접근과 개방 · 조직 반응 관찰"
		elif geometry and (_last_capsule.get("extracted_flaps",0)==0 or _last_capsule.get("retained_detached_area",0.)>1e-8): objective="분리된 전낭편 확인 · 집게로 가장자리를 잡아 열린 통로로 인출"
		elif float(_last_lens.get("nucleus_remaining",0.))<.01 and float(_last_lens.get("cortex_remaining",0.))>.02: objective="피질 잔여물 확인 · 관류·흡인 기구로 국소 제거"
		elif float(_last_lens.get("adhesion_released",1.))<.2 and _last_capsule.get("broken_edges",0)>0: objective="캐뉼라 국소 관류 · 피질 부착과 핵의 움직임 관찰"
	var report_metrics:=metrics.duplicate()
	report_metrics["time_seconds"]=clock; report_metrics["lens_removed"]=1.-float(_last_lens.get("remaining_mass",1.))
	report_metrics["iol_alignment"]=_last_iol.get("alignment",0.); report_metrics["tissue_breaks"]=_last_capsule.get("broken_edges",0)
	report_metrics["wound_leak"]=incision.metrics().leak
	report_metrics["posterior_open_area"]=_last_injury.get("posterior_open_area",0.); report_metrics["corneal_open_area"]=_last_injury.get("corneal_open_area",0.)
	report_metrics["corneal_damage_area"]=_last_injury.get("corneal_damage_area",0.)
	report_metrics["extracted_flaps"]=_last_capsule.get("extracted_flaps",0)
	for key in ["extracted_area","retained_detached_area","cut_loss_area"]: report_metrics[key]=_last_capsule.get(key,0.)
	if geometry:
		report_metrics["length_unit"]="mm"; report_metrics["area_unit"]="mm²"
		report_metrics["path_length"]/=geometry.units_per_mm
		for key in ["posterior_open_area","corneal_open_area","corneal_damage_area","extracted_area","retained_detached_area","cut_loss_area"]: report_metrics[key]/=geometry.units_per_mm*geometry.units_per_mm
	ui.refresh({"director":state,"case_id":case_id,"room_view":room_view,"paused":paused,"status":status,"tools":hand_tools,"selected":selected,"latched":latched,"blade_active":geometry!=null and grip_down and hand_tools[selected]=="knife","clock":clock,"pedal_stage":pedal_stage,"capsule":_last_capsule,"lens":_last_lens,"iol":_last_iol,"wound":incision.metrics(),"assisted":assisted,"debug":wireframe,"frame_count":recording.frames.size(),"reviewing":reviewing,"metrics":report_metrics,"machine":machine,"pupil_radius":pupil_radius,"ending":state.ending,"objective":objective,"show_briefing":not case_active and state.ending=="","practice":practice,"sound":_sound,"high_contrast":high_contrast,"reduced_motion":reduced_motion,"review_index":review_index,"injury":_last_injury})

func preview_frame(index: int) -> void:
	var frame: Dictionary=recording.frame_at(index)
	if frame.is_empty(): return
	release_controls(); reviewing=true; review_index=index; room_view=false; display.apply_frame(frame); refresh_ui()

func end_review() -> void:
	reviewing=false; update_geometry()

func save_session() -> void:
	var report: Dictionary=director.snapshot()
	report["simulation_metrics"]=metrics.duplicate(); report["model"]="specialist-simulation-1 / uncalibrated"
	report["geometry"]={"model_units_per_mm":geometry.units_per_mm,"lens_diameter_mm":geometry.lens_radius*2./geometry.units_per_mm,"lens_thickness_mm":geometry.lens_half_thickness*2./geometry.units_per_mm,"kind":"representative anterior segment"} if geometry else {"kind":"legacy unitless specimen"}
	var raw: String=recording.export_json(report)
	if raw.to_utf8_buffer().size()>32000000: status="기록 용량 한도 초과. 세션을 나누어 저장하세요."; refresh_ui(); return
	var path: String="user://case_%s_%d.json" % [case_id,Time.get_unix_time_from_system()]
	var file:=FileAccess.open(path,FileAccess.WRITE)
	if file: file.store_string(raw); status="저장: "+ProjectSettings.globalize_path(path)
	else: status="저장할 수 없습니다. 폴더 권한과 저장 공간을 확인하세요."
	refresh_ui()

func export_observations() -> void:
	save_session()

func _build_audio() -> void:
	_audio=AudioStreamPlayer.new(); add_child(_audio)
	var stream:=AudioStreamWAV.new()
	stream.format=AudioStreamWAV.FORMAT_16_BITS; stream.mix_rate=22050
	var data:=PackedByteArray(); data.resize(2205*2)
	for i in range(2205): data.encode_s16(i*2,int(sin(i/22050.*TAU*880.)*sin(i/2205.*PI)*1800.))
	stream.data=data; _audio.stream=stream
