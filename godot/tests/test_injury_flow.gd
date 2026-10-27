extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	lens.set("rupture_leak",.5)
	var before:float=lens.metrics().volume
	lens.step(.05,Vector3(2,.68,0),false,false)
	var state:Dictionary=lens.metrics()
	if not state.has("rupture_outflow"): push_error("posterior rupture boundary flow missing"); quit(1); return
	check(state.rupture_outflow>0. and state.volume<before,"actual posterior breach drains the anterior compartment")
	check(absf(state.volume-before-(state.inflow-state.outflow)*.05)<1e-8,"macro-step reported flows obey exact integrated volume balance")
	check(state.removed_mass==0. and absf(state.remaining_mass-1.)<1e-6,"boundary leak cannot erase lens material")
	lens.inflow=.5; lens.suction=.7; lens.wound_leak=.2
	before=state.volume; lens.step(.05,Vector3(2,.68,0),false,true); state=lens.metrics()
	check(state.outflow>=state.rupture_outflow+state.leak_outflow,"all leak channels included once in actual total outflow")
	check(absf(state.volume-before-(state.inflow-state.outflow)*.05)<1e-8,"variable flow averages conserve volume")
	lens.inflow=0.
	for i in range(800): lens.step(.05,Vector3(2,.68,0),false,true)
	check(lens.metrics().volume>=.2 and lens.metrics().finite,"prolonged rupture retains finite bounded compartment")
	lens.reset(); check(lens.get("rupture_leak")==0.,"new case clears posterior conductance")
	print("Injury flow: ",failures," failures"); quit(1 if failures else 0)
