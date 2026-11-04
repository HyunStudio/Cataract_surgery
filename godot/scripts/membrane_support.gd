extends RefCounted
## Linear original-material bases with one virtual control per connected support
## star. Fine cut geometry is retained. This builds a discretization only; it is
## not an accepted mechanical solve or calibrated biological material model.
const MAX_FACES:=8192
const MAX_POINTS:=4096
const EMBEDDING_DISTANCE:=2e-6
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"reason":reason}
static func _key(a:int,b:int)->Vector2i:
	return Vector2i(mini(a,b),maxi(a,b))
static func _root(parent:Array[int],index:int)->int:
	var current:=index
	while parent[current]!=current:current=parent[current]
	while parent[index]!=index:
		var next:int=parent[index];parent[index]=current;index=next
	return current
static func _join(parent:Array[int],a:int,b:int)->void:
	var first:=_root(parent,a);var last:=_root(parent,b)
	if first!=last:parent[maxi(first,last)]=mini(first,last)
static func _project(p:Vector3,axis:int)->Vector2:
	return Vector2(p.y,p.z) if axis==0 else (Vector2(p.x,p.z) if axis==1 else Vector2(p.x,p.y))
static func _weights(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->PackedFloat64Array:
	var axis:=(b-a).cross(c-a).abs().max_axis_index()
	var pa:=_project(a,axis);var pb:=_project(b,axis);var pc:=_project(c,axis);var point:=_project(p,axis)
	var ux:float=float(pb.x)-pa.x;var uy:float=float(pb.y)-pa.y
	var vx:float=float(pc.x)-pa.x;var vy:float=float(pc.y)-pa.y
	var qx:float=float(point.x)-pa.x;var qy:float=float(point.y)-pa.y
	var determinant:=ux*vy-uy*vx
	if absf(determinant)<1e-12:return PackedFloat64Array()
	var second:float=(qx*vy-qy*vx)/determinant;var third:float=(ux*qy-uy*qx)/determinant
	var result:=PackedFloat64Array([1.-second-third,second,third])
	var sum:=0.
	for i in range(3):
		if not is_finite(result[i]) or result[i]<-1e-6:return PackedFloat64Array()
		result[i]=maxf(0.,result[i]);sum+=result[i]
	for i in range(3):result[i]/=sum
	if (a*result[0]+b*result[1]+c*result[2]).distance_to(p)>EMBEDDING_DISTANCE:return PackedFloat64Array()
	return result

static func _feature_weights(p:Vector3,original:PackedVector3Array,triangle:PackedInt32Array,feature:PackedInt32Array)->PackedFloat64Array:
	if feature.size()==3:return _weights(p,original[triangle[0]],original[triangle[1]],original[triangle[2]])
	var result:=PackedFloat64Array([0.,0.,0.]);var ordered:=feature.duplicate();ordered.sort()
	if ordered.size()==1:result[triangle.find(ordered[0])]=1.
	else:
		var first:Vector3=original[ordered[0]];var last:Vector3=original[ordered[1]]
		var length_sq:=0.;var projection:=0.
		for axis in range(3):
			var delta:float=float(last[axis])-first[axis]
			length_sq+=delta*delta;projection+=(float(p[axis])-first[axis])*delta
		if length_sq<1e-20:return PackedFloat64Array()
		var fraction:float=clampf(projection/length_sq,0.,1.)
		result[triangle.find(ordered[0])]=1.-fraction;result[triangle.find(ordered[1])]=fraction
	var reconstructed:=Vector3.ZERO
	for j in range(3):reconstructed+=original[triangle[j]]*result[j]
	if reconstructed.distance_to(p)>EMBEDDING_DISTANCE:return PackedFloat64Array()
	return result

static func build(original:PackedVector3Array,original_indices:PackedInt32Array,points:PackedVector3Array,indices:PackedInt32Array,ancestors:PackedInt32Array,areas:PackedFloat64Array,density:float)->Dictionary:
	if not is_finite(density) or density<.01 or density>100.:return invalid("density")
	if original.size()<3 or original.size()>MAX_POINTS or points.size()<3 or points.size()>MAX_POINTS:return invalid("point_budget")
	if original_indices.is_empty() or original_indices.size()%3!=0 or original_indices.size()>MAX_FACES*3 or indices.is_empty() or indices.size()%3!=0 or indices.size()>MAX_FACES*3:return invalid("face_budget")
	var faces:int=indices.size()/3;var original_faces:int=original_indices.size()/3
	if ancestors.size()!=faces or areas.size()!=faces:return invalid("face_count")
	for values in [original,points]:
		for p in values:
			if not p.is_finite() or p.length_squared()>256.:return invalid("coordinate")
	for v in original_indices:
		if v<0 or v>=original.size():return invalid("original_index")
	for v in indices:
		if v<0 or v>=points.size():return invalid("fine_index")
	# Original material feature identity, not geometric proximity, determines
	# whether a fine vertex lies in an original face, edge or vertex. Adjacent
	# faces must evaluate its same interpolation even after float32 publication.
	var features:Dictionary={}
	for face in range(faces):
		var ancestor:int=ancestors[face]
		if ancestor<0 or ancestor>=original_faces:return invalid("ancestor")
		var triangle:=PackedInt32Array([original_indices[ancestor*3],original_indices[ancestor*3+1],original_indices[ancestor*3+2]])
		for j in range(3):
			var vertex:int=indices[face*3+j]
			if not features.has(vertex):features[vertex]=triangle
			else:
				var common:=PackedInt32Array()
				for id in features[vertex]:
					if triangle.has(id):common.append(id)
				if common.is_empty():return invalid("ancestor_continuity")
				features[vertex]=common
	var original_areas:=PackedFloat64Array();original_areas.resize(original_faces)
	for face in range(original_faces):
		var a:Vector3=original[original_indices[face*3]];var b:Vector3=original[original_indices[face*3+1]];var c:Vector3=original[original_indices[face*3+2]]
		var area:float=(b-a).cross(c-a).length()*.5
		if not is_finite(area) or area<1e-12:return invalid("original_resolution")
		original_areas[face]=area
	var parent:Array[int]=[];parent.resize(faces*3)
	for i in range(parent.size()):parent[i]=i
	var weights:=PackedFloat64Array();weights.resize(faces*9)
	var covered:=PackedFloat64Array();covered.resize(original_faces)
	var edge_faces:Dictionary={}
	for face in range(faces):
		var ancestor:int=ancestors[face]
		if ancestor<0 or ancestor>=original_faces:return invalid("ancestor")
		if not is_finite(areas[face]) or areas[face]<=0.:return invalid("material_area")
		covered[ancestor]+=areas[face]
		var a:Vector3=original[original_indices[ancestor*3]];var b:Vector3=original[original_indices[ancestor*3+1]];var c:Vector3=original[original_indices[ancestor*3+2]]
		var u:Vector3=points[indices[face*3]];var v:Vector3=points[indices[face*3+1]];var w:Vector3=points[indices[face*3+2]]
		if (v-u).cross(w-u).dot((b-a).cross(c-a))<=0.:return invalid("fine_orientation")
		for corner in range(3):
			var triangle:=PackedInt32Array([original_indices[ancestor*3],original_indices[ancestor*3+1],original_indices[ancestor*3+2]])
			var vertex:int=indices[face*3+corner]
			var shape:=_feature_weights(points[vertex],original,triangle,features[vertex])
			if shape.is_empty():return invalid("embedding")
			for j in range(3):weights[face*9+corner*3+j]=shape[j]
			var first:int=indices[face*3+corner];var last:int=indices[face*3+(corner+1)%3];var edge:=_key(first,last)
			if not edge_faces.has(edge):edge_faces[edge]=[]
			var incident:Array=edge_faces[edge]
			if incident.size()>=2:return invalid("nonmanifold_edge")
			if not incident.is_empty():
				var other:Dictionary=incident[0]
				if other.start==first:return invalid("edge_orientation")
				var other_ancestor:int=ancestors[other.face]
				for j in range(3):
					for k in range(3):
						if original_indices[ancestor*3+j]==original_indices[other_ancestor*3+k]:_join(parent,face*3+j,other.face*3+k)
			incident.append({"face":face,"start":first})
	for face in range(original_faces):
		if covered[face]>original_areas[face]+maxf(1e-9,original_areas[face]*1e-6):return invalid("material_surplus")
	var controls:=PackedInt32Array();var elements:=PackedInt32Array();elements.resize(faces*3)
	var nodes:Dictionary={};var mass:=PackedFloat64Array()
	for face in range(faces):
		for j in range(3):
			var root:=_root(parent,face*3+j)
			if not nodes.has(root):
				nodes[root]=controls.size();controls.append(original_indices[ancestors[face]*3+j]);mass.append(0.)
			var node:int=nodes[root];elements[face*3+j]=node
			var shape_integral:float=(weights[face*9+j]+weights[face*9+3+j]+weights[face*9+6+j])/3.
			mass[node]+=density*areas[face]*shape_integral
	var minimum_mass:=INF
	for value in mass:
		if not is_finite(value) or value<=0.:return invalid("support_mass")
		minimum_mass=minf(minimum_mass,value)
	var point_nodes:Array[PackedInt32Array]=[];var point_weights:Array[PackedFloat64Array]=[]
	for point in points:point_nodes.append(PackedInt32Array());point_weights.append(PackedFloat64Array())
	for face in range(faces):
		for corner in range(3):
			var vertex:int=indices[face*3+corner];var mapping:Dictionary={}
			for j in range(3):
				var value:float=weights[face*9+corner*3+j]
				if value>0.:mapping[elements[face*3+j]]=value
			var ordered:Array=mapping.keys();ordered.sort()
			var nodes_at_point:=PackedInt32Array(ordered);var weights_at_point:=PackedFloat64Array()
			for node in ordered:weights_at_point.append(mapping[node])
			if point_nodes[vertex].is_empty():point_nodes[vertex]=nodes_at_point;point_weights[vertex]=weights_at_point
			else:
				if point_nodes[vertex]!=nodes_at_point:return invalid("support_continuity")
				for j in range(weights_at_point.size()):
					if absf(point_weights[vertex][j]-weights_at_point[j])>1e-12:return invalid("weight_continuity")
	# Integrate each original affine basis over its retained real material.
	# Many small display triangles can share one well-shaped material cell.
	var cell_map:Dictionary={};var cells:Array[Dictionary]=[]
	for face in range(faces):
		var key:=Vector4i(ancestors[face],elements[face*3],elements[face*3+1],elements[face*3+2])
		if not cell_map.has(key):
			cell_map[key]=cells.size();cells.append({"parent":ancestors[face],"nodes":Vector3i(key.y,key.z,key.w),"area":0.})
		cells[cell_map[key]].area+=areas[face]
	return {"valid":true,"reason":"","controls":controls,"elements":elements,"weights":weights,"mass":mass,"minimum_mass":minimum_mass,"cells":cells,"point_nodes":point_nodes,"point_weights":point_weights}
