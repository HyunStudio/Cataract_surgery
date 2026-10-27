extends SceneTree
const UI = preload("res://scripts/simulation_ui.gd")
class FakeApp extends Control:
	var calls: Array = []
	func choose_tool(id): calls.append(["tool",id])
	func switch_hand(): calls.append(["hand"])
	func prepare_check(id): calls.append(["prepare",id])
	func set_machine(key,value): calls.append(["machine",key,value])
	func start_practice(): calls.append(["practice"])
	func withdraw_tools(): calls.append(["withdraw"])
	func preview_frame(index): calls.append(["review",index])
	func set_sound(value): calls.append(["sound",value])
var failures := 0
func check(value: bool,label: String) -> void:
	if not value: failures+=1; printerr("FAIL UI: ",label)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size=Vector2i(1152,800)
	root.content_scale_size=Vector2i(1152,800)
	var app=FakeApp.new()
	root.add_child(app)
	app.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var ui=UI.new()
	app.add_child(ui)
	ui.build(app)
	var state={"director":{"stage":"briefing","ready":false,"preparation":{},"inspection":{},"objective":"준비 확인","timeline":[]},"case_id":"standard","show_briefing":true,"tools":["forceps","phaco"],"selected":0,"latched":[false,false],"machine":{"energy":.3,"suction":.5,"inflow":.5,"focus":.5,"illumination":.8},"frame_count":1}
	ui.refresh(state)
	await process_frame; await process_frame
	check(ui.briefing.visible,"initial briefing visible")
	check(ui.tool_buttons.phaco.disabled,"tools disabled before preparation")
	check(ui.start_button.disabled,"start requires preparation")
	ui.prep_checks.patient.emit_signal("pressed")
	check(app.calls.has(["prepare","patient"]),"preparation callback wired")
	state.director={"stage":"operating","ready":true,"inspection":{},"objective":"조직 상태 확인","timeline":[]}
	state.show_briefing=false
	state.room_view=false
	ui.refresh(state)
	await process_frame
	check(not ui.briefing.visible and not ui.tool_buttons.phaco.disabled,"operation controls available")
	check(ui.viewport_box.size.x>=400 and ui.viewport_box.size.y>=300,"operative viewport usable at1152width")
	check(not ui.viewport_box.get_global_rect().intersects(ui.left_scroll.get_global_rect()),"left panel outside operative viewport")
	check(not ui.viewport_box.get_global_rect().intersects(ui.right_scroll.get_global_rect()),"right panel outside operative viewport")
	print("UI layout: viewport=",ui.viewport_box.get_global_rect()," left=",ui.left_scroll.get_global_rect()," right=",ui.right_scroll.get_global_rect()," root=",ui.size)
	check(ui.right_scroll.get_global_rect().end.x<=1152,"cockpit stays within window")
	ui.tool_buttons.phaco.emit_signal("pressed")
	ui.hand_button.emit_signal("pressed")
	ui.machine_sliders.energy.value=.6
	check(app.calls.has(["tool","phaco"]) and app.calls.has(["hand"]),"tool and hand callbacks wired")
	check(app.calls.has(["machine","energy",.6]),"machine callback wired")
	state.practice=true
	ui.refresh(state)
	check(not ui.finish_button.disabled and ui.finish_button.text=="연습 종료","practice can end without claiming full case completion")
	state.practice=false
	state.high_contrast=true
	ui.refresh(state)
	check(ui.explanation.get_theme_color("font_color")==Color.WHITE,"high contrast changes text rendering")
	state.paused=true
	ui.refresh(state)
	check(ui.tool_buttons.phaco.disabled,"pause disables operative controls")
	state.paused=false
	state.ending="completed"
	state.director.ending="completed"
	state.director.stage="debrief"
	state.director.timeline=[{"time":0.0,"event":"preparation","details":{"check":"side"}},{"time":1.0,"event":"instrument_selected","details":{"tool":"forceps"}},{"time":2.0,"event":"patient_motion"},{"time":3.0,"event":"completed"}]
	state.metrics={"time_seconds":123.4,"path_length":12.34,"energy_exposure":2.5,"iris_contacts":1.2,"posterior_contacts":.4,"tissue_breaks":3,"wound_leak":.125}
	state.frame_count=20
	ui.refresh(state)
	check(ui.debrief.visible and ui.tool_buttons.phaco.disabled,"ending shows debrief and locks tools")
	check(ui.review_slider.max_value==19,"recording slider bounded by captured frames")
	var report: String=ui.report_text()
	check(report.contains("123.4") and report.contains("12.340") and report.contains("접촉") and report.contains("누출"),"debrief presents actionable measured metrics")
	check(report.contains("환자 움직임") and report.contains("전낭 집게") and report.contains("수술 부위") and not report.contains("instrument_selected"),"timeline uses Korean event and instrument/check names")
	state.metrics["length_unit"]="mm"; state.metrics["area_unit"]="mm²"; state.metrics["corneal_damage_area"]=.5
	ui.refresh(state)
	check(ui.report_text().contains("12.340 mm") and ui.report_text().contains("mm²") and ui.report_text().contains("각막 표면 손상"),"dimensioned reports label real length scale and distinguish surface damage")
	state.metrics["extracted_flaps"]=1; state.metrics["extracted_area"]=4.634; state.metrics["retained_detached_area"]=0.
	state.director.timeline.append({"time":10.,"event":"capsule_flap_removed"})
	ui.refresh(state)
	check(ui.report_text().contains("4.634") and ui.report_text().contains("분리 전낭편 인출 확인"),"debrief shows measured extracted area and named flap event")
	ui.sound_toggle.button_pressed=true
	check(app.calls.has(["sound",true]),"sound accessibility toggle invokes app")
	ui.review_slider.value=5
	check(app.calls.has(["review",5]),"review callback wired")
	state.reviewing=true
	ui.refresh(state)
	check(not ui.debrief.visible and ui.review_controls.visible,"recorded viewport has reachable review exit controls")
	app.queue_free()
	await process_frame
	print("Simulation UI tests: ","PASS" if failures==0 else str(failures)+" failures")
	quit(0 if failures==0 else 1)
