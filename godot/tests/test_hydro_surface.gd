extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var geometry=load("res://scripts/anterior_segment.gd").new()
	var lens=load("res://scripts/lens_fluid_solver.gd").new(); lens.geometry=geometry; lens.reset()
	check(lens.material.get("surface_flow")==true,"volumetric cortex has a connected subcapsular flow field")
	if failures: quit(1); return
	var active:=PackedByteArray(); active.resize(lens.particles.size()); active.fill(1)
	var positions:=PackedVector3Array()
	for p in lens.particles: positions.append(p.position)
	var tip:Vector3=positions[19]
	for i in range(100): lens.material.step(.02,tip,0.,positions,active)
	check(lens.material.metrics(active,lens._masses).adhesion_released==0.,"fresh cortex does not release without admitted flow")
	for i in range(5): lens.material.step(.02,tip,1.,positions,active)
	check(lens.material.adhesion[28]>.95,"short local injection does not instantly clear the opposite cortex")
	var before:float=lens.material.adhesion[21]
	for i in range(600): lens.material.step(.02,tip,1.,positions,active)
	check(lens.material.adhesion[21]<before-.05,"accepted flow propagates to a neighboring cortical anchor outside direct tip radius")
	for i in range(positions.size()):
		check(is_finite(lens.material.adhesion[i]) and lens.material.adhesion[i]>=0. and lens.material.adhesion[i]<=1.,"propagated attachment remains bounded")
		if not lens.material.is_cortex(i): check(lens.material.adhesion[i]==0.,"flow field does not turn nuclear bonds into cortex")
	lens.reset()
	check(lens.material.metrics(active,lens._masses).adhesion_released==0.,"reset clears propagated field and restores attachment")
	print("Hydro surface: ",failures," failures"); quit(1 if failures else 0)
