extends RefCounted
## Read-only smooth display of the lens solver's fixed three-layer ring topology.
## Interpolated tangent-plane shading is a visual approximation, not added material.
## Faces are supported by the source particles and their real initial bond links.
const RING_STARTS := [1,7,19]
const RING_COUNTS := [6,12,18]
const SUBDIVISIONS := 3
var detached_positions := PackedVector3Array()
var source_triangles := PackedInt32Array()
var visible_source_triangles := PackedInt32Array()
var _mesh := ArrayMesh.new()
var _faces: Array[Dictionary] = []
var _sources: Array[Vector3i] = []
var _weights: Array[Vector3] = []
var _rest_uv := PackedVector2Array()
var _bond_lookup: Dictionary = {}
var _particle_count := 0
var _bond_count := -1
var _material: ShaderMaterial

func update_from_solver(solver) -> ArrayMesh:
	if solver.particles.size()!=111:
		_mesh.clear_surfaces()
		detached_positions.clear()
		visible_source_triangles.clear()
		return _mesh
	if _particle_count!=solver.particles.size() or _bond_count!=solver.bonds.size():
		_cache_topology(solver)
	var positions := PackedVector3Array()
	var normals := PackedVector3Array()
	var degrees := PackedInt32Array()
	positions.resize(_particle_count)
	normals.resize(_particle_count)
	normals.fill(Vector3.ZERO)
	degrees.resize(_particle_count)
	degrees.fill(0)
	for i in range(_particle_count): positions[i]=solver.particles[i].position
	for bond in solver.bonds:
		if bond.active and solver.particles[bond.a].active and solver.particles[bond.b].active:
			degrees[bond.a]+=1
			degrees[bond.b]+=1
	detached_positions.clear()
	for i in range(_particle_count):
		if solver.particles[i].active and degrees[i]==0: detached_positions.append(positions[i])
	var surviving: Array[Dictionary] = []
	visible_source_triangles.clear()
	for face in _faces:
		var nodes: Vector3i = face.nodes
		if not solver.particles[nodes.x].active or not solver.particles[nodes.y].active or not solver.particles[nodes.z].active: continue
		var connected := true
		for edge in face.bonds:
			if not solver.bonds[edge].active:
				connected=false
				break
		if not connected: continue
		var normal := -(positions[nodes.y]-positions[nodes.x]).cross(positions[nodes.z]-positions[nodes.x])
		if not normal.is_finite() or normal.length_squared()<0.0000000001: continue
		for index in [nodes.x,nodes.y,nodes.z]: normals[index]+=normal
		visible_source_triangles.append_array(PackedInt32Array([nodes.x,nodes.y,nodes.z]))
		surviving.append(face)
	_mesh.clear_surfaces()
	if surviving.is_empty(): return _mesh
	for i in range(_particle_count): normals[i]=normals[i].normalized() if normals[i].length_squared()>0.000000001 else Vector3.UP
	var vertices := positions.duplicate()
	var smooth_normals := normals.duplicate()
	vertices.resize(_sources.size())
	smooth_normals.resize(_sources.size())
	for i in range(_particle_count,_sources.size()):
		var nodes := _sources[i]
		var weight := _weights[i]
		var a := positions[nodes.x]
		var b := positions[nodes.y]
		var c := positions[nodes.z]
		var normal_a := normals[nodes.x]
		var normal_b := normals[nodes.y]
		var normal_c := normals[nodes.z]
		var p := a*weight.x+b*weight.y+c*weight.z
		# Phong tessellation: shared edges interpolate identical endpoint planes.
		var pa := p-normal_a*(p-a).dot(normal_a)
		var pb := p-normal_b*(p-b).dot(normal_b)
		var pc := p-normal_c*(p-c).dot(normal_c)
		vertices[i]=p.lerp(pa*weight.x+pb*weight.y+pc*weight.z,0.65)
		smooth_normals[i]=(normal_a*weight.x+normal_b*weight.y+normal_c*weight.z).normalized()
	var indices := PackedInt32Array()
	for face in surviving: indices.append_array(face.indices)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=smooth_normals
	arrays[Mesh.ARRAY_TEX_UV]=_rest_uv
	arrays[Mesh.ARRAY_INDEX]=indices
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	_mesh.surface_set_material(0,_material)
	return _mesh

func _cache_topology(solver) -> void:
	_particle_count=solver.particles.size()
	_bond_count=solver.bonds.size()
	_faces.clear()
	_sources.clear()
	_weights.clear()
	_rest_uv.clear()
	_bond_lookup.clear()
	source_triangles.clear()
	for i in range(_bond_count):
		var bond: Dictionary=solver.bonds[i]
		_bond_lookup[_key(bond.a,bond.b)]=i
	for i in range(_particle_count):
		_sources.append(Vector3i(i,i,i))
		_weights.append(Vector3(1,0,0))
		var p:Vector3=solver.particles[i].position
		_rest_uv.append(Vector2(p.x,p.z)/1.44+Vector2(.5,.5))
	for layer in [0,2]:
		var offset: int=layer*37
		var normal:=Vector3.UP if layer==2 else Vector3.DOWN
		for k in range(6): _face(offset,offset+1+k,offset+1+(k+1)%6,normal,solver)
		_stitch(offset+1,6,offset+7,12,normal,solver)
		_stitch(offset+7,12,offset+19,18,normal,solver)
	for layer in range(2):
		for k in range(18):
			var a:=layer*37+19+k
			var b:=layer*37+19+(k+1)%18
			var c: int=a+37
			var d: int=b+37
			var normal:Vector3=(solver.particles[a].position-Vector3(0,.68,0))*Vector3(1,0,1)
			_face(a,b,c,normal,solver)
			_face(b,d,c,normal,solver)
	if _material==null:
		_material=ShaderMaterial.new()
		_material.shader=load("res://assets/lens_surface.gdshader")

func _stitch(inner_start:int,inner_count:int,outer_start:int,outer_count:int,normal:Vector3,solver) -> void:
	var i:=0
	var j:=0
	while i<inner_count or j<outer_count:
		var next_inner:=float(i+1)/inner_count if i<inner_count else INF
		var next_outer:=float(j+1)/outer_count if j<outer_count else INF
		if next_inner<next_outer:
			_face(inner_start+i%inner_count,outer_start+j%outer_count,inner_start+(i+1)%inner_count,normal,solver)
			i+=1
		else:
			_face(inner_start+i%inner_count,outer_start+j%outer_count,outer_start+(j+1)%outer_count,normal,solver)
			j+=1

func _key(a:int,b:int) -> int:
	return mini(a,b)*111+maxi(a,b)

func _face(a:int,b:int,c:int,wanted_normal:Vector3,solver) -> void:
	var pa:Vector3=solver.particles[a].position
	var pb:Vector3=solver.particles[b].position
	var pc:Vector3=solver.particles[c].position
	if (pb-pa).cross(pc-pa).dot(wanted_normal)>0:
		var swap:=b
		b=c
		c=swap
	var links:=PackedInt32Array()
	for pair in [Vector2i(a,b),Vector2i(b,c),Vector2i(c,a)]:
		if _bond_lookup.has(_key(pair.x,pair.y)): links.append(_bond_lookup[_key(pair.x,pair.y)])
	# A geometric strip diagonal may not be a direct physical edge. Two actual
	# links still connect the whole triangle; no face bridges disconnected nodes.
	if links.size()<2: return
	var nodes:=Vector3i(a,b,c)
	var lattice:Dictionary={}
	for i in range(SUBDIVISIONS+1):
		for j in range(SUBDIVISIONS+1-i):
			var weight:=Vector3(float(SUBDIVISIONS-i-j),float(i),float(j))/SUBDIVISIONS
			var index:int
			if i==0 and j==0: index=a
			elif i==SUBDIVISIONS: index=b
			elif j==SUBDIVISIONS: index=c
			else:
				index=_sources.size()
				_sources.append(nodes)
				_weights.append(weight)
				_rest_uv.append(_rest_uv[a]*weight.x+_rest_uv[b]*weight.y+_rest_uv[c]*weight.z)
			lattice[Vector2i(i,j)]=index
	var indices:=PackedInt32Array()
	for i in range(SUBDIVISIONS):
		for j in range(SUBDIVISIONS-i):
			indices.append_array(PackedInt32Array([lattice[Vector2i(i,j)],lattice[Vector2i(i+1,j)],lattice[Vector2i(i,j+1)]]))
			if i+j<SUBDIVISIONS-1:
				indices.append_array(PackedInt32Array([lattice[Vector2i(i+1,j)],lattice[Vector2i(i+1,j+1)],lattice[Vector2i(i,j+1)]]))
	_faces.append({"nodes":nodes,"bonds":links,"indices":indices})
	source_triangles.append_array(PackedInt32Array([a,b,c]))
