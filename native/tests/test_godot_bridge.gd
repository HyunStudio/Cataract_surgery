extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	if not ClassDB.class_exists("MembraneKernel"):
		push_error("native MembraneKernel must register through GDExtension")
		quit(1); return
	var kernel=ClassDB.instantiate("MembraneKernel")
	check(ClassDB.class_exists("MembraneContactKernel"),"native coupled contact kernel registers separately")
	if failures: quit(1); return
	var coupled=ClassDB.instantiate("MembraneContactKernel")
	var local:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://local_jaw_contact.json"))
	var face_ids:=PackedInt32Array(); var body_data:=PackedFloat64Array()
	for face in local.triangles:
		for index in face: face_ids.append(index)
	for body in local.capsules:
		for value in body.a: body_data.append(value)
		for value in body.b: body_data.append(value)
		body_data.append(body.radius)
	var request:Dictionary={"predicted":PackedFloat64Array(local.predicted),"initial":PackedFloat64Array(local.initial),"inverse":PackedFloat64Array(local.inverse),"a":PackedInt32Array(local.a),"b":PackedInt32Array(local.b),"rest":PackedFloat64Array(local.rest),"alpha":local.alpha,"triangles":face_ids,"capsules":body_data,"budget":100,"force_tolerance":1e-8,"gap_tolerance":1e-9,"complementarity_tolerance":1e-11}
	var preserved:Dictionary=request.duplicate(true)
	var contact:Dictionary=coupled.solve_contact(request)
	check(contact.status==0 and contact.stats.size()==12 and contact.xyz is PackedFloat64Array,"joint energy/contact retains a float64engine boundary")
	check(request==preserved,"joint result never mutates caller predictor positions topology or bodies")
	check(contact.xyz.size()==request.initial.size() and contact.dual.size()==local.triangles.size()*local.capsules.size(),"joint bridge retains every material point and contact reaction")
	check(contact.stats[1]<=1e-8 and contact.stats[2]<=1e-9 and contact.stats[3]<=1e-11,"joint bridge preserves force feasibility and complementarity diagnostics")
	check(absf(contact.stats[0]-1.2512200570759009e-8)<2e-10,"joint bridge agrees with independent local constrained energy")
	for malformed in [{}, {"initial":PackedVector3Array()}, request.merged({"initial":PackedFloat64Array([0,0])},true), request.merged({"triangles":PackedInt32Array([0,1])},true), request.merged({"capsules":PackedFloat64Array([0,0,0])},true), request.merged({"a":PackedInt32Array()},true), request.merged({"budget":1.5},true)]:
		var invalid:Dictionary=coupled.solve_contact(malformed)
		check(invalid.status==-1,"joint malformed types/shapes reject before native pointer access")
	var limited:Dictionary=coupled.solve_contact(request.merged({"budget":0},true))
	check(limited.status==1 and limited.xyz==request.initial,"joint exhaustion never publishes a partial physical state")
	print("Native coupled bridge: ",contact.stats)
	var xyz:=PackedFloat64Array([0,0,0,2,0,0])
	var inverse:=PackedFloat64Array([1,2])
	var a:=PackedInt32Array([0]); var b:=PackedInt32Array([1]); var rest:=PackedFloat64Array([1])
	var solved:Dictionary=kernel.solve(xyz,inverse,a,b,rest,.1,100,1e-10)
	check(solved.status==0,"analytic spring converges through Godot bridge")
	check(absf(solved.xyz[0]-1./3.1)<1e-9 and absf(solved.xyz[3]-(2.-2./3.1))<1e-9,"double precision solution survives Godot boundary")
	check(xyz==PackedFloat64Array([0,0,0,2,0,0]),"native output does not mutate caller's packed input")
	check(solved.stats.size()==8 and solved.stats[1]<=1e-10,"bridge preserves objective diagnostics")
	for malformed in [PackedFloat64Array([0,0]),PackedFloat64Array([0,0,0])]:
		var rejected:Dictionary=kernel.solve(malformed,inverse,a,b,rest,.1,100,1e-10)
		check(rejected.status==-1 and rejected.xyz==malformed,"shape mismatch rejects before native pointer access")
	var bad_edges:Dictionary=kernel.solve(xyz,inverse,PackedInt32Array(),b,rest,.1,100,1e-10)
	check(bad_edges.status==-1,"mismatched edge arrays reject before native pointer access")
	var exhausted:Dictionary=kernel.solve(xyz,inverse,a,b,rest,.1,0,1e-10)
	check(exhausted.status==1 and exhausted.xyz==xyz,"work exhaustion is preserved through bridge")
	var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://refined_flap.json"))
	var points:=PackedFloat64Array(); var ea:=PackedInt32Array(); var eb:=PackedInt32Array(); var lengths:=PackedFloat64Array()
	for point in data.positions:
		for value in point: points.append(value)
	for i in range(data.a.size()):
		if data.active[i]: ea.append(data.a[i]); eb.append(data.b[i]); lengths.append(data.rest[i])
	var start:=Time.get_ticks_usec()
	var scene:Dictionary=kernel.solve(points,PackedFloat64Array(data.inverse),ea,eb,lengths,data.alpha,100,1e-8)
	var elapsed:=Time.get_ticks_usec()-start
	check(scene.status==0 and scene.stats[1]<=1e-8,"actual refined-flap input converges through Godot")
	check(scene.stats[0]<=3.8194e-8,"Godot bridge preserves the independent energy reference")
	check(scene.xyz.size()==points.size(),"Godot bridge retains every material point")
	print("Native bridge scene: ",scene.stats," usec=",elapsed)
	print("Native Godot bridge: ",failures," failures")
	quit(1 if failures else 0)
