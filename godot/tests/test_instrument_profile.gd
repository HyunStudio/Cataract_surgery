extends SceneTree
var failures := 0
func check(ok:bool,message:String)->void:
	if not ok:
		failures+=1
		push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	if not FileAccess.file_exists("res://scripts/instrument_profile.gd"):
		check(false,"shared dimensioned instrument profile is missing")
		quit(1)
		return
	var profile=load("res://scripts/instrument_profile.gd")
	var ids=["knife","forceps","cannula","manipulator","phaco","ia","injector"]
	for id in ids:
		var segments:Array=profile.segments(id,.04)
		check(not segments.is_empty(),id+" has body geometry")
		var found_shaft:=false
		for segment in segments:
			check(segment.a.is_finite() and segment.b.is_finite() and segment.a.distance_to(segment.b)>0.,id+" has finite nonzero segments")
			check(is_finite(segment.radius) and segment.radius>0.,id+" has positive finite thickness")
			check(segment.has("cutting") and segment.has("energy"),"functional tags present")
			check(maxf(segment.a.x,segment.b.x)<=3.05,"profile excludes external handle")
			if segment.part=="shaft":
				found_shaft=true
				check(segment.a.is_equal_approx(Vector3(.20,0,0)) and segment.b.is_equal_approx(Vector3(3.05,0,0)),"shaft covers inserted body")
				check(is_equal_approx(segment.radius,.04 if id in ["phaco","ia","injector"] else .020),"shaft thickness follows tool type")
		check(found_shaft,"shaft included for "+id)
	var phaco:Array=profile.segments("phaco",.04)
	check(phaco.size()==3,"phaco includes tip shaft and sleeve")
	check(phaco[0].energy and not phaco[0].cutting,"only working phaco tip can transmit energy")
	check(phaco[2].a.is_equal_approx(Vector3(.22,0,0)) and phaco[2].b.is_equal_approx(Vector3(.75,0,0)) and is_equal_approx(phaco[2].radius,.054),"sleeve contact envelope follows rendered dimensions")
	check(profile.segments("knife",.04)[0].cutting,"blade is cutting contact")
	check(profile.segments("knife",.04)[0].radius>=sqrt(.06*.06+.0075*.0075),"blade capsule encloses prism cross section")
	var open:Array=profile.segments("forceps",.04,false)
	var closed:Array=profile.segments("forceps",.04,true)
	check(open.size()==3 and closed.size()==3,"both jaws plus shaft participate")
	var closest:=Geometry3D.get_closest_points_between_segments(closed[0].a,closed[0].b,closed[1].a,closed[1].b)
	check(closest[0].distance_to(closest[1])>=closed[0].radius+closed[1].radius-1e-8,"closed opposing jaw envelopes can touch but cannot interpenetrate and squeeze tissue out of an impossible gap")
	check(open[0].a.is_equal_approx(Vector3(0,0,-.025)) and open[0].b.is_equal_approx(Vector3(.22,0,-.045)),"open jaw contact covers full rod")
	check(closed[0].a.is_equal_approx(Vector3(0,0,-.010)) and closed[0].b.is_equal_approx(Vector3(.22,0,-.018)),"closed jaw endpoints approach centerline without overlapping solids")
	check(closed[2]==open[2],"grip never changes rigid shaft")
	check(profile.segments("cannula",.04)[0].b.is_equal_approx(Vector3(.18,.025,0)),"bent cannula tip retained")
	check(profile.segments("manipulator",.04)[0].b.is_equal_approx(Vector3(.025,0,.06)),"hook retained")
	for invalid_radius in [0.,-.01,NAN,INF]:
		check(profile.segments("phaco",invalid_radius).is_empty(),"invalid radius rejects geometry")
	check(profile.segments("unknown",.04).is_empty(),"unknown tool rejects geometry")
	for axis in [Vector3.LEFT,Vector3(1.,2.,3.),Vector3.UP,Vector3.DOWN]:
		var frame:Basis=profile.frame(axis)
		check(frame.x.is_equal_approx(-axis.normalized()),"local +X points toward handle")
		check(frame.is_finite() and is_equal_approx(frame.determinant(),1.),"contact frame is finite orthonormal rotation")
		check(is_zero_approx(frame.x.dot(frame.y)) and is_zero_approx(frame.x.dot(frame.z)),"frame axes perpendicular")
	check(profile.frame(Vector3.LEFT).is_equal_approx(Basis.IDENTITY),"default render frame matches +X handle")
	check(profile.frame(Vector3.ZERO).is_equal_approx(Basis.IDENTITY),"zero axis falls back safely")
	check(profile.frame(Vector3(NAN,0,0)).is_equal_approx(Basis.IDENTITY),"invalid axis falls back safely")
	check(profile.frame(Vector3(1e30,0,0)).is_equal_approx(Basis.IDENTITY),"overflowing axis magnitude falls back safely")
	var renderer=load("res://scripts/surgical_instrument.gd")
	for id in ids:
		var model:Node3D=renderer.build(id,.04)
		var rods:Array=model.get_children().filter(func(node):return node is MeshInstance3D and node.mesh is CylinderMesh)
		var expected:Array=profile.segments(id,.04)
		var rod_index:=0
		for segment in expected:
			if segment.part=="blade": continue
			# Decorative lumen precedes the actual inserted-body rods.
			var rod:MeshInstance3D=rods[rod_index+(1 if id in ["phaco","ia","injector"] else 0)]
			var half:Vector3=rod.basis.y*rod.mesh.height*.5
			check((rod.position-half).is_equal_approx(segment.a) and (rod.position+half).is_equal_approx(segment.b),"rendered "+segment.part+" endpoints match contact shape for "+id)
			check(is_equal_approx(rod.mesh.top_radius,segment.radius),"rendered "+segment.part+" radius matches contact shape for "+id)
			rod_index+=1
		var shaft:MeshInstance3D=model.get_node("Shaft")
		check(is_equal_approx(shaft.mesh.height,2.85),"rendered shaft reaches profile endpoint")
		check(is_equal_approx(shaft.mesh.top_radius,.04 if id in ["phaco","ia","injector"] else .020),"rendered shaft uses profile thickness")
		if id in ["phaco","ia"]:
			check(is_equal_approx(model.get_node("Sleeve").mesh.top_radius,.054),"rendered sleeve uses contact profile")
		model.free()
	# Exercise the live display and replay path, not just the static builder.
	var display=load("res://scripts/surgical_display.gd").new()
	root.add_child(display)
	display.build()
	display._build_tool_models(true)
	var rigs=[{"tip":Vector3(.1,.2,.3),"axis":Vector3(1,2,3).normalized()},{"tip":Vector3.ZERO,"axis":Vector3.LEFT}]
	for grip in [false,true,false]:
		display._render_tools(rigs,["forceps","phaco"],0,[{"grip":grip},{}])
		var model:Node3D=display.tool_models[0].forceps
		check(model.basis.is_equal_approx(profile.frame(rigs[0].axis)),"live dimensioned tool uses the shared contact frame")
		var jaws:Array=profile.segments("forceps",.018,grip).filter(func(s):return s.part=="jaw")
		check(display._forceps_jaws[0].size()==2,"both live jaws are tracked for closure")
		for i in range(mini(2,display._forceps_jaws[0].size())):
			var rod:MeshInstance3D=display._forceps_jaws[0][i].node
			var half:Vector3=rod.basis.y*rod.mesh.height*.5
			check((rod.position-half).is_equal_approx(jaws[i].a) and (rod.position+half).is_equal_approx(jaws[i].b),"live jaw closure and reopening match both contact endpoints")
	display.free()
	print("Instrument profile tests: ",failures," failures")
	quit(1 if failures else 0)
