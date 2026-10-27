extends SceneTree
func _initialize()->void:
	var model=load("res://scripts/anatomy_contact.gd").new()
	var capsule=load("res://scripts/capsule_solver.gd").new()
	var started:=Time.get_ticks_usec()
	for i in range(120): model.resolve(Vector3(.2,.68,0),Vector3(.21,.68,0),.01,"phaco",false,capsule,[[],[]])
	print("Contact query inside chamber: ",(Time.get_ticks_usec()-started)/120000.," ms")
	quit()
