extends RefCounted
## Uncalibrated dimensionless membrane experiment; numerical behavior is not clinical validation.
## Edge-length XPBD constraints transmit local tool traction to an anchored circular rim.
const RINGS := 6
const SECTORS := 36
const RADIUS := .88
const MAX_DT := .1
const NATIVE_COUPLING_BUDGET:=32
## Scene-unit numerical tolerance above float32 publication noise, not tear strength.
const NATIVE_COUPLING_TOLERANCE:=1e-6
const FaceContact=preload("res://scripts/membrane_contact.gd")
const ToolPath=preload("res://scripts/instrument_path.gd")
const Cutter=preload("res://scripts/membrane_cut.gd")
const Refinement=preload("res://scripts/membrane_refinement.gd")
const Precision=preload("res://scripts/membrane_precision.gd")
var _cutter=Cutter.new()
var _incision_events:=0
var _retired_breaks:=0
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
var _face_rest_area:=PackedFloat64Array()
var _triangle_faces:=PackedInt32Array()
var _triangle_area:=PackedFloat64Array()
var _face_edges: Array = []
var _edge_map: Dictionary = {}
var _incident: Array = []
var _grasps: Dictionary = {}
var _grasp_faces:Dictionary={}
var _grasp_offsets:Dictionary={}
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
var stretch_backend:RefCounted
var contact_backend:RefCounted
var _physical_xyz:=PackedFloat64Array()
var _physical_previous:=PackedFloat64Array()
var _physical_rest:=PackedFloat64Array()
var joint_stats:=PackedFloat64Array()
var _joint_tip_history:Dictionary={}
var native_failure:Dictionary={}
var _backend_failed:=false

func set_stretch_backend(backend:RefCounted)->bool:
	if backend and contact_backend: return false
	if backend and (not backend.has_method("project") or (backend.has_method("ready") and not backend.ready())): return false
	stretch_backend=backend; native_failure={}; return true

func set_contact_backend(backend:RefCounted)->bool:
	if backend and (stretch_backend or not backend.has_method("solve_contact")): return false
	if backend and not contact_backend:
		_physical_xyz=Precision.pack(positions); _physical_previous=Precision.pack(_previous); _physical_rest=Precision.pack(rest_positions)
	contact_backend=backend; native_failure={}; return true

func _checkpoint()->Dictionary:
	var saved:={}
	for property in get_property_list():
		if (int(property.usage)&PROPERTY_USAGE_SCRIPT_VARIABLE)==0: continue
		var value=get(property.name)
		if value is Array or value is Dictionary: value=value.duplicate(true)
		elif typeof(value) in [TYPE_PACKED_BYTE_ARRAY,TYPE_PACKED_INT32_ARRAY,TYPE_PACKED_FLOAT64_ARRAY,TYPE_PACKED_VECTOR3_ARRAY]: value=value.duplicate()
		saved[property.name]=value
	return saved

func _init() -> void:
	reset()

func reset() -> void:
	native_failure={}; _backend_failed=false
	body_contact_count=0; body_contact_residual=0.; body_contact_uncertain=0
	tissue_boundary=null; _extracted_flaps=0; _extracted_area=0.; _components=[]; _component_dirty=true
	positions = PackedVector3Array([Vector3(0, .82, 0)])
	anchored = PackedByteArray([0])
	edges = []; _faces = []; _face_edges = []; _edge_map = {}
	_grasps = {}; _integration_steps = 0; _peak_strain = 0.0; _dirty = false
	_grasp_faces={}; _grasp_offsets={}; _incision_events=0; _retired_breaks=0; _face_rest_area=PackedFloat64Array(); _triangle_faces=PackedInt32Array(); _triangle_area=PackedFloat64Array()
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
	_physical_xyz=Precision.pack(positions); _physical_previous=Precision.pack(_previous); _physical_rest=Precision.pack(rest_positions)
	joint_stats=PackedFloat64Array()
	_joint_tip_history={}

func _vertex(ring: int, sector: int) -> int:
	return 1 + (ring - 1) * SECTORS + posmod(sector, SECTORS)

func _add_face(a: int, b: int, c: int,material_area:float=-1.) -> void:
	_faces.append([a, b, c])
	_face_edges.append([_edge(a, b), _edge(b, c), _edge(c, a)])
	_face_rest_area.append(material_area if material_area>=0. else (rest_positions[b]-rest_positions[a]).cross(rest_positions[c]-rest_positions[a]).length()*.5)

func _edge(a: int, b: int) -> int:
	var key := Vector2i(mini(a, b), maxi(a, b))
	if _edge_map.has(key): return _edge_map[key]
	var index := edges.size()
	_edge_map[key] = index
	edges.append({"a": a, "b": b, "rest": rest_positions[a].distance_to(rest_positions[b]), "active": true, "lambda": .0})
	_edge_a.append(a); _edge_b.append(b); _edge_rest.append(edges[index].rest); _edge_active.append(1); _lambdas.append(0.0)
	_incident[a].append(index)
	_incident[b].append(index)
	return index

func _rebuild_triangles() -> void:
	triangles.clear(); _retained_area=0.; _triangle_faces.clear(); _triangle_area.clear()
	var support:=PackedInt32Array(); support.resize(_edge_a.size()); support.fill(0)
	for i in range(_faces.size()):
		var intact:=true
		for v in _faces[i]:
			if _removed[v]!=0: intact=false
		for edge_id in _face_edges[i]:
			if _edge_active[edge_id]==0: intact=false
		if not intact: continue
		_triangle_faces.append(i); _triangle_area.append(_face_rest_area[i])
		for vertex_id in _faces[i]: triangles.append(vertex_id)
		for edge_id in _face_edges[i]: support[edge_id]+=1
		_retained_area+=_face_rest_area[i]
	if geometry:
		# An edge without any surviving membrane face cannot remain an invisible tether.
		for edge_id in range(_edge_a.size()):
			if support[edge_id]==0: _edge_active[edge_id]=0; edges[edge_id].active=false
		for hand in _grasps.keys():
			if not _connected(_grasps[hand]): _grasps.erase(hand); _grasp_faces.erase(hand); _grasp_offsets.erase(hand)
		_pinned=anchored.duplicate()
		for vertex in _grasps.values(): _pinned[vertex]=1
	_dirty=false; _component_dirty=true

func release() -> void:
	_grasps.clear(); _grasp_faces.clear(); _grasp_offsets.clear()
	_pinned = anchored.duplicate()

func release_hand(hand: int) -> void:
	_grasps.erase(hand); _grasp_faces.erase(hand); _grasp_offsets.erase(hand)
	_pinned = anchored.duplicate()
	for vertex in _grasps.values(): _pinned[vertex] = 1

func incise(start:Vector3,finish:Vector3,depth_axis:Vector3,half_depth:float)->Dictionary:
	# Prepare geometry, material state and attachment identities before any
	# mutation. Failure keeps the accepted specimen and numerical history.
	var cut:Dictionary=_cutter.slice(positions,triangles,start,finish,depth_axis,half_depth)
	if not cut.valid or not cut.changed: return {"valid":cut.valid,"changed":false,"reason":cut.reason}
	var grasp_faces:={}
	for hand in _grasps:
		if _grasp_faces.has(hand):
			var live:=_triangle_faces.find(_grasp_faces[hand])
			if live>=0: grasp_faces[hand]=live
	var prepared:Dictionary=Refinement.transfer({"rest":rest_positions,"previous":_previous,"anchored":anchored,"removed":_removed,"outside":_outside,"indices":triangles,"face_areas":_triangle_area,"grasps":_grasps,"grasp_faces":grasp_faces},cut,surface_density)
	if not prepared.valid: return {"valid":false,"changed":false,"reason":prepared.reason}
	var next_xyz:=PackedFloat64Array(); var next_previous:=PackedFloat64Array(); var next_rest:=PackedFloat64Array()
	if contact_backend:
		next_xyz=Precision.transfer(_physical_xyz,cut.bindings)
		next_previous=Precision.transfer(_physical_previous,cut.bindings)
		next_rest=Precision.transfer(_physical_rest,cut.bindings)
	for active in _edge_active:
		if active==0: _retired_breaks+=1
	positions=cut.points; rest_positions=prepared.rest; _previous=prepared.previous
	if contact_backend:
		_physical_xyz=next_xyz; _physical_previous=next_previous; _physical_rest=next_rest
		positions=Precision.publish(_physical_xyz); rest_positions=Precision.publish(_physical_rest); _previous=Precision.publish(_physical_previous)
	anchored=prepared.anchored; _removed=prepared.removed; _outside=prepared.outside
	_rest_area=prepared.lumped; _inverse_mass=prepared.inverse
	_grasps=prepared.grasps; _grasp_faces=prepared.grasp_faces
	for hand in _grasp_offsets.keys():
		if not _grasps.has(hand): _grasp_offsets.erase(hand)
	edges=[]; _faces=[]; _face_edges=[]; _edge_map={}; _face_rest_area=PackedFloat64Array()
	_edge_a=PackedInt32Array(); _edge_b=PackedInt32Array(); _edge_rest=PackedFloat64Array(); _edge_active=PackedByteArray(); _lambdas=PackedFloat64Array()
	_incident=[]
	for i in range(positions.size()): _incident.append([])
	for off in range(0,cut.indices.size(),3): _add_face(cut.indices[off],cut.indices[off+1],cut.indices[off+2],prepared.face_areas[off/3])
	if contact_backend:
		for e in range(_edge_a.size()):
			_edge_rest[e]=Precision.distance(_physical_rest,_edge_a[e],_edge_b[e]); edges[e].rest=_edge_rest[e]
	_pinned=anchored.duplicate()
	for v in _grasps.values(): _pinned[v]=1
	_rebuild_triangles(); _incision_events+=1
	return {"valid":true,"changed":true,"reason":""}

func _grasp_face(vertex:int)->int:
	for off in range(0,triangles.size(),3):
		if vertex in [triangles[off],triangles[off+1],triangles[off+2]]: return _triangle_faces[off/3]
	return -1

func _tool_frame(tool:Dictionary)->Basis:
	for part in tool.get("body",[]):
		if part.has("path"): return Basis(part.path.rotation1)
	return Basis.IDENTITY

func _grasp_target(tool:Dictionary,t:float,start:Vector3,acquired:bool)->Vector3:
	if acquired: return start # New contact is acquired at the accepted endpoint.
	var local:Vector3=_grasp_offsets[tool.hand]
	for part in tool.get("body",[]):
		if not part.has("path"): continue
		var path:Dictionary=part.path
		var old:Vector3=path.tip0+Basis(path.rotation0)*local
		return path.tip0.lerp(path.tip1,t)+Basis(path.rotation0.slerp(path.rotation1,t))*local+(start-old)*(1.-t)
	return start.lerp(tool.tip+local,t)

func step(dt: float, tool_tip: Vector3, tool_radius: float, grip: bool, cut: bool) -> void:
	if passive_tips.size() > 8: return
	var tools: Array[Dictionary] = [{"hand": 0, "tip": tool_tip, "radius": tool_radius, "grip": grip, "cut": cut}]
	var hand := 1
	for tip in passive_tips:
		tools.append({"hand": hand, "tip": tip, "radius": tool_radius, "grip": false, "cut": false})
		hand += 1
	step_tools(dt, tools)

func step_tools(dt: float, tools: Array[Dictionary]) -> void:
	if not stretch_backend and not contact_backend:
		_step_tools(dt,tools); return
	var saved:=_checkpoint()
	_backend_failed=false
	_step_tools(dt,tools)
	if _backend_failed:
		var failure:=native_failure.duplicate(true)
		for key in saved: set(key,saved[key])
		native_failure=failure

func _step_tools(dt: float, tools: Array[Dictionary]) -> void:
	# Validate the whole batch first: malformed second-hand input cannot partly advance time.
	if not is_finite(dt) or dt < .000001 or dt > MAX_DT or tools.size() > 16: return
	if not is_finite(stretch_compliance) or stretch_compliance < 0 or not is_finite(damping) or not is_finite(tear_strain) or tear_strain <= 0: return
	if not is_finite(pressure_load) or absf(pressure_load) > 5.0 or not is_finite(surface_density) or surface_density < .01 or surface_density > 100.0: return
	# A later density change cannot move refined support outside the
	# contact solver's inverse-mass domain, even before a grip is released.
	for area in _rest_area:
		if not is_finite(area) or area<0.: return
		if area>0. and (not is_finite(1./(surface_density*area)) or 1./(surface_density*area)>1e12): return
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
		if contact_backend and tool.grip and tool.get("body",[]).is_empty():
			_joint_failure("native_joint_requires_grasp_body"); return
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
	native_failure={}
	for hand_id in _grasps.keys():
		if not present.has(hand_id): _grasps.erase(hand_id); _grasp_faces.erase(hand_id); _grasp_offsets.erase(hand_id)
	for tool in tools:
		if not tool.grip: _grasps.erase(tool.hand); _grasp_faces.erase(tool.hand); _grasp_offsets.erase(tool.hand)
	_refresh_components()
	var acquired:={}
	for tool in tools:
		if not tool.grip or _grasps.has(tool.hand): continue
		var nearest: float = tool.radius
		var vertex := -1
		for i in range(positions.size()):
			if _removed[i]!=0 or anchored[i] != 0 or i in _grasps.values() or not _connected(i): continue
			var distance: float = positions[i].distance_to(tool.tip)
			if distance <= nearest: nearest = distance; vertex = i
		if vertex >= 0:
			_grasps[tool.hand] = vertex; _grasp_faces[tool.hand]=_grasp_face(vertex)
			_grasp_offsets[tool.hand]=_tool_frame(tool).transposed()*(positions[vertex]-tool.tip)
			acquired[tool.hand]=true
	var grasp_starts:={}
	for hand in _grasps: grasp_starts[hand]=positions[_grasps[hand]]
	_pinned = anchored.duplicate()
	for vertex in _grasps.values(): _pinned[vertex] = 1
	for i in range(positions.size()):
		_inverse_mass[i] = 0.0 if _pinned[i] != 0 or _removed[i]!=0 or _rest_area[i]<=0. else 1.0 / (surface_density * _rest_area[i])
	_integration_steps += 1
	body_contact_count=0; body_contact_residual=0.; body_contact_uncertain=0
	var damping_factor := clampf(damping, 0, 1)
	var joint_tip_starts:={}
	if contact_backend:
		for tool in tools: joint_tip_starts[tool.hand]=_joint_tip_history.get(tool.hand,tool.tip)
	for substep in range(substeps):
		var body:Array=[]
		for tool in tools:
			for segment in tool.get("body",[]):
				var part:Dictionary=ToolPath.interval(segment,float(substep)/substeps,float(substep+1)/substeps)
				if part.get("part","")=="jaw" and _grasps.has(tool.hand): part["attachment"]=_grasps[tool.hand]
				body.append(part)
		if contact_backend:
			for tool in tools:
				if not tool.get("body",[]).is_empty(): continue
				var start:Vector3=joint_tip_starts[tool.hand]
				var old_tip:Vector3=start.lerp(tool.tip,float(substep)/substeps)
				var new_tip:Vector3=start.lerp(tool.tip,float(substep+1)/substeps)
				body.append({"a":new_tip,"b":new_tip,"previous_a":old_tip,"previous_b":old_tip,"radius":tool.get("contact_radius",tool.radius)})
		var body_previous:=positions.duplicate() if not body.is_empty() else PackedVector3Array()
		var contact_previous:=positions.duplicate() if tissue_boundary else PackedVector3Array()
		if contact_backend:
			if not _joint_substep(h,alpha,damping_factor,tools,body,float(substep+1)/substeps,grasp_starts,acquired,body_previous,contact_previous): return
			for tool in tools: _joint_tip_history[tool.hand]=tool.tip
			continue
		var acceleration := _pressure_acceleration()
		for i in range(positions.size()):
			if anchored[i] != 0 or _removed[i]!=0: continue
			var old := positions[i]
			positions[i] += (positions[i] - _previous[i]) * damping_factor + acceleration[i] * h * h
			_previous[i] = old
		for tool in tools:
			if _grasps.has(tool.hand):
				var vertex: int = _grasps[tool.hand]
				positions[vertex] = positions[vertex].move_toward(_grasp_target(tool,float(substep+1)/substeps,grasp_starts[tool.hand],acquired.has(tool.hand)), .08)
			if tool.get("body",[]).is_empty(): _project_contact(tool.tip, tool.get("contact_radius",tool.radius))
		for edge_id in range(_edge_a.size()):
			_lambdas[edge_id] = 0.0
			if _edge_active[edge_id] == 0: continue
			var a := _edge_a[edge_id]
			var b := _edge_b[edge_id]
			var strain := positions[a].distance_to(positions[b]) / _edge_rest[edge_id] - 1.0
			if not stretch_backend: _peak_strain = maxf(_peak_strain, strain)
			var broken:bool = not stretch_backend and strain > tear_strain
			if not broken:
				for tool in tools:
					if tool.cut and _segment_distance(tool.tip, positions[a], positions[b]) < tool.radius:
						broken = true; break
			if broken:
				_edge_active[edge_id] = 0; edges[edge_id].active = false; _dirty = true
		if not body.is_empty() and _dirty: _rebuild_triangles()
		if _face_contact.has_method("begin_substep"): _face_contact.begin_substep(stretch_backend!=null)
		var settled:bool=not stretch_backend
		var motion:=INF; var operator_motion:=INF; var constitutive_residual:=INF; var contact_residual:=0.
		var budget:int=NATIVE_COUPLING_BUDGET if stretch_backend else clampi(solver_iterations,1,16)
		for iteration in range(budget):
			var iterate:=positions.duplicate() if stretch_backend else PackedVector3Array()
			_project_stretch(alpha)
			if _backend_failed: return
			if stretch_backend: operator_motion=_position_correction(positions,iterate)
			if not body.is_empty():
				var before_body:=positions.duplicate() if stretch_backend else PackedVector3Array()
				var projected:Dictionary=_face_contact.project(positions,triangles,_inverse_mass,body,body_previous)
				if projected.valid:
					# A small projection residual does not certify an unresolved
					# swept interval. Native ticks require resolved body motion.
					if stretch_backend and projected.uncertain>0:
						native_failure={"reason":"native_body_uncertain","uncertain":projected.uncertain}
						_backend_failed=true; return
					positions=projected.positions
					if stretch_backend: operator_motion=maxf(operator_motion,_position_correction(positions,before_body))
					contact_residual=projected.residual
					body_contact_count+=projected.contacts
					body_contact_residual=maxf(body_contact_residual,projected.residual)
					body_contact_uncertain+=projected.uncertain
				else:
					body_contact_uncertain+=1
					if stretch_backend:
						native_failure={"reason":"native_body_contact"}; _backend_failed=true; return
			if stretch_backend and tissue_boundary and geometry:
				var before_boundary:=positions.duplicate()
				_project_boundary(contact_previous)
				if _backend_failed: return
				operator_motion=maxf(operator_motion,_position_correction(positions,before_boundary))
			if stretch_backend:
				motion=_position_correction(positions,iterate)
				constitutive_residual=_native_constitutive_residual(alpha)
				if motion<=NATIVE_COUPLING_TOLERANCE and operator_motion<=NATIVE_COUPLING_TOLERANCE and constitutive_residual<=NATIVE_COUPLING_TOLERANCE and contact_residual<=NATIVE_COUPLING_TOLERANCE:
					settled=true; break
		if not settled:
			native_failure={"reason":"native_coupling_exhausted","iterations":budget,"position_residual":motion,"operator_residual":operator_motion,"constitutive_residual":constitutive_residual,"contact_residual":contact_residual}
			_backend_failed=true; return
		for i in range(positions.size()):
			if anchored[i] != 0:
				positions[i] = rest_positions[i]; _previous[i] = positions[i]
			elif _pinned[i] != 0:
				_previous[i] = positions[i]
		if _dirty: _rebuild_triangles()
		if not stretch_backend and tissue_boundary and geometry: _boundary_step(contact_previous)
		if _backend_failed: return
		if stretch_backend:
			# Constitutive failure uses accepted motion, never the inertial predictor.
			for edge_id in range(_edge_a.size()):
				if _edge_active[edge_id]==0: continue
				var strain:float=positions[_edge_a[edge_id]].distance_to(positions[_edge_b[edge_id]])/_edge_rest[edge_id]-1.
				_peak_strain=maxf(_peak_strain,strain)
				if strain>tear_strain:
					_edge_active[edge_id]=0; edges[edge_id].active=false; _dirty=true
			if _dirty: _rebuild_triangles()
			if tissue_boundary and geometry: _retire_exterior_flaps()

func _joint_substep(h:float,alpha:float,damping_factor:float,tools:Array[Dictionary],body:Array,t:float,grasp_starts:Dictionary,acquired:Dictionary,body_previous:PackedVector3Array,contact_previous:PackedVector3Array)->bool:
	# External edits to rendering/history proxies cannot silently reset physics.
	if Precision.publish(_physical_xyz)!=positions or Precision.publish(_physical_previous)!=_previous:
		return _joint_failure("native_joint_proxy_mutation")
	for tool in tools:
		if tool.cut: return _joint_failure("native_joint_requires_geometric_incision")
	var old:=_physical_xyz.duplicate(); var predicted:=old.duplicate()
	var acceleration:=_pressure_acceleration()
	for v in range(positions.size()):
		if anchored[v]!=0 or _removed[v]!=0: continue
		for axis in range(3): predicted[3*v+axis]+=(old[3*v+axis]-_physical_previous[3*v+axis])*damping_factor+float(acceleration[v][axis])*h*h
	var initial:=old.duplicate()
	for tool in tools:
		if not _grasps.has(tool.hand): continue
		var v:int=_grasps[tool.hand]
		var target:Vector3=positions[v].move_toward(_grasp_target(tool,t,grasp_starts[tool.hand],acquired.has(tool.hand)),.08)
		for axis in range(3):
			# Retain the exact physical point when the prescribed proxy did not move.
			var value:float=old[3*v+axis]+(float(target[axis])-float(positions[v][axis]))
			predicted[3*v+axis]=value; initial[3*v+axis]=value
	var a:=PackedInt32Array(); var b:=PackedInt32Array(); var rest:=PackedFloat64Array()
	for e in range(_edge_a.size()):
		if _edge_active[e]==0: continue
		a.append(_edge_a[e]); b.append(_edge_b[e]); rest.append(_edge_rest[e])
	var capsules:=PackedFloat64Array()
	for part in body:
		for point in [part.a,part.b]:
			for axis in range(3): capsules.append(point[axis])
		capsules.append(part.radius)
	var result:Dictionary=contact_backend.solve_contact({"predicted":predicted,"initial":initial,"inverse":_inverse_mass,"a":a,"b":b,"rest":rest,"alpha":alpha,"triangles":triangles,"capsules":capsules,"budget":100,"force_tolerance":1e-8,"gap_tolerance":1e-9,"complementarity_tolerance":1e-11})
	if result.get("status",-1)!=0: return _joint_failure("native_joint_solve",result.get("status",-1))
	if not result.get("xyz") is PackedFloat64Array or result.xyz.size()!=old.size() or not result.get("stats") is PackedFloat64Array or result.stats.size()!=12: return _joint_failure("native_joint_output")
	for i in range(old.size()):
		if not is_finite(result.xyz[i]) or absf(result.xyz[i])>16. or (_inverse_mass[i/3]==0. and result.xyz[i]!=predicted[i]): return _joint_failure("native_joint_output")
	for index in range(4):
		if not is_finite(result.stats[index]) or result.stats[index]<0.: return _joint_failure("native_joint_output")
	if result.stats[1]>1e-8 or result.stats[2]>1e-9 or result.stats[3]>1e-11: return _joint_failure("native_joint_residual")
	positions=Precision.publish(result.xyz)
	if not body.is_empty():
		_face_contact.begin_substep(true)
		var checked:Dictionary=_face_contact.project(positions,triangles,_inverse_mass,body,body_previous)
		if not checked.valid or checked.uncertain>0: return _joint_failure("native_joint_body_unresolved")
		if not is_finite(checked.get("residual",INF)) or checked.residual<0. or checked.residual>1e-9: return _joint_failure("native_joint_body_residual")
		# The swept/original-side guard may reject, never project a converged
		# physical candidate out of force balance. Anatomical coupling is pending.
		if checked.positions!=positions: return _joint_failure("native_joint_body_correction")
		body_contact_count+=checked.contacts; body_contact_residual=maxf(body_contact_residual,checked.residual)
	if tissue_boundary and geometry:
		var proxy:=positions.duplicate()
		_project_boundary(contact_previous)
		if _backend_failed: return false
		if positions!=proxy: return _joint_failure("native_joint_boundary_correction")
	_physical_xyz=result.xyz.duplicate(); _physical_previous=old
	joint_stats=result.stats.duplicate()
	for v in range(positions.size()):
		if _pinned[v]!=0 or _removed[v]!=0:
			for axis in range(3): _physical_previous[3*v+axis]=_physical_xyz[3*v+axis]
	_previous=Precision.publish(_physical_previous)
	for e in range(_edge_a.size()):
		if _edge_active[e]==0: continue
		var strain:=Precision.distance(_physical_xyz,_edge_a[e],_edge_b[e])/_edge_rest[e]-1.
		_peak_strain=maxf(_peak_strain,strain)
		if strain>tear_strain: _edge_active[e]=0; edges[e].active=false; _dirty=true
	if _dirty: _rebuild_triangles()
	if tissue_boundary and geometry: _retire_exterior_flaps()
	return true

func _joint_failure(reason:String,status:int=-1)->bool:
	native_failure={"reason":reason,"status":status}; _backend_failed=true; return false

func _position_correction(a:PackedVector3Array,b:PackedVector3Array)->float:
	var motion:=0.
	for v in range(a.size()): motion=maxf(motion,a[v].distance_to(b[v]))
	return motion

func _native_constitutive_residual(alpha:float)->float:
	var residual:=0.
	for e in range(_edge_a.size()):
		if _edge_active[e]==0: continue
		var constraint:float=positions[_edge_a[e]].distance_to(positions[_edge_b[e]])-_edge_rest[e]+alpha*_lambdas[e]
		if not is_finite(constraint): return INF
		residual=maxf(residual,absf(constraint))
	return residual

func _project_stretch(alpha:float)->void:
	if stretch_backend:
		var result:Dictionary=stretch_backend.project(positions,_inverse_mass,_edge_a,_edge_b,_edge_rest,_edge_active,_lambdas,alpha)
		var valid:bool=result.get("valid",false) and result.get("positions") is PackedVector3Array and result.get("lambda") is PackedFloat64Array
		if valid: valid=result.positions.size()==positions.size() and result["lambda"].size()==_lambdas.size()
		if valid:
			for i in range(positions.size()):
				if not result.positions[i].is_finite() or result.positions[i].length_squared()>256. or (_inverse_mass[i]==0. and result.positions[i]!=positions[i]): valid=false; break
		if valid:
			for value in result["lambda"]:
				if not is_finite(value): valid=false; break
		if not valid:
			native_failure={"reason":result.get("reason","native_output"),"status":result.get("status",-1)}; _backend_failed=true; return
		positions=result.positions; _lambdas=result["lambda"]; return
	for edge_id in range(_edge_a.size()):
		if _edge_active[edge_id] == 0: continue
		var a := _edge_a[edge_id]; var b := _edge_b[edge_id]
		var wa := _inverse_mass[a]; var wb := _inverse_mass[b]
		if wa + wb == 0: continue
		var offset := positions[a] - positions[b]; var length := offset.length()
		var normal:=offset/length if length>0. else (rest_positions[a]-rest_positions[b])/_edge_rest[edge_id]
		var delta := (-(length - _edge_rest[edge_id]) - alpha * _lambdas[edge_id]) / (wa + wb + alpha)
		_lambdas[edge_id] += delta
		var correction := normal * delta
		positions[a] += correction * wa; positions[b] -= correction * wb

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
		elif _rest_area[i] > 0.:
			forces[i] /= surface_density * _rest_area[i]
		else: forces[i]=Vector3.ZERO
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
	var broken := _retired_breaks
	var energy := .0
	for edge_id in range(_edge_a.size()):
		if _edge_active[edge_id] == 0: broken += 1
		else:
			var extension := positions[_edge_a[edge_id]].distance_to(positions[_edge_b[edge_id]]) - _edge_rest[edge_id]
			energy += .5 * extension * extension
	return {"body_contacts":body_contact_count,"body_projection_peak_residual":body_contact_residual,"body_uncertain":body_contact_uncertain,"incision_events":_incision_events,"initial_area":_initial_area,"retained_area":_retained_area,"cut_loss_area":maxf(0.,_initial_area-_retained_area-_extracted_area),"retained_detached_area":detached_area,"detached_flaps":detached_count,"extracted_flaps":_extracted_flaps,"extracted_area":_extracted_area,"max_strain": _peak_strain, "broken_edges": broken, "grasped": _grasps.get(0, -1), "grasps": _grasps.duplicate(), "integration_steps": _integration_steps, "finite": finite and is_finite(energy), "strain_energy": energy, "vertices": positions.size(), "triangles": triangles.size() / 3}

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
		_components[id].area+=_triangle_area[i/3]
func detached_components()->Array[Dictionary]:
	_refresh_components()
	var result:Array[Dictionary]=[]
	for component in _components:
		if not component.anchored and component.area>1e-12: result.append(component.duplicate(true))
	return result
func _boundary_step(before:PackedVector3Array)->void:
	_project_boundary(before)
	if not _backend_failed: _retire_exterior_flaps()
func _project_boundary(before:PackedVector3Array)->void:
	_refresh_components()
	for component in _components:
		if component.anchored or component.area<=1e-12: continue
		for v in component.vertices:
			var result:Dictionary=tissue_boundary.resolve(before[v],positions[v],_outside[v]!=0)
			if (stretch_backend or contact_backend) and not result.valid:
				native_failure={"reason":"native_tissue_boundary"}; _backend_failed=true; return
			if (stretch_backend or contact_backend) and _inverse_mass[v]==0. and result.position!=positions[v]:
				native_failure={"reason":"native_kinematic_boundary","vertex":v}; _backend_failed=true; return
			positions[v]=result.position; _outside[v]=1 if result.outside else 0
			if result.contact or not result.valid: _previous[v]=positions[v]
func _retire_exterior_flaps()->void:
	_refresh_components()
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
			if _removed[_grasps[hand]]!=0: _grasps.erase(hand); _grasp_faces.erase(hand); _grasp_offsets.erase(hand)
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
