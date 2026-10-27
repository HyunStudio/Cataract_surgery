extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures+=1; push_error(message)
func _initialize() -> void:
	var source = load("res://scripts/incision_model.gd")
	if source==null:
		push_error("incision model missing")
		quit(1)
		return
	var model = source.new()
	for i in range(60): model.cut(0,Vector3(1.32,.84,0),true)
	check(model.metrics().entry_count==0,"holding a stationary blade cannot create incision")
	for i in range(31): model.cut(0,Vector3(1.32,.84,-.1+float(i)/150.),true)
	check(model.opened[0],"continuous local blade stroke creates entry")
	model.update(1./60.,[.8,.1])
	check(not model.metrics().sealed,"inserted shaft holds wound open")
	for i in range(180): model.update(1./60.,[.05,.05])
	check(model.metrics().sealed,"withdrawal lets elastic gap close")
	model.reset()
	model.cut(0,Vector3(1.32,.84,-.1),true)
	model.cut(0,Vector3(1.32,.84,.1),true)
	check(not model.opened[0],"disconnected endpoint clicks cannot cut wound")
	model.cut(0,Vector3(NAN,.84,0),true)
	check(not model.opened[0],"invalid contact does not change incision")
	print("Incision tests: ",failures," failures")
	quit(1 if failures else 0)
