extends RefCounted
## Bounded research model: equal-mass spring particles + one fluid compartment.
## Parameters and pressure are dimensionless, uncalibrated and NOT device settings.
## This is neither CFD nor a validated model of human lens material.
const MaterialModel=preload("res://scripts/lens_material.gd")
var material=MaterialModel.new()
var layered:=false
var hydro_flow:=0.0
var tissue_access:=true
const CENTER := Vector3(0.0,0.68,0.0)
const INITIAL_MASS := 1.0
const MIN_VOLUME := 0.2
const MAX_VOLUME := 1.6
const INLET_RADIUS := 0.05
const MAX_STEP := 0.05
const SUBSTEP := 1.0/240.0
var particles: Array[Dictionary] = []
var bonds: Array[Dictionary] = []
var inflow: float = 0.0
var suction: float = 0.0
var energy: float = 0.0
var hardness: float = 0.4
var wound_leak: float = 0.0
var passive_tips := PackedVector3Array()
var _contact_tips := PackedVector3Array()
var _removed_mass: float = 0.0
var _volume: float = 1.0
var _inflow_rate: float = 0.0
var _outflow_rate: float = 0.0
var _accelerations := PackedVector3Array()
var _degree := PackedInt32Array()
## Packed numerical authority; public dictionaries are read-only presentation mirrors.
var _positions := PackedVector3Array()
var _velocities := PackedVector3Array()
var _masses := PackedFloat64Array()
var _active := PackedByteArray()
var _bond_a := PackedInt32Array()
var _bond_b := PackedInt32Array()
var _bond_rest := PackedFloat64Array()
var _bond_active := PackedByteArray()
var _bond_damage := PackedFloat64Array()
var _damage_scale := 1.0
var _fracture_strain := .5
var _leak_rate := 0.0
var _fragment_count := 1
var _fragments_dirty := false

func _init() -> void:
	reset()

func reset() -> void:
	particles.clear()
	bonds.clear()
	inflow=0.0
	suction=0.0
	energy=0.0
	hardness=.4
	wound_leak=0.0
	hydro_flow=0.0; tissue_access=true
	passive_tips.clear()
	_contact_tips.clear()
	_removed_mass=0.0
	_volume=1.0
	_inflow_rate=0.0
	_outflow_rate=0.0
	_leak_rate=0.0
	_fragment_count=1; _fragments_dirty=false
	# Three interlinked layers, each with 1+6+12+18 particles; no region masks.
	for layer in range(-1,2):
		var radial_scale: float = 0.86 if layer!=0 else 1.0
		_append_particle(CENTER+Vector3(0,layer*0.047,0))
		for ring in range(1,4):
			for i in range(ring*6):
				var angle := float(i)/float(ring*6)*TAU
				var radius := ring*0.22*radial_scale
				_append_particle(CENTER+Vector3(cos(angle)*radius,layer*0.047,sin(angle)*radius))
	for particle in particles: particle.mass=INITIAL_MASS/particles.size()
	for i in range(particles.size()):
		for j in range(i+1,particles.size()):
			var distance: float = particles[i].position.distance_to(particles[j].position)
			if distance<=0.244:
				bonds.append({"a":i,"b":j,"rest":distance,"active":true,"damage":0.0})
	_accelerations.resize(particles.size())
	_degree.resize(particles.size())
	_positions=PackedVector3Array(); _velocities=PackedVector3Array(); _masses=PackedFloat64Array(); _active=PackedByteArray()
	for particle in particles:
		_positions.append(particle.position); _velocities.append(particle.velocity); _masses.append(particle.mass); _active.append(1)
	_bond_a=PackedInt32Array(); _bond_b=PackedInt32Array(); _bond_rest=PackedFloat64Array(); _bond_active=PackedByteArray(); _bond_damage=PackedFloat64Array()
	for bond in bonds:
		_bond_a.append(bond.a); _bond_b.append(bond.b); _bond_rest.append(bond.rest); _bond_active.append(1); _bond_damage.append(0.0)

	material.reset(_positions)
	_sync_public()

func _append_particle(position: Vector3) -> void:
	particles.append({"position":position,"velocity":Vector3.ZERO,"mass":0.0,"active":true})

func step(dt: float, tip: Vector3, active: bool, aspiration: bool) -> void:
	# Refuse invalid input before touching parameters, geometry, mass or volume.
	if not is_finite(dt) or dt<=0.0 or dt>MAX_STEP or not tip.is_finite() or tip.length_squared()>256.0:
		return
	if passive_tips.size()>4: return
	for other_tip in passive_tips:
		if not other_tip.is_finite() or other_tip.length_squared()>256.0: return
	_contact_tips=PackedVector3Array([tip])
	for other_tip in passive_tips:
		var duplicate := false
		for existing_tip in _contact_tips:
			if existing_tip.distance_squared_to(other_tip)<0.00000001: duplicate=true
		if not duplicate: _contact_tips.append(other_tip)
	inflow=_control(inflow)
	suction=_control(suction)
	energy=_control(energy)
	hardness=clampf(hardness,0.0,1.0) if is_finite(hardness) else .4
	wound_leak=_control(wound_leak)
	hydro_flow=_control(hydro_flow)
	_damage_scale=1.0/(1.0+2.0*(hardness-.4))
	_fracture_strain=.5+.5*(hardness-.4)
	var count := ceili(dt/SUBSTEP)
	var h := dt/count
	for i in range(count):
		_integrate(h,tip,active,aspiration)
	_sync_public()

func _sync_public() -> void:
	for i in range(_positions.size()):
		particles[i].position=_positions[i]
		particles[i].velocity=_velocities[i]
		particles[i].active=_active[i]!=0
		particles[i]["cortex"]=material.is_cortex(i)
		particles[i]["adhesion"]=material.adhesion[i]
	for i in range(_bond_a.size()):
		bonds[i].damage=_bond_damage[i]

func _control(value: float) -> float:
	return clampf(value,0.0,1.0) if is_finite(value) else 0.0

func _integrate(h: float, tip: Vector3, active: bool, aspiration: bool) -> void:
	_accelerations.fill(Vector3.ZERO)
	_degree.fill(0)
	for bond_id in range(_bond_a.size()):
		if _bond_active[bond_id]==0: continue
		var a := _bond_a[bond_id]
		var b := _bond_b[bond_id]
		if _active[a]==0 or _active[b]==0:
			_break_bond(bond_id)
			continue
		var pa := _positions[a]
		var pb := _positions[b]
		var delta := pb-pa
		var distance := delta.length()
		var rest := _bond_rest[bond_id]
		var strain := absf(distance-rest)/maxf(0.01,rest)
		# Only strained links or links at an active local tip can fail.
		if active and tissue_access and energy>0.0:
			var nearest := minf(pa.distance_to(tip),pb.distance_to(tip))
			if nearest<0.22:
				_bond_damage[bond_id]+=h*energy*10.0*(1.0-nearest/0.22)*_damage_scale
		var threshold:=_fracture_strain
		if layered and (material.is_cortex(a) or material.is_cortex(b)):
			threshold=.32
			# Aspiration can peel locally released cortical fibres; it adds no nuclear energy.
			if aspiration and tissue_access and suction>0.:
				_bond_damage[bond_id]+=h*suction*14.*material.peel_weight(a,b,tip,_positions)
		if strain>threshold or _bond_damage[bond_id]>=1.0:
			_break_bond(bond_id)
			continue
		_degree[a]+=1
		_degree[b]+=1
		if distance>0.000001:
			# Equal masses: symmetric acceleration conserves internal momentum.
			var force := delta/distance*(distance-rest)*38.0
			_accelerations[a]+=force
			_accelerations[b]-=force
	var obstruction := 0.0
	var decay := exp(-4.0*h)
	for i in range(_positions.size()):
		if _active[i]==0: continue
		var position := _positions[i]
		if layered: _accelerations[i]+=material.adhesion_acceleration(i,position)
		var to_tip := tip-position
		var distance := to_tip.length()
		if distance<0.12:
			var occupied := (1.0-distance/0.12)*(0.95 if _degree[i]>0 else 0.5)
			obstruction=maxf(obstruction,occupied)
		# Solid contact exists for every retained tool, including an unpowered probe.
		# Accumulate contact accelerations once, then integrate this particle once.
		for contact_tip in _contact_tips:
			var away := position-contact_tip
			var contact_distance := away.length()
			if contact_distance<0.085:
				var direction := away/contact_distance if contact_distance>0.00001 else Vector3.UP
				_accelerations[i]+=direction*(0.085-contact_distance)*90.0
		# Only free particles can travel into the aspiration port. Bound tissue obstructs it.
		if aspiration and tissue_access and suction>0.0 and _degree[i]==0 and distance<0.44:
			if distance<=INLET_RADIUS:
				_remove_at_inlet(i)
				continue
			_accelerations[i]+=to_tip/maxf(distance,0.00001)*suction*24.0*(1.0-distance/0.44)
		var velocity := (_velocities[i]+_accelerations[i]*h)*decay
		velocity=velocity.limit_length(2.4)
		var next := position+velocity*h
		# Swept inlet test avoids missing the port between substeps.
		if aspiration and tissue_access and suction>0.0 and _degree[i]==0:
			var segment := next-position
			var t := clampf(to_tip.dot(segment)/maxf(segment.length_squared(),0.000000001),0,1)
			if (position+segment*t).distance_to(tip)<=INLET_RADIUS:
				_positions[i]=position+segment*t
				_remove_at_inlet(i)
				continue
		# A simple bounded chamber wall, not anatomical contact or hydrodynamics.
		var radial := Vector2(next.x,next.z)
		if radial.length()>1.10:
			radial=radial.normalized()*1.10
			next.x=radial.x
			next.z=radial.y
			velocity.x*=0.2
			velocity.z*=0.2
		if next.y<0.36 or next.y>1.04:
			next.y=clampf(next.y,0.36,1.04)
			velocity.y*=0.2
		_velocities[i]=velocity
		_positions[i]=next
	_integrate_compartment(h,aspiration,obstruction)
	if layered: material.step(h,tip,hydro_flow*(_inflow_rate/.08),_positions,_active)

func _remove_at_inlet(index: int) -> void:
	if _active[index]==0: return
	_removed_mass+=_masses[index]
	_active[index]=0
	if layered: material.adhesion[index]=0.
	_velocities[index]=Vector3.ZERO
	_fragments_dirty=true

func _break_bond(index: int) -> void:
	_bond_active[index]=0
	bonds[index].active=false
	_fragments_dirty=true

func _integrate_compartment(h: float, aspiration: bool, obstruction: float) -> void:
	_inflow_rate=0.08*inflow
	var aspiration_rate := 0.08*suction*(1.0-clampf(obstruction,0.0,0.98)) if aspiration else 0.0
	_leak_rate=0.08*wound_leak
	var requested_outflow := aspiration_rate+_leak_rate
	_outflow_rate=requested_outflow
	# Limit actual boundary flows so reported volume obeys the same balance law.
	_outflow_rate=minf(_outflow_rate,(_volume-MIN_VOLUME)/h+_inflow_rate)
	if requested_outflow>0: _leak_rate*=_outflow_rate/requested_outflow
	_inflow_rate=minf(_inflow_rate,(MAX_VOLUME-_volume)/h+_outflow_rate)
	_volume+=(_inflow_rate-_outflow_rate)*h
	_volume=clampf(_volume,MIN_VOLUME,MAX_VOLUME)

func metrics() -> Dictionary:
	var remaining := 0.0
	var finite := is_finite(_volume) and is_finite(_removed_mass) and is_finite(_inflow_rate) and is_finite(_outflow_rate)
	for i in range(_positions.size()):
		finite=finite and _positions[i].is_finite() and _velocities[i].is_finite() and is_finite(_masses[i])
		if _active[i]!=0: remaining+=_masses[i]
	for i in range(_bond_rest.size()):
		finite=finite and is_finite(_bond_rest[i]) and is_finite(_bond_damage[i])
	if _fragments_dirty: _count_fragments()
	var result:Dictionary={"remaining_mass":remaining,"removed_mass":_removed_mass,"fragments":_fragment_count,"volume":_volume,"pressure":pow(_volume,2.0),"inflow":_inflow_rate,"outflow":_outflow_rate,"leak_outflow":_leak_rate,"finite":finite}
	if layered: result.merge(material.metrics(_active,_masses))
	return result

func _count_fragments() -> void:
	var parents := PackedInt32Array()
	parents.resize(_positions.size())
	for i in range(parents.size()): parents[i]=i
	for i in range(_bond_a.size()):
		var a := _bond_a[i]
		var b := _bond_b[i]
		if _bond_active[i]==0 or _active[a]==0 or _active[b]==0: continue
		while parents[a]!=a: a=parents[a]
		while parents[b]!=b: b=parents[b]
		if a!=b: parents[b]=a
	_fragment_count=0
	for i in range(parents.size()):
		if _active[i]!=0 and parents[i]==i: _fragment_count+=1
	_fragments_dirty=false
