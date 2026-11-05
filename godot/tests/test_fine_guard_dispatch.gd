extends SceneTree
const Step=preload("res://scripts/embedded_contact_step.gd")
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
class Legacy extends RefCounted:
	var legacy_calls:=0
	func guard_motion(_value:Dictionary)->Dictionary:
		legacy_calls+=1;return {"status":0,"stats":PackedFloat64Array([0.,1.,-1.,-1.,1.,0.,0.,0.])}
class Extended extends Legacy:
	var fine_calls:=0
	var count:=0
	func guard_fine_motion(value:Dictionary)->Dictionary:
		fine_calls+=1;count=value.current.size()/3
		return {"status":0,"stats":PackedFloat64Array([0.,1.,-1.,-1.,1.,0.,0.,0.])}
func _initialize()->void:
	var geometry:=PackedFloat64Array();geometry.resize(4097*3)
	var guard:=Extended.new();var context:={"guard":guard,"kinds":PackedInt32Array([0]),"packets":PackedFloat64Array()}
	var answer:=Step.guard(geometry,geometry,PackedInt32Array([0,1,4096]),context)
	check(answer.valid and guard.fine_calls==1 and guard.legacy_calls==0 and guard.count==4097,"large fine geometry dispatches to its explicit complete interval interface")
	answer=Step.guard(geometry.slice(0,9),geometry.slice(0,9),PackedInt32Array([0,1,2]),context)
	check(answer.valid and guard.legacy_calls==1 and guard.fine_calls==1,"small geometry retains the legacy guard contract")
	context.guard=Legacy.new()
	check(not Step.guard(geometry,geometry,PackedInt32Array([0,1,4096]),context).valid,"a legacy guard cannot silently accept an oversized fine mesh")
	var points:=PackedVector3Array();points.resize(4097);var packet:=PackedFloat64Array();packet.resize(41);packet[12]=.1
	var state:={"rest":points,"indices":PackedInt32Array([0,1,4096]),"fine_point_limit":8192}
	check(not Step.prepare(state,{"kinds":PackedInt32Array([0]),"packets":packet,"guard":Legacy.new()}).valid,"unsupported large geometry is rejected before a numerical candidate")
	print("Fine guard dispatch: ",failures," failures");quit(1 if failures else 0)
