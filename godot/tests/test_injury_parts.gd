extends SceneTree
var failures:=0
class StationaryTip:
	extends RefCounted
	var record:Dictionary
	func stationary(_tip,_radius,_wounds): return [record.duplicate(true)]
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize(): call_deferred("run")
func contact(app,part:String,cut:bool,power:bool)->Dictionary:
	var mesh:Dictionary=app.injury.surfaces.posterior
	var point:Vector3=(mesh.positions[mesh.triangles[0]]+mesh.positions[mesh.triangles[1]]+mesh.positions[mesh.triangles[2]])/3.
	return {"surface":"posterior","point":point,"triangle":0,"revision":0,"load":.00002,"part":part,"cutting":cut,"energy":power}
func reset(app,tool:String):
	app.new_case("standard"); app.hand_tools[0]=tool
	app.grip_down=tool=="knife"; app.pedal_down=tool=="phaco"; app.pedal_stage=3; app.machine.energy=1.
func run():
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	for part in ["shaft","sleeve"]:
		reset(app,"knife"); app._contact_records=[[contact(app,part,false,false)],[]]
		app._update_injury(.05)
		check(not app.injury.metrics().posterior_breached,part+" contact cannot inherit active blade cutting")
		reset(app,"phaco"); app._contact_records=[[contact(app,part,false,false)],[]]
		for i in range(12): app._update_injury(.05)
		check(not app.injury.metrics().posterior_breached,part+" contact cannot inherit ultrasound")
	reset(app,"knife"); app._contact_records=[[contact(app,"blade",true,false)],[]]
	app._update_injury(.05)
	check(app.injury.metrics().posterior_breached,"active working blade still causes local structural injury")
	reset(app,"phaco"); app._contact_records=[[contact(app,"working_tip",false,true)],[]]
	for i in range(12): app._update_injury(.05)
	check(app.injury.metrics().posterior_breached,"powered working tip still causes local structural injury")
	reset(app,"knife"); var legacy:=contact(app,"blade",true,false)
	legacy.erase("part"); legacy.erase("cutting"); legacy.erase("energy")
	app._contact_records=[[legacy],[]]; app._update_injury(.05)
	check(app.injury.metrics().posterior_breached,"legacy tip records retain blade eligibility")
	reset(app,"knife"); var uncertain:=contact(app,"blade",true,false)
	uncertain["conservative"]=true; uncertain.load=.1
	app._contact_records=[[uncertain],[]]
	for i in range(12): app._update_injury(.05)
	check(not app.injury.metrics().posterior_breached,"unproved conservative body candidate cannot cut or accumulate mechanical injury")
	reset(app,"phaco"); uncertain=contact(app,"working_tip",false,true); uncertain["conservative"]=true
	app._contact_records=[[uncertain],[]]
	var actual_anatomy=app.anatomy; var stationary=StationaryTip.new()
	stationary.record=contact(app,"working_tip",false,true); stationary.record.erase("part"); stationary.record.load=0.
	app.anatomy=stationary
	for i in range(9): app._update_injury(.05)
	check(app.injury.metrics().posterior_breached,"uncertain same-face body candidate cannot suppress or dilute proved stationary tip power")
	app.anatomy=actual_anatomy
	app.queue_free(); await process_frame
	print("Injury part dispatch: ",failures," failures"); quit(1 if failures else 0)
