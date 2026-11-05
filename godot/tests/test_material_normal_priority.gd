extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Backend extends RefCounted:
	var point_mode:="success"
	var point_calls:=0
	var legacy_calls:=0
	var legacy_budget:=-1
	var negative_work:=false
	func material_witness_fem(_value:Dictionary)->Dictionary:
		return {"status":3,"values":PackedFloat64Array([.09,.2,.2,.3,.4,.2,0.,.4,.4,.2,.4,0.,2.])}
	func solve_material_points_fem(value:Dictionary)->Dictionary:
		point_calls+=1
		var stats:=PackedFloat64Array();stats.resize(16);stats[2]=2.
		var answer:={"status":1 if point_mode=="fail" else 0,"xyz":value.xyz.duplicate(),"reaction":PackedFloat64Array(),"dual":PackedFloat64Array(),"stats":stats}
		if point_mode=="malformed":answer["normal_rows"]=[]
		return answer
	func solve_contact_fem(value:Dictionary)->Dictionary:
		legacy_calls+=1;legacy_budget=value.budget
		var stats:=PackedFloat64Array();stats.resize(16);stats[2]=-1. if negative_work else 1.
		return {"status":0,"xyz":value.xyz.duplicate(),"reaction":PackedFloat64Array(),"dual":PackedFloat64Array([0.]),"stats":stats}
class Guard extends RefCounted:
	func guard_motion(_value:Dictionary)->Dictionary:return {"status":0,"stats":PackedFloat64Array([0.,1.,-1.,-1.,.2,0.,0.,0.])}
func model():
	var result=load("res://scripts/embedded_membrane.gd").new()
	result.initialize(PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]),PackedInt32Array([0,1,2]),PackedByteArray([0,0,0]),1.)
	return result
func _initialize()->void:
	var packet:=PackedFloat64Array();packet.resize(41)
	for off in [0,3,6,9]:packet[off]=.2 if off in [0,6] else .2001;packet[off+1]=.3;packet[off+2]=.4
	packet[12]=.1
	var motion:={"kinds":PackedInt32Array([0]),"packets":packet,"guard":Guard.new()};var force:=PackedFloat64Array();force.resize(9)
	var tissue=model();var backend:=Backend.new();var before:Dictionary=tissue.snapshot()
	var result:Dictionary=tissue.advance_contact(1./60.,force,backend,2.,3.,motion,1.,100)
	check(result.valid and backend.point_calls==1 and backend.legacy_calls==0,"finite axis attempts the valid distributed model first")
	check(tissue.snapshot().steps==before.steps+1,"priority candidate publishes exactly one accepted tick")
	tissue=model();backend=Backend.new();backend.point_mode="fail"
	result=tissue.advance_contact(1./60.,force,backend,2.,3.,motion,1.,100)
	check(result.valid and backend.point_calls==1 and backend.legacy_calls==1 and backend.legacy_budget==98,"ordinary fallback receives only the remaining shared work budget")
	check(result.get("work_iterations")==3,"point and ordinary candidate work are counted together")
	tissue=model();backend=Backend.new();backend.point_mode="malformed";before=tissue.snapshot()
	result=tissue.advance_contact(1./60.,force,backend,2.,3.,motion,1.,100)
	check(not result.valid and backend.legacy_calls==0 and tissue.snapshot()==before,"malformed primary response cannot switch models or publish")
	tissue=model();backend=Backend.new();backend.point_mode="fail";backend.negative_work=true;before=tissue.snapshot()
	result=tissue.advance_contact(1./60.,force,backend,2.,3.,motion,1.,100)
	check(not result.valid and tissue.snapshot()==before,"negative ordinary work cannot hide inside positive point work")
	print("Material normal priority: ",failures," failures");quit(1 if failures else 0)
