extends RefCounted
const GeometryLimits=preload("res://scripts/fine_geometry_limits.gd")
const Exact=preload("res://scripts/exact_material.gd")
## Fine affine retessellation only. Coarse mechanics and accepted histories
## remain authoritative. Coincident positions never identify connected banks.
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"changed":false,"reason":"material_reduce_"+reason}
static func edge(a:int,b:int)->Vector2i:return Vector2i(mini(a,b),maxi(a,b))
static func _canonical(s:Dictionary,vertex:int,chart:Vector3i)->PackedFloat64Array:
	var result:=PackedFloat64Array([0.,0.,0.])
	for j in range(s.support.point_nodes[vertex].size()):
		var node:int=s.support.point_nodes[vertex][j];var corner:=-1
		for k in range(3):
			if chart[k]==node:corner=k
		if corner<0:return PackedFloat64Array()
		result[corner]=s.support.point_weights[vertex][j]
	return result
static func _topology(s:Dictionary)->Dictionary:
	var faces:Array=[];var incident:Dictionary={};var edges:Dictionary={};var neighbors:Dictionary={};var boundary:Dictionary={}
	for f in range(s.ancestors.size()):
		var ids:PackedInt32Array=s.indices.slice(f*3,f*3+3);var rows:Array[PackedFloat64Array]=[]
		if ids[0]==ids[1] or ids[1]==ids[2] or ids[2]==ids[0]:return invalid("index")
		var chart:=Vector3i(s.support.elements[f*3],s.support.elements[f*3+1],s.support.elements[f*3+2])
		for j in range(3):
			var v:int=ids[j];var u:int=ids[(j+1)%3]
			if v<0 or v>=s.rest.size() or v==u:return invalid("index")
			if chart[j]<0 or chart[j]>=s.support.controls.size() or chart[j]==chart[(j+1)%3]:return invalid("control")
			rows.append(s.support.weights.slice(f*9+j*3,f*9+j*3+3))
			if not incident.has(v):incident[v]=[]
			if not neighbors.has(v):neighbors[v]={}
			incident[v].append(f);neighbors[v][u]=true
			# Undirected neighbors need both orientations even at a boundary.
			if not neighbors.has(u):neighbors[u]={}
			neighbors[u][v]=true
			var key:=edge(v,u)
			if not edges.has(key):edges[key]=[]
			if not edges[key].is_empty():
				var other:PackedInt32Array=faces[edges[key][0]].ids
				for k in range(3):
					if other[k]==v and other[(k+1)%3]==u:return invalid("winding")
			edges[key].append(f)
			if edges[key].size()>2:return invalid("nonmanifold")
		faces.append({"ids":ids,"chart":chart,"ancestor":s.ancestors[f],"rows":rows,"area":s.areas[f]})
	for key in edges:
		if edges[key].size()!=1:continue
		if not boundary.has(key.x):boundary[key.x]=[]
		if not boundary.has(key.y):boundary[key.y]=[]
		boundary[key.x].append(key.y);boundary[key.y].append(key.x)
	return {"valid":true,"faces":faces,"incident":incident,"edges":edges,"neighbors":neighbors,"boundary":boundary}
static func _candidate(s:Dictionary,t:Dictionary,v:int,protected_faces:Dictionary)->Dictionary:
	if s.anchored[v]!=0 or s.removed[v]!=0 or s.outside[v]!=0 or t.boundary.get(v,[]).size()!=2:return {}
	var star:Array=t.incident[v];var first:Dictionary=t.faces[star[0]];var chart:Vector3i=first.chart
	# A boundary-edge collapse requires one connected incident disk, not a
	# bow-tie plus an unrelated fan that happens to have boundary degree two.
	var visited:Dictionary={star[0]:true};var stack:Array=[star[0]]
	while not stack.is_empty():
		var face_id:int=stack.pop_back()
		for u in t.faces[face_id].ids:
			if u==v:continue
			for adjacent in t.edges[edge(v,u)]:
				if not visited.has(adjacent):visited[adjacent]=true;stack.append(adjacent)
	if visited.size()!=star.size():return {}
	var rows:Dictionary={}
	for f in star:
		var face:Dictionary=t.faces[f]
		if protected_faces.has(f) or face.chart!=chart or face.ancestor!=first.ancestor:return {}
		var orientation:Dictionary=Exact.orientation(face.rows[0],face.rows[1],face.rows[2])
		if not orientation.valid or orientation.sign<=0:return {}
		for j in range(3):
			var vertex:int=face.ids[j];var row:PackedFloat64Array=face.rows[j]
			# Every corner must describe the exact accepted publication map,
			# not merely a nearby normalized or per-face approximation.
			if row!=_canonical(s,vertex,chart) or not Exact.eligible(row):return {}
			rows[vertex]=row
	var a:int=t.boundary[v][0];var b:int=t.boundary[v][1]
	if not rows.has(a) or not rows.has(b) or not Exact.collinear_between(rows[a],rows[v],rows[b]):return {}
	for target in [a,b]:
		var edge_faces:Array=t.edges[edge(v,target)]
		if edge_faces.size()!=1:continue
		var deleted:int=edge_faces[0];var opposite:=-1
		for node in t.faces[deleted].ids:
			if node!=v and node!=target:opposite=node
		var common:Array=[]
		for node in t.neighbors[v]:
			if t.neighbors[target].has(node):common.append(node)
		if common.size()!=1 or common[0]!=opposite:continue
		var replacements:Dictionary={};var old_area:=0.;var total:=0.;var safe:=true
		for f in star:
			var face:Dictionary=t.faces[f];old_area+=face.area
			if f==deleted:continue
			var ids:PackedInt32Array=face.ids.duplicate();var next_rows:Array=face.rows.duplicate(true)
			var at:=ids.find(v);ids[at]=target;next_rows[at]=rows[target].duplicate()
			var orientation:Dictionary=Exact.orientation(next_rows[0],next_rows[1],next_rows[2])
			if not orientation.valid or orientation.sign<=0:safe=false;break
			var denominator:=1.
			for row in next_rows:denominator*=row[0]+row[1]+row[2]
			var fraction:float=orientation.value/denominator
			if not is_finite(fraction) or fraction<=0.:safe=false;break
			total+=fraction
			replacements[f]={"ids":ids,"rows":next_rows,"chart":chart,"ancestor":first.ancestor,"area":fraction}
		if not safe or replacements.is_empty() or not is_finite(total) or total<=0.:continue
		var distributed:=0.;var keys:Array=replacements.keys()
		for j in range(keys.size()):
			var next:Dictionary=replacements[keys[j]]
			next.area=old_area-distributed if j==keys.size()-1 else old_area*(next.area/total)
			if not is_finite(next.area) or next.area<=0.:safe=false;break
			distributed+=next.area
		if safe:return {"vertex":v,"target":target,"deleted":deleted,"replacements":replacements,"star":star,"boundary":PackedInt32Array([a,b]),"rows":[rows[a],rows[v],rows[b]],"chart":chart,"ancestor":first.ancestor}
	return {}
static func _pass(s:Dictionary,limit:int)->Dictionary:
	var t:=_topology(s)
	if not t.valid:return t
	var protected_faces:Dictionary={}
	for held in s.grasps.values():protected_faces[held.face]=true
	var blocked:Dictionary={};var selected:Array=[]
	for vertex in t.incident:
		var v:int=vertex;var conflict:=blocked.has(v)
		for other in t.neighbors[v]:conflict=conflict or blocked.has(other)
		if conflict:continue
		var candidate:=_candidate(s,t,v,protected_faces)
		if candidate.is_empty():continue
		selected.append(candidate);blocked[v]=true
		for other in t.neighbors[v]:blocked[other]=true
		if selected.size()>=limit:break
	if selected.is_empty():return {"valid":true,"changed":false}
	var deleted:Dictionary={};var replacements:Dictionary={};var removed:Dictionary={}
	for candidate in selected:
		deleted[candidate.deleted]=true;removed[candidate.vertex]=true
		replacements.merge(candidate.replacements)
	var keep:=PackedInt32Array();var remap:=PackedInt32Array();remap.resize(s.rest.size());remap.fill(-1)
	for v in range(s.rest.size()):
		if not removed.has(v):remap[v]=keep.size();keep.append(v)
	var next:Dictionary=s.duplicate(true);var support:Dictionary=next.support
	for key in ["rest","fallback","anchored","removed","outside"]:
		next[key].clear()
		for v in keep:next[key].append(s[key][v])
	for key in ["point_nodes","point_weights"]:
		support[key]=[]
		for v in keep:support[key].append(s.support[key][v].duplicate())
	next.indices=PackedInt32Array();next.ancestors=PackedInt32Array();next.areas=PackedFloat64Array()
	support.elements=PackedInt32Array();support.weights=PackedFloat64Array()
	var face_map:Dictionary={}
	for f in range(t.faces.size()):
		if deleted.has(f):continue
		face_map[f]=next.ancestors.size()
		var face:Dictionary=replacements.get(f,t.faces[f])
		next.ancestors.append(face.ancestor);next.areas.append(face.area)
		for j in range(3):
			next.indices.append(remap[face.ids[j]]);support.elements.append(face.chart[j]);support.weights.append_array(face.rows[j])
	for held in next.grasps.values():
		if not face_map.has(held.face):return invalid("held_remap")
		if held.has("vertex"):
			if remap[held.vertex]<0:return invalid("held_remap")
			held.vertex=remap[held.vertex]
		held.face=face_map[held.face]
	return {"valid":true,"changed":true,"state":next,"keep":keep,"certificates":selected}
static func simplify(state:Dictionary,max_removals:int=128,fine_point_limit:int=4096)->Dictionary:
	if max_removals<1 or max_removals>256 or not GeometryLimits.supported(fine_point_limit):return invalid("budget")
	if not state.has_all(["rest","fallback","anchored","removed","outside","indices","ancestors","areas","support","grasps"]):return invalid("shape")
	if not state.support is Dictionary or not state.support.has_all(["elements","weights","point_nodes","point_weights","controls"]):return invalid("support_shape")
	var faces:int=state.indices.size()/3;var points:int=state.rest.size()
	if points<3 or points>fine_point_limit or faces<1 or faces>8192 or state.indices.size()%3!=0 or state.ancestors.size()!=faces or state.areas.size()!=faces:return invalid("shape")
	for key in ["fallback","anchored","removed","outside"]:
		if state[key].size()!=points:return invalid("shape")
	if state.support.elements.size()!=faces*3 or state.support.weights.size()!=faces*9 or state.support.point_nodes.size()!=points or state.support.point_weights.size()!=points:return invalid("support_shape")
	for value in state.areas:
		if not is_finite(value) or value<=0.:return invalid("area")
	var current:Dictionary=state;var sources:=PackedInt32Array();var certificates:Array=[]
	for j in range(points):sources.append(j)
	for attempt in range(8):
		var pass_result:=_pass(current,max_removals-certificates.size())
		if not pass_result.valid:return pass_result
		if not pass_result.changed:break
		for proof in pass_result.certificates:
			certificates.append({"vertex":sources[proof.vertex],"target":sources[proof.target],"boundary":PackedInt32Array([sources[proof.boundary[0]],sources[proof.boundary[1]]]),"rows":proof.rows,"chart":proof.chart,"ancestor":proof.ancestor})
		var kept:=PackedInt32Array()
		for j in pass_result.keep:kept.append(sources[j])
		sources=kept;current=pass_result.state
		if certificates.size()>=max_removals:break
	return {"valid":true,"changed":not certificates.is_empty(),"state":current,"point_sources":sources,"removed_vertices":certificates.size(),"certificates":certificates}
