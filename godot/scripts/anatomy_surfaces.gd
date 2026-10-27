extends RefCounted
## Shared synthetic anatomical geometry for display and continuous tip contact.
## Coordinates are matched to this simulator, not calibrated patient dimensions.
static func cornea()->Dictionary:
	return _disk(1.42,10,64,"cornea")
static func posterior()->Dictionary:
	return _disk(.88,6,36,"posterior")
static func _height(radius:float,outer:float,kind:String)->float:
	if kind=="cornea": return .79+.142*sqrt(maxf(0.,1.-radius*radius/(outer*outer)))
	return .50+.08*radius*radius/(outer*outer)
static func _disk(radius:float,rings:int,sectors:int,kind:String)->Dictionary:
	var points:=PackedVector3Array([Vector3(0,_height(0,radius,kind),0)])
	var ids:=PackedInt32Array()
	for ring in range(1,rings+1):
		var r:=radius*ring/rings
		for sector in range(sectors):
			var a:=TAU*sector/sectors
			points.append(Vector3(cos(a)*r,_height(r,radius,kind),sin(a)*r))
	for i in range(sectors): ids.append_array(PackedInt32Array([0,1+(i+1)%sectors,1+i]))
	for ring in range(rings-1):
		for i in range(sectors):
			var a:=1+ring*sectors+i; var b:=1+ring*sectors+(i+1)%sectors
			var c:=a+sectors; var d:=b+sectors
			ids.append_array(PackedInt32Array([a,b,c,b,d,c]))
	return {"positions":points,"triangles":ids}
static func iris(inner:float)->Dictionary:
	var points:=PackedVector3Array(); var ids:=PackedInt32Array()
	const N:=96
	# Conical iris rises toward the pupil and closes over a finite thickness.
	for ring in [[inner,.8675],[1.4,.8025],[inner,.8425],[1.4,.7775]]:
		for i in range(N):
			var a:=TAU*i/N
			points.append(Vector3(cos(a)*ring[0],ring[1],sin(a)*ring[0]))
	for i in range(N):
		var next:=(i+1)%N
		for pair in [[0,1],[3,2],[2,0],[1,3]]:
			var a:int=pair[0]*N+i; var b:int=pair[0]*N+next
			var c:int=pair[1]*N+i; var d:int=pair[1]*N+next
			ids.append_array(PackedInt32Array([a,b,c,b,d,c]))
	return {"positions":points,"triangles":ids}
static func mesh(data:Dictionary)->ArrayMesh:
	var points:PackedVector3Array=data.positions; var ids:PackedInt32Array=data.triangles
	if ids.is_empty(): return ArrayMesh.new()
	var normals:=PackedVector3Array(); normals.resize(points.size()); normals.fill(Vector3.ZERO)
	var uv:=PackedVector2Array()
	for p in points: uv.append(Vector2(p.x,p.z)/2.84+Vector2(.5,.5))
	for i in range(0,ids.size(),3):
		var a:=ids[i]; var b:=ids[i+1]; var c:=ids[i+2]
		var normal:=(points[b]-points[a]).cross(points[c]-points[a])
		for index in [a,b,c]: normals[index]+=normal
	for i in range(normals.size()): normals[i]=normals[i].normalized() if normals[i].length_squared()>.000000001 else Vector3.UP
	var arrays:=[]; arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=points; arrays[Mesh.ARRAY_NORMAL]=normals; arrays[Mesh.ARRAY_TEX_UV]=uv; arrays[Mesh.ARRAY_INDEX]=ids
	var result:=ArrayMesh.new(); result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays); return result
