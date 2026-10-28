extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
class Guard extends RefCounted:
	var calls:Array[Dictionary]=[]
	var reply:Dictionary={"status":0,"stats":PackedFloat64Array([0,0,-1,-1,INF,0,0,0])}
	var collide_call:=0
	func guard_motion(request:Dictionary)->Dictionary:
		calls.append(request.duplicate(true))
		if collide_call>0 and calls.size()==collide_call:
			return {"status":1,"stats":PackedFloat64Array([1,1,0,2,-.001,0,0,4]),"witness_t":.25}
		return reply.duplicate(true)
func _initialize()->void:
	check(FileAccess.file_exists("res://scripts/anatomical_contact.gd"),"nonmutating anatomical surface query adapter exists")
	if failures: quit(1); return
	var source=load("res://scripts/anatomical_contact.gd")
	var model=source.new()
	var points:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)])
	var mesh:Dictionary={"positions":points,"triangles":PackedInt32Array([0,1,2])}
	check(model.configure(mesh,.004),"actual finite triangle mesh can be frozen")
	var before:=PackedFloat64Array(); var after:=PackedFloat64Array(); var selected:=PackedInt32Array()
	for i in range(70): before.append_array([.001*i,.1,0.]); after.append_array([.001*i,.2,0.]); selected.append(i)
	var old_before:=before.duplicate(); var old_after:=after.duplicate()
	var built:Dictionary=model.requests(before,after,selected)
	check(built.valid and built.chunks.size()==2,"all selected points are split within the native64body bound")
	if built.valid:
		check(built.chunks[0].vertices==selected.slice(0,64) and built.chunks[1].vertices==selected.slice(64,70),"chunk keeps exact tissue vertex identities")
		var request:Dictionary=built.chunks[0].request
		check(request.previous==request.current and request.triangles==PackedInt32Array([0,1,2]) and request.kinds.size()==64,"anatomy remains static while tissue points move")
		check(request.packets.slice(0,13)==PackedFloat64Array([0,.1,0,0,.1,0,0,.2,0,0,.2,0,.004]),"point capsule packet retains double endpoints and physical margin")
		check(request.budget==128 and request.gap_tolerance==1e-9,"original guard work and gap bounds are retained")
	# A successful replacement freezes its source arrays; invalid replacement
	# preserves the previous configured geometry.
	points[0]=Vector3(9,9,9); mesh.triangles[0]=2
	var frozen:Dictionary=model.requests(before,after,selected)
	check(frozen.valid and frozen.chunks[0].request.previous[0]==-1. and frozen.chunks[0].request.triangles[0]==0,"caller edits cannot mutate configured anatomy")
	check(not model.configure({"positions":points,"triangles":PackedInt32Array([0,0,1])},.004) and model.requests(before,after,selected).valid,"invalid replacement is atomic")
	for unsupported_radius in [5e-10,1e-9]:
		check(not model.configure({"positions":points,"triangles":PackedInt32Array([0,1,2])},unsupported_radius),"surface margin must exceed native guard gap tolerance")
		var retained:Dictionary=model.requests(before,after,selected)
		check(retained.valid and retained.chunks[0].request.previous[0]==-1. and retained.chunks[0].request.packets[12]==.004,"unsupported margin preserves previously configured mesh and radius")
	var guard:=Guard.new(); var clear:Dictionary=model.inspect(guard,before,after,selected)
	check(clear.status==0 and guard.calls.size()==2,"clear result requires every point chunk to be certified")
	guard=Guard.new(); guard.collide_call=2
	var hit:Dictionary=model.inspect(guard,before,after,selected)
	check(hit.status==1 and hit.vertex==66 and hit.face==0 and hit.witness_t==.25,"collision maps native body index to the original tissue vertex")
	check(hit.triangle==PackedFloat64Array([-1,0,-1,1,0,-1,0,0,1]) and hit.radius==.004,"finite anatomical face and radius accompany the witness")
	for reply in [{"status":2},{"status":0},{"status":"0","stats":PackedFloat64Array([0,0,-1,-1,INF,0,0,0])},{"status":0,"stats":PackedFloat64Array([0,0,0,0,NAN,0,0,0])},{"status":1,"stats":PackedFloat64Array([1,1,INF,0,-.001,0,0,4]),"witness_t":.5},{"status":1,"stats":PackedFloat64Array([1,1,0,70,-.001,0,0,4]),"witness_t":.5}]:
		guard=Guard.new(); guard.reply=reply
		check(model.inspect(guard,before,after,selected).status!=0,"unknown or malformed guard output cannot certify anatomy clearance")
	for bad in [PackedInt32Array([-1]),PackedInt32Array([70]),PackedInt32Array([0,0])]:
		guard=Guard.new()
		check(model.inspect(guard,before,after,bad).status==-1 and guard.calls.is_empty(),"invalid tissue selection rejects before calling native code")
	var many_faces:=PackedInt32Array()
	for i in range(16384): many_faces.append_array(PackedInt32Array([0,1,2]))
	var crowded=source.new()
	check(crowded.configure({"positions":PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(0,0,1)]),"triangles":many_faces},.004),"maximum supported face count is explicit")
	var batches:Dictionary=crowded.requests(before,after,selected)
	check(batches.valid and batches.chunks.size()==18,"dense anatomy reduces point chunks to obey65536pair limit")
	if batches.valid:
		for chunk in batches.chunks: check(chunk.request.kinds.size()*16384<=65536,"every native call fits the pair bound")
	check(before==old_before and after==old_after,"anatomical inspection never publishes a tissue correction")
	print("Anatomical contact: ",failures," failures"); quit(1 if failures else 0)
