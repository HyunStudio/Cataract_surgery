extends RefCounted
## Finite curtain incision of an oriented triangle membrane. No material is removed.
## Source-edge identity preserves shared nodes without welding coincident old seams.
## This geometric engineering model is not calibrated tissue fracture mechanics.
const EPS:=0.0000001
const MAX_WORK:=2000000
var _points:=PackedVector3Array()
var _original:=PackedVector3Array()
var _bindings:Array[Dictionary]=[]
var _edge_nodes:Dictionary={}
var _input_edges:Dictionary={}
var _cut_faces:Dictionary={}
var _failure:=""
var _work:=0
var _vertex_limit:=0
var _triangle_limit:=0
var _start:=Vector3.ZERO
var _tangent:=Vector3.ZERO
var _depth:=Vector3.ZERO
var _normal:=Vector3.ZERO
var _length:=0.
var _half_depth:=0.
var _clip_polygon:=PackedVector2Array()

func _invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason,"points":PackedVector3Array(),"indices":PackedInt32Array(),"sources":PackedInt32Array(),"bindings":[],"work":_work}
func _tick()->bool:
	_work+=1
	if _work>MAX_WORK: _failure="work_budget"; return false
	return true
static func _dot(a:Vector3,b:Vector3)->float:
	return float(a.x)*b.x+float(a.y)*b.y+float(a.z)*b.z
static func _key(a:int,b:int)->Vector2i:
	return Vector2i(mini(a,b),maxi(a,b))
static func _area(a:Vector3,b:Vector3,c:Vector3)->float:
	return (b-a).cross(c-a).length()*.5
static func _project(p:Vector3,axis:int)->Vector2:
	return Vector2(p.y,p.z) if axis==0 else (Vector2(p.x,p.z) if axis==1 else Vector2(p.x,p.y))
static func _cross(a:Vector2,b:Vector2)->float:
	return float(a.x)*b.y-float(a.y)*b.x
func _bary(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->Vector3:
	var axis:=(b-a).cross(c-a).abs().max_axis_index()
	var pa:=_project(a,axis); var pb:=_project(b,axis); var pc:=_project(c,axis); var pp:=_project(p,axis)
	var ux:float=float(pb.x)-pa.x; var uy:float=float(pb.y)-pa.y
	var vx:float=float(pc.x)-pa.x; var vy:float=float(pc.y)-pa.y
	var qx:float=float(pp.x)-pa.x; var qy:float=float(pp.y)-pa.y
	var determinant:=ux*vy-uy*vx
	if absf(determinant)<1e-20: return Vector3(-INF,-INF,-INF)
	var second:=(qx*vy-qy*vx)/determinant; var third:=(ux*qy-uy*qx)/determinant
	return Vector3(1.-second-third,second,third)

func slice(points:PackedVector3Array,indices:PackedInt32Array,start:Vector3,finish:Vector3,depth_axis:Vector3,half_depth:float,max_vertices:int=4096,max_triangles:int=8192)->Dictionary:
	return _slice(points,indices,start,finish,depth_axis,half_depth,max_vertices,max_triangles,PackedVector2Array())

## A finite, planar sharp-edge sweep patch. Coplanar sliding has no unique
## transverse incision, so it leaves those faces intact rather than guessing.
func slice_triangle(points:PackedVector3Array,indices:PackedInt32Array,a:Vector3,b:Vector3,c:Vector3,max_vertices:int=4096,max_triangles:int=8192)->Dictionary:
	_work=0
	for point in [a,b,c]:
		if not point.is_finite() or point.length_squared()>256.:return _invalid("patch")
	var edge:=b-a;var length:=edge.length()
	if length<=EPS:return _invalid("patch_resolution")
	var tangent:=edge/length
	var depth:=c-a-tangent*_dot(c-a,tangent);var height:=depth.length()
	if height<=EPS:return _invalid("patch_resolution")
	depth/=height
	var polygon:=PackedVector2Array([Vector2.ZERO,Vector2(length,0.),Vector2(_dot(c-a,tangent),height)])
	return _slice(points,indices,a,b,depth,height,max_vertices,max_triangles,polygon)

func _slice(points:PackedVector3Array,indices:PackedInt32Array,start:Vector3,finish:Vector3,depth_axis:Vector3,half_depth:float,max_vertices:int,max_triangles:int,polygon:PackedVector2Array)->Dictionary:
	_failure=""; _work=0; _edge_nodes={}; _input_edges={}; _cut_faces={}; _bindings=[]
	_clip_polygon=polygon.duplicate()
	_vertex_limit=max_vertices; _triangle_limit=max_triangles
	if points.is_empty() or points.size()>max_vertices or max_vertices<3 or max_vertices>8192 or indices.is_empty() or indices.size()%3!=0 or indices.size()/3>max_triangles or max_triangles<1 or max_triangles>16384: return _invalid("input_budget")
	for p in points:
		if not p.is_finite() or p.length_squared()>256.: return _invalid("point")
	for v in indices:
		if v<0 or v>=points.size(): return _invalid("index")
	for p in [start,finish,depth_axis]:
		if not p.is_finite() or p.length_squared()>256.: return _invalid("curtain")
	if not is_finite(half_depth) or half_depth<=EPS or half_depth>(1. if polygon.is_empty() else 4.): return _invalid("depth")
	_length=start.distance_to(finish)
	if _length<=EPS or _length>4.: return _invalid("stroke")
	_start=start; _half_depth=half_depth; _tangent=(finish-start)/_length
	_depth=depth_axis-_tangent*_dot(depth_axis,_tangent)
	if _depth.length_squared()<1e-12: return _invalid("curtain_axis")
	_depth=_depth.normalized(); _normal=_tangent.cross(_depth).normalized()
	_points=points.duplicate(); _original=points.duplicate()
	for i in range(points.size()): _bindings.append({"ids":Vector3i(i,i,i),"weights":Vector3(1,0,0)})
	for off in range(0,indices.size(),3):
		var face:=PackedInt32Array([indices[off],indices[off+1],indices[off+2]])
		if _area(points[face[0]],points[face[1]],points[face[2]])<=1e-12: return _invalid("degenerate_face")
		for j in range(3):
			var a:int=face[j]; var b:int=face[(j+1)%3]; var key:=_key(a,b)
			if not _input_edges.has(key): _input_edges[key]=[]
			var incident:Array=_input_edges[key]
			if incident.size()>=2 or (not incident.is_empty() and incident[0].a==a): return _invalid("nonmanifold_source")
			incident.append({"face":off/3,"a":a})
	if not _valid_vertex_links(indices): return _invalid(_failure)
	for off in range(0,indices.size(),3):
		if not _tick(): return _invalid(_failure)
		var face:=Vector3i(indices[off],indices[off+1],indices[off+2])
		_plan(face,int(off/3))
		if _failure!="": return _invalid(_failure)
	var output:Array[PackedInt32Array]=[]; var sources:=PackedInt32Array(); var seams:={}
	for off in range(0,indices.size(),3):
		var face:=Vector3i(indices[off],indices[off+1],indices[off+2]); var id:int=off/3
		var local:Array[PackedInt32Array]=[PackedInt32Array([face.x,face.y,face.z])]
		var nodes:PackedInt32Array=_cut_faces[id].nodes.duplicate() if _cut_faces.has(id) else PackedInt32Array()
		for j in range(3):
			for v in _edge_nodes.get(_key(face[j],face[(j+1)%3]),PackedInt32Array()):
				if not nodes.has(v): nodes.append(v)
		for v in nodes:
			local=_insert(local,v)
			if _failure!="": return _invalid(_failure)
		var retained:=0.; var local_seams:={}
		var original_normal:=(points[face.y]-points[face.x]).cross(points[face.z]-points[face.x])
		for triangle in local:
			if not _tick(): return _invalid(_failure)
			var normal:=(_points[triangle[1]]-_points[triangle[0]]).cross(_points[triangle[2]]-_points[triangle[0]])
			if _dot(normal,original_normal)<=0.: return _invalid("subdivision_winding")
			retained+=_area(_points[triangle[0]],_points[triangle[1]],_points[triangle[2]])
			output.append(triangle); sources.append(id)
			if output.size()>_triangle_limit: return _invalid("triangle_budget")
			if _cut_faces.has(id):
				var cut:Dictionary=_cut_faces[id]
				for j in range(3):
					var a:int=triangle[j]; var b:int=triangle[(j+1)%3]
					if _on_segment(_points[a],cut.a,cut.b) and _on_segment(_points[b],cut.a,cut.b):
						seams[_key(a,b)]=true; local_seams[_key(a,b)]=true
		if _cut_faces.has(id) and not _complete_seam(_cut_faces[id].nodes,local_seams): return _invalid("incomplete_face_seam")
		var original_area:=_area(points[face.x],points[face.y],points[face.z])
		if absf(retained-original_area)>maxf(1e-9,original_area*.00001): return _invalid("area_not_preserved")
	if not _cut_faces.is_empty() and seams.is_empty(): return _invalid("missing_seam")
	_split_fans(output,seams)
	if _failure!="": return _invalid(_failure)
	var packed:=PackedInt32Array()
	for triangle in output: packed.append_array(triangle)
	return {"valid":true,"changed":not _cut_faces.is_empty(),"reason":"","points":_points,"indices":packed,"sources":sources,"bindings":_bindings,"work":_work}

func _valid_vertex_links(indices:PackedInt32Array)->bool:
	var incident:={}; var boundary:={}
	for off in range(0,indices.size(),3):
		for j in range(3):
			var v:int=indices[off+j]
			if not incident.has(v): incident[v]=PackedInt32Array()
			incident[v].append(off/3)
	for edge in _input_edges:
		if _input_edges[edge].size()==1:
			boundary[edge.x]=int(boundary.get(edge.x,0))+1; boundary[edge.y]=int(boundary.get(edge.y,0))+1
	for v in incident:
		if int(boundary.get(v,0)) not in [0,2]: _failure="nonmanifold_vertex"; return false
		var stack:=PackedInt32Array([incident[v][0]]); var visited:={incident[v][0]:true}
		while not stack.is_empty():
			if not _tick(): return false
			var face:=stack[stack.size()-1]; stack.resize(stack.size()-1)
			for j in range(3):
				var other:int=indices[face*3+j]
				if other==v: continue
				for adjacent in _input_edges[_key(v,other)]:
					if not visited.has(adjacent.face): visited[adjacent.face]=true; stack.append(adjacent.face)
		if visited.size()!=incident[v].size(): _failure="nonmanifold_vertex"; return false
	return true
func _complete_seam(nodes:PackedInt32Array,seams:Dictionary)->bool:
	var neighbors:={}
	for edge in seams:
		if not neighbors.has(edge.x): neighbors[edge.x]=PackedInt32Array()
		if not neighbors.has(edge.y): neighbors[edge.y]=PackedInt32Array()
		neighbors[edge.x].append(edge.y); neighbors[edge.y].append(edge.x)
	var visited:={nodes[0]:true}; var stack:=PackedInt32Array([nodes[0]])
	while not stack.is_empty():
		if not _tick(): return false
		var v:=stack[stack.size()-1]; stack.resize(stack.size()-1)
		for next in neighbors.get(v,PackedInt32Array()):
			if not visited.has(next): visited[next]=true; stack.append(next)
	return visited.has(nodes[1]) and visited.has(nodes[2])

func _plan(face:Vector3i,id:int)->void:
	var distance:=PackedFloat64Array(); var hit:=PackedVector3Array()
	for v in [face.x,face.y,face.z]:
		var signed:=_dot(_original[v]-_start,_normal)
		distance.append(0. if absf(signed)<EPS else signed)
	if maxf(absf(distance[0]),maxf(absf(distance[1]),absf(distance[2])))<EPS:
		if not _clip_polygon.is_empty():return
		var lo:=Vector2(INF,INF); var hi:=Vector2(-INF,-INF)
		for v in [face.x,face.y,face.z]:
			var q:=Vector2(_dot(_original[v]-_start,_tangent),_dot(_original[v]-_start,_depth)); lo=lo.min(q); hi=hi.max(q)
		if hi.x>=0. and lo.x<=_length and hi.y>=-_half_depth and lo.y<=_half_depth: _failure="coplanar_curtain"
		return
	for j in range(3):
		var k:=(j+1)%3
		if absf(distance[j])<EPS: _unique(hit,_original[face[j]])
		if (distance[j]<0. and distance[k]>0.) or (distance[j]>0. and distance[k]<0.):
			var a:=mini(face[j],face[k]); var b:=maxi(face[j],face[k])
			var da:=_dot(_original[a]-_start,_normal); var db:=_dot(_original[b]-_start,_normal)
			_unique(hit,_original[a].lerp(_original[b],da/(da-db)))
	if hit.size()<2: return
	if hit.size()>2: _failure="ambiguous_intersection"; return
	var clipped:=_clip(hit[0],hit[1])
	if clipped.is_empty(): return
	var a:Vector3=clipped[0]; var b:Vector3=clipped[1]
	if a.distance_to(b)<=EPS*4.: return
	# An incision along an already-open edge must not refine or heal its banks.
	for j in range(3):
		var u:Vector3=_original[face[j]]; var v:Vector3=_original[face[(j+1)%3]]
		if a.distance_to(Geometry3D.get_closest_point_to_segment(a,u,v))<=EPS*2. and b.distance_to(Geometry3D.get_closest_point_to_segment(b,u,v))<=EPS*2. and _input_edges[_key(face[j],face[(j+1)%3])].size()==1: return
	var first:=_node(a,face); var last:=_node(b,face)
	if _failure!="": return
	# A transverse segment's interior midpoint must not snap onto a nearby
	# source edge in a thin wedge. Only a material segment actually lying on
	# that edge shares its midpoint with the adjacent source face.
	var edge_midpoint:=false
	for j in range(3):
		var edge:=_key(face[j],face[(j+1)%3])
		if _material_on_edge(first,edge) and _material_on_edge(last,edge):edge_midpoint=true
	var middle:=_node((a+b)*.5,face,edge_midpoint)
	if _failure!="": return
	if first==last: _failure="collapsed_cut"; return
	_cut_faces[id]={"a":a,"b":b,"nodes":PackedInt32Array([first,last,middle])}

func _unique(points:PackedVector3Array,p:Vector3)->void:
	for prior in points:
		if prior.distance_to(p)<=EPS: return
	points.append(p)
func _clip(a:Vector3,b:Vector3)->PackedVector3Array:
	var lo:=0.; var hi:=1.
	if not _clip_polygon.is_empty():
		var point:=Vector2(_dot(a-_start,_tangent),_dot(a-_start,_depth))
		var motion:=Vector2(_dot(b-a,_tangent),_dot(b-a,_depth))
		for i in range(_clip_polygon.size()):
			var first:Vector2=_clip_polygon[i];var side:Vector2=_clip_polygon[(i+1)%_clip_polygon.size()]-first
			var value:=_cross(side,point-first);var delta:=_cross(side,motion)
			if absf(delta)<1e-15:
				if value<-EPS*side.length():return PackedVector3Array()
			else:
				var crossing:float=-value/delta
				if delta>0.:lo=maxf(lo,crossing)
				else:hi=minf(hi,crossing)
				if hi<=lo:return PackedVector3Array()
		return PackedVector3Array([a.lerp(b,lo),a.lerp(b,hi)])
	for axis in [0,1]:
		var direction:Vector3=_tangent if axis==0 else _depth
		var value:=_dot(a-_start,direction); var delta:=_dot(b-a,direction)
		var lower:=0. if axis==0 else -_half_depth; var upper:=_length if axis==0 else _half_depth
		if absf(delta)<1e-15:
			if value<lower or value>upper: return PackedVector3Array()
		else:
			var u:=(lower-value)/delta; var v:=(upper-value)/delta
			lo=maxf(lo,minf(u,v)); hi=minf(hi,maxf(u,v))
			if hi<=lo: return PackedVector3Array()
	return PackedVector3Array([a.lerp(b,lo),a.lerp(b,hi)])
func _material_on_edge(index:int,edge:Vector2i)->bool:
	var binding:Dictionary=_bindings[index]
	for j in range(3):
		if binding.weights[j]>0. and binding.ids[j]!=edge.x and binding.ids[j]!=edge.y:return false
	return true

func _node(p:Vector3,face:Vector3i,snap_edges:=true)->int:
	for v in [face.x,face.y,face.z]:
		if p.distance_to(_original[v])<=EPS: return v
	var weights:=_bary(p,_original[face.x],_original[face.y],_original[face.z])
	var edge:=Vector2i(-1,-1)
	var nearest:=EPS*2. if snap_edges else 0.
	for j in range(3):
		var a:Vector3=_original[face[(j+1)%3]]; var b:Vector3=_original[face[(j+2)%3]]
		var closest:=Geometry3D.get_closest_point_to_segment(p,a,b)
		var distance:=p.distance_to(closest)
		if distance<nearest:
			nearest=distance; edge=_key(face[(j+1)%3],face[(j+2)%3])
	var edge_first:=-1;var edge_last:=-1
	if edge.x>=0:
		# Both incident faces must use the same source-edge arithmetic order.
		# Reversed closest-point interpolation and three-term reconstruction
		# can otherwise create distinct rounded copies of one shared crossing.
		var a:Vector3=_original[edge.x];var b:Vector3=_original[edge.y]
		var t:=clampf(_dot(p-a,b-a)/_dot(b-a,b-a),0.,1.)
		weights=Vector3.ZERO
		for j in range(3):
			if face[j]==edge.x:edge_first=j;weights[j]=1.-t
			if face[j]==edge.y:edge_last=j;weights[j]=t
	if not weights.is_finite() or minf(weights.x,minf(weights.y,weights.z))<0.: _failure="outside_binding"; return -1
	if edge.x>=0:p=_affine(_original[edge.x],_original[edge.y],_original[edge.y],Vector3(weights[edge_first],weights[edge_last],0.))
	else:p=_affine(_original[face.x],_original[face.y],_original[face.z],weights)
	if edge.x>=0:
		for v in _edge_nodes.get(edge,PackedInt32Array()):
			if _points[v].distance_to(p)<=EPS*2.: return v
	if _points.size()>=_vertex_limit: _failure="vertex_budget"; return -1
	var index:=_points.size(); _points.append(p); _bindings.append({"ids":face,"weights":weights})
	if edge.x>=0:
		if not _edge_nodes.has(edge): _edge_nodes[edge]=PackedInt32Array()
		_edge_nodes[edge].append(index)
	return index

static func _affine(a:Vector3,b:Vector3,c:Vector3,weights:Vector3)->Vector3:
	# Normalize in scalar double arithmetic. Rounded Vector3 weights need not
	# sum to exactly one; a direct weighted sum then drifts off the source plane.
	var total:float=float(weights.x)+weights.y+weights.z
	var result:=Vector3.ZERO
	for axis in range(3):
		var base:float=a[axis]
		result[axis]=base+((float(b[axis])-base)*weights.y+(float(c[axis])-base)*weights.z)/total
	return result

func _insert(triangles:Array[PackedInt32Array],v:int)->Array[PackedInt32Array]:
	var output:Array[PackedInt32Array]=[]; var found:=false
	for triangle in triangles:
		if not _tick(): return []
		if triangle.has(v): output.append(triangle); found=true; continue
		var on_edge:=-1; var nearest:=EPS*2.
		for j in range(3):
			var a:Vector3=_points[triangle[j]]; var b:Vector3=_points[triangle[(j+1)%3]]
			var distance:=_points[v].distance_to(Geometry3D.get_closest_point_to_segment(_points[v],a,b))
			if distance<nearest: nearest=distance; on_edge=j
		if on_edge>=0:
			# A rounded edge point is one topological edge insertion, not a
			# three-face fan with a microscopic overlapping third triangle.
			var a:int=triangle[on_edge]; var b:int=triangle[(on_edge+1)%3]; var c:int=triangle[(on_edge+2)%3]
			output.append(PackedInt32Array([a,v,c])); output.append(PackedInt32Array([v,b,c])); found=true
			continue
		var weights:=_bary(_points[v],_points[triangle[0]],_points[triangle[1]],_points[triangle[2]])
		if not weights.is_finite() or minf(weights.x,minf(weights.y,weights.z))<-.0000002: output.append(triangle); continue
		found=true
		for j in range(3):
			var a:int=triangle[j]; var b:int=triangle[(j+1)%3]
			if _area(_points[a],_points[b],_points[v])>1e-14: output.append(PackedInt32Array([a,b,v]))
		if output.size()>_triangle_limit: _failure="triangle_budget"; return []
	if not found: _failure="point_insertion"
	return output
func _on_segment(p:Vector3,a:Vector3,b:Vector3)->bool:
	var delta:=b-a; var length_sq:=_dot(delta,delta)
	var t:=_dot(p-a,delta)/length_sq
	# Endpoint tolerance is a scene distance. A fixed fractional tolerance
	# shrinks incorrectly on short segments and leaves uncut bridges.
	return p.distance_to(a+delta*clampf(t,0.,1.))<=EPS*4.

func _split_fans(triangles:Array[PackedInt32Array],seams:Dictionary)->void:
	var incident:={}; var edges:={}; var seam_vertices:={}; var assignment:={}
	for key in seams: seam_vertices[key.x]=true; seam_vertices[key.y]=true
	for i in range(triangles.size()):
		for v in triangles[i]:
			if not incident.has(v): incident[v]=PackedInt32Array()
			incident[v].append(i)
		for j in range(3):
			var key:=_key(triangles[i][j],triangles[i][(j+1)%3])
			if not edges.has(key): edges[key]=PackedInt32Array()
			edges[key].append(i)
			if edges[key].size()>2: _failure="nonmanifold_subdivision"; return
	for v in seam_vertices:
		var visited:={}; var fan:=0
		for seed in incident.get(v,PackedInt32Array()):
			if visited.has(seed): continue
			var target:int=v
			if fan>0:
				if _points.size()>=_vertex_limit: _failure="vertex_budget"; return
				target=_points.size(); _points.append(_points[v]); _bindings.append(_bindings[v].duplicate(true))
			fan+=1
			var stack:=PackedInt32Array([seed]); visited[seed]=true
			while not stack.is_empty():
				if not _tick(): return
				var current:=stack[stack.size()-1]; stack.resize(stack.size()-1); assignment[Vector2i(v,current)]=target
				for other in triangles[current]:
					if other==v: continue
					var key:=_key(v,other)
					if seams.has(key): continue
					for neighbor in edges[key]:
						if not visited.has(neighbor): visited[neighbor]=true; stack.append(neighbor)
	for i in range(triangles.size()):
		for j in range(3):
			var key:=Vector2i(triangles[i][j],i)
			if assignment.has(key): triangles[i][j]=assignment[key]
