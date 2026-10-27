extends SceneTree
var failures := 0
func check(ok: bool, message: String) -> void:
	if not ok: failures += 1; push_error(message)
func _initialize() -> void:
	if not ResourceLoader.exists("res://scripts/iol_dynamics.gd"):
		check(false,"IOL dynamics implementation missing"); quit(1); return
	var s = load("res://scripts/iol_dynamics.gd").new()
	var nozzle := Vector3(.25,.72,0)
	for i in range(120): s.step(1./60.,nozzle,false,Vector3(3,3,3),false)
	check(s.metrics().delivered==0.,"idle cannot advance injector plunger")
	for i in range(30): s.step(1./60.,nozzle,true,Vector3(3,3,3),false)
	var partial: float = s.metrics().delivered
	check(partial>0. and partial<1.,"user plunger yields partial delivery")
	for i in range(100): s.step(1./60.,nozzle,false,Vector3(3,3,3),false)
	check(is_equal_approx(s.metrics().delivered,partial),"release pauses plunger without stopping free elastic recovery")
	for i in range(180): s.step(1./60.,nozzle,true,Vector3(3,3,3),false)
	for i in range(300): s.step(1./60.,nozzle,false,Vector3(3,3,3),false)
	check(s.metrics().deployed,"released optic and haptics recover elastic rest shape")
	check(s.positions[0].distance_to(s.positions[s.optic_count/2])>.8,"deployment measures real expanded optic")
	var before: float = s.metrics().alignment
	check(before<.6,"free recovery must not silently center offaxis implantation")
	for i in range(180):
		var x := .81-.25*float(i)/179.
		s.step(1./60.,nozzle,false,Vector3(x,.72,0),true)
	check(s.metrics().alignment>before+.1,"local manipulator contact translates actual implant toward center")
	var saved: PackedVector3Array = s.positions.duplicate()
	for bad in [NAN,INF,-1.,0.,1.]: s.step(bad,nozzle,true,Vector3.ZERO,true)
	s.step(1./60.,Vector3(NAN,0,0),true,Vector3.ZERO,true)
	check(s.positions==saved,"invalid input cannot partly mutate implant")
	check(s.metrics().finite,"implant stays finite")
	for i in range(240): s.step(.05,nozzle,false,Vector3(sin(i*.1),.72,cos(i*.1)),true)
	check(s.metrics().finite and s.metrics().alignment>=0. and s.metrics().alignment<=1.,"maximum accepted step and moving contacts remain bounded")
	s.reset()
	check(s.metrics().delivered==0. and not s.metrics().deployed,"reset returns implant to cartridge")
	print("IOL dynamics: ",failures," failures"); quit(1 if failures else 0)
