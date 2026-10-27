extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var lens=load("res://scripts/lens_fluid_solver.gd").new()
	check(lens.has_method("visual_state"),"lens provides independent packed presentation state")
	if failures: quit(1); return
	var capsule=load("res://scripts/capsule_solver.gd").new()
	check(capsule.has_method("visual_state"),"capsule provides independent packed presentation state")
	if failures: quit(1); return
	var adapter=load("res://scripts/visual_snapshot.gd")
	var compact:Dictionary=lens.visual_state()
	var expanded:Dictionary=adapter.expand_lens(compact)
	check(expanded.particles==lens.particles and expanded.bonds==lens.bonds,"packed capture preserves all current public particle and bond fields")
	var preserved:Dictionary=expanded.duplicate(true)
	lens.energy=1.; lens.suction=1.
	for i in range(30): lens.step(.02,Vector3(0,.68,0),true,true)
	check(adapter.expand_lens(compact)==preserved,"live fracture and motion cannot mutate frozen packed state")
	expanded.particles[0].position=Vector3(9,9,9); expanded.bonds[0].active=false
	check(adapter.expand_lens(compact)==preserved,"expanded callers cannot mutate the snapshot")
	var latest:Dictionary=lens.visual_state()
	check(adapter.expand_lens(latest)!=preserved,"fixture actually changes lens state before testing isolation")
	check(adapter.expand_lens(latest).particles==lens.particles and adapter.expand_lens(latest).bonds==lens.bonds,"changed damage velocity and activity remain exact")
	latest.positions[0]=Vector3(8,8,8)
	check(lens.particles[0].position!=Vector3(8,8,8),"packed callers cannot modify live solver arrays")
	var legacy:Dictionary={"particles":[],"bonds":[]}
	check(adapter.expand_lens(legacy)==legacy,"empty dictionary replay fixture remains compatible")
	var cap:Dictionary=capsule.visual_state()
	var cap_rich:Dictionary=adapter.expand_capsule(cap)
	check(cap_rich.positions==capsule.positions and cap_rich.triangles==capsule.triangles and cap_rich.edges==capsule.edges,"packed membrane capture preserves all public fields")
	var prior:Dictionary=cap_rich.duplicate(true)
	for i in range(12): capsule.step(.02,Vector3(0,.82,0),.08,false,true)
	check(adapter.expand_capsule(cap)==prior,"cut topology and motion cannot change an earlier capsule snapshot")
	cap.positions[0]=Vector3(7,7,7)
	check(capsule.positions[0]!=Vector3(7,7,7),"packed capsule callers cannot modify live positions")
	var cap_latest:Dictionary=adapter.expand_capsule(capsule.visual_state())
	check(cap_latest.triangles!=prior.triangles,"fixture actually cuts membrane topology before capture")
	check(cap_latest.edges==capsule.edges and cap_latest.triangles==capsule.triangles,"new membrane snapshot follows actual cut topology")
	print("Visual snapshot: ",failures," failures"); quit(1 if failures else 0)
