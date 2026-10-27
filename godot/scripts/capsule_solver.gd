extends RefCounted
## Uncalibrated dimensionless membrane experiment; numerical behavior is not clinical validation.
## Edge-length XPBD constraints transmit local tool traction to an anchored circular rim.
const RINGS := 6
const SECTORS := 36
const RADIUS := .88
const MAX_DT := .1
const FaceContact=preload("res://scripts/membrane_contact.gd")
const ToolPath=preload("res://scripts/instrument_path.gd")
var _face_contact=FaceContact.new()
var body_contact_count:=0
var body_contact_residual:=0.
var body_contact_uncertain:=0
var tissue_boundary:RefCounted
var _removed:=PackedByteArray()
var _outside:=PackedByteArray()
var _vertex_component:=PackedInt32Array()
var _components:Array[Dictionary]=[]
var _component_dirty:=true
var _extracted_flaps:=0
var _extracted_area:=0.
var _initial_area:=0.
var _retained_area:=0.
var geometry:RefCounted
var positions := PackedVector3Array()
var rest_positions := PackedVector3Array()
var triangles := PackedInt32Array()
var anchored := PackedByteArray()
## Read-only topology mirror for renderers; packed arrays own the numerical constraints.
var edges: Array[Dictionary] = []
var stretch_compliance := .000005
var damping := .98
var tear_strain := .65
var solver_iterations := 6
## Pressure difference and areal mass density are dimensionless and uncalibrated.
var pressure_load := 0.0
var surface_density := 1.0
var passive_tips := PackedVector3Array()
var _previous := PackedVector3Array()
var _rest_area := PackedFloat64Array()
var _faces: Array = []
var _face_edges: Array = []
var _edge_map: Dictionary = {}
var _incident: Array = []
var _grasps: Dictionary = {}
var _pinned := PackedByteArray()
var _edge_a := PackedInt32Array()
var _edge_b := PackedInt32Array()
var _edge_rest := PackedFloat64Array()
var _edge_active := PackedByteArray()
var _lambdas := PackedFloat64Array()
var _inverse_mass := PackedFloat64Array()
var _integration_steps := 0
var _peak_strain := 0.0
var _dirty := false

func _init() -> void:
	reset()

func reset() -> void:
	body_contact_count=0; body_contact_residual=0.; body_contact_uncertain=0
	tissue_boundary=null; _extracted_flaps=0; _extracted_area=0.; _components=[]; _component_dirty=true
	positions = PackedVector3Array([Vector3(0, .82, 0)])
	anchored = PackedByteArray([0])
	edges = []; _faces = []; _face_edges = []; _edge_map = {}
	_grasps = {}; _integration_steps = 0; _peak_strain = 0.0; _dirty = false
	_edge_a = PackedInt32Array(); _edge_b = PackedInt32Array(); _edge_rest = PackedFloat64Array(); _edge_active = PackedByteArray(); _lambdas = PackedFloat64Array()
	pressure_load = 0.0
	passive_tips = PackedVector3Array()
	for ring in range(1, RINGS + 1):
		var radius := RADIUS * ring / RINGS
		for sector in range(SECTORS):
			var angle := TAU * sector / SECTORS
			positions.append(Vector3(cos(angle) * radius, .8 + .02 * (1.0 - pow(radius / RADIUS, 2)), sin(angle) * radius))
			anchored.append(1 if ring == RINGS else 0)
	if geometry:
		for i in range(positions.size()):
			var ring:int=int((i-1)/SECTORS)+1 if i>0 else 0
			var theta:=PI*.5*ring/RINGS
			var r:float=geometry.bag_radius*sin(theta)
			var angle:float=TAU*((i-1)%SECTORS)/SECTORS if i>0 else 0.
			positions[i]=Vector3(cos(angle)*r,0. if anchored[i]!=0 else geometry.bag_half_thickness*cos(theta),sin(angle)*r)
	_removed.resize(positions.size()); _removed.fill(0); _outside.resize(positions.size()); _outside.fill(0)
	rest_positions = positions.duplicate()
	_previous = positions.duplicate()
	_incident = []
	for i in range(positions.size()): _incident.append([])
	for sector in range(SECTORS):
		_add_face(0, _vertex(1, sector + 1), _vertex(1, sector))
	for ring in range(1, RINGS):
		for sector in range(SECTORS):
			var a := _vertex(ring, sector)
			var b := _vertex(ring, sector + 1)
			var c := _vertex(ring + 1, sector)
			var d := _vertex(ring + 1, sector + 1)
			_add_face(a, b, c)
			_add_face(b, d, c)
	_rebuild_triangles(); _initial_area=_retained_area
	_rest_area = PackedFloat64Array()
	_rest_area.resize(positions.size())
	for face in _faces:
		var area := (rest_positions[face[1]] - rest_positions[face[0]]).cross(rest_positions[face[2]] - rest_positions[face[0]]).length() * .5
		for vertex_id in face: _rest_area[vertex_id] += area / 3.0
	_inverse_mass.resize(positions.size())
	_pinned = anchored.duplicate()

func _vertex(ring: int, sector: int) -> int:
	return 1 + (ring - 1) * SECTORS + posmod(sector, SECTORS)

func _add_face(a: int, b: int, c: int) -> void:
	_faces.append([a, b, c])
	_face_edges.append([_edge(a, b), _edge(b, c), _edge(c, a)])

func _edge(a: int, b: int) -> int:
	var key := Vector2i(mini(a, b), maxi(a, b))
	if _edge_map.has(key): return _edge_map[key]
	var index := edges.size()
	_edge_map[key] = index
	edges.append({"a": a, "b": b, "rest": positions[a].distance_to(positions[b]), "active": true, "lambda": .0})
	_edge_a.append(a); _edge_b.append(b); _edge_rest.append(edges[index].rest); _edge_active.append(1); _lambdas.append(0.0)
	_incident[a].append(index)
	_incident[b].append(index)
	return index

func _rebuild_triangles() -> void:
	triangles.clear(); _retained_area=0.
	var support:=PackedInt32Array(); support.resize(_edge_a.size()); support.fill(0)
	for i in range(_faces.size()):
		var intact:=true
		for v in _faces[i]:
			if _removed[v]!=0: intact=false
		for edge_id in _face_edges[i]:
			if _edge_active[edge_id]==0: intact=false
		if not intact: continue
		for vertex_id in _faces[i]: triangles.append(vertex_id)
		for edge_id in _face_edges[i]: support[edge_id]+=1
		var face:Array=_faces[i]
		_retained_area+=(rest_positions[face[1]]-rest_positions[face[0]]).cross(rest_positions[face[2]]-rest_positions[face[0]]).length()*.5
	if geometry:
		# An edge without any surviving membrane face cannot remain an invisible tether.
		for edge_id in range(_edge_a.size()):
			if support[edge_id]==0: _edge_active[edge_id]=0; edges[edge_id].active=false
		for hand in _grasps.keys():
			if not _connected(_grasps[hand]): _grasps.erase(hand)
		_pinned=anchored.duplicate()
		for vertex in _grasps.values(): _pinned[vertex]=1
	_dirty=false; _component_dirty=true

func release() -> void:
	_grasps.clear()
	_pinned = anchored.duplicate()

func release_hand(hand: int) -> void:
	_grasps.erase(hand)
	_pinned = anchored.duplicate()
	for vertex in _grasps.values(): _pinned[vertex] = 1

func step(dt: float, tool_tip: Vector3, tool_radius: float, grip: bool, cut: bool) -> void:
	if passive_tips.size() > 8: return
	var tools: Array[Dictionary] = [{"hand": 0, "tip": tool_tip, "radius": tool_radius, "grip": grip, "cut": cut}]
	var hand := 1
	for tip in passive_tips:
		tools.append({"hand": hand, "tip": tip, "radius": tool_radius, "grip": false, "cut": false})
		hand += 1
	step_tools(dt, tools)

func step_tools(dt: float, tools: Array[Dictionary]) -> void:
	# Validate the whole batch first: malformed second-hand input cannot partly advance time.
	if not is_finite(dt) or dt < .000001 or dt > MAX_DT or tools.size() > 16: return
	if not is_finite(stretch_compliance) or stretch_compliance < 0 or not is_finite(damping) or not is_finite(tear_strain) or tear_strain <= 0: return
	if not is_finite(pressure_load) or absf(pressure_load) > 5.0 or not is_finite(surface_density) or surface_density < .01 or surface_density > 100.0: return
	var substeps := clampi(ceili(dt / (1.0 / 120.0)), 1, 12)
	var h := dt / substeps
	var alpha := stretch_compliance / (h * h)
	if not is_finite(alpha): return
	var present: Dictionary = {}
	var body_size:=0
	for tool in tools:
		if not tool.get("hand") is int or tool.hand < 0 or tool.hand > 15 or present.has(tool.hand): return
		if not tool.get("tip") is Vector3 or not tool.tip.is_finite(): return
		if not (tool.get("radius") is float or tool.get("radius") is int) or not is_finite(tool.radius) or tool.radius <= 0 or tool.radius > .3: return
		var contact_radius=tool.get("contact_radius",tool.radius)
		if not (contact_radius is float or contact_radius is int) or not is_finite(contact_radius) or contact_radius<=0. or contact_radius>.3: return
		if not tool.get("grip") is bool or not tool.get("cut") is bool: return
		if tool.has("body") and (not tool.body is Array or not _face_contact.valid_body(tool.body)): return
		for part in tool.get("body",[]):
			if part.has("attachment"): return # Only the solver can bind its own grasp.
		body_size+=tool.get("body",[]).size()
		if body_size>64: return
		present[tool.hand] = true
		if tool.has("body"): substeps=maxi(substeps,ToolPath.steps(tool.body))
	h=dt/substeps; alpha=stretch_compliance/(h*h)
	if not is_finite(h) or h<=0. or not is_finite(alpha): return
	for tool in tools:
		for part in tool.get("body",[]):
			for substep in range(substeps):
				if not _face_contact.valid_body([ToolPath.interval(part,float(substep)/substeps,float(substep+1)/substeps)]): return
	for hand_id in _grasps.keys():
		if not present.has(hand_id): _grasps.erase(hand_id)
	for tool in tools:
		if not tool.grip: _grasps.erase(tool.hand)
	_refresh_components()
	for tool in tools:
		if not tool.grip or _grasps.has(tool.hand): continue
		var nearest: float = tool.radius
		var vertex := -1
		for i in range(positions.size()):
			if _removed[i]!=0 or anchored[i] != 0 or i in _grasps.values() or not _connected(i): continue
			var distance: float = positions[i].distance_to(tool.tip)
			if distance <= nearest: nearest = distance; vertex = i
		if vertex >= 0: _grasps[tool.hand] = vertex
	_pinned = anchored.duplicate()
	for vertex in _grasps.values(): _pinned[vertex] = 1
	for i in range(positions.size()):
		_inverse_mass[i] = 0.0 if _pinned[i] != 0 or _removed[i]!=0 else 1.0 / (surface_density * _rest_area[i])
	_integration_steps += 1
	body_contact_count=0; body_contact_residual=0.; body_contact_uncertain=0
	var damping_factor := clampf(damping, 0, 1)
	for substep in range(substeps):
		var body:Array=[]
		for tool in tools:
			for segment in tool.get("body",[]):
				var part:Dictionary=ToolPath.interval(segment,float(substep)/substeps,float(substep+1)/substeps)
				if part.get("part","")=="jaw" and _grasps.has(tool.hand): part["attachment"]=_grasps[tool.hand]
				body.append(part)
		var body_previous:=positions.duplicate() if not body.is_empty() else PackedVector3Array()
		var contact_previous:=positions.duplicate() if tissue_boundary else PackedVector3Array()
		var acceleration := _pressure_acceleration()
		for i in range(positions.size()):
			if anchored[i] != 0 or _removed[i]!=0: continue
			var old := positions[i]
			positions[i] += (positions[i] - _previous[i]) * damping_factor + acceleration[i] * h * h
			_previous[i] = old
		for tool in tools:
			if _grasps.has(tool.hand):
				var vertex: int = _grasps[tool.hand]
				positions[vertex] = positions[vertex].move_toward(tool.tip, .08)
			if tool.get("body",[]).is_empty(): _project_contact(tool.tip, tool.get("contact_radius",tool.radius))
		for edge_id in range(_edge_a.size()):
			_lambdas[edge_id] = 0.0
			if _edge_active[edge_id] == 0: continue
			var a := _edge_a[edge_id]
			var b := _edge_b[edge_id]
			var strain := positions[a].distance_to(positions[b]) / _edge_rest[edge_id] - 1.0
			_peak_strain = maxf(_peak_strain, strain)
			var broken := strain > tear_strain
			if not broken:
				for tool in tools:
					if tool.cut and _segment_distance(tool.tip, positions[a], positions[b]) < tool.radius:
						broken = true; break
			if broken:
				_edge_active[edge_id] = 0; edges[edge_id].active = false; _dirty = true
		if not body.is_empty() and _dirty: _rebuild_triangles()
		for iteration in range(clampi(solver_iterations, 1, 16)):
			for edge_id in range(_edge_a.size()):
				if _edge_active[edge_id] == 0: continue
				var a := _edge_a[edge_id]
				var b := _edge_b[edge_id]
				var wa := _inverse_mass[a]
				var wb := _inverse_mass[b]
				if wa + wb == 0: continue
				var offset := positions[a] - positions[b]
				var length := offset.length()
				if length < .0000001: continue
				var delta := (-(length - _edge_rest[edge_id]) - alpha * _lambdas[edge_id]) / (wa + wb + alpha)
				_lambdas[edge_id] += delta
				var correction := offset / length * delta
				positions[a] += correction * wa
				positions[b] -= correction * wb
			if not body.is_empty():
				var projected:Dictionary=_face_contact.project(positions,triangles,_inverse_mass,body,body_previous)
				if projected.valid:
					positions=projected.positions
					body_contact_count+=projected.contacts
					body_contact_residual=maxf(body_contact_residual,projected.residual)
					body_contact_uncertain+=projected.uncertain
				else:
					body_contact_uncertain+=1
		for i in range(positions.size()):
			if anchored[i] != 0:
				positions[i] = rest_positions[i]; _previous[i] = positions[i]
			elif _pinned[i] != 0:
				_previous[i] = positions[i]
		if _dirty: _rebuild_triangles()
		if tissue_boundary and geometry: _boundary_step(contact_previous)

func _project_contact(tip: Vector3, radius: float) -> void:
	for i in range(positions.size()):
		if _pinned[i] != 0 or _removed[i]!=0: continue
		var offset := positions[i] - tip
		if offset.length() < radius:
			positions[i] = tip + (offset.normalized() if offset.length() > .000001 else Vector3.UP) * radius

func _pressure_acceleration() -> PackedVector3Array:
	var forces := PackedVector3Array()
	forces.resize(positions.size())
	if pressure_load == 0.0: return forces
	if geometry: _refresh_components()
	# Oriented area vector gives pressure force along each intact face's current normal.
	for offset in range(0, triangles.size(), 3):
		var a := triangles[offset]
		# A free flap is wetted on both sides by the same compartment.
		if geometry and not _components[_vertex_component[a]].anchored: continue
		var b := triangles[offset + 1]
		var c := triangles[offset + 2]
		var force := (positions[b] - positions[a]).cross(positions[c] - positions[a]) * (.5 * pressure_load / 3.0)
		forces[a] += force; forces[b] += force; forces[c] += force
	for i in range(positions.size()):
		if _pinned[i] != 0:
			forces[i] = Vector3.ZERO
		elif _rest_area[i] > .000000001:
			forces[i] /= surface_density * _rest_area[i]
	return forces

func _connected(vertex_id: int) -> bool:
	if _removed[vertex_id]!=0: return false
	for edge_id in _incident[vertex_id]:
		if _edge_active[edge_id] != 0: return true
	return false

static func _segment_distance(point: Vector3, a: Vector3, b: Vector3) -> float:
	var segment := b - a
	if segment.length_squared() < .000000001: return point.distance_to(a)
	return point.distance_to(a + segment * clampf((point - a).dot(segment) / segment.length_squared(), 0, 1))

func metrics() -> Dictionary:
	_refresh_components()
	var detached_area:=0.; var detached_count:=0
	for component in _components:
		if not component.anchored and component.area>1e-12: detached_area+=component.area; detached_count+=1
	var finite := true
	for point in positions:
		if not point.is_finite(): finite = false
	var broken := 0
	var energy := .0
	for edge_id in range(_edge_a.size()):
		if _edge_active[edge_id] == 0: broken += 1
		else:
			var extension := positions[_edge_a[edge_id]].distance_to(positions[_edge_b[edge_id]]) - _edge_rest[edge_id]
			energy += .5 * extension * extension
	return {"body_contacts":body_contact_count,"body_projection_peak_residual":body_contact_residual,"body_uncertain":body_contact_uncertain,"initial_area":_initial_area,"retained_area":_retained_area,"cut_loss_area":maxf(0.,_initial_area-_retained_area-_extracted_area),"retained_detached_area":detached_area,"detached_flaps":detached_count,"extracted_flaps":_extracted_flaps,"extracted_area":_extracted_area,"max_strain": _peak_strain, "broken_edges": broken, "grasped": _grasps.get(0, -1), "grasps": _grasps.duplicate(), "integration_steps": _integration_steps, "finite": finite and is_finite(energy), "strain_energy": energy, "vertices": positions.size(), "triangles": triangles.size() / 3}

func visual_state()->Dictionary:
	var mirror_lambda:=PackedFloat64Array(); mirror_lambda.resize(edges.size())
	for i in range(edges.size()): mirror_lambda[i]=edges[i]["lambda"]
	return {"positions":positions.duplicate(),"triangles":triangles.duplicate(),"edge_a":_edge_a.duplicate(),"edge_b":_edge_b.duplicate(),"edge_rest":_edge_rest.duplicate(),"edge_active":_edge_active.duplicate(),"edge_lambda":mirror_lambda}

func _refresh_components()->void:
	if not _component_dirty: return
	_component_dirty=false; _components=[]
	_vertex_component.resize(positions.size()); _vertex_component.fill(-1)
	var neighbors:Array=[]
	for i in range(positions.size()): neighbors.append(PackedInt32Array())
	for edge_id in range(_edge_a.size()):
		if _edge_active[edge_id]==0: continue
		var a:=_edge_a[edge_id]; var b:=_edge_b[edge_id]
		neighbors[a].append(b); neighbors[b].append(a)
	for seed in range(positions.size()):
		if _removed[seed]!=0 or _vertex_component[seed]>=0: continue
		var id:=_components.size(); var stack:=PackedInt32Array([seed]); var vertices:=PackedInt32Array(); var attached:=false
		_vertex_component[seed]=id
		while not stack.is_empty():
			var v:=stack[stack.size()-1]; stack.resize(stack.size()-1); vertices.append(v)
			if anchored[v]!=0: attached=true
			for next in neighbors[v]:
				if _vertex_component[next]<0: _vertex_component[next]=id; stack.append(next)
		_components.append({"id":id,"vertices":vertices,"anchored":attached,"area":0.})
	for i in range(0,triangles.size(),3):
		var a:=triangles[i]; var b:=triangles[i+1]; var c:=triangles[i+2]
		var id:=_vertex_component[a]
		_components[id].area+=(rest_positions[b]-rest_positions[a]).cross(rest_positions[c]-rest_positions[a]).length()*.5
func detached_components()->Array[Dictionary]:
	_refresh_components()
	var result:Array[Dictionary]=[]
	for component in _components:
		if not component.anchored and component.area>1e-12: result.append(component.duplicate(true))
	return result
func _boundary_step(before:PackedVector3Array)->void:
	_refresh_components()
	for component in _components:
		if component.anchored or component.area<=1e-12: continue
		for v in component.vertices:
			var result:Dictionary=tissue_boundary.resolve(before[v],positions[v],_outside[v]!=0)
			positions[v]=result.position; _outside[v]=1 if result.outside else 0
			if result.contact or not result.valid: _previous[v]=positions[v]
	var retire:Array[Dictionary]=[]
	for component in _components:
		if component.anchored or component.area<=1e-12: continue
		var held:=false; var exterior:=true
		for v in component.vertices:
			if v in _grasps.values(): held=true
			if _outside[v]==0: exterior=false
		if held and exterior: retire.append(component)
	for component in retire:
		for v in component.vertices: _removed[v]=1
		for hand in _grasps.keys():
			if _removed[_grasps[hand]]!=0: _grasps.erase(hand)
		_extracted_flaps+=1; _extracted_area+=component.area; _dirty=true
	if not retire.is_empty():
		for edge_id in range(_edge_a.size()):
			if _removed[_edge_a[edge_id]]!=0 or _removed[_edge_b[edge_id]]!=0: _edge_active[edge_id]=0; edges[edge_id].active=false
		_rebuild_triangles()
func collision_triangles(hand:int)->PackedInt32Array:
	_refresh_components()
	if not _grasps.has(hand): return triangles
	var id:=_vertex_component[_grasps[hand]]
	if id<0 or _components[id].anchored: return triangles
	var result:=PackedInt32Array()
	for i in range(0,triangles.size(),3):
		if _vertex_component[triangles[i]]!=id: result.append_array(PackedInt32Array([triangles[i],triangles[i+1],triangles[i+2]]))
	return result
