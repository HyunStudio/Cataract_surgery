extends RefCounted
## Pure closed height-shell subtraction by bounded convex XZ incision prisms.
## Ambiguous wall pairing, nonmanifold input, or work exhaustion rejects atomically.
## Supports paired upper/lower shells per cut interval, not arbitrary solid CSG.
## EPS is a geometric welding tolerance; 16-gon radius is inset 4*EPS.
## Output sources map each retained face to its input triangle; walls use -1.
const EPS:=0.000001
const MAX_WORK:=4000000
var _work:=0
var _failed:=false

func _invalid(reason:String)->Dictionary:
	return {"valid":false,"points":PackedVector3Array(),"indices":PackedInt32Array(),"sources":PackedInt32Array(),"reason":reason}

func build(points:PackedVector3Array,indices:PackedInt32Array,paths:Array,width:float,portals:Array=[],max_triangles:int=60000)->Dictionary:
	_work=0; _failed=false
	if not is_finite(width) or width<=EPS*8.0 or width>16.0 or max_triangles<1 or max_triangles>60000 or indices.size()%3!=0 or indices.is_empty() or indices.size()/3>max_triangles or points.size()>120000: return _invalid("input")
	for p in points:
		if not p.is_finite() or p.length_squared()>256.0: return _invalid("point")
	for i in indices:
		if i<0 or i>=points.size(): return _invalid("index")
	if not is_closed(points,indices): return _invalid("source_not_closed")
	var footprints:Array[PackedVector2Array]=[]
	for hand in range(paths.size()):
		var path=paths[hand]
		if not (path is Array or path is PackedVector3Array) or path.size()<2 or path.size()>2048: return _invalid("path")
		var clean:Array[Vector3]=[]
		for p in path:
			if not p is Vector3 or not p.is_finite() or p.length_squared()>256.0: return _invalid("path_point")
			if clean.is_empty() or p.distance_to(clean[-1])>EPS: clean.append(p)
		if clean.size()<2: return _invalid("empty_stroke")
		var offset:=Vector2.ZERO
		if hand<portals.size():
			if not portals[hand] is Vector3 or not portals[hand].is_finite() or portals[hand].length_squared()>256.0: return _invalid("portal")
			var center:Vector3=(clean[0]+clean[-1])*.5
			offset=Vector2(portals[hand].x-center.x,portals[hand].z-center.z)
		# Remove only forward collinear interior samples; preserve curved concavity.
		var compressed:Array[Vector3]=[]
		for p in clean:
			while compressed.size()>=2:
				var u:=Vector2(compressed[-1].x-compressed[-2].x,compressed[-1].z-compressed[-2].z)
				var v:=Vector2(p.x-compressed[-1].x,p.z-compressed[-1].z)
				if absf(u.cross(v))>EPS*u.length()*v.length() or u.dot(v)<0.0: break
				compressed.pop_back()
			compressed.append(p)
		for i in range(1,compressed.size()):
			var a:=Vector2(compressed[i-1].x,compressed[i-1].z); var b:=Vector2(compressed[i].x,compressed[i].z)
			var samples:=PackedVector2Array()
			for corner in [a,b,b+offset,a+offset]:
				for j in range(16): samples.append(corner+Vector2(cos(TAU*j/16.0),sin(TAU*j/16.0))*(width-EPS*4.0))
			var hull:=Geometry2D.convex_hull(samples)
			if hull.size()>1 and hull[0].is_equal_approx(hull[-1]): hull.remove_at(hull.size()-1)
			if Geometry2D.is_polygon_clockwise(hull): hull.reverse()
			footprints.append(hull)
			if footprints.size()>128: return _invalid("stroke_budget")
	var output:={"valid":true,"points":PackedVector3Array(),"indices":PackedInt32Array(),"sources":PackedInt32Array(),"reason":""}
	if footprints.is_empty():
		output.points=points.duplicate(); output.indices=indices.duplicate()
		for i in range(indices.size()/3): output.sources.append(i)
		return output
	var triangles:Array[Dictionary]=[]
	var removed:=false
	for off in range(0,indices.size(),3):
		var fragments:Array[PackedVector3Array]=[PackedVector3Array([points[indices[off]],points[indices[off+1]],points[indices[off+2]]])]
		for footprint in footprints:
			var next:Array[PackedVector3Array]=[]
			for polygon in fragments:
				var current:=polygon
				for edge in range(footprint.size()):
					_work+=current.size()
					if _work>MAX_WORK: return _invalid("clip_budget")
					var a:=footprint[edge]; var b:=footprint[(edge+1)%footprint.size()]
					var outside:=_clip(current,a,b,false)
					if outside.size()>=3: next.append(outside)
					current=_clip(current,a,b,true)
					if current.size()<3: break
				if current.size()>=3: removed=true
			fragments=next
			if fragments.size()>max_triangles: return _invalid("fragment_budget")
		for polygon in fragments:
			for j in range(1,polygon.size()-1):
				_add_triangle(triangles,polygon[0],polygon[j],polygon[j+1],int(off/3))
				if triangles.size()>max_triangles: return _invalid("triangle_budget")
	if not removed: return _invalid("outside_shell")
	# Conform clipping partitions before pairing the exposed upper/lower cut edges.
	triangles=_conform(triangles,max_triangles)
	if _failed: return _invalid("conform_budget")
	output=_pack(triangles)
	var boundary:=_boundaries(output.points,output.indices)
	if _failed: return _invalid("nonmanifold_cut")
	var groups:Array[Dictionary]=[]
	for edge in boundary:
		var a:Vector3=edge[0]; var b:Vector3=edge[1]
		var av:=Vector2(a.x,a.z); var bv:=Vector2(b.x,b.z)
		var direction:Vector2=(bv-av).normalized()
		if av.distance_to(bv)<=EPS: continue # Rim endpoints are closed by the paired wall interval.
		if direction.x<0.0 or (absf(direction.x)<EPS and direction.y<0.0): direction=-direction
		var found:=false
		for group in groups:
			_work+=1
			if _work>MAX_WORK: return _invalid("wall_budget")
			if absf(direction.cross(group.direction))<0.0001 and absf((av-group.origin).cross(group.direction))<EPS*2.0:
				group.edges.append(edge); found=true; break
		if not found: groups.append({"direction":direction,"origin":av,"edges":[edge]})
	for group in groups:
		var cuts:Array[float]=[]
		for edge in group.edges:
			for p in edge: cuts.append(Vector2(p.x,p.z).dot(group.direction))
		cuts.sort()
		var unique:Array[float]=[]
		for t in cuts:
			if unique.is_empty() or t-unique[-1]>EPS: unique.append(t)
		for j in range(1,unique.size()):
			var lo:=unique[j-1]; var hi:=unique[j]; var mid:float=(lo+hi)*.5
			var active:=_wall_active_edges(group.edges,group.direction,mid)
			if _failed: return _invalid("wall_search_budget")
			if active.is_empty(): continue
			if active.size()!=2: return _invalid("ambiguous_wall_pair")
			var a:=_at(active[0],group.direction,lo); var b:=_at(active[0],group.direction,hi)
			var c:=_at(active[1],group.direction,lo); var d:=_at(active[1],group.direction,hi)
			# Match the first skin edge's direction, then oppose it at the wall.
			if (active[0][1]-active[0][0]).dot(b-a)>0.0:
				_add_triangle(triangles,b,a,c,-1); _add_triangle(triangles,b,c,d,-1)
			else:
				_add_triangle(triangles,a,b,d,-1); _add_triangle(triangles,a,d,c,-1)
			if triangles.size()>max_triangles: return _invalid("wall_triangle_budget")
	triangles=_conform(triangles,max_triangles)
	if _failed: return _invalid("final_conform_budget")
	output=_pack(triangles)
	if output.indices.size()/3>max_triangles: return _invalid("packed_triangle_budget")
	if not is_closed(output.points,output.indices): return _invalid("result_not_closed")
	return output

func _wall_active_edges(edges:Array,direction:Vector2,mid:float)->Array:
	var active:Array=[]
	for edge in edges:
		_work+=1
		if _work>MAX_WORK: _failed=true; return []
		var u:float=Vector2(edge[0].x,edge[0].z).dot(direction); var v:float=Vector2(edge[1].x,edge[1].z).dot(direction)
		if mid>minf(u,v)-EPS*.1 and mid<maxf(u,v)+EPS*.1: active.append(edge)
	return active

func _at(edge:Array,direction:Vector2,t:float)->Vector3:
	var u:float=Vector2(edge[0].x,edge[0].z).dot(direction); var v:float=Vector2(edge[1].x,edge[1].z).dot(direction)
	return edge[0].lerp(edge[1],clampf((t-u)/(v-u),0.0,1.0))

func _clip(polygon:PackedVector3Array,a:Vector2,b:Vector2,inside:bool)->PackedVector3Array:
	var result:=PackedVector3Array()
	if polygon.is_empty(): return result
	for i in range(polygon.size()):
		var p:=polygon[i]; var q:=polygon[(i+1)%polygon.size()]
		var dp:float=(b-a).cross(Vector2(p.x,p.z)-a); var dq:float=(b-a).cross(Vector2(q.x,q.z)-a)
		var ip:=dp>=0.0 if inside else dp<=0.0; var iq:=dq>=0.0 if inside else dq<=0.0
		if ip: result.append(p)
		if ip!=iq and dp!=dq: result.append(p.lerp(q,dp/(dp-dq)))
	return result

func _add_triangle(triangles:Array[Dictionary],a:Vector3,b:Vector3,c:Vector3,source:int)->void:
	if (b-a).cross(c-a).length_squared()>1e-22: triangles.append({"p":PackedVector3Array([a,b,c]),"source":source})

func _key(p:Vector3)->String:
	return "%d,%d,%d" % [roundi(p.x/EPS),roundi(p.y/EPS),roundi(p.z/EPS)]

func _pack(triangles:Array[Dictionary])->Dictionary:
	var points:=PackedVector3Array(); var indices:=PackedInt32Array(); var sources:=PackedInt32Array(); var lookup:={}
	for triangle in triangles:
		var ids:Array[int]=[]
		for p in triangle.p:
			var cell:=Vector3i(roundi(p.x/EPS),roundi(p.y/EPS),roundi(p.z/EPS))
			var found:=-1
			for dx in range(-1,2):
				for dy in range(-1,2):
					for dz in range(-1,2):
						var near:Vector3i=cell+Vector3i(dx,dy,dz)
						if lookup.has(near):
							for index in lookup[near]:
								if points[index].distance_to(p)<=EPS: found=index; break
			if found<0:
				found=points.size(); points.append(p)
				if not lookup.has(cell): lookup[cell]=[]
				lookup[cell].append(found)
			ids.append(found)
		if ids[0]==ids[1] or ids[1]==ids[2] or ids[2]==ids[0]: continue
		indices.append_array(PackedInt32Array(ids)); sources.append(triangle.source)
	return {"valid":true,"points":points,"indices":indices,"sources":sources,"reason":""}

func _boundaries(points:PackedVector3Array,indices:PackedInt32Array)->Array:
	var lookup:={}; var result:Array=[]
	for off in range(0,indices.size(),3):
		for j in range(3):
			var a:=points[indices[off+j]]; var b:=points[indices[off+(j+1)%3]]
			var ka:=_key(a); var kb:=_key(b); var key:=ka+"|"+kb if ka<kb else kb+"|"+ka
			if not lookup.has(key): lookup[key]=[]
			lookup[key].append([a,b])
	for edges in lookup.values():
		if edges.size()==1: result.append(edges[0])
		elif edges.size()!=2: _failed=true
		elif _key(edges[0][0])==_key(edges[1][0]): _failed=true
	return result

func is_closed(points:PackedVector3Array,indices:PackedInt32Array)->bool:
	if indices.is_empty() or indices.size()%3!=0: return false
	for p in points:
		if not p.is_finite() or p.length_squared()>256.0: return false
	for i in indices:
		if i<0 or i>=points.size(): return false
	for off in range(0,indices.size(),3):
		var a:=points[indices[off]]; var b:=points[indices[off+1]]; var c:=points[indices[off+2]]
		if (b-a).cross(c-a).length_squared()<=1e-22: return false
	var old_failed:=_failed; _failed=false
	var boundary:=_boundaries(points,indices)
	var closed:=boundary.is_empty() and not _failed
	_failed=old_failed
	return closed

func _conform(triangles:Array[Dictionary],limit:int)->Array[Dictionary]:
	if triangles.is_empty(): return []
	var packed:=_pack(triangles)
	var vertices:PackedVector3Array=packed.points
	var bounds:=AABB(vertices[0],Vector3.ZERO)
	for vertex in vertices: bounds=bounds.expand(vertex)
	var cell_size:=maxf(bounds.size[bounds.size.max_axis_index()]/24.0,EPS*8.0)
	var bins:={}
	for index in range(vertices.size()):
		var vertex:=vertices[index]
		var cell:=Vector3i(floori(vertex.x/cell_size),floori(vertex.y/cell_size),floori(vertex.z/cell_size))
		if not bins.has(cell): bins[cell]=[]
		bins[cell].append(index)
	var canonical:Array[Dictionary]=[]
	for offset in range(0,packed.indices.size(),3):
		canonical.append({"p":PackedVector3Array([vertices[packed.indices[offset]],vertices[packed.indices[offset+1]],vertices[packed.indices[offset+2]]]),"source":packed.sources[int(offset/3)]})
	var result:Array[Dictionary]=[]
	for triangle in canonical:
		var polygon:=PackedVector3Array(); var changed:=false
		for i in range(3):
			var a:Vector3=triangle.p[i]; var b:Vector3=triangle.p[(i+1)%3]; var delta:=b-a; var length_sq:=delta.length_squared()
			var cuts:Array[float]=[0.0]
			if length_sq<=EPS*EPS: continue
			var lo:Vector3=a.min(b)-Vector3.ONE*EPS; var hi:Vector3=a.max(b)+Vector3.ONE*EPS
			var first:=Vector3i(floori(lo.x/cell_size),floori(lo.y/cell_size),floori(lo.z/cell_size))
			var last_cell:=Vector3i(floori(hi.x/cell_size),floori(hi.y/cell_size),floori(hi.z/cell_size))
			for cx in range(first.x,last_cell.x+1):
				for cy in range(first.y,last_cell.y+1):
					for cz in range(first.z,last_cell.z+1):
						_work+=1
						if _work>MAX_WORK: _failed=true; return []
						var cell:=Vector3i(cx,cy,cz)
						if not bins.has(cell): continue
						for index in bins[cell]:
							_work+=1
							if _work>MAX_WORK: _failed=true; return []
							var v:=vertices[index]
							var t:float=(v-a).dot(delta)/length_sq
							if t>EPS/sqrt(length_sq) and t<1.0-EPS/sqrt(length_sq) and v.distance_to(a+delta*t)<EPS*.3: cuts.append(t)
			cuts.sort()
			var last:=-1.0
			for t in cuts:
				if (t-last)*sqrt(length_sq)>EPS*.3: polygon.append(a+delta*t); last=t
			if cuts.size()>1: changed=true
		if not changed:
			result.append(triangle)
			if result.size()>limit: _failed=true; return []
			continue
		var center:=Vector3.ZERO
		for p in polygon: center+=p
		center/=polygon.size()
		for j in range(polygon.size()):
			_add_triangle(result,center,polygon[j],polygon[(j+1)%polygon.size()],triangle.source)
			if result.size()>limit: _failed=true; return []
		if result.size()>limit: _failed=true; return []
	return result
