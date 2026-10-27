extends SceneTree
var failures:Array[String]=[]
func check(ok:bool,message:String)->void:
	if not ok: failures.append(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	var script=load("res://scripts/lens_fluid_solver.gd")
	check(script!=null and script.can_instantiate(),"Lens/fluid solver must load")
	if script==null or not script.can_instantiate(): finish(); return
	var solver=script.new()
	var bench=script.new()
	var started:=Time.get_ticks_usec()
	for i in range(180): bench.step(1.0/60.0,Vector3(2,.68,0),false,false)
	print("Lens benchmark: ",(Time.get_ticks_usec()-started)/180000.0," ms per 60Hz step;111 particles, baseline material")
	solver.reset()
	check(solver.particles.size()>=80 and solver.particles.size()<=150,"Lens is a bounded connected particle material")
	var initial=solver.particles.duplicate(true)
	for i in range(300): solver.step(1.0/60.0,Vector3(2,.68,0),false,false)
	var state:Dictionary=solver.metrics()
	check(absf(state.remaining_mass-1.0)<1e-6 and state.removed_mass==0.0,"No-op preserves lens mass")
	check(state.fragments==1,"Undisturbed lens remains connected")
	for i in range(initial.size()):
		check(solver.particles[i].position.distance_to(initial[i].position)<1e-5,"Unloaded spring material stays at equilibrium")
	var tip:=Vector3(.42,.68,0)
	solver.energy=1.0
	var distant: Array[int]=[]
	for i in range(solver.bonds.size()):
		var bond:Dictionary=solver.bonds[i]
		if solver.particles[bond.a].position.distance_to(tip)>.5 and solver.particles[bond.b].position.distance_to(tip)>.5: distant.append(i)
	for i in range(120): solver.step(1.0/60.0,tip,true,false)
	var broken:=0
	for bond in solver.bonds:
		if not bond.active: broken+=1
	check(broken>0,"Local energy/contact breaks actual material links")
	check(solver.metrics().remaining_mass>0.999,"Fragmentation alone cannot delete mass")
	var intact_far:=0
	for index in distant:
		if solver.bonds[index].active: intact_far+=1
	check(intact_far>=distant.size()*.85,"Local contact preserves distant lens connections")
	solver.suction=1.0
	var removed_before:float=solver.metrics().removed_mass
	for i in range(600): solver.step(1.0/60.0,tip,false,true)
	state=solver.metrics()
	check(state.removed_mass>removed_before,"Aspiration transports liberated particles into tip")
	check(state.remaining_mass>0.25,"A local stationary action cannot globally remove the lens")
	check(absf(state.remaining_mass+state.removed_mass-1.0)<1e-6,"Active and removed lens masses sum to initial mass")
	for particle in solver.particles:
		if not particle.active: check(particle.position.distance_to(tip)<=.055,"Removed particles actually reached inlet")
	check(state.finite,"Fragmentation/aspiration remains numerically finite")
	# Pure mechanical collision must also deform and fracture material without phaco energy.
	solver.reset()
	for i in range(120):
		var mechanical_tip:=Vector3(0.0,.63+float(i)/120.0*.12,0.0)
		solver.step(1.0/60.0,mechanical_tip,true,false)
	var mechanical_breaks:=0
	for bond in solver.bonds:
		if not bond.active: mechanical_breaks+=1
	check(mechanical_breaks>0,"Mechanical displacement can break strained links without energy")
	check(solver.metrics().removed_mass==0.0,"Mechanical breakup preserves all material")
	# Clean compartment has no occlusion; equal normalized inflow/outflow balances volume.
	solver.reset()
	solver.inflow=.5
	solver.suction=.5
	for i in range(600): solver.step(1.0/60.0,Vector3(1.2,.68,0),false,true)
	state=solver.metrics()
	check(absf(state.volume-1.0)<1e-5,"Balanced flow preserves compartment volume")
	check(absf(state.inflow-state.outflow)<1e-6,"Unobstructed equal controls produce equal flow")
	solver.inflow=0.0
	for i in range(300): solver.step(1.0/60.0,Vector3(1.2,.68,0),false,true)
	check(solver.metrics().volume<.99 and solver.metrics().pressure<1.0,"Unbalanced outflow lowers volume and synthetic pressure")
	solver.reset()
	solver.suction=1.0
	solver.step(1.0/60.0,Vector3(1.2,.68,0),false,true)
	var open_out:float=solver.metrics().outflow
	solver.step(1.0/60.0,Vector3(.42,.68,0),false,true)
	check(solver.metrics().outflow<open_out,"Connected tissue occludes local outflow")
	var stable:Dictionary=solver.metrics().duplicate(true)
	var positions=solver.particles.duplicate(true)
	for bad_dt in [0.0,-.01,.5,NAN,INF]: solver.step(bad_dt,tip,true,true)
	solver.step(1.0/60.0,Vector3(NAN,.68,0),true,true)
	solver.step(1.0/60.0,Vector3(INF,.68,0),true,true)
	check(solver.particles==positions and solver.metrics()==stable,"Invalid dt/tip are refused without partial mutation")
	solver.reset()
	solver.suction=1.0
	for i in range(180): solver.step(1.0/60.0,Vector3(.42,.68,0),false,true)
	check(solver.metrics().removed_mass==0.0,"Suction cannot delete connected intact tissue")
	# Maximum accepted steps, moving contact, and extreme controls remain bounded.
	solver.inflow=5.0
	solver.suction=2.0
	solver.energy=3.0
	for i in range(120):
		var moving_tip:=Vector3(sin(i*.12)*.55,.68+cos(i*.07)*.04,cos(i*.12)*.55)
		solver.step(.05,moving_tip,true,true)
	state=solver.metrics()
	check(state.finite and state.volume>=.2 and state.volume<=1.6,"Maximum-step moving contact keeps bounded finite material and compartment")
	check(absf(state.remaining_mass+state.removed_mass-1.0)<1e-6,"Stress run conserves total mass")
	check(solver.inflow==1.0 and solver.suction==1.0 and solver.energy==1.0,"Research controls are bounded before integration")
	for particle in solver.particles:
		check(particle.velocity.length()<=2.401,"Particle velocity remains bounded")
	# Mechanical contact is independent of the energy/activation switch.
	solver.reset()
	var passive_initial=solver.particles.duplicate(true)
	for i in range(12): solver.step(1.0/60.0,Vector3(0,.63,0),false,false)
	var unpowered_motion:=0.0
	for i in range(solver.particles.size()): unpowered_motion=maxf(unpowered_motion,solver.particles[i].position.distance_to(passive_initial[i].position))
	check(unpowered_motion>.0001,"Unpowered selected tip mechanically deforms local material")
	check(solver.metrics().removed_mass==0.0,"Unpowered contact cannot delete mass")
	var energy_damage:=0.0
	for bond in solver.bonds: energy_damage+=float(bond.damage)
	check(energy_damage==0.0,"Unpowered contact does not deposit energy damage")
	solver.reset()
	passive_initial=solver.particles.duplicate(true)
	# Set through Object to make the RED failure readable before property exists.
	solver.set("passive_tips",PackedVector3Array([Vector3(0,.63,0)]))
	for i in range(12): solver.step(1.0/60.0,Vector3(2,.68,0),false,false)
	var other_motion:=0.0
	for i in range(solver.particles.size()): other_motion=maxf(other_motion,solver.particles[i].position.distance_to(passive_initial[i].position))
	check(other_motion>.0001,"Retained passive instrument mechanically deforms material")
	check(solver.metrics().removed_mass==0.0,"Passive instrument preserves mass")
	var before_bad=solver.particles.duplicate(true)
	var metrics_before_bad=solver.metrics().duplicate(true)
	solver.set("passive_tips",PackedVector3Array([Vector3(NAN,0,0)]))
	solver.step(1.0/60.0,Vector3(.4,.68,0),true,true)
	check(solver.particles==before_bad and solver.metrics()==metrics_before_bad,"Invalid passive contact is rejected before any integration")
	var standard=script.new()
	var dense=script.new()
	dense.set("hardness",.8)
	standard.energy=1.0; dense.energy=1.0
	# Compare before both exposures saturate the same local neighborhood.
	for i in range(9):
		standard.step(1.0/60.0,Vector3(.42,.68,0),true,false)
		dense.step(1.0/60.0,Vector3(.42,.68,0),true,false)
	var standard_broken:=0
	var dense_broken:=0
	for bond in standard.bonds:
		if not bond.active: standard_broken+=1
	for bond in dense.bonds:
		if not bond.active: dense_broken+=1
	print("Material fracture comparison: standard=",standard_broken,", dense=",dense_broken)
	check(dense_broken<standard_broken,"Dense material fractures fewer links for the same local energy exposure")
	solver.reset()
	solver.set("wound_leak",.5)
	var volume_before:float=solver.metrics().volume
	solver.step(1.0/60.0,Vector3(2,.68,0),false,false)
	state=solver.metrics()
	check(state.volume<volume_before and absf(state.outflow-.04)<1e-6,"External wound leakage lowers volume and appears in actual outflow")
	check(absf(state.volume-volume_before-(state.inflow-state.outflow)/60.0)<1e-6,"Leak compartment obeys its reported volume balance")
	check(state.remaining_mass>0.99999 and state.removed_mass==0.0,"Wound leakage does not delete lens mass")
	check(absf(state.leak_outflow-state.outflow)<1e-6,"Leak is reported separately and included once in total outflow")
	solver.reset(); solver.hardness=100.0; solver.wound_leak=INF
	solver.step(1.0/60.0,Vector3(2,.68,0),false,false)
	check(solver.hardness==1.0 and solver.wound_leak==0.0 and solver.metrics().finite,"Hardness clamps and nonfinite leakage safely disables external flow")
	solver.hardness=NAN; solver.wound_leak=-100.0
	solver.step(1.0/60.0,Vector3(2,.68,0),false,false)
	check(solver.hardness==.4 and solver.wound_leak==0.0,"Nonfinite hardness returns to baseline and negative leakage clamps")
	solver.reset(); solver.energy=1.0; solver.suction=1.0; solver.inflow=1.0
	var sweep_tip:=Vector3(.66,.68,0)
	for i in range(3000):
		var nearest:=INF
		var found:=false
		for particle in solver.particles:
			if not particle.active: continue
			var distance:float=particle.position.distance_squared_to(sweep_tip)
			if distance<nearest:
				nearest=distance; tip=particle.position; found=true
		if not found: break
		sweep_tip=tip
		solver.step(1.0/60.0,sweep_tip,true,true)
	state=solver.metrics()
	check(state.removed_mass>=.98 and absf(state.remaining_mass+state.removed_mass-1)<1e-6,"Adaptive physical phaco/aspiration sweep can remove at least98percent with mass conservation")
	print("Adaptive sweep removed mass: ",state.removed_mass)
	finish()
func finish()->void:
	for message in failures: push_error(message)
	print("LENS/FLUID: ","PASS" if failures.is_empty() else "FAIL (%d)"%failures.size())
	quit(0 if failures.is_empty() else 1)
