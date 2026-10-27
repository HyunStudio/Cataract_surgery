extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func plane(y:float,x0:float=-4.,x1:float=4.)->Dictionary:
	return {"positions":PackedVector3Array([Vector3(x0,y,-4),Vector3(x1,y,-4),Vector3(x1,y,4),Vector3(x0,y,4)]),"triangles":PackedInt32Array([0,1,2,0,2,3]),"revision":7}
func _initialize()->void:
	if not FileAccess.file_exists("res://scripts/instrument_body_contact.gd"):
		check(false,"whole instrument body contact resolver missing"); quit(1); return
	var solver=load("res://scripts/instrument_body_contact.gd").new()
	var r:Dictionary=solver.resolve(Vector3(0,.5,0),Vector3.LEFT,Vector3(0,-.5,0),Vector3.LEFT,"phaco",.04,false,{"iris":plane(0.,1.,2.)})
	check(r.valid and r.fraction<.5,"shaft midpoint cannot tunnel when tip misses finite patch")
	check(not r.contacts.is_empty() and r.contacts[0].part=="shaft","midshaft witness names shaft")
	if not r.contacts.is_empty():
		var c:Dictionary=r.contacts[0]
		check(c.surface=="iris" and c.revision==7 and c.triangle>=0 and c.point.is_finite(),"contact retains mesh provenance")
		check(not c.cutting and not c.energy,"rigid shaft never inherits working-tip function")
	r=solver.resolve(Vector3(0,.1,0),Vector3.LEFT,Vector3(0,0,0),Vector3.LEFT,"phaco",.04,false,{"cornea":plane(0.,.3,.6)})
	check(r.valid and r.fraction<.6 and not r.contacts.is_empty() and r.contacts[0].part=="sleeve","larger sleeve blocks before narrow shaft")
	for tool in ["knife","phaco"]:
		r=solver.resolve(Vector3(0,.5,0),Vector3.LEFT,Vector3(0,-.5,0),Vector3.LEFT,tool,.04,false,{"posterior":plane(0.,1.,2.)})
		for c in r.contacts: check(not c.cutting and not c.energy,"shaft contact cannot cut or energize for "+tool)
	r=solver.resolve(Vector3(0,.01,0),Vector3.LEFT,Vector3(0,.01,0),Vector3.LEFT,"injector",.04,false,{"iris":plane(0.)})
	check(r.valid and r.recovered and r.tip.y>.04,"stationary overlapping tool is pushed outside actual surface")
	var kernel=load("res://scripts/capsule_surface.gd").new()
	var profile=load("res://scripts/instrument_profile.gd")
	for s in profile.segments("injector",.04):
		var hit:Dictionary=kernel.query(r.tip+profile.frame(r.axis)*s.a,r.tip+profile.frame(r.axis)*s.b,s.radius,plane(0.).positions,plane(0.).triangles)
		check(not hit.hit,"recovered pose has clearance for every segment")
	# A half-turn about world Y sweeps through z=+/-2; endpoint poses lie z=0.
	var front:=plane(2.,-1.,1.); var back:=plane(-2.,-1.,1.)
	for mesh in [front,back]:
		for i in range(mesh.positions.size()):
			var p:Vector3=mesh.positions[i]
			mesh.positions[i]=Vector3(p.x,p.z,p.y)
	r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3.ZERO,Vector3.RIGHT,"injector",.02,false,{"iris":front,"cornea":back})
	check(r.valid and r.fraction<1. and not r.contacts.is_empty(),"large angular sweep cannot shortcut endpoint arc")
	r=solver.resolve(Vector3(0,.5,0),Vector3.LEFT,Vector3(0,-.5,0),Vector3.LEFT,"phaco",.04,false,{"anterior":plane(0.)})
	check(r.valid and r.fraction==1. and r.contacts.is_empty(),"elastic anterior capsule excluded from rigid resolver")
	for malformed in [{"iris":{}},{"iris":{"positions":PackedVector3Array([Vector3.ZERO]),"triangles":PackedInt32Array([0,1,2])}},{"iris":{"positions":PackedVector3Array([Vector3(NAN,0,0)]),"triangles":PackedInt32Array()}}]:
		r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3.ONE,Vector3.LEFT,"phaco",.04,false,malformed)
		check(not r.valid and r.fraction==0. and r.tip==Vector3.ZERO,"malformed mesh fails closed atomically")
	for tool in ["missing"]:
		r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3.ONE,Vector3.LEFT,tool,.04,false,{})
		check(not r.valid and r.fraction==0.,"unknown tool fails closed")
	r=solver.resolve(Vector3.ZERO,Vector3.ZERO,Vector3.ONE,Vector3.LEFT,"phaco",.04,false,{})
	check(not r.valid and r.fraction==0.,"invalid axis fails closed")
	for invalid_radius in [0.,-1.,NAN,INF,1000001.]:
		r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3.ONE,Vector3.LEFT,"phaco",invalid_radius,false,{})
		check(not r.valid and r.fraction==0.,"invalid body radius fails closed without surfaces")
	r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3(NAN,0,0),Vector3.LEFT,"phaco",.04,false,{})
	check(not r.valid and r.fraction==0. and r.tip==Vector3.ZERO,"nonfinite proposed pose preserves accepted origin")
	r=solver.resolve(Vector3.ZERO,Vector3.LEFT,Vector3.ONE,Vector3.LEFT,"phaco",.04,false,{})
	check(r.valid and r.fraction==1. and r.tip==Vector3.ONE,"absent rigid surfaces allow motion")
	print("Instrument body contact: ",failures," failures"); quit(1 if failures else 0)
