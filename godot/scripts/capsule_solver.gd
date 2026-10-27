extends RefCounted
## Uncalibrated dimensionless membrane experiment; numerical behavior is not clinical validation.
## Edge-length XPBD constraints transmit local tool traction to an anchored circular rim.
const RINGS := 6
const SECTORS := 36
const RADIUS := .88
const MAX_DT := .1
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
	_rebuild_triangles()
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
	triangles = PackedInt32Array()
	for i in range(_faces.size()):
		var intact := true
		for edge_id in _face_edges[i]:
			if _edge_active[edge_id] == 0: intact = false
		if intact:
			for vertex_id in _faces[i]: triangles.append(vertex_id)
	_dirty = false

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
	for tool in tools:
		if not tool.get("hand") is int or tool.hand < 0 or tool.hand > 15 or present.has(tool.hand): return
		if not tool.get("tip") is Vector3 or not tool.tip.is_finite(): return
		if not (tool.get("radius") is float or tool.get("radius") is int) or not is_finite(tool.radius) or tool.radius <= 0 or tool.radius > .3: return
		var contact_radius=tool.get("contact_radius",tool.radius)
		if not (contact_radius is float or contact_radius is int) or not is_finite(contact_radius) or contact_radius<=0. or contact_radius>.3: return
		if not tool.get("grip") is bool or not tool.get("cut") is bool: return
		present[tool.hand] = true
	for hand_id in _grasps.keys():
		if not present.has(hand_id): _grasps.erase(hand_id)
	for tool in tools:
		if not tool.grip: _grasps.erase(tool.hand)
	for tool in tools:
		if not tool.grip or _grasps.has(tool.hand): continue
		var nearest: float = tool.radius
		var vertex := -1
		for i in range(positions.size()):
			if anchored[i] != 0 or i in _grasps.values() or not _connected(i): continue
			var distance: float = positions[i].distance_to(tool.tip)
			if distance <= nearest: nearest = distance; vertex = i
		if vertex >= 0: _grasps[tool.hand] = vertex
	_pinned = anchored.duplicate()
	for vertex in _grasps.values(): _pinned[vertex] = 1
	for i in range(positions.size()):
		_inverse_mass[i] = 0.0 if _pinned[i] != 0 else 1.0 / (surface_density * _rest_area[i])
	_integration_steps += 1
	var damping_factor := clampf(damping, 0, 1)
	for substep in range(substeps):
		var acceleration := _pressure_acceleration()
		for i in range(positions.size()):
			if anchored[i] != 0: continue
			var old := positions[i]
			positions[i] += (positions[i] - _previous[i]) * damping_factor + acceleration[i] * h * h
			_previous[i] = old
		for tool in tools:
			if _grasps.has(tool.hand):
				var vertex: int = _grasps[tool.hand]
				positions[vertex] = positions[vertex].move_toward(tool.tip, .08)
			_project_contact(tool.tip, tool.get("contact_radius",tool.radius))
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
		for i in range(positions.size()):
			if anchored[i] != 0:
				positions[i] = rest_positions[i]; _previous[i] = positions[i]
			elif _pinned[i] != 0:
				_previous[i] = positions[i]
		if _dirty: _rebuild_triangles()

func _project_contact(tip: Vector3, radius: float) -> void:
	for i in range(positions.size()):
		if _pinned[i] != 0: continue
		var offset := positions[i] - tip
		if offset.length() < radius:
			positions[i] = tip + (offset.normalized() if offset.length() > .000001 else Vector3.UP) * radius

func _pressure_acceleration() -> PackedVector3Array:
	var forces := PackedVector3Array()
	forces.resize(positions.size())
	if pressure_load == 0.0: return forces
	# Oriented area vector gives pressure force along each intact face's current normal.
	for offset in range(0, triangles.size(), 3):
		var a := triangles[offset]
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
	for edge_id in _incident[vertex_id]:
		if _edge_active[edge_id] != 0: return true
	return false

static func _segment_distance(point: Vector3, a: Vector3, b: Vector3) -> float:
	var segment := b - a
	if segment.length_squared() < .000000001: return point.distance_to(a)
	return point.distance_to(a + segment * clampf((point - a).dot(segment) / segment.length_squared(), 0, 1))

func metrics() -> Dictionary:
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
	return {"max_strain": _peak_strain, "broken_edges": broken, "grasped": _grasps.get(0, -1), "grasps": _grasps.duplicate(), "integration_steps": _integration_steps, "finite": finite and is_finite(energy), "strain_energy": energy, "vertices": positions.size(), "triangles": triangles.size() / 3}

func visual_state()->Dictionary:
	var mirror_lambda:=PackedFloat64Array(); mirror_lambda.resize(edges.size())
	for i in range(edges.size()): mirror_lambda[i]=edges[i]["lambda"]
	return {"positions":positions.duplicate(),"triangles":triangles.duplicate(),"edge_a":_edge_a.duplicate(),"edge_b":_edge_b.duplicate(),"edge_rest":_edge_rest.duplicate(),"edge_active":_edge_active.duplicate(),"edge_lambda":mirror_lambda}
