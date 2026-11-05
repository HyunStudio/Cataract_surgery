extends RefCounted
## Observation only: no writes to the model or solver.
static func save(app,central_vertex:int,pieces:Array)->void:
	var model=app.capsule
	var state:Dictionary=model._embedded_state.duplicate(true)
	var binary:={"state":state,"central_vertex":central_vertex,"components":pieces,"metrics":model.metrics(),"clock":app.clock,"failure":model.native_failure.duplicate(true)}
	var blade_trace:Array=[]
	if model._embedded_solver!=null and model._embedded_solver.has_method("observed_blade_trace"):blade_trace=model._embedded_solver.observed_blade_trace()
	binary["blade_trace"]=blade_trace
	var poses:Array=[]
	for rig in app.rigs:poses.append({"tip":[rig.tip.x,rig.tip.y,rig.tip.z],"axis":[rig.axis.x,rig.axis.y,rig.axis.z],"roll":rig.roll})
	binary["poses"]=poses
	DirAccess.make_dir_recursive_absolute("res://reports")
	var file:=FileAccess.open("res://reports/operative-terminal.bin",FileAccess.WRITE)
	file.store_var(binary);file.close()
	var central_detached:=false
	for piece in pieces:
		if central_vertex in piece.vertices:central_detached=true
	var readable_pieces:Array=[]
	for piece in pieces:readable_pieces.append({"id":piece.id,"vertices":Array(piece.vertices),"anchored":piece.anchored,"area":piece.area})
	for entry in blade_trace:entry.patch=Array(entry.patch)
	var data:={"scope":"Final geometric connectivity and owned material state only; not a whole-app checkpoint or qualification.","central_vertex":central_vertex,"central_detached":central_detached,"xyz":Array(load("res://scripts/embedded_membrane.gd")._publish(state,state.xyz)),"rest":Array(load("res://scripts/membrane_precision.gd").pack(state.rest)),"triangles":Array(state.indices),"anchored":Array(state.anchored),"removed":Array(state.removed),"areas":Array(state.areas),"components":readable_pieces,"metrics":binary.metrics,"poses":poses,"clock":app.clock,"blade_trace":blade_trace}
	file=FileAccess.open("res://reports/operative-terminal.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(data,"  ",true,true));file.close()
