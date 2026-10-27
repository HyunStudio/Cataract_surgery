extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func vectors(values:Array)->PackedVector3Array:
	var out:=PackedVector3Array()
	for i in range(0,values.size(),3): out.append(Vector3(values[i],values[i+1],values[i+2]))
	return out
func _initialize()->void:
	var solver=load("res://scripts/membrane_contact.gd").new()
	var face:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)])
	var part:Dictionary={"previous_a":Vector3(-.5,.01000025,0),"previous_b":Vector3(-.4,.01000025,0),"a":Vector3(.5,.01000025,0),"b":Vector3(.6,.01000025,0),"radius":.01}
	var hit:Dictionary=solver._moving_hit(part,face,face)
	check(hit.valid and not hit.hit and not hit.uncertain,"analytically separated parallel sweep is clear throughout its time interval")
	var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/near_tangent_jaw.json"))
	var segment:=vectors(data.segment); var old:=vectors(data.old); var current:=vectors(data.current)
	part={"previous_a":segment[0],"previous_b":segment[1],"a":segment[2],"b":segment[3],"radius":data.radius}
	hit=solver._moving_hit(part,old,current)
	check(hit.valid and not hit.hit and not hit.uncertain,"real near-tangent moving jaw has certified clearance without exhausting work")
	check(hit.evaluations<=128,"the actual failing scene stays inside the unchanged query budget")
	print("Near-tangent fixture evaluations: ",hit.evaluations)
	var limited:Dictionary=solver._moving_hit(part,old,current,1)
	check(limited.valid and not limited.hit and limited.uncertain and limited.evaluations==1,"an unresolved hull at the work limit is uncertain, never certified clear")
	for budget in [0,129]: check(not solver._moving_hit(part,old,current,budget).valid,"unsupported work budgets reject explicitly")
	data=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/near_tangent_jaw_262.json"))
	segment=vectors(data.segment); old=vectors(data.old); current=vectors(data.current)
	part={"previous_a":segment[0],"previous_b":segment[1],"a":segment[2],"b":segment[3],"radius":data.radius}
	hit=solver._moving_hit(part,old,current)
	check(hit.valid and not hit.hit and not hit.uncertain,"actual tick262 clear jaw sweep is resolved inside the unchanged query budget")
	print("Tick262 fixture evaluations: ",hit.evaluations)
	for order in [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]:
		var permuted_old:=PackedVector3Array(); var permuted_current:=PackedVector3Array()
		for index in order: permuted_old.append(old[index]); permuted_current.append(current[index])
		hit=solver._moving_hit(part,permuted_old,permuted_current)
		check(hit.valid and not hit.hit and not hit.uncertain,"swept hull certificate is independent of triangle indexing and winding")


	part={"previous_a":Vector3(0,.1,0),"previous_b":Vector3(0,.1,0),"a":Vector3(0,-.1,0),"b":Vector3(0,-.1,0),"radius":.01}
	hit=solver._moving_hit(part,face,face)
	check(hit.valid and hit.hit and not hit.uncertain,"a crossing remains contact even when both endpoints are clear")
	for heights in [[.1,-.3],[.3,-.1]]:
		part={"previous_a":Vector3(0,heights[0],0),"previous_b":Vector3(0,heights[0],0),"a":Vector3(0,heights[1],0),"b":Vector3(0,heights[1],0),"radius":.01}
		hit=solver._moving_hit(part,face,face)
		check(hit.valid and hit.hit and not hit.uncertain,"clear midpoint cannot hide a crossing in either pending time half")

	part={"previous_a":Vector3.ZERO,"previous_b":Vector3.ZERO,"a":Vector3.ZERO,"b":Vector3.ZERO,"radius":.01}
	var below:=PackedVector3Array(); var above:=PackedVector3Array()
	for point in face: below.append(point+Vector3(0,-.1,0)); above.append(point+Vector3(0,.1,0))
	hit=solver._moving_hit(part,below,above)
	check(hit.valid and hit.hit and not hit.uncertain,"moving tissue cannot pass a stationary tool between clear endpoint poses")
	part={"previous_a":Vector3(-.5,.01000005,0),"previous_b":Vector3(-.4,.01000005,0),"a":Vector3(.5,.01000005,0),"b":Vector3(.6,.01000005,0),"radius":.01}
	hit=solver._moving_hit(part,face,face)
	check(hit.valid and hit.hit and not hit.uncertain,"the existing contact skin cannot be discarded by a hull certificate")
	print("Moving membrane: ",failures," failures"); quit(1 if failures else 0)
