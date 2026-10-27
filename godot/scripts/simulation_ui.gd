extends Control
## Presentation and callbacks only. All numerical state belongs to the application.
const MINT := Color("7be0c5")
const DIM := Color("88a6b0")
const IDS := ["knife","forceps","cannula","phaco","ia","injector","manipulator"]
const NAMES := ["절개도","전낭 집게","수류분리 캐뉼라","유화 핸드피스","관류 · 흡인","IOL 인젝터","위치 조정 기구"]
const CASE_IDS := ["standard","dense","small_pupil","motion"]
const CASE_NAMES := ["표준 사례  /  Standard","고밀도 수정체  /  Dense","작은 동공  /  Small pupil","환자 움직임  /  Motion"]
var viewport_box: SubViewportContainer
var viewport_3d: SubViewport
var explanation: Label
var diagnostics: Label
var hand_button: Button
var briefing: PanelContainer
var alert_popup: PanelContainer
var debrief: PanelContainer
var review_slider: HSlider
var review_controls: HBoxContainer
var left_scroll: ScrollContainer
var right_scroll: ScrollContainer
var tool_buttons: Dictionary = {}
var inspection_buttons: Dictionary = {}
var machine_sliders: Dictionary = {}
var prep_checks: Dictionary = {}
var start_button: Button
var finish_button: Button
var sound_toggle: CheckButton
var _app: Object
var _objective: Label
var _top_status: Label
var _case_picker: OptionButton
var _machine_values: Dictionary = {}
var _inspection_labels := {"residual":"잔여 수정체 확인","implant":"IOL 전개 · 정렬 확인","wound":"진입 상처 확인"}
var _latch: Button
var _hand_status: Label
var _pause: Button
var _room: Button
var _monitor: Control
var _vitals: Label
var _telemetry: Label
var _alert_text: Label
var _report: RichTextLabel
var _help: PanelContainer
var _overlays: Array[PanelContainer] = []
var _settings: Dictionary = {}
var _report_signature := ""
var _reviewing := false
var _viewport_review_slider: HSlider
var _high_contrast := false
var _background: ColorRect

class Trace extends Control:
	var time := 0.0
	var alert := false
	func _draw() -> void:
		var w := size.x
		var h := size.y
		for x in range(0,int(w),20): draw_line(Vector2(x,0),Vector2(x,h),Color("183b42"))
		for y in range(0,int(h),20): draw_line(Vector2(0,y),Vector2(w,y),Color("183b42"))
		var points := PackedVector2Array()
		for i in range(160):
			var phase := fposmod(i/159.0*3.0-time*.65,1.0)
			var pulse := exp(-pow((phase-.38)/.017,2))*-.48+exp(-pow((phase-.42)/.024,2))*.21+sin(phase*TAU)*.035
			points.append(Vector2(i/159.0*w,h*(.57+pulse)))
		draw_polyline(points,Color("e8ba7c") if alert else Color("75dcae"),1.6,true)

func build(app: Object) -> void:
	_app=app
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_theme()
	var background:=ColorRect.new()
	_background=background
	background.color=Color("07151c"); background.mouse_filter=Control.MOUSE_FILTER_IGNORE
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); add_child(background)
	var margin:=MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]: margin.add_theme_constant_override("margin_"+side,14)
	add_child(margin)
	var all:=_column(margin)
	var top:=HBoxContainer.new(); all.add_child(top)
	var brand:=_label("OPHTHO  /  SIM",23,MINT); top.add_child(brand)
	_top_status=_label("STANDARD  ·  00:00",14,DIM); _top_status.size_flags_horizontal=Control.SIZE_EXPAND_FILL; top.add_child(_top_status)
	_room=_button("수술실 보기",func(): _call("set_room_view",[not _room.get_meta("room",true)])); top.add_child(_room)
	_pause=_button("일시정지  Esc",func(): _call("toggle_pause")); top.add_child(_pause)
	top.add_child(_button("도움말  ?",func(): _call("toggle_help")))
	all.add_child(HSeparator.new())
	var body:=HBoxContainer.new(); body.size_flags_vertical=Control.SIZE_EXPAND_FILL; all.add_child(body)
	left_scroll=_side(body,218)
	var left:=_column(left_scroll)
	left.add_child(_label("OPERATIVE PLAN",11,MINT))
	_objective=_label("준비 확인",19); _objective.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; left.add_child(_objective)
	left.add_child(HSeparator.new())
	hand_button=_button("왼손 선택  Tab",func(): _call("switch_hand")); left.add_child(hand_button)
	_hand_status=_label("L  집게    R  유화 프로브",12,DIM); _hand_status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; left.add_child(_hand_status)
	_latch=_button("집게 고정  G",func(): _call("toggle_latch")); left.add_child(_latch)
	left.add_child(_label("INSTRUMENT TRAY",11,MINT))
	for i in range(IDS.size()):
		var id: String=IDS[i]
		var button:=_button("%d  %s"%[i+1,NAMES[i]],func(): _call("choose_tool",[id]))
		button.alignment=HORIZONTAL_ALIGNMENT_LEFT; button.set_meta("caption",button.text)
		button.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS
		tool_buttons[id]=button; left.add_child(button)
	left.add_child(_button("기구 인출",func(): _call("withdraw_tools")))
	left.add_child(HSeparator.new())
	left.add_child(_label("마우스  조준 · 휠  삽입 깊이\nQ / E  각도 · Tab  손 전환\nG  집게 고정 · Space  페달",12,DIM))
	left.add_child(_button("수치 진단  F2",func(): _call("toggle_debug")))
	var center:=_column(body); center.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	var view_header:=HBoxContainer.new(); center.add_child(view_header)
	view_header.add_child(_label("OPERATIVE MICROSCOPE",11,MINT))
	var view_hint:=_label("기구 축 · 접점 · 깊이",11,DIM); view_hint.size_flags_horizontal=Control.SIZE_EXPAND_FILL; view_hint.horizontal_alignment=HORIZONTAL_ALIGNMENT_RIGHT; view_header.add_child(view_hint)
	viewport_box=SubViewportContainer.new(); viewport_box.stretch=true
	viewport_box.size_flags_horizontal=Control.SIZE_EXPAND_FILL; viewport_box.size_flags_vertical=Control.SIZE_EXPAND_FILL
	viewport_box.custom_minimum_size=Vector2(380,300); center.add_child(viewport_box)
	viewport_3d=SubViewport.new(); viewport_3d.size=Vector2i(960,720); viewport_3d.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	viewport_box.add_child(viewport_3d)
	explanation=_label("기구를 선택하고 조직 상태를 관찰하세요.",14); explanation.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; center.add_child(explanation)
	_telemetry=_label("DEPTH  —     PEDAL  OFF     RECORD  0",12,MINT); center.add_child(_telemetry)
	review_controls=HBoxContainer.new(); review_controls.visible=false; center.add_child(review_controls)
	review_controls.add_child(_label("기록 / REVIEW",11,MINT))
	_viewport_review_slider=HSlider.new(); _viewport_review_slider.step=1.; _viewport_review_slider.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	_viewport_review_slider.value_changed.connect(func(value): _call("preview_frame",[int(value)])); review_controls.add_child(_viewport_review_slider)
	review_controls.add_child(_button("검토 종료",func(): _call("end_review")))
	diagnostics=_label("",11,DIM); diagnostics.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; diagnostics.visible=false; center.add_child(diagnostics)
	right_scroll=_side(body,254)
	var right:=_column(right_scroll)
	right.add_child(_label("LIVE   /   합성 환자 모니터",11,MINT))
	_monitor=Trace.new(); _monitor.custom_minimum_size=Vector2(210,86); right.add_child(_monitor)
	_vitals=_label("72  HR     98%  SpO₂",19,MINT); right.add_child(_vitals)
	right.add_child(HSeparator.new())
	right.add_child(_label("DEVICE CONSOLE",11,MINT))
	var presets:=HBoxContainer.new(); right.add_child(presets)
	for pair in [["balanced","균형"],["gentle","저자극"],["dense","고밀도"]]:
		var preset: String=pair[0]
		var b:=_button(pair[1],func(): _call("set_preset",[preset])); b.size_flags_horizontal=Control.SIZE_EXPAND_FILL; presets.add_child(b)
	for pair in [["energy","유화 출력"],["suction","흡인"],["inflow","관류 유입"],["focus","초점"],["illumination","조명"]]: _slider(right,pair[0],pair[1])
	right.add_child(_label("FINAL INSPECTION",11,MINT))
	for id in ["residual","implant","wound"]:
		var check_id: String=id
		var b:=_button(_inspection_labels[id],func(): _call("inspect",[check_id])); right.add_child(b); inspection_buttons[id]=b
	finish_button=_button("사례 마무리",func(): _call("finish_case")); right.add_child(finish_button)
	right.add_child(_button("안전 중단",func(): _call("abort_case")))
	all.add_child(_label("합성 사례 · 모든 장비 수치는 시뮬레이션 기준     |     Ctrl+Space  관류 · Shift+Space  흡인 · Space  유화",11,DIM))
	_build_briefing(); _build_help(); _build_alert(); _build_debrief()
	resized.connect(_resize_overlays)
	call_deferred("_resize_overlays")

func _build_theme() -> void:
	var skin:=Theme.new(); skin.default_font_size=14
	var font:=SystemFont.new(); font.font_names=PackedStringArray(["Malgun Gothic","Arial"]); skin.default_font=font
	skin.set_color("font_color","Label",Color("dfedf0")); skin.set_color("font_color","Button",Color("dfedf0"))
	skin.set_color("font_disabled_color","Button",Color("5f7882"))
	for name in ["normal","hover","pressed","disabled","focus"]:
		var style:=StyleBoxFlat.new(); style.bg_color=Color("17343e") if name=="hover" else Color("102731")
		if name=="pressed": style.bg_color=Color("205147")
		if name=="disabled": style.bg_color=Color("0d2028")
		style.border_color=Color("4a8e8b") if name=="focus" else Color("28444d"); style.set_border_width_all(1); style.set_corner_radius_all(5)
		style.content_margin_left=9; style.content_margin_right=9; style.content_margin_top=7; style.content_margin_bottom=7
		skin.set_stylebox(name,"Button",style)
	skin.set_constant("separation","VBoxContainer",8); skin.set_constant("separation","HBoxContainer",10)
	theme=skin

func _column(parent: Node) -> VBoxContainer:
	var box:=VBoxContainer.new(); box.size_flags_horizontal=Control.SIZE_EXPAND_FILL; parent.add_child(box); return box
func _label(value: String,font_size:=14,color:=Color("dfedf0")) -> Label:
	var label:=Label.new(); label.text=value; label.add_theme_font_size_override("font_size",font_size); label.add_theme_color_override("font_color",color); label.set_meta("original_color",color); label.mouse_filter=Control.MOUSE_FILTER_IGNORE; return label
func _button(value: String,callback: Callable) -> Button:
	var button:=Button.new(); button.text=value; button.custom_minimum_size.y=36; button.pressed.connect(callback); return button
func _side(parent: Node,width: float) -> ScrollContainer:
	var scroll:=ScrollContainer.new(); scroll.custom_minimum_size.x=width; scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL; scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED; parent.add_child(scroll); return scroll
func _call(method: String,args: Array=[]) -> void:
	if is_instance_valid(_app) and _app.has_method(method): _app.callv(method,args)
func _slider(parent: Node,key: String,caption: String) -> void:
	var row:=HBoxContainer.new(); parent.add_child(row); row.add_child(_label(caption,13,DIM))
	var value:=_label("0%",12,MINT); value.size_flags_horizontal=Control.SIZE_EXPAND_FILL; value.horizontal_alignment=HORIZONTAL_ALIGNMENT_RIGHT; row.add_child(value); _machine_values[key]=value
	var slider:=HSlider.new(); slider.min_value=0.; slider.max_value=1.; slider.step=.01; slider.custom_minimum_size.y=22
	slider.value_changed.connect(func(v): _call("set_machine",[key,v])); parent.add_child(slider); machine_sliders[key]=slider

func _overlay(title: String) -> Array:
	var panel:=PanelContainer.new(); panel.z_index=20
	var style:=StyleBoxFlat.new(); style.bg_color=Color("10232df5"); style.border_color=Color("46877e"); style.set_border_width_all(1); style.set_corner_radius_all(10)
	for side in ["left","right","top","bottom"]: style.set("content_margin_"+side,22.0)
	panel.add_theme_stylebox_override("panel",style); add_child(panel); _overlays.append(panel)
	var scroll:=ScrollContainer.new(); scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED; panel.add_child(scroll)
	var content:=_column(scroll); content.add_child(_label(title,24,MINT)); panel.visible=false
	return [panel,content]
func _resize_overlays() -> void:
	for panel in _overlays:
		var height:=280.0 if panel==alert_popup else 720.0
		panel.size=Vector2(minf(820,size.x-72),minf(height,size.y-88)); panel.position=(size-panel.size)*.5

func _build_briefing() -> void:
	var parts:=_overlay("사례 브리핑  /  CASE BRIEFING"); briefing=parts[0]; var content: VBoxContainer=parts[1]
	content.add_child(_label("환자 · 수술 부위 · 장비를 확인하고 현미경으로 진입합니다.",15))
	_case_picker=OptionButton.new()
	for caption in CASE_NAMES: _case_picker.add_item(caption)
	_case_picker.item_selected.connect(func(index): _call("new_case",[CASE_IDS[index]])); content.add_child(_case_picker)
	var about:=_label("표준: 기본 조직 반응\n고밀도: 파쇄 저항 증가 · 작은 동공: 시야 제한\n환자 움직임: 조작 중 상태 변화에 대응",14,DIM); about.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; content.add_child(about)
	content.add_child(HSeparator.new())
	for pair in [["patient","가상 환자 및 사례 확인"],["side","수술 부위 확인"],["equipment","기구 · 관류 · 흡인 장비 점검"]]:
		var id: String=pair[0]; var check:=CheckButton.new(); check.text=pair[1]; check.pressed.connect(func(): _call("prepare_check",[id])); content.add_child(check); prep_checks[id]=check
	start_button=_button("준비 완료 · 수술 시작",func(): _call("begin_operation")); content.add_child(start_button)
	content.add_child(_button("자유 술기 연습",func(): _call("start_practice")))
	content.add_child(_label("기본 조작  마우스 조준 · 휠 깊이 · Tab 양손 전환 · G 집게 고정\n페달  Ctrl+Space 관류 · Shift+Space 흡인 · Space 유화",14,DIM))

func _build_help() -> void:
	var parts:=_overlay("조작과 접근성  /  CONTROLS"); _help=parts[0]; var content: VBoxContainer=parts[1]
	var copy:=_label("마우스  기구 조준\n휠  삽입 깊이    Q / E  기구 각도\nTab  선택 손 전환    G  집게 고정 / 해제\nSpace  유화 페달    Ctrl+Space  관류    Shift+Space  흡인\nF2  상세 수치    Esc  일시정지\n\n집게를 고정한 뒤 다른 손의 기구를 조작할 수 있습니다.\n최종 검사는 실제 잔여물, IOL 상태와 상처 관찰을 확인합니다.\n기구를 인출한 뒤 최종 상처 상태를 확인하세요.",15); copy.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; content.add_child(copy)
	for pair in [["assisted","마우스 깊이 보조","set_assisted"],["high_contrast","높은 대비","set_high_contrast"],["reduced_motion","움직임 감소","set_reduced_motion"],["sound","장비 소리","set_sound"]]:
		var method: String=pair[2]; var check:=CheckButton.new(); check.text=pair[1]; check.toggled.connect(func(value): _call(method,[value])); content.add_child(check); _settings[pair[0]]=check
		if pair[0]=="sound": sound_toggle=check
	content.add_child(_label("수치 모델과 장비 값은 비보정 시뮬레이션입니다. 실제 의료 술기나 장비 설정의 기준으로 검증되지 않았습니다.",12,DIM))
	content.add_child(_button("닫기",func(): _call("toggle_help")))

func _build_alert() -> void:
	var parts:=_overlay("상태 확인 필요  /  ATTENTION"); alert_popup=parts[0]; alert_popup.z_index=30; var content: VBoxContainer=parts[1]
	_alert_text=_label("환자 움직임을 확인하고 조작을 멈추세요.",19); _alert_text.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART; content.add_child(_alert_text)
	content.add_child(_button("상태 평가 · 조작 재개",func(): _call("acknowledge")))
	content.add_child(_button("안전 중단",func(): _call("abort_case")))

func _build_debrief() -> void:
	var parts:=_overlay("사례 기록  /  DEBRIEF"); debrief=parts[0]; debrief.z_index=25; var content: VBoxContainer=parts[1]
	_report=RichTextLabel.new(); _report.custom_minimum_size.y=300; _report.size_flags_vertical=Control.SIZE_EXPAND_FILL; content.add_child(_report)
	content.add_child(_label("기록 장면 검토  /  CAPTURED STATES",12,MINT))
	review_slider=HSlider.new(); review_slider.step=1.; review_slider.min_value=0.; review_slider.max_value=0.; review_slider.value_changed.connect(func(value): _call("preview_frame",[int(value)])); content.add_child(review_slider)
	var actions:=HBoxContainer.new(); content.add_child(actions)
	actions.add_child(_button("검토 종료",func(): _call("end_review")))
	actions.add_child(_button("수치 기록 저장",func(): _call("save_session")))
	actions.add_child(_button("새 사례",func(): _call("new_case",[CASE_IDS[_case_picker.selected]])))

func refresh(state: Dictionary) -> void:
	var contrast: bool=state.get("high_contrast",false)
	if contrast!=_high_contrast:
		_high_contrast=contrast
		_background.color=Color.BLACK if contrast else Color("07151c")
		_apply_contrast(self,contrast)
	var director: Dictionary=state.get("director",{})
	var ending: String=str(state.get("ending",director.get("ending","")))
	var paused: bool=state.get("paused",false)
	var alert: String=str(director.get("alert",""))
	var ready: bool=director.get("ready",director.get("stage","")=="operating")
	var room: bool=state.get("room_view",true)
	var elapsed: float=state.get("clock",director.get("elapsed",0.))
	var case_id: String=state.get("case_id",director.get("case_id","standard"))
	var selected: int=clampi(int(state.get("selected",0)),0,1)
	var tools: Array=state.get("tools",["forceps","phaco"])
	var latched: Array=state.get("latched",[false,false])
	var interactive: bool=ready and not paused and ending=="" and alert=="" and not state.get("reviewing",false)
	briefing.visible=state.get("show_briefing",director.get("stage","briefing")=="briefing" or (ready and room and elapsed==0. and not state.get("practice",false) and ending==""))
	debrief.visible=ending!="" and not state.get("reviewing",false)
	review_controls.visible=state.get("reviewing",false)
	alert_popup.visible=alert!="" and ending==""
	_top_status.text="%s  ·  %02d:%02d%s"%[case_id.to_upper(),int(elapsed)/60,int(elapsed)%60,"  /  PAUSED" if paused else ""]
	_pause.text="계속하기  Esc" if paused else "일시정지  Esc"
	_room.text="현미경 보기" if room else "수술실 보기"; _room.set_meta("room",room)
	_objective.text=str(state.get("objective",director.get("objective","조직 상태 관찰")))
	explanation.text=str(state.get("status","집게로 접점을 고정하고 다른 손의 기구를 조작할 수 있습니다."))
	hand_button.text=("왼손 선택  L" if selected==0 else "오른손 선택  R")+"  [Tab]"
	hand_button.disabled=not interactive; _latch.disabled=not interactive
	_latch.text="집게 고정 해제  G" if selected<latched.size() and latched[selected] else "집게 고정  G"
	_hand_status.text="L  %s%s\nR  %s%s"%[_tool_name(tools,0),"  [고정]" if latched.size()>0 and latched[0] else "",_tool_name(tools,1),"  [고정]" if latched.size()>1 and latched[1] else ""]
	for id in tool_buttons:
		var button: Button=tool_buttons[id]; button.disabled=not interactive
		button.text=("● " if selected<tools.size() and _tool_id(tools[selected])==id else "")+str(button.get_meta("caption"))
	var preparation: Dictionary=director.get("preparation",{})
	for id in prep_checks: prep_checks[id].set_pressed_no_signal(preparation.get(id,false))
	start_button.disabled=not ready
	if case_id in CASE_IDS: _case_picker.select(CASE_IDS.find(case_id))
	var machine: Dictionary=state.get("machine",{})
	for key in machine_sliders:
		var value: float=clampf(float(machine.get(key,.0)),0.,1.)
		machine_sliders[key].set_value_no_signal(value); _machine_values[key].text="%d%%"%roundi(value*100)
		machine_sliders[key].editable=interactive
	var inspection: Dictionary=director.get("inspection",{})
	for id in inspection_buttons:
		inspection_buttons[id].disabled=not interactive
		inspection_buttons[id].text=("✓ " if inspection.get(id,false) else "○ ")+_inspection_labels[id]
	var practice: bool=state.get("practice",false)
	finish_button.text="연습 종료" if practice else "사례 마무리"
	finish_button.disabled=not interactive or (not practice and false in [inspection.get("residual",false),inspection.get("implant",false),inspection.get("wound",false)])
	for key in _settings: _settings[key].set_pressed_no_signal(state.get(key,key=="assisted"))
	_monitor.time=0. if state.get("reduced_motion",false) else elapsed; _monitor.alert=alert!=""; _monitor.queue_redraw()
	_vitals.text="%d  HR     98%%  SpO₂"%roundi(72.+sin(elapsed*.2)*2.)
	var lens: Dictionary=state.get("lens",{}); var capsule: Dictionary=state.get("capsule",{}); var iol: Dictionary=state.get("iol",{})
	_telemetry.text="잔여물 %d%%   ·   IOL %d%%   ·   페달 %s   ·   기록 %d"%[roundi(float(lens.get("remaining_mass",1.))*100),roundi(float(iol.get("delivered",0.))*100),str(state.get("pedal_stage","OFF")),int(state.get("frame_count",0))]
	if lens.has("nucleus_remaining"):
		_telemetry.text+="   ·   핵 %.0f%% / 피질 %.0f%%   ·   부착 해제 %.0f%%"%[float(lens.nucleus_remaining)*100.,float(lens.cortex_remaining)*100.,float(lens.adhesion_released)*100.]
	diagnostics.visible=state.get("debug",false)
	if diagnostics.visible: diagnostics.text="MEMBRANE  strain %.3f / broken %d    LENS  fragments %d / volume %.3f / synthetic pressure %.3f\nIOL alignment %.3f  ·  solver state finite %s"%[capsule.get("max_strain",0.),capsule.get("broken_edges",0),lens.get("fragments",1),lens.get("volume",1.),lens.get("pressure",1.),iol.get("alignment",0.),str(capsule.get("finite",true) and lens.get("finite",true) and iol.get("finite",true))]
	_alert_text.text="환자 움직임이 감지되었습니다. 기구 작동을 멈추고 상태를 평가하세요." if alert=="motion" else "상태 변화: "+alert
	var frames:=maxi(0,int(state.get("frame_count",0)))
	review_slider.max_value=maxi(0,frames-1); review_slider.editable=frames>0
	_viewport_review_slider.max_value=maxi(0,frames-1); _viewport_review_slider.editable=frames>0
	if state.has("review_index"):
		review_slider.set_value_no_signal(state.review_index); _viewport_review_slider.set_value_no_signal(state.review_index)
	if ending!="": _refresh_report(state,director,ending)
	else: _report_signature=""

func _apply_contrast(node: Node,enabled: bool) -> void:
	if node is Label and node.has_meta("original_color"):
		node.add_theme_color_override("font_color",Color.WHITE if enabled else node.get_meta("original_color"))
	for child in node.get_children(): _apply_contrast(child,enabled)

func _tool_id(value: Variant) -> String:
	return str(value.get("id",value.get("tool","forceps"))) if value is Dictionary else str(value)
func _tool_name(tools: Array,index: int) -> String:
	if index>=tools.size(): return "—"
	var id:=_tool_id(tools[index]); var found:=IDS.find(id)
	return NAMES[found] if found>=0 else id
func _refresh_report(state: Dictionary,director: Dictionary,ending: String) -> void:
	var timeline: Array=director.get("timeline",[])
	var observed: Dictionary=state.get("metrics",{})
	var signature:=ending+str(timeline.size())+str(state.get("frame_count",0))+str(observed)
	if signature==_report_signature: return
	_report_signature=signature
	var lens: Dictionary=state.get("lens",{}); var iol: Dictionary=state.get("iol",{})
	var title: String="연습 종료" if state.get("practice",false) else ("사례 완료" if ending=="completed" else "안전 중단")
	var lines: Array[String]=[title,"잔여 수정체 %.1f%%  ·  제거 질량 %.1f%%"%[float(lens.get("remaining_mass",1.))*100,float(lens.get("removed_mass",0.))*100],"IOL 전달 %.1f%%  ·  중심 정렬 %.1f%%"%[float(iol.get("delivered",0.))*100,float(iol.get("alignment",0.))*100],"","관찰 시간 %.1f s  ·  기구 이동 %.3f sim"%[observed.get("time_seconds",state.get("clock",0.)),observed.get("path_length",0.)],"유화 작용 누적 %.3f  (상대 적분)"%observed.get("energy_exposure",0.),"홍채 접촉 %.2f s  ·  후방 접촉 %.2f s"%[observed.get("iris_contacts",0.),observed.get("posterior_contacts",0.)],"전낭 접촉 제한 %.2f s  ·  각막 접촉 제한 %.2f s"%[observed.get("capsule_contacts",0.),observed.get("cornea_contacts",0.)],"막 연결 파열 %d  ·  상처 누출 %.3f  (시뮬레이션 값)"%[observed.get("tissue_breaks",0),observed.get("wound_leak",0.)],"","관찰 기록  /  TIMELINE"]
	for event in timeline.slice(maxi(0,timeline.size()-100)):
		if event is Dictionary: lines.append("%6.1fs   %s"%[event.get("time",0.),_event_caption(event)])
	lines.append("\n수치 기록은 이 시뮬레이션 사례의 관찰값입니다.")
	_report.text="\n".join(lines)

func report_text() -> String:
	return _report.text

func _event_caption(event: Dictionary) -> String:
	var names: Dictionary={"case_started":"사례 시작","preparation":"준비 확인","operation_started":"수술 조작 시작","instrument_selected":"기구 선택","material_removed":"수정체 잔여물 제거 확인","implant_delivery":"IOL 전달 시작","implant_deployed":"IOL 전개 확인","implant_aligned":"IOL 중심 정렬 확인","entry_observed":"진입 상처 관찰","inspection":"최종 검사 확인","inspection_invalidated":"상태 변화로 검사 재확인 필요","patient_motion":"환자 움직임 감지","alert_acknowledged":"환자 상태 평가 · 조작 재개","completed":"사례 완료","safe_stop":"안전 중단"}
	var kind: String=str(event.get("event",""))
	var caption: String=names.get(kind,"관찰 이벤트")
	var details: Dictionary=event.get("details",{})
	if details.has("tool"):
		var id: String=str(details.tool); var index:=IDS.find(id)
		caption+=": "+(NAMES[index] if index>=0 else id)
	if details.has("check"):
		var checks: Dictionary={"patient":"가상 환자","side":"수술 부위","equipment":"장비 점검","residual":"잔여 수정체","implant":"IOL 전개 · 정렬","wound":"진입 상처"}
		caption+=": "+str(checks.get(details.check,details.check))
	if details.has("reason"): caption+=": "+str(details.reason)
	return caption
