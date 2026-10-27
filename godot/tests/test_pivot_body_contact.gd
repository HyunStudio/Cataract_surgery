extends SceneTree
var failures:=0
func check(ok:bool,message:String):
	if not ok: failures+=1; push_error(message)
func patch()->Dictionary:
	return {"positions":PackedVector3Array([Vector3(1,0,-.4),Vector3(1.5,0,-.4),Vector3(1.5,0,.4),Vector3(1,0,.4)]),"triangles":PackedInt32Array([0,1,2,0,2,3]),"revision":9}
func _initialize():
	if not FileAccess.file_exists("res://scripts/pivot_body_contact.gd"):
		check(false,"portal-constrained body path resolver missing"); quit(1); return
	var solver=load("res://scripts/pivot_body_contact.gd").new()
	var portal:=Vector3(2,.3,0); var start:=Vector3(0,.7,0); var finish:=Vector3(0,-.7,0)
	var mesh:=patch(); var original:PackedInt32Array=mesh.triangles.duplicate()
	var r:Dictionary=solver.resolve(portal,start,(start-portal).normalized(),finish,(finish-portal).normalized(),"phaco",.04,false,{"iris":mesh})
	check(r.valid and r.fraction<1. and r.fraction>0.,"midshaft cannot cross an iris patch with clear tip endpoints")
	check((r.tip-portal).cross(r.axis).length()<1e-6 and r.tip.distance_to(start.lerp(finish,r.fraction))<1e-6,"returned contact pose lies on actual tip path and portal axis")
	check(not r.contacts.is_empty() and r.contacts[0].part=="shaft" and r.contacts[0].revision==9,"body contact preserves part and source provenance")
	check(mesh.triangles==original,"contact cannot change authoritative tissue")
	r=solver.resolve(portal,start,(start-portal).normalized(),finish,(finish-portal).normalized(),"phaco",.04,false,{})
	check(r.valid and r.fraction==1. and r.tip==finish,"unobstructed pivot path reaches exact requested tip")
	r=solver.resolve(portal,start,Vector3.UP,finish,(finish-portal).normalized(),"phaco",.04,false,{})
	check(not r.valid and r.tip==start,"off-pivot source orientation rejects atomically")
	r=solver.resolve(portal,start,(start-portal).normalized(),finish,(finish-portal).normalized(),"phaco",.04,false,{"iris":{}})
	check(not r.valid and r.tip==start,"invalid rigid surface rejects before motion")
	var tiny:=portal+Vector3(0,1e-7,0)
	r=solver.resolve(portal,tiny,Vector3.LEFT,tiny,Vector3.LEFT,"phaco",.04,false,{"iris":mesh})
	check(not r.valid,"near-pivot absolute distance cannot hide an unrelated axis and bypass cone bounds")
	var oversized:Dictionary=mesh.duplicate(true)
	for i in range(70000): oversized.triangles.append_array(PackedInt32Array([0,1,2]))
	r=solver.resolve(portal,start,(start-portal).normalized(),finish,(finish-portal).normalized(),"phaco",.04,false,{"iris":oversized})
	check(not r.valid and r.reason=="geometry_budget","oversized geometry rejects before unbounded body queries")
	var exhausted:={"positions":PackedVector3Array([Vector3(.16,.03,.03)]),"triangles":PackedInt32Array(),"revision":9}
	for i in range(300): exhausted.triangles.append_array(PackedInt32Array([0,0,0]))
	r=solver.resolve(Vector3(2,0,0),Vector3.ZERO,Vector3.LEFT,Vector3(.1,0,0),Vector3.LEFT,"phaco",.04,false,{"posterior":exhausted})
	check(not r.valid and r.reason=="work_budget" and r.tip==Vector3.ZERO and r.contacts.is_empty(),"exhausted sweep cannot invent a triangle or powered injury witness")
	var closure:={"positions":PackedVector3Array([Vector3(.2,-.001,.043),Vector3(.201,.001,.043),Vector3(.2,.001,.044)]),"triangles":PackedInt32Array([0,1,2]),"revision":0}
	r=solver.resolve(Vector3(2,0,0),Vector3.ZERO,Vector3.LEFT,Vector3(.01,0,0),Vector3.LEFT,"forceps",.01,true,{"iris":closure},false)
	check(r.valid and r.fraction==0. and not r.contacts.is_empty(),"closing jaws cannot erase contact in the prior open pose")
	var opening:={"positions":PackedVector3Array([Vector3(.2,-.001,.025),Vector3(.201,.001,.025),Vector3(.2,.001,.026)]),"triangles":PackedInt32Array([0,1,2]),"revision":0}
	r=solver.resolve(Vector3(2,0,0),Vector3.ZERO,Vector3.LEFT,Vector3.ZERO,Vector3.LEFT,"forceps",.01,false,{"iris":opening},true)
	var jaw_load:=0.
	for c in r.contacts:
		if not c.conservative: jaw_load=maxf(jaw_load,c.load)
	check(jaw_load>0.,"proved jaw opening contact uses articulation motion even with a stationary tip")
	var phantom:={"positions":PackedVector3Array([Vector3(.769,.1,.05),Vector3(.769,.10001,.05),Vector3(.769,.1,.05001)]),"triangles":PackedInt32Array([0,1,2]),"revision":0}
	r=solver.resolve(Vector3(2,0,0),Vector3(0,.5,0),Vector3(-2,.5,0).normalized(),Vector3(0,-.5,0),Vector3(-2,-.5,0).normalized(),"phaco",.04,false,{"iris":phantom})
	check(r.valid and not r.contacts.is_empty() and r.contacts[0].conservative and r.contacts[0].load==0.,"inflated near miss blocks conservatively without a fabricated injury witness")
	check(solver.get("use_index")!=null,"body geometry has a source-preserving candidate index")
	if solver.get("use_index")!=null:
		var segment=load("res://scripts/anterior_segment.gd").new()
		var surfaces:={"iris":segment.iris(.96),"posterior":segment.posterior()}
		var a:=Vector3(.4,.1,0); var b:=Vector3(.4,-.4,0); var p:Vector3=segment.portals[0]
		solver.use_index=false
		var exhaustive:Dictionary=solver.resolve(p,a,(a-p).normalized(),b,(b-p).normalized(),"injector",.07,false,surfaces)
		solver.use_index=true
		var indexed:Dictionary=solver.resolve(p,a,(a-p).normalized(),b,(b-p).normalized(),"injector",.07,false,surfaces)
		check(indexed==exhaustive,"candidate pruning preserves exact actual-body result and source IDs")
		surfaces.iris.positions[0]=Vector3(NAN,0,0)
		r=solver.resolve(p,a,(a-p).normalized(),b,(b-p).normalized(),"injector",.07,false,surfaces)
		check(not r.valid,"same-revision source edits cannot reuse stale validated geometry")
	r=solver.resolve(portal,portal,Vector3.LEFT,portal+Vector3.LEFT*.1,Vector3.LEFT,"phaco",.04,false,{})
	check(r.valid and r.fraction==1.,"collinear departure from the pivot has no normalized-axis singularity")
	var departure:Vector3=portal+Vector3(-.04,.03,0)
	r=solver.resolve(portal,portal,Vector3.LEFT,departure,(departure-portal).normalized(),"phaco",.04,false,{"iris":mesh})
	check(r.valid and r.fraction==1.,"outside halfspace certifies oblique pivot departure without a singular angular guess")
	# The exact axis is normalized linear tip displacement, not a free-pose
	# quaternion interpolation. Every point of that curve needs an enclosure.
	var p0:=Vector3(.1,.2,.15); var p1:=Vector3(1.6,-.1,-.1)
	for i in range(10):
		var t0:=i/10.; var t1:=(i+1)/10.
		var interval:Dictionary=solver.interval(portal,p0,p1,(p0-portal).normalized(),1.,3.05,t0,t1)
		check(interval.valid,"bounded normalization interval is supported")
		for j in range(101):
			var s:=j/100.; var t:=lerpf(t0,t1,s); var tip:=p0.lerp(p1,t)
			var exact:Vector3=tip-(tip-portal).normalized()*3.05
			check(exact.distance_to(interval.a.lerp(interval.b,s))<=interval.error+2e-6,"normalized-axis endpoint curve remains inside certified chord error")
	print("Pivot body contact: ",failures," failures"); quit(1 if failures else 0)
