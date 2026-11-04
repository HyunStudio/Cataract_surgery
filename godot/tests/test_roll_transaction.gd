extends SceneTree
class RejectingCapsule:
	extends "res://scripts/capsule_solver.gd"
	var observe:Callable
	func requires_physics_transaction()->bool:return true
	func step_tools(_dt:float,_tools:Array[Dictionary])->void:
		observe.call()
		native_failure={"reason":"roll_transaction_probe","status":2}
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func run()->void:
	var app=load("res://scripts/simulator.gd").new();root.add_child(app)
	app.set_physics_process(false);app.set_process(false);app.set_process_input(false)
	await process_frame;app.start_practice();await process_frame
	var model:=RejectingCapsule.new();model.geometry=app.geometry;model.reset();app.capsule=model
	var seen:Array=[];model.observe=func():seen.append(app.rigs[0].roll)
	var event:=InputEventKey.new();event.keycode=KEY_C;event.pressed=true;app._input(event)
	var before:Dictionary=app.rigs[0].capture_state();var clock:float=app.clock
	app._physics_process(1./60.)
	check(seen.size()==1 and seen[0]>0.,"failure happens after a real queued roll enters the physical tick")
	check(app.paused and app.rigs[0].capture_state()==before and app.clock==clock,"rejected tissue step restores complete accepted axial pose and clock")
	check(app._command_rolls==[null,null],"failed physical tick cancels both pending axial intents")
	model.observe=Callable();app.free();await process_frame
	print("Roll transaction: ",failures," failures");quit(1 if failures else 0)
