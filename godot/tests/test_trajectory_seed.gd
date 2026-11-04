extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:
	check(FileAccess.file_exists("res://scripts/trajectory_seed.gd"),"trajectory retry remaps numerical seeds without changing physical state")
	if failures:quit(1);return
	var helper=load("res://scripts/trajectory_seed.gd")
	var dual:=PackedFloat64Array();dual.resize(60000);dual[0]=1e-300
	var candidate:={"xyz":PackedFloat64Array([1.,2.,3.]),"dual":dual,"times":PackedFloat64Array([.25,.5,1.]),"pairs":20000,"penalty":1e7}
	var saved:=candidate.duplicate(true);var next:Dictionary=helper.transition(candidate,.125)
	check(next.valid and next.times==PackedFloat64Array([.125,.25,1.]),"only exact-zero nonendpoint layers retire when the dense pair limit would overflow")
	check(next.multiplier_seed.size()==60000 and next.multiplier_seed[20000]==1e-300 and next.penalty_seed==1e7,"every positive reaction including tiny values retains its exact normalization and penalty")
	check(candidate==saved,"exchange never changes its source numerical candidate")
	next.initial[0]=9.;next.multiplier_seed[20000]=7.
	check(candidate==saved,"returned seeds cannot alias or modify the source candidate")
	var full:=candidate.duplicate(true);full.dual[20000]=1.
	check(not helper.transition(full,.125).valid,"pair limit cannot be bypassed by dropping a positive layer or endpoint")
	for malformed in [candidate.merged({"penalty":0.},true),candidate.merged({"dual":PackedFloat64Array([0.])},true),candidate.merged({"times":PackedFloat64Array([.5,.25,1.])},true),candidate.merged({"xyz":PackedFloat64Array([NAN,0.,0.])},true)]:
		check(not helper.transition(malformed,.125).valid,"bad numerical metadata cannot become a warm request")
	for witness in [0.,NAN,.25,1.]:check(not helper.transition(candidate,witness).valid,"invalid or duplicate witness rejects")
	print("Trajectory numerical seed: ",failures," failures");quit(1 if failures else 0)
