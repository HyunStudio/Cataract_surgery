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
var _grasped := -1
var _peak_strain := 0.0
var _dirty := false

func _init() -> void:
	reset()

func reset() -> void:
	positions = PackedVector3Array([Vector3(0, .82, 0)])
	anchored = PackedByteArray([0])
	edges = []; _faces = []; _face_edges = []; _edge_map = {}
	_grasped = -1; _peak_strain = 0.0; _dirty = false
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
	_incident[a].append(index)
	_incident[b].append(index)
	return index

func _rebuild_triangles() -> void:
	triangles = PackedInt32Array()
	for i in range(_faces.size()):
		var intact := true
		for edge_id in _face_edges[i]:
			if not edges[edge_id].active: intact = false
		if intact:
			for vertex_id in _faces[i]: triangles.append(vertex_id)
	_dirty = false

func release() -> void:
	_grasped = -1

func step(dt: float, tool_tip: Vector3, tool_radius: float, grip: bool, cut: bool) -> void:
	# Reject long stalls instead of injecting accumulated mechanical energy.
	if not is_finite(dt) or dt < .000001 or dt > MAX_DT or not tool_tip.is_finite() or not is_finite(tool_radius) or tool_radius <= 0 or tool_radius > .3:
		return
	if not is_finite(stretch_compliance) or stretch_compliance < 0 or not is_finite(damping) or not is_finite(tear_strain) or tear_strain <= 0:
		return
	if not is_finite(pressure_load) or absf(pressure_load) > 5.0 or not is_finite(surface_density) or surface_density < .01 or surface_density > 100.0:
		return
	if passive_tips.size() > 8: return
	for tip in passive_tips:
		if not tip.is_finite(): return
	if not grip: release()
	if grip and _grasped < 0:
		var nearest := tool_radius
		for i in range(positions.size()):
			if anchored[i] != 0 or not _connected(i): continue
			var distance := positions[i].distance_to(tool_tip)
			if distance <= nearest:
				nearest = distance; _grasped = i
	var substeps := clampi(ceili(dt / (1.0 / 120.0)), 1, 12)
	var h := dt / substeps
	var alpha := stretch_compliance / (h * h)
	for substep in range(substeps):
		var acceleration := _pressure_acceleration()
		for i in range(positions.size()):
			if anchored[i] != 0: continue
			var old := positions[i]
			positions[i] += (positions[i] - _previous[i]) * clampf(damping, 0, 1) + acceleration[i] * h * h
			_previous[i] = old
		if _grasped >= 0:
			positions[_grasped] = positions[_grasped].move_toward(tool_tip, .08)
		_project_contact(tool_tip, tool_radius)
		for tip in passive_tips: _project_contact(tip, tool_radius)
		for edge in edges:
			edge["lambda"] = .0
			if not edge.active: continue
			var strain: float = positions[edge.a].distance_to(positions[edge.b]) / edge.rest - 1.0
			_peak_strain = maxf(_peak_strain, strain)
			if strain > tear_strain or (cut and _segment_distance(tool_tip, positions[edge.a], positions[edge.b]) < tool_radius):
				edge.active = false; _dirty = true
		for iteration in range(clampi(solver_iterations, 1, 16)):
			for edge in edges:
				if not edge.active: continue
				var a: int = edge.a
				var b: int = edge.b
				var wa := 0.0 if anchored[a] != 0 or a == _grasped else 1.0 / (surface_density * _rest_area[a])
				var wb := 0.0 if anchored[b] != 0 or b == _grasped else 1.0 / (surface_density * _rest_area[b])
				if wa + wb == 0: continue
				var offset := positions[a] - positions[b]
				var length := offset.length()
				if length < .0000001: continue
				var delta: float = (-(length - edge.rest) - alpha * edge["lambda"]) / (wa + wb + alpha)
				edge["lambda"] += delta
				var correction := offset / length * delta
				positions[a] += correction * wa
				positions[b] -= correction * wb
		for i in range(positions.size()):
			if anchored[i] != 0:
				positions[i] = rest_positions[i]; _previous[i] = positions[i]
			elif i == _grasped:
				_previous[i] = positions[i]
		if _dirty: _rebuild_triangles()

func _project_contact(tip: Vector3, radius: float) -> void:
	for i in range(positions.size()):
		if anchored[i] != 0 or i == _grasped: continue
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
		if anchored[i] != 0 or i == _grasped:
			forces[i] = Vector3.ZERO
		elif _rest_area[i] > .000000001:
			forces[i] /= surface_density * _rest_area[i]
	return forces

func _connected(vertex_id: int) -> bool:
	for edge_id in _incident[vertex_id]:
		if edges[edge_id].active: return true
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
	for edge in edges:
		if not edge.active: broken += 1
		else:
			var extension: float = positions[edge.a].distance_to(positions[edge.b]) - edge.rest
			energy += .5 * extension * extension
	return {"max_strain": _peak_strain, "broken_edges": broken, "grasped": _grasped, "finite": finite and is_finite(energy), "strain_energy": energy, "vertices": positions.size(), "triangles": triangles.size() / 3}
