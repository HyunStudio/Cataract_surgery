extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(FileAccess.file_exists("res://scripts/recorded_body_pose.gd"),"independent scalar-double recorded body sampler exists")
	if failures:quit(1);return
	var sampler=load("res://scripts/recorded_body_pose.gd")
	var data=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/recorded-poses.json"))
	for case in data:
		var kinds:=PackedInt32Array(case.kinds);var packets:=PackedFloat64Array(case.packets)
		var saved:=packets.duplicate()
		for index in range(case.times.size()):
			var t:float=case.times[index];var result:Dictionary=sampler.sample(kinds,packets,t)
			check(result.valid and result.capsules.size()==kinds.size()*7,"recorded pose returns double capsule layer")
			if not result.valid:continue
			for k in range(result.capsules.size()):check(absf(result.capsules[k]-case.expected[index][k])<=1e-13,"SciPy pose case=%s t=%s coordinate=%s difference=%s"%[data.find(case),t,k,result.capsules[k]-case.expected[index][k]])
			if t==0. or t==1.:
				for body in range(kinds.size()):
					for k in range(6):check(result.capsules[body*7+k]==packets[body*41+(6 if t==1. else 0)+k],"recorded endpoints remain bitwise exact")
		check(saved==packets,"pose sampling never changes recorded input")
	var kinds:=PackedInt32Array(data[0].kinds);var packet:=PackedFloat64Array(data[0].packets)
	for t in [NAN,INF,-.1,1.1]:check(not sampler.sample(kinds,packet,t).valid,"invalid time rejects")
	for malformed in [PackedFloat64Array(),PackedFloat64Array([0.])]:check(not sampler.sample(kinds,malformed,.5).valid,"invalid packet shape rejects")
	check(not sampler.sample(PackedInt32Array([2]),packet,.5).valid,"unknown body kind rejects")
	var bad:=packet.duplicate();bad[12]=0.
	check(not sampler.sample(kinds,bad,.5).valid,"zero radius rejects")
	bad=PackedFloat64Array(data[1].packets)
	for k in range(19,23):bad[k]=0.
	check(not sampler.sample(PackedInt32Array([1]),bad,.5).valid,"invalid recorded quaternion rejects")
	print("Recorded trajectory pose: ",failures," failures");quit(1 if failures else 0)
