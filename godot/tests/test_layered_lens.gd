extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	lens.set("layered",true)
	var initial:Dictionary=lens.metrics()
	if not initial.has("nucleus_remaining"):
		push_error("layered solver metrics missing"); quit(1); return
	check(initial.nucleus_remaining>0. and initial.cortex_remaining>0.,"both anatomical material classes exist")
	lens.inflow=1.; lens.set("hydro_flow",1.)
	for i in range(90): lens.step(1./60.,Vector3(.66,.76,0),false,false)
	var state:Dictionary=lens.metrics()
	check(state.adhesion_released>.005,"cannula local inflow releases cortical adhesion")
	check(state.removed_mass==0.,"hydrodissection alone cannot delete tissue")
	check(state.adhesion_released<.5,"one local jet cannot globally detach all cortex")
	check(absf(state.nucleus_remaining+state.cortex_remaining+state.removed_mass-1.)<1e-6,"layer subtotals conserve total mass")
	var baseline=load("res://scripts/lens_fluid_solver.gd").new(); baseline.set("layered",true); baseline.inflow=1.
	for i in range(90): baseline.step(1./60.,Vector3(.66,.76,0),false,false)
	check(baseline.metrics().adhesion_released==0.,"ordinary irrigation does not act as cannula hydrodissection")
	var nucleus_before:float=baseline.metrics().nucleus_remaining
	baseline.suction=1.
	for i in range(120): baseline.step(1./60.,Vector3(0,.68,0),false,true)
	check(absf(baseline.metrics().nucleus_remaining-nucleus_before)<1e-6,"central aspiration cannot emulate nuclear ultrasonic fracture")
	var peeling=load("res://scripts/lens_fluid_solver.gd").new(); peeling.layered=true; peeling.inflow=1.; peeling.wound_leak=1.; peeling.hydro_flow=1.
	for step in range(2200):
		var most_attached:=-1.; var hydro_tip:=Vector3(2,.76,0)
		for i in range(peeling.particles.size()):
			if peeling.material.is_cortex(i) and peeling.material.adhesion[i]>most_attached:
				most_attached=peeling.material.adhesion[i]; hydro_tip=peeling.particles[i].position+Vector3(0,.04,0)
		if most_attached<.1: break
		peeling.step(1./60.,hydro_tip,false,false)
	peeling.hydro_flow=0.; peeling.suction=1.
	var cortical_tip:=Vector3(.66,.68,0)
	for step in range(900):
		var nearest:=INF; var found:=false
		for i in range(peeling.particles.size()):
			if not peeling.material.is_cortex(i) or not peeling.particles[i].active: continue
			var next:float=peeling.particles[i].position.distance_squared_to(cortical_tip)
			if next<nearest: nearest=next; cortical_tip=peeling.particles[i].position; found=true
		if not found: break
		peeling.step(1./60.,cortical_tip,false,true)
	var peeled:Dictionary=peeling.metrics()
	check(peeled.cortex_remaining<initial.cortex_remaining*.5,"IA without ultrasound can peel locally released cortex")
	check(peeled.nucleus_remaining>initial.nucleus_remaining*.9,"cortical IA preserves the nuclear material")
	print("Cortical IA: ",JSON.stringify(peeled))
	var blocked=load("res://scripts/lens_fluid_solver.gd").new(); blocked.layered=true; blocked.inflow=1.
	for i in range(200): blocked.step(.05,Vector3(2,.68,0),false,false)
	blocked.hydro_flow=1.
	for i in range(40): blocked.step(1./60.,Vector3(.66,.76,0),false,false)
	check(blocked.metrics().inflow==0. and blocked.metrics().adhesion_released==0.,"commanded pump without admitted flow cannot hydrodissect")
	lens.hydro_flow=0.; lens.energy=1.; lens.suction=1.; lens.inflow=1.
	var tip:=Vector3(.6,.68,0)
	for step in range(3500):
		var distance:=INF; var found:=false
		for particle in lens.particles:
			if not particle.active: continue
			var next:float=particle.position.distance_squared_to(tip)
			if next<distance: distance=next; tip=particle.position; found=true
		if not found: break
		lens.step(1./60.,tip,true,true)
	state=lens.metrics()
	check(state.finite and state.removed_mass>=.98,"layered model remains physically removable through local fracture/aspiration")
	check(absf(state.nucleus_remaining+state.cortex_remaining-state.remaining_mass)<1e-6,"partial and complete removal retain material identity")
	print("Layered lens: ",failures," failures; ",JSON.stringify(state)); quit(1 if failures else 0)
