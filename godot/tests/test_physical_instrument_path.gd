extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class Capture extends RefCounted:
	var request:Dictionary={}
	func solve_contact(value:Dictionary)->Dictionary:
		request=value.duplicate(true); return {"status":1}
func distance(a:PackedFloat64Array,b:PackedFloat64Array)->float:
	var squared:=0.
	for k in range(3): squared+=(a[k]-b[k])*(a[k]-b[k])
	return sqrt(squared)
func _initialize()->void:
	var path=load("res://scripts/instrument_path.gd")
	check(path.has_method("physical_sample"),"pose paths expose authoritative packed64 physical sampling")
	if failures: quit(1); return
	var profile=load("res://scripts/instrument_profile.gd")
	var local:Array=profile.segments("forceps",.018,true)
	check(local[0].get("physical_a") is PackedFloat64Array and local[0].physical_a[2]==-.01 and local[1].physical_a[2]==.01,"closed jaw dimensions retain original double values")
	for axis in [Vector3.LEFT,Vector3(-1,.03,0).normalized(),Vector3(1,2,3).normalized(),Vector3.UP,Vector3.DOWN]:
		var tip:=Vector3(.4,.9,0)
		var jaws:Array=path.build("forceps",.018,tip,axis,true,tip,axis,true,false)
		var first:Dictionary=path.physical_sample(jaws[0],1.)
		var second:Dictionary=path.physical_sample(jaws[1],1.)
		check(distance(first.a,second.a)>=.02-8e-15,"rigid physical closed jaws do not acquire float32 interpenetration")
		for point in [first.a,first.b,second.a,second.b]: check(point is PackedFloat64Array and point.size()==3,"physical axes are scalar doubles")
	var body:Array=path.build("forceps",.018,Vector3.ZERO,Vector3.LEFT,true,Vector3(.1,.2,.3),Vector3(1,2,3).normalized(),false,false)
	var part:Dictionary=path.interval(body[0],.25,.75)
	var first:Dictionary=path.physical_sample(body[0],.25); var last:Dictionary=path.physical_sample(body[0],.75)
	check(part.physical_previous_a==first.a and part.physical_a==last.a,"interval retains double physical endpoints")
	var motion:Dictionary=path.motion_request(PackedFloat64Array([0,0,0]),PackedFloat64Array([0,0,0]),PackedInt32Array(),[part])
	check(motion.packets.slice(0,3)==first.a and motion.packets.slice(6,9)==last.a,"continuous guard and endpoint solver use the same authoritative axes")
	check(motion.packets[29]==-.01 and motion.packets[35]==-.025,"motion packet retains double local closure dimensions")
	for invalid in [PackedFloat64Array([0,0]),PackedFloat64Array([0,NAN,0]),PackedFloat64Array([0,INF,0])]:
		check(not path.valid(part.merged({"physical_a":invalid},true)),"malformed physical endpoint metadata rejects")
	var far:=Vector3(3,3,3)
	var physical_body:Array=path.build("forceps",.018,far,Vector3.LEFT,true,far,Vector3.LEFT,true,false)
	var model=load("res://scripts/capsule_solver.gd").new(); var capture:=Capture.new()
	model.set_contact_backend(capture)
	var tools:Array[Dictionary]=[{"hand":0,"tip":far,"radius":.018,"grip":false,"cut":false,"body":physical_body}]
	model.step_tools(1./120.,tools)
	check(not capture.request.is_empty(),"actual joint step captures physical forceps request")
	if not capture.request.is_empty():
		check(capture.request.capsules[2]==3.-.01 and capture.request.capsules[9]==3.+.01,"joint force request keeps double jaw positions instead of render proxy values")
		check(capture.request.capsules[6]==.01 and capture.request.capsules[13]==.01,"physical radii remain unchanged")
	var legacy:Array=physical_body.duplicate(true)
	for segment in legacy:
		for key in ["physical_a","physical_b","physical_previous_a","physical_previous_b"]: segment.erase(key)
		for key in ["physical_a0","physical_b0","physical_a1","physical_b1"]: segment.path.erase(key)
	var legacy_interval:Dictionary=path.interval(legacy[0],0.,.5)
	check(path.valid(legacy_interval) and not legacy_interval.has("physical_a"),"unannotated legacy pose intervals retain their original represented geometry")
	var legacy_sample:Dictionary=path.physical_sample(legacy[0],.5)
	check(legacy_sample.a[2]==float(path.sample(legacy[0],.5).a.z),"explicit legacy sampling retains original float32 pose publication")
	var old_capture:=Capture.new(); model.set_contact_backend(old_capture); tools[0].body=legacy
	model.step_tools(1./120.,tools)
	check(not old_capture.request.is_empty(),"unannotated legacy paths still reach an actual joint timestep")
	if not old_capture.request.is_empty(): check(old_capture.request.capsules[2]==float(legacy[0].a.z),"legacy static request keeps its represented axis")
	print("Physical instrument path: ",failures," failures"); quit(1 if failures else 0)
