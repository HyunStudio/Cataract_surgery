extends RefCounted
const G=preload("res://scripts/cut_geometry.gd")
var _physical:=false
const Precision=preload("res://scripts/membrane_precision.gd")
## Finite curtain incision of an oriented triangle membrane. No material is removed.
## Source-edge identity preserves shared nodes without welding coincident old seams.
## This geometric engineering model is not calibrated tissue fracture mechanics.
const EPS:=0.0000001
const MAX_WORK:=2000000
var _points=PackedVector3Array()
var _original=PackedVector3Array()
var _bindings:Array[Dictionary]=[]
var _edge_nodes:Dictionary={}
var _input_edges:Dictionary={}
var _cut_faces:Dictionary={}
var _failure:=""
var _work:=0
var _vertex_limit:=0
var _triangle_limit:=0
var _start=Vector3.ZERO
var _tangent=Vector3.ZERO
var _depth=Vector3.ZERO
var _normal=Vector3.ZERO
var _length:=0.
var _half_depth:=0.
var _clip_polygon=[]

func _invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":reason,"points":PackedVector3Array(),"indices":PackedInt32Array(),"sources":PackedInt32Array(),"bindings":[],"work":_work}
func _tick()->bool:
	_work+=1
	if _work>MAX_WORK: _failure="work_budget"; return false
	return true
static func _dot(a,b)->float:
	return float(a[0])*b[0]+float(a[1])*b[1]+float(a[2])*b[2]
static func _key(a:int,b:int)->Vector2i:
	return Vector2i(mini(a,b),maxi(a,b))
static func _area(a,b,c)->float:
	var ux:float=float(b[0])-a[0];var uy:float=float(b[1])-a[1];var uz:float=float(b[2])-a[2]
	var vx:float=float(c[0])-a[0];var vy:float=float(c[1])-a[1];var vz:float=float(c[2])-a[2]
	var nx:=uy*vz-uz*vy;var ny:=uz*vx-ux*vz;var nz:=ux*vy-uy*vx
	return sqrt(nx*nx+ny*ny+nz*nz)*.5
func _project(p,axis:int):
	return G.make2(p[1],p[2],_physical) if axis==0 else (G.make2(p[0],p[2],_physical) if axis==1 else G.make2(p[0],p[1],_physical))
static func _cross(a,b)->float:return float(a[0])*b[1]-float(a[1])*b[0]
func _bary(p,a,b,c):
	var normal=G.cross(G.sub(b,a),G.sub(c,a));var axis:int=normal.abs().max_axis_index() if normal is Vector3 else 0
	if _physical:
		for j in range(1,3):
			if absf(normal[j])>absf(normal[axis]):axis=j
	var pa=_project(a,axis);var pb=_project(b,axis);var pc=_project(c,axis);var pp=_project(p,axis)
	var ux:float=float(pb[0])-pa[0];var uy:float=float(pb[1])-pa[1]
	var vx:float=float(pc[0])-pa[0];var vy:float=float(pc[1])-pa[1]
	var qx:float=float(pp[0])-pa[0];var qy:float=float(pp[1])-pa[1]
	var determinant:=ux*vy-uy*vx
	if absf(determinant)<1e-20:return G.make3(-INF,-INF,-INF,_physical)
	var second:float=(qx*vy-qy*vx)/determinant;var third:float=(ux*qy-uy*qx)/determinant
	return G.make3(1.-second-third,second,third,_physical)

func slice(points:PackedVector3Array,indices:PackedInt32Array,start:Vector3,finish:Vector3,depth_axis:Vector3,half_depth:float,max_vertices:int=4096,max_triangles:int=8192)->Dictionary:
	_physical=false
	return _slice(points,indices,start,finish,depth_axis,half_depth,max_vertices,max_triangles,[])

## A finite, planar sharp-edge sweep patch. Coplanar sliding has no unique
## transverse incision, so it leaves those faces intact rather than guessing.
## material_partition additionally verifies positive affine material triangles
## and returns their source fractions. Legacy display geometry is a separate
## contract: rounded orientation alone does not qualify original-material FEM.
func slice_triangle(points:PackedVector3Array,indices:PackedInt32Array,a:Vector3,b:Vector3,c:Vector3,max_vertices:int=4096,max_triangles:int=8192,material_partition:bool=false)->Dictionary:
	_physical=false
	return _triangle(points,indices,a,b,c,max_vertices,max_triangles,material_partition)

func slice_triangle64(values:PackedFloat64Array,indices:PackedInt32Array,a:Vector3,b:Vector3,c:Vector3,max_vertices:int=4096,max_triangles:int=8192)->Dictionary:
	_physical=true;_work=0
	if values.is_empty() or values.size()%3!=0 or values.size()/3>max_vertices:return _invalid("physical_shape")
	var points:Array=[]
	for i in range(0,values.size(),3):points.append(PackedFloat64Array([values[i],values[i+1],values[i+2]]))
	return _triangle(points,indices,G.make3(a.x,a.y,a.z,true),G.make3(b.x,b.y,b.z,true),G.make3(c.x,c.y,c.z,true),max_vertices,max_triangles,true)

func _triangle(points,indices:PackedInt32Array,a,b,c,max_vertices:int,max_triangles:int,material_partition:bool)->Dictionary:
	_work=0
	for point in [a,b,c]:
		if not G.finite(point) or G.norm2(point)>256.:return _invalid("patch")
	var edge=G.sub(b,a);var length:=G.length(edge)
	if length<=EPS:return _invalid("patch_resolution")
	var tangent=G.divide(edge,length)
	var depth=G.sub(G.sub(c,a),G.mul(tangent,_dot(G.sub(c,a),tangent)));var height:=G.length(depth)
	if height<=EPS:return _invalid("patch_resolution")
	depth=G.divide(depth,height)
	var polygon:Array=[G.make2(0.,0.,_physical),G.make2(length,0.,_physical),G.make2(_dot(G.sub(c,a),tangent),height,_physical)]
	return _slice(points,indices,a,b,depth,height,max_vertices,max_triangles,polygon,material_partition)

func _slice(points,indices:PackedInt32Array,start,finish,depth_axis,half_depth:float,max_vertices:int,max_triangles:int,polygon:Array,material_partition:bool=false)->Dictionary:
	_failure=""; _work=0; _edge_nodes={}; _input_edges={}; _cut_faces={}; _bindings=[]
	_clip_polygon=polygon.duplicate()
	_vertex_limit=max_vertices; _triangle_limit=max_triangles
	if points.is_empty() or points.size()>max_vertices or max_vertices<3 or max_vertices>8192 or indices.is_empty() or indices.size()%3!=0 or indices.size()/3>max_triangles or max_triangles<1 or max_triangles>16384: return _invalid("input_budget")
	for p in points:
		if not G.finite(p) or G.norm2(p)>256.: return _invalid("point")
	for v in indices:
		if v<0 or v>=points.size(): return _invalid("index")
	for p in [start,finish,depth_axis]:
		if not G.finite(p) or G.norm2(p)>256.: return _invalid("curtain")
	if not is_finite(half_depth) or half_depth<=EPS or half_depth>(1. if polygon.is_empty() else 4.): return _invalid("depth")
	_length=G.distance(start,finish)
	if _length<=EPS or _length>4.: return _invalid("stroke")
	_start=start; _half_depth=half_depth; _tangent=G.divide(G.sub(finish,start),_length)
	_depth=G.sub(depth_axis,G.mul(_tangent,_dot(depth_axis,_tangent)))
	if G.norm2(_depth)<1e-12: return _invalid("curtain_axis")
	_depth=G.normalized(_depth);_normal=G.normalized(G.cross(_tangent,_depth))
	_points=points.duplicate(); _original=points.duplicate()
	for i in range(points.size()): _bindings.append({"ids":Vector3i(i,i,i),"weights":Vector3(1,0,0)})
	for off in range(0,indices.size(),3):
		var face:=PackedInt32Array([indices[off],indices[off+1],indices[off+2]])
		var area:=_area(points[face[0]],points[face[1]],points[face[2]])
		# Original-material mechanics retains fine display slivers without
		# making them independent elastic elements. A prior accepted positive
		# output face cannot become invalid solely by entering the next cut.
		# All winding, material partition and seam checks still apply below.
		if not is_finite(area) or area<=(0. if material_partition else 1e-12): return _invalid("degenerate_face")
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
	var output:Array[PackedInt32Array]=[]; var sources:=PackedInt32Array();var fractions:=PackedFloat64Array(); var seams:={}
	for off in range(0,indices.size(),3):
		var face:=Vector3i(indices[off],indices[off+1],indices[off+2]); var id:int=off/3
		var local:Array[PackedInt32Array]=[PackedInt32Array([face.x,face.y,face.z])]
		var nodes:PackedInt32Array=_cut_faces[id].nodes.duplicate() if _cut_faces.has(id) else PackedInt32Array()
		for j in range(3):
			for v in _edge_nodes.get(_key(face[j],face[(j+1)%3]),PackedInt32Array()):
				if not nodes.has(v): nodes.append(v)
		for v in nodes:
			var required:=Vector2i(-1,-1)
			if _cut_faces.has(id) and v==_cut_faces[id].nodes[2]:required=_key(_cut_faces[id].nodes[0],_cut_faces[id].nodes[1])
			local=_insert(local,v,required)
			if _failure!="": return _invalid(_failure)
		var retained:=0.; var local_seams:={}
		var original_normal=G.cross(G.sub(points[face.y],points[face.x]),G.sub(points[face.z],points[face.x]))
		for triangle in local:
			if not _tick(): return _invalid(_failure)
			var normal=G.cross(G.sub(_points[triangle[1]],_points[triangle[0]]),G.sub(_points[triangle[2]],_points[triangle[0]]))
			if _dot(normal,original_normal)<=0.: return _invalid("subdivision_winding")
			if material_partition:
				var fraction:=_material_fraction(triangle,face)
				if _failure!="":return _invalid(_failure)
				if fraction<=0.:return _invalid("material_subdivision_winding")
				retained+=fraction;fractions.append(fraction)
			else:retained+=_area(_points[triangle[0]],_points[triangle[1]],_points[triangle[2]])
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
		# Material mode verifies the affine source domain. Display mode retains
		# its prior rounded geometric-area contract and emits no material fractions.
		var retained_area:float=retained*original_area if material_partition else retained
		if absf(retained_area-original_area)>maxf(1e-9,original_area*.00001): return _invalid("area_not_preserved")
	if not _cut_faces.is_empty() and seams.is_empty(): return _invalid("missing_seam")
	_split_fans(output,seams)
	if _failure!="": return _invalid(_failure)
	var packed:=PackedInt32Array()
	for triangle in output: packed.append_array(triangle)
	var published=PackedVector3Array();var points64:=PackedFloat64Array()
	if _physical:
		for point in _points:points64.append_array(point);published.append(Vector3(point[0],point[1],point[2]))
	else:published=_points
	return {"valid":true,"changed":not _cut_faces.is_empty(),"reason":"","points":published,"points64":points64,"indices":packed,"sources":sources,"bindings":_bindings,"fractions":fractions,"work":_work}

func _source_weights(index:int,face:Vector3i)->PackedFloat64Array:
	var binding:Dictionary=_bindings[index];var result:=PackedFloat64Array([0.,0.,0.])
	var weights:=Precision.binding_weights(binding);var total:float=weights[0]+weights[1]+weights[2]
	if not is_finite(total) or total<=0.:_failure="subdivision_binding";return result
	for j in range(3):
		var weight:float=weights[j]/total
		if not is_finite(weight) or weight<0.:_failure="subdivision_binding";return result
		if weight==0.:continue
		var corner:=-1
		for k in range(3):
			if face[k]==binding.ids[j]:corner=k;break
		if corner<0:_failure="subdivision_binding_source";return result
		result[corner]+=weight
	return result
func _material_fraction(triangle:PackedInt32Array,face:Vector3i)->float:
	var a:=_source_weights(triangle[0],face);var b:=_source_weights(triangle[1],face);var c:=_source_weights(triangle[2],face)
	return _material_orientation(a,b,c)
static func _material_orientation(a:PackedFloat64Array,b:PackedFloat64Array,c:PackedFloat64Array)->float:
	return (b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1])

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
	for node in nodes:
		if not visited.has(node):return false
	return true

func _plan(face:Vector3i,id:int)->void:
	var distance:=PackedFloat64Array();var hit:Array=[]
	for v in [face.x,face.y,face.z]:
		var signed:=_dot(G.sub(_original[v],_start),_normal)
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
			var da:=_dot(G.sub(_original[a],_start),_normal); var db:=_dot(G.sub(_original[b],_start),_normal)
			_unique(hit,G.lerp(_original[a],_original[b],da/(da-db)))
	if hit.size()<2: return
	if hit.size()>2: _failure="ambiguous_intersection"; return
	var clipped=_clip(hit[0],hit[1])
	if clipped.is_empty(): return
	var a=clipped[0];var b=clipped[1]
	if G.distance(a,b)<=EPS*4.: return
	# An incision along an already-open edge must not refine or heal its banks.
	for j in range(3):
		var u=_original[face[j]];var v=_original[face[(j+1)%3]]
		if G.distance(a,G.closest(a,u,v))<=EPS*2. and G.distance(b,G.closest(b,u,v))<=EPS*2. and _input_edges[_key(face[j],face[(j+1)%3])].size()==1: return
	var first:=_node(a,face); var last:=_node(b,face)
	if _failure!="": return
	if first==last: _failure="collapsed_cut"; return
	var middle:=_midpoint(first,last,face)
	if _failure!="":return
	_cut_faces[id]={"a":a,"b":b,"nodes":PackedInt32Array([first,last,middle])}

func _unique(points:Array,p)->void:
	for prior in points:
		if G.distance(prior,p)<=EPS: return
	points.append(p)
func _clip(a,b)->Array:
	var lo:=0.; var hi:=1.
	if not _clip_polygon.is_empty():
		var point=G.make2(_dot(G.sub(a,_start),_tangent),_dot(G.sub(a,_start),_depth),_physical)
		var motion=G.make2(_dot(G.sub(b,a),_tangent),_dot(G.sub(b,a),_depth),_physical)
		for i in range(_clip_polygon.size()):
			var first=_clip_polygon[i];var side=G.sub(_clip_polygon[(i+1)%_clip_polygon.size()],first)
			var value:=_cross(side,G.sub(point,first));var delta:=_cross(side,motion)
			if absf(delta)<1e-15:
				if value<-EPS*G.length(side):return []
			else:
				var crossing:float=-value/delta
				if delta>0.:lo=maxf(lo,crossing)
				else:hi=minf(hi,crossing)
				if hi<=lo:return []
		return [G.lerp(a,b,lo),G.lerp(a,b,hi)]
	for axis in [0,1]:
		var direction=_tangent if axis==0 else _depth
		var value:=_dot(G.sub(a,_start),direction); var delta:=_dot(G.sub(b,a),direction)
		var lower:=0. if axis==0 else -_half_depth; var upper:=_length if axis==0 else _half_depth
		if absf(delta)<1e-15:
			if value<lower or value>upper: return []
		else:
			var u:=(lower-value)/delta; var v:=(upper-value)/delta
			lo=maxf(lo,minf(u,v)); hi=minf(hi,maxf(u,v))
			if hi<=lo: return []
	return [G.lerp(a,b,lo),G.lerp(a,b,hi)]
func _material_on_edge(index:int,edge:Vector2i)->bool:
	var binding:Dictionary=_bindings[index]
	var weights:=Precision.binding_weights(binding)
	for j in range(3):
		if weights[j]>0. and binding.ids[j]!=edge.x and binding.ids[j]!=edge.y:return false
	return true

func _midpoint(first:int,last:int,face:Vector3i)->int:
	# This interior node opens both banks even when both segment tips lie
	# inside one face. Compose the accepted material bindings, never refit
	# a rounded display midpoint in an ill-conditioned source triangle.
	var a:=_source_weights(first,face);var b:=_source_weights(last,face);var weights:=PackedFloat64Array()
	for j in range(3):weights.append(.5*(a[j]+b[j]))
	if _failure!="":return -1
	var point=G.make3(0.,0.,0.,_physical);var total:float=weights[0]+weights[1]+weights[2]
	for axis in range(3):
		var base:float=_original[face[0]][axis]
		point[axis]=base+((float(_original[face[1]][axis])-base)*weights[1]+(float(_original[face[2]][axis])-base)*weights[2])/total
	var edge:=Vector2i(-1,-1)
	for j in range(3):
		if weights[j]==0.:edge=_key(face[(j+1)%3],face[(j+2)%3]);break
	if edge.x>=0:
		for old in _edge_nodes.get(edge,PackedInt32Array()):
			if old==first or old==last:continue
			var t:=_edge_fraction(old,edge);var lo:=_edge_fraction(first,edge);var hi:=_edge_fraction(last,edge)
			if t>minf(lo,hi) and t<maxf(lo,hi) and G.distance(_points[old],point)<=EPS*2.:return old
	if _points.size()>=_vertex_limit:_failure="vertex_budget";return -1
	var index:int=_points.size();_points.append(point)
	_bindings.append({"ids":face,"weights":Vector3(weights[0],weights[1],weights[2]),"weights64":weights})
	if edge.x>=0:
		if not _edge_nodes.has(edge):_edge_nodes[edge]=PackedInt32Array()
		_edge_nodes[edge].append(index)
	return index

func _node(p,face:Vector3i,snap_edges:=true)->int:
	for v in [face.x,face.y,face.z]:
		if G.distance(p,_original[v])<=EPS: return v
	var weights=_bary(p,_original[face.x],_original[face.y],_original[face.z])
	var edge:=Vector2i(-1,-1)
	var nearest:=EPS*2. if snap_edges else 0.
	for j in range(3):
		var a=_original[face[(j+1)%3]];var b=_original[face[(j+2)%3]]
		var closest=G.closest(p,a,b)
		var distance:=G.distance(p,closest)
		if distance<nearest:
			nearest=distance; edge=_key(face[(j+1)%3],face[(j+2)%3])
	var edge_first:=-1;var edge_last:=-1
	if edge.x>=0:
		# Both incident faces must use the same source-edge arithmetic order.
		# Reversed closest-point interpolation and three-term reconstruction
		# can otherwise create distinct rounded copies of one shared crossing.
		var a=_original[edge.x];var b=_original[edge.y]
		var t:=clampf(_dot(G.sub(p,a),G.sub(b,a))/_dot(G.sub(b,a),G.sub(b,a)),0.,1.)
		weights=G.make3(0.,0.,0.,_physical)
		for j in range(3):
			if face[j]==edge.x:edge_first=j;weights[j]=1.-t
			if face[j]==edge.y:edge_last=j;weights[j]=t
	if not G.finite(weights) or minf(weights[0],minf(weights[1],weights[2]))<0.: _failure="outside_binding"; return -1
	if edge.x>=0:p=_affine(_original[edge.x],_original[edge.y],_original[edge.y],G.make3(weights[edge_first],weights[edge_last],0.,_physical))
	else:p=_affine(_original[face.x],_original[face.y],_original[face.z],weights)
	if edge.x>=0:
		for v in _edge_nodes.get(edge,PackedInt32Array()):
			if G.distance(_points[v],p)<=EPS*2.: return v
	if _points.size()>=_vertex_limit: _failure="vertex_budget"; return -1
	var index:int=_points.size(); _points.append(p); _bindings.append({"ids":face,"weights":Vector3(weights[0],weights[1],weights[2]),"weights64":weights} if _physical else {"ids":face,"weights":weights})
	if edge.x>=0:
		if not _edge_nodes.has(edge): _edge_nodes[edge]=PackedInt32Array()
		_edge_nodes[edge].append(index)
	return index

static func _affine(a,b,c,weights):
	# Normalize in scalar double arithmetic. Rounded Vector3 weights need not
	# sum to exactly one; a direct weighted sum then drifts off the source plane.
	var total:float=float(weights[0])+weights[1]+weights[2]
	var result=G.make3(0.,0.,0.,a is PackedFloat64Array)
	for axis in range(3):
		var base:float=a[axis]
		result[axis]=base+((float(b[axis])-base)*weights[1]+(float(c[axis])-base)*weights[2])/total
	return result

func _edge_fraction(index:int,edge:Vector2i)->float:
	var binding:Dictionary=_bindings[index];var total:=0.;var last:=0.
	var weights:=Precision.binding_weights(binding)
	for j in range(3):
		total+=weights[j]
		if binding.ids[j]==edge.y:last+=weights[j]
	return last/total

func _source_edge(index:int)->Vector2i:
	var binding:Dictionary=_bindings[index];var ids:=PackedInt32Array()
	var weights:=Precision.binding_weights(binding)
	for j in range(3):
		if weights[j]>0. and not ids.has(binding.ids[j]):ids.append(binding.ids[j])
	return _key(ids[0],ids[1]) if ids.size()==2 else Vector2i(-1,-1)

func _insert(triangles:Array[PackedInt32Array],v:int,required:Vector2i=Vector2i(-1,-1))->Array[PackedInt32Array]:
	# Pick one topological insertion for the whole local mesh. Independent
	# proximity tests per triangle can select different almost coincident edges
	# and create three incident faces along a single new edge in a thin wedge.
	for triangle in triangles:
		if triangle.has(v):return triangles
	var chosen:=Vector2i(-1,-1);var nearest:=EPS*2.;var visited:Dictionary={}
	var source:=_source_edge(v)
	var fraction:=_edge_fraction(v,source) if source.x>=0 else 0.
	var face:Vector3i=_bindings[v].ids
	if required.x>=0:
		for triangle in triangles:
			for j in range(3):
				if _key(triangle[j],triangle[(j+1)%3])==required:chosen=required
		if chosen.x<0:_failure="midpoint_edge_insertion";return []
	for triangle in triangles:
		if required.x>=0:break
		if not _tick(): return []
		for j in range(3):
			var key:=_key(triangle[j],triangle[(j+1)%3])
			if visited.has(key):continue
			visited[key]=true
			if source.x>=0:
				# Rounded display proximity can prefer an unrelated almost
				# coincident edge. Source identity and affine order determine
				# the unique boundary subedge that actually contains this point.
				if not _material_on_edge(key.x,source) or not _material_on_edge(key.y,source):continue
				var first:=_edge_fraction(key.x,source);var last:=_edge_fraction(key.y,source)
				if fraction>minf(first,last) and fraction<maxf(first,last):
					if chosen.x>=0 and chosen!=key:_failure="material_edge_ambiguous";return []
					chosen=key
				continue
			var first:=_source_weights(key.x,face);var last:=_source_weights(key.y,face)
			# An interior material point cannot split a source boundary edge:
			# that drops its nonzero third-coordinate material region. Internal
			# fan edges retain the existing local display insertion rule, with
			# both incident triangles and all final partition/winding checks.
			var boundary:=false
			for component in range(3):
				if first[component]==0. and last[component]==0.:boundary=true;break
			if boundary:continue
			var a=_points[key.x];var b=_points[key.y]
			var distance:=G.distance(_points[v],G.closest(_points[v],a,b))
			if distance<nearest:nearest=distance;chosen=key
	if source.x>=0 and chosen.x<0:_failure="material_edge_insertion";return []
	var container:=-1;var best:=-INF
	if chosen.x<0:
		for i in range(triangles.size()):
			if not _tick():return []
			var triangle:PackedInt32Array=triangles[i]
			var weights=_bary(_points[v],_points[triangle[0]],_points[triangle[1]],_points[triangle[2]])
			if not G.finite(weights):continue
			var inside:=minf(weights[0],minf(weights[1],weights[2]))
			if inside>=-.0000002 and inside>best:best=inside;container=i
		if container<0:_failure="point_insertion";return []
	var output:Array[PackedInt32Array]=[]
	for i in range(triangles.size()):
		if not _tick():return []
		var triangle:PackedInt32Array=triangles[i];var on_edge:=-1
		if chosen.x>=0:
			for j in range(3):
				if _key(triangle[j],triangle[(j+1)%3])==chosen:on_edge=j;break
		if on_edge>=0:
			var a:int=triangle[on_edge];var b:int=triangle[(on_edge+1)%3];var c:int=triangle[(on_edge+2)%3]
			output.append(PackedInt32Array([a,v,c]));output.append(PackedInt32Array([v,b,c]))
		elif i==container:
			for j in range(3):
				var a:int=triangle[j];var b:int=triangle[(j+1)%3]
				if _area(_points[a],_points[b],_points[v])>1e-14:output.append(PackedInt32Array([a,b,v]))
		else:output.append(triangle)
		if output.size()>_triangle_limit:_failure="triangle_budget";return []
	return output
func _on_segment(p,a,b)->bool:
	var delta=G.sub(b,a);var length_sq:=_dot(delta,delta)
	var t:=_dot(G.sub(p,a),delta)/length_sq
	# Endpoint tolerance is a scene distance. A fixed fractional tolerance
	# shrinks incorrectly on short segments and leaves uncut bridges.
	return G.distance(p,G.add(a,G.mul(delta,clampf(t,0.,1.))))<=EPS*4.

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
