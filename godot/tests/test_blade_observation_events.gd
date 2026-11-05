extends "res://tests/test_blade_observation.gd"
func new_cut(app)->void:
	app.grip_down=true;roll(app)
	check(app.ui._telemetry.text.contains("새 절개 형성"),"event lifecycle starts with accepted cut feedback")
func hidden_on_refresh(app,message:String)->void:
	var clock:float=app.clock
	app.refresh_ui()
	check(not app.ui._telemetry.text.contains("칼날:") and app.clock==clock,message)
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app)
	app.set_physics_process(false);app.set_process(false);app.set_process_input(false)
	await process_frame;app.start_practice();app.choose_tool("knife")
	var model:=ObservedCapsule.new();model.geometry=app.geometry;model.reset();app.capsule=model
	new_cut(app)
	var release:=InputEventMouseButton.new();release.button_index=MOUSE_BUTTON_LEFT;release.pressed=false
	app._input(release)
	check(not app.grip_down,"actual mouse release disarms cutting before any physics or presentation update")
	hidden_on_refresh(app,"mouse release clears feedback on next HUD refresh without another physics tick")
	new_cut(app)
	app.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	check(not app.grip_down,"actual focus notification immediately disarms cutting")
	hidden_on_refresh(app,"focus loss clears feedback on next HUD refresh")
	new_cut(app)
	var exit_event:=InputEventMouseMotion.new();exit_event.position=Vector2(-100,-100);app._input(exit_event)
	check(not app.grip_down,"pointer exit disarms cutting")
	hidden_on_refresh(app,"pointer exit suppresses feedback at presentation")
	new_cut(app);app.switch_hand()
	hidden_on_refresh(app,"other selected hand cannot display the previous knife observation")
	app.switch_hand();app.choose_tool("knife");new_cut(app);app.choose_tool("forceps")
	hidden_on_refresh(app,"a different instrument cannot display the previous knife observation")
	app.free();await process_frame
	print("Blade observation events: ",failures," failures");quit(1 if failures else 0)
