extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void:
	var source=load("res://scripts/anatomy_contact.gd")
	if source==null: push_error("anatomy contact coordinator missing"); quit(1); return
	var model=source.new()
	var membrane=load("res://scripts/capsule_solver.gd").new()
	var original:Vector3=membrane.positions[0]
	var tools:Array[Dictionary]=[{"hand":0,"tip":Vector3(0,.86,0),"radius":.065,"contact_radius":.018,"grip":false,"cut":false}]
	membrane.step_tools(1./60.,tools)
	check(membrane.positions[0].distance_to(original)<.000001,"grasp reach must not enlarge the solid contact radius")
	var capsule={"positions":PackedVector3Array(),"triangles":PackedInt32Array()}
	var wounds:=[[],[]]
	var result:Dictionary=model.resolve(Vector3(0,.75,0),Vector3(0,.40,0),.018,"phaco",false,capsule,wounds)
	check("posterior" in result.contacts and result.position.y>.51,"posterior bowl blocks downward approach geometrically")
	result=model.resolve(Vector3(.9,.85,0),Vector3(.9,.68,0),.018,"phaco",false,capsule,wounds)
	check("iris" not in result.contacts,"normal pupil includes radius .9")
	model.set_pupil(.74)
	result=model.resolve(Vector3(.9,.85,0),Vector3(.9,.68,0),.018,"phaco",false,capsule,wounds)
	check("iris" in result.contacts and result.position.y>.78,"small pupil changes actual annular contact")
	result=model.resolve(Vector3(0,1.1,0),Vector3(0,.85,0),.018,"phaco",false,capsule,wounds)
	check("cornea" in result.contacts,"corneal dome blocks external penetration")
	wounds[0]=[Vector3(0,.932,-.1),Vector3(0,.932,.1)]
	result=model.resolve(Vector3(0,1.1,0),Vector3(0,.85,0),.018,"phaco",false,capsule,wounds)
	check(not "cornea" in result.contacts,"only the spatial incision path provides corneal passage")
	result=model.resolve(Vector3(.05,1.1,0),Vector3(.05,.85,0),.018,"phaco",false,capsule,wounds)
	check("cornea" in result.contacts,"sphere footprint must fit entirely inside the corneal window")
	wounds=[[],[]]
	capsule={"positions":PackedVector3Array([Vector3(-.3,.82,-.3),Vector3(.3,.82,-.3),Vector3(0,.82,.3)]),"triangles":PackedInt32Array([0,1,2])}
	result=model.resolve(Vector3(0,.90,0),Vector3(0,.68,0),.018,"phaco",false,capsule,wounds)
	check("capsule" in result.contacts and result.position.y>.83,"intact current capsule blocks local downward entry")
	result=model.resolve(Vector3(0,.90,0),Vector3(0,.68,0),.018,"knife",true,capsule,wounds)
	check(not "capsule" in result.contacts,"actively cutting blade may cross membrane")
	result=model.resolve(Vector3(0,.90,0),Vector3(0,.68,0),.018,"knife",false,capsule,wounds)
	check("capsule" in result.contacts,"inactive blade cannot ghost through tissue")
	capsule.triangles=PackedInt32Array()
	result=model.resolve(Vector3(0,.90,0),Vector3(0,.68,0),.018,"phaco",false,capsule,wounds)
	check(not "capsule" in result.contacts,"actual missing connectivity opens passage")
	result=model.resolve(Vector3(.9,.85,0),Vector3(1.05,.68,0),.018,"phaco",false,capsule,wounds)
	check(result.position.x>1. and result.position.y>.78,"contact preserves tangential sliding")
	print("Anatomy contact: ",failures," failures"); quit(1 if failures else 0)
