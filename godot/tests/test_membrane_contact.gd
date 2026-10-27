extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var source=load("res://scripts/membrane_contact.gd")
	if source==null: check(false,"membrane face contact module exists"); quit(1); return
	var solver=source.new()
	var points:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)])
	var faces:=PackedInt32Array([0,1,2])
	var masses:=PackedFloat64Array([1,1,1])
	var body:=[{"a":Vector3(-.2,.02,0),"b":Vector3(.2,.02,0),"previous_a":Vector3(-.2,.2,0),"previous_b":Vector3(.2,.2,0),"radius":.08}]
	var r:Dictionary=solver.project(points,faces,masses,body,points,.2)
	check(r.valid and r.contacts>0,"shaft touches face interior while all vertices are clear")
	check(r.positions[0].y<0. and r.positions[1].y<0. and r.positions[2].y<0.,"contact distributes displacement to face vertices away from tool")
	check(points[0].y==0.,"projection never mutates input state")
	var pinned:Dictionary=solver.project(points,faces,PackedFloat64Array([0,1,1]),body,points,.2)
	check(pinned.positions[0]==points[0] and pinned.positions[1].y<0.,"pinned vertex remains fixed while movable face responds")
	var fixed:Dictionary=solver.project(points,faces,PackedFloat64Array([0,0,0]),body,points,.2)
	check(fixed.positions==points and fixed.residual>0.,"unsatisfiable fixed contact reports residual without removing tissue")
	body[0].a.y=-.2; body[0].b.y=-.2
	r=solver.project(points,faces,masses,body,points,.5)
	check(r.contacts>0 and r.positions[2].y<0.,"fast crossing retains previous side even when final capsule is clear")
	var invalid:Array=body.duplicate(true); invalid.append({"a":Vector3(NAN,0,0)})
	r=solver.project(points,faces,masses,invalid,points,.2)
	check(not r.valid and r.positions==points,"malformed later body input rejects whole projection atomically")
	var cap=load("res://scripts/capsule_solver.gd").new()
	cap.damping=0.; cap.stretch_compliance=100.
	var center:Vector3=(cap.positions[0]+cap.positions[1]+cap.positions[2])/3.
	var segment:={"a":center+Vector3(-.025,.001,0),"b":center+Vector3(.025,.001,0),"previous_a":center+Vector3(-.025,.05,0),"previous_b":center+Vector3(.025,.05,0),"radius":.01}
	var original:PackedVector3Array=cap.positions.duplicate()
	var tools:Array[Dictionary]=[{"hand":0,"tip":Vector3(3,3,3),"radius":.01,"grip":false,"cut":false,"body":[segment]}]
	cap.step_tools(1./60.,tools)
	check(cap.positions!=original,"actual membrane solver applies distributed body-face response")
	var state:Dictionary=cap.visual_state(); var steps:int=cap.metrics().integration_steps
	tools.append({"hand":1,"tip":Vector3.ZERO,"radius":.01,"grip":false,"cut":false,"body":[{}]})
	cap.step_tools(1./60.,tools)
	check(cap.metrics().integration_steps==steps and cap.visual_state()==state,"malformed second-hand body cannot partly advance actual solver")
	var many:Array=[]
	for i in range(33): many.append(segment.duplicate())
	tools[0].body=many; tools[1].body=many
	cap.step_tools(1./60.,tools)
	check(cap.metrics().integration_steps==steps and cap.visual_state()==state,"aggregate body budget rejects before any hand advances")
	var unequal:Dictionary=solver.project(points,faces,PackedFloat64Array([1,2,1]),[{"a":Vector3(-.2,.02,0),"b":Vector3(.2,.02,0),"previous_a":Vector3(-.2,.2,0),"previous_b":Vector3(.2,.2,0),"radius":.08}],points,.2)
	check(absf(unequal.positions[0].y/unequal.positions[1].y- .35/(2.*.15))<.001,"projection respects unequal inverse masses and barycentric support")
	var moving_old:=PackedVector3Array([Vector3(-1.2,1,0),Vector3(-.8,1,0),Vector3(-1,-1,2)])
	var moving_new:=PackedVector3Array()
	for p in moving_old: moving_new.append(p+Vector3(2,0,0))
	var stationary:=[{"a":Vector3.ZERO,"b":Vector3.ZERO,"previous_a":Vector3.ZERO,"previous_b":Vector3.ZERO,"radius":.08}]
	r=solver.project(moving_new,faces,masses,stationary,moving_old,.2)
	check(r.valid and r.contacts==0 and r.positions==moving_new,"moving face with certified plane clearance cannot be projected from inflated candidate alone")
	var skinny:=PackedVector3Array([Vector3.ZERO,Vector3(.01,0,0),Vector3(0,0,1e-7)])
	r=solver.project(skinny,faces,masses,[{"a":Vector3(.0025,.0005,2.5e-8),"b":Vector3(.0025,.0005,2.5e-8),"previous_a":Vector3(.0025,.02,2.5e-8),"previous_b":Vector3(.0025,.02,2.5e-8),"radius":.001}],skinny,.1)
	check(r.valid and r.contacts>0 and r.positions[0].y<0.,"skinny nonzero membrane face still receives distributed contact")
	var outside:=points.duplicate(); outside[1].x=1e7
	r=solver.project(outside,faces,masses,stationary,outside,.1)
	check(not r.valid and r.positions==outside,"unsupported finite geometry cannot become certified clear")
	r=solver.project(points,faces,PackedFloat64Array([1e300,1,1]),stationary,points,.1)
	check(not r.valid and r.positions==points,"unsupported inverse mass rejects before overflow")
	print("Membrane contact: ",failures," failures"); quit(1 if failures else 0)
