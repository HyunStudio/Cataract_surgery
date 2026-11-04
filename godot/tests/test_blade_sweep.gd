extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	if not FileAccess.file_exists("res://scripts/blade_sweep.gd"):
		check(false,"operator blade sweep module exists");quit(1);return
	var sweep=load("res://scripts/blade_sweep.gd");var profile=load("res://scripts/instrument_profile.gd")
	var renderer=load("res://scripts/surgical_instrument.gd");var tool:Node3D=renderer.build("knife",.018)
	var blade:MeshInstance3D=tool.get_node("Blade");var faces:PackedVector3Array=blade.mesh.get_faces()
	var edges:Array=profile.cutting_edges("knife")
	check(edges.size()==2,"generic pointed blade has two shared leading cutting edges")
	for edge in edges:
		var found:=false
		for i in range(0,faces.size(),3):
			for j in range(3):
				var a:Vector3=blade.transform*faces[i+j];var b:Vector3=blade.transform*faces[i+(j+1)%3]
				if (a.is_equal_approx(edge.a) and b.is_equal_approx(edge.b)) or (a.is_equal_approx(edge.b) and b.is_equal_approx(edge.a)):found=true
		check(found,"cutting edges are real visible blade mesh edges")
		check(edge.a==Vector3.ZERO,"sharp blade tip agrees with the controlled tool origin")
	check(profile.cutting_edges("forceps").is_empty() and profile.cutting_edges("phaco").is_empty(),"nonblade instruments do not acquire sharp-edge cuts")
	for active in [false,true]:
		var stationary:Dictionary=sweep.build("knife",Vector3.ZERO,Vector3.LEFT,Vector3.ZERO,Vector3.LEFT,active)
		check(stationary.valid and stationary.patches.is_empty(),"stationary or inactive blades do not sweep an incision")
	var straight:Dictionary=sweep.build("knife",Vector3(0,.05,0),Vector3.LEFT,Vector3(0,-.05,0),Vector3.LEFT,true)
	check(straight.valid and not straight.patches.is_empty(),"actual moving sharp edges generate finite triangle patches")
	if straight.valid:
		for patch in straight.patches:
			check(patch.size()==3,"blade patches are bounded triangles")
			for point in patch:check(point.is_finite() and point.x>=-1e-6 and point.x<=.180001 and absf(point.z)<=.060001,"sweep follows the blade rather than the long shaft")
	var rotated:Dictionary=sweep.build("knife",Vector3(.1,.2,.3),Vector3.LEFT,Vector3(.12,.21,.3),Vector3(-1,.2,.15).normalized(),true)
	check(rotated.valid and rotated.steps>1 and rotated.patches.size()<=256,"angular blade sweep is sampled with a bounded pose path")
	if rotated.valid:
		var end_points:=PackedVector3Array()
		for patch in rotated.patches:
			for point in patch:end_points.append(point)
		for edge in edges:
			for point in [edge.a,edge.b]:
				var target:Vector3=Vector3(.12,.21,.3)+profile.frame(Vector3(-1,.2,.15).normalized())*point
				check(Array(end_points).any(func(candidate):return candidate.is_equal_approx(target)),"last swept edge matches the actual final rendered pose")
	var passive:Dictionary=sweep.build("forceps",Vector3.ZERO,Vector3.LEFT,Vector3.UP*.1,Vector3.LEFT,true)
	check(passive.valid and passive.patches.is_empty(),"forceps motion never generates blade cuts")
	for args in [[Vector3(NAN,0,0),Vector3.LEFT,Vector3.ZERO,Vector3.LEFT],[Vector3.ZERO,Vector3.ZERO,Vector3.UP*.1,Vector3.LEFT],[Vector3.ZERO,Vector3.LEFT,Vector3(4,0,0),Vector3.LEFT]]:
		var rejected:Dictionary=sweep.build("knife",args[0],args[1],args[2],args[3],true)
		check(not rejected.valid and rejected.patches.is_empty(),"invalid or over-budget motion cannot leave partial cutting patches")
	tool.free();print("Blade sweep: ",failures," failures");quit(1 if failures else 0)
