extends RefCounted
## Optional nonmutating surface-distance queries. Does not classify shell
## interiors, wounds or exterior state, and does not solve contact response.
const GeometryLimits=preload("res://scripts/fine_geometry_limits.gd")
const GAP:=1e-9
const QUERY_BUDGET:=128
var _xyz:=PackedFloat64Array()
var _triangles:=PackedInt32Array()
var _radius:=.004

func configure(mesh:Dictionary,radius:=.004)->bool:
	if not mesh.get("positions") is PackedVector3Array or not mesh.get("triangles") is PackedInt32Array: return false
	var points:PackedVector3Array=mesh.positions
	var ids:PackedInt32Array=mesh.triangles
	if points.is_empty() or points.size()>4096 or ids.is_empty() or ids.size()%3!=0 or ids.size()/3>16384 or not is_finite(radius) or radius<=GAP or radius>.3: return false
	var xyz:=PackedFloat64Array()
	for point in points:
		for axis in range(3):
			if not is_finite(point[axis]) or absf(point[axis])>16.: return false
			xyz.append(point[axis])
	for i in range(0,ids.size(),3):
		for j in range(3):
			if ids[i+j]<0 or ids[i+j]>=points.size(): return false
		if ids[i]==ids[i+1] or ids[i]==ids[i+2] or ids[i+1]==ids[i+2]: return false
	_xyz=xyz; _triangles=ids.duplicate(); _radius=radius
	return true

func requests(previous:PackedFloat64Array,current:PackedFloat64Array,vertices:PackedInt32Array,fine_point_limit:int=4096)->Dictionary:
	if _xyz.is_empty() or previous.is_empty() or previous.size()%3!=0 or previous.size()!=current.size() or not GeometryLimits.supported(fine_point_limit) or previous.size()/3>fine_point_limit: return {"valid":false,"reason":"shape"}
	for coordinate in range(previous.size()):
		if not is_finite(previous[coordinate]) or not is_finite(current[coordinate]) or absf(previous[coordinate])>16. or absf(current[coordinate])>16.: return {"valid":false,"reason":"coordinate"}
	var seen:={}
	for vertex in vertices:
		if vertex<0 or vertex>=previous.size()/3 or seen.has(vertex): return {"valid":false,"reason":"selection"}
		seen[vertex]=true
	# Every selected point is queried against every configured finite face;
	# no candidate pair is dropped by an unproved local-neighborhood heuristic.
	var capacity:=mini(64,65536/(_triangles.size()/3))
	var chunks:Array[Dictionary]=[]
	for begin in range(0,vertices.size(),capacity):
		var selected:=vertices.slice(begin,mini(begin+capacity,vertices.size()))
		var packets:=PackedFloat64Array(); var kinds:=PackedInt32Array()
		for vertex in selected:
			var packet:=PackedFloat64Array(); packet.resize(41)
			for axis in range(3):
				packet[axis]=previous[3*vertex+axis]; packet[3+axis]=previous[3*vertex+axis]
				packet[6+axis]=current[3*vertex+axis]; packet[9+axis]=current[3*vertex+axis]
			packet[12]=_radius; packets.append_array(packet); kinds.append(0)
		chunks.append({"vertices":selected,"request":{"previous":_xyz.duplicate(),"current":_xyz.duplicate(),"triangles":_triangles.duplicate(),"packets":packets,"kinds":kinds,"budget":QUERY_BUDGET,"gap_tolerance":GAP}})
	return {"valid":true,"chunks":chunks}

func inspect(backend:RefCounted,previous:PackedFloat64Array,current:PackedFloat64Array,vertices:PackedInt32Array,fine_point_limit:int=4096)->Dictionary:
	var built:=requests(previous,current,vertices,fine_point_limit)
	if not built.valid: return {"status":-1,"reason":built.reason}
	if not backend or not backend.has_method("guard_motion"): return {"status":-1,"reason":"backend"}
	var gap:=INF; var calls:=0
	for chunk in built.chunks:
		var reply:Variant=backend.guard_motion(chunk.request); calls+=1
		if not reply is Dictionary: return {"status":-1,"reason":"native_output","calls":calls}
		var result:Dictionary=reply
		var raw_status:Variant=result.get("status",null)
		if not raw_status is int: return {"status":-1,"reason":"native_status","calls":calls}
		var code:int=raw_status
		if code==2: return {"status":2,"reason":"uncertain","calls":calls}
		if code!=0 and code!=1: return {"status":-1,"reason":"native_status","calls":calls}
		if not result.get("stats") is PackedFloat64Array or result.stats.size()!=8: return {"status":-1,"reason":"native_output","calls":calls}
		var stats:PackedFloat64Array=result.stats
		if is_nan(stats[4]) or stats[4]==-INF: return {"status":-1,"reason":"native_gap","calls":calls}
		if code==0:
			if stats[4]<-GAP: return {"status":-1,"reason":"native_residual","calls":calls}
			gap=minf(gap,stats[4]); continue
		var time:Variant=result.get("witness_t",null)
		if not (time is float or time is int) or not is_finite(time) or time<0. or time>1. or not is_finite(stats[4]) or stats[4]>=-GAP: return {"status":-1,"reason":"native_witness","calls":calls}
		if not is_finite(stats[2]) or not is_finite(stats[3]) or stats[2]<0. or stats[2]>=_triangles.size()/3 or stats[3]<0. or stats[3]>=chunk.vertices.size(): return {"status":-1,"reason":"native_index","calls":calls}
		var face:=int(stats[2]); var body:=int(stats[3])
		if float(face)!=stats[2] or float(body)!=stats[3]: return {"status":-1,"reason":"native_index","calls":calls}
		var triangle:=PackedFloat64Array()
		for j in range(3): triangle.append_array(_xyz.slice(3*_triangles[3*face+j],3*_triangles[3*face+j]+3))
		return {"status":1,"vertex":chunk.vertices[body],"face":face,"triangle":triangle,"radius":_radius,"witness_t":float(time),"gap":stats[4],"calls":calls}
	return {"status":0,"gap":gap,"calls":calls}
