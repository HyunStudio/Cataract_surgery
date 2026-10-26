extends RefCounted
## Bounded research model: equal-mass spring particles + one fluid compartment.
## Parameters and pressure are dimensionless, uncalibrated and NOT device settings.
## This is neither CFD nor a validated model of human lens material.
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
var passive_tips := PackedVector3Array()
var _contact_tips := PackedVector3Array()
var _removed_mass: float = 0.0
var _volume: float = 1.0
var _inflow_rate: float = 0.0
var _outflow_rate: float = 0.0
var _accelerations := PackedVector3Array()
var _degree := PackedInt32Array()

func _init() -> void:
	reset()

func reset() -> void:
	particles.clear()
	bonds.clear()
	inflow=0.0
	suction=0.0
	energy=0.0
	passive_tips.clear()
	_contact_tips.clear()
	_removed_mass=0.0
	_volume=1.0
	_inflow_rate=0.0
	_outflow_rate=0.0
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
	var count := ceili(dt/SUBSTEP)
	var h := dt/count
	for i in range(count):
		_integrate(h,tip,active,aspiration)

func _control(value: float) -> float:
	return clampf(value,0.0,1.0) if is_finite(value) else 0.0

func _integrate(h: float, tip: Vector3, active: bool, aspiration: bool) -> void:
	_accelerations.fill(Vector3.ZERO)
	_degree.fill(0)
	for bond in bonds:
		if not bond.active: continue
		var a: int = bond.a
		var b: int = bond.b
		if not particles[a].active or not particles[b].active:
			bond.active=false
			continue
		var pa: Vector3 = particles[a].position
		var pb: Vector3 = particles[b].position
		var delta := pb-pa
		var distance := delta.length()
		var strain := absf(distance-float(bond.rest))/maxf(0.01,float(bond.rest))
		# Only strained links or links at an active local tip can fail.
		if active and energy>0.0:
			var nearest := minf(pa.distance_to(tip),pb.distance_to(tip))
			if nearest<0.22:
				bond.damage=float(bond.damage)+h*energy*10.0*(1.0-nearest/0.22)
		if strain>0.50 or float(bond.damage)>=1.0:
			bond.active=false
			continue
		_degree[a]+=1
		_degree[b]+=1
		if distance>0.000001:
			# Equal masses: symmetric acceleration conserves internal momentum.
			var force := delta/distance*(distance-float(bond.rest))*38.0
			_accelerations[a]+=force
			_accelerations[b]-=force
	var obstruction := 0.0
	for i in range(particles.size()):
		var particle: Dictionary = particles[i]
		if not particle.active: continue
		var position: Vector3 = particle.position
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
		if aspiration and suction>0.0 and _degree[i]==0 and distance<0.44:
			if distance<=INLET_RADIUS:
				_remove_at_inlet(i)
				continue
			_accelerations[i]+=to_tip/maxf(distance,0.00001)*suction*24.0*(1.0-distance/0.44)
		var velocity: Vector3 = (particle.velocity+_accelerations[i]*h)*exp(-4.0*h)
		velocity=velocity.limit_length(2.4)
		var next := position+velocity*h
		# Swept inlet test avoids missing the port between substeps.
		if aspiration and suction>0.0 and _degree[i]==0:
			var segment := next-position
			var t := clampf(to_tip.dot(segment)/maxf(segment.length_squared(),0.000000001),0,1)
			if (position+segment*t).distance_to(tip)<=INLET_RADIUS:
				particle.position=position+segment*t
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
		particle.velocity=velocity
		particle.position=next
	_integrate_compartment(h,aspiration,obstruction)

func _remove_at_inlet(index: int) -> void:
	var particle: Dictionary = particles[index]
	if not particle.active: return
	_removed_mass+=float(particle.mass)
	particle.active=false
	particle.velocity=Vector3.ZERO

func _integrate_compartment(h: float, aspiration: bool, obstruction: float) -> void:
	_inflow_rate=0.08*inflow
	_outflow_rate=0.08*suction*(1.0-clampf(obstruction,0.0,0.98)) if aspiration else 0.0
	# Limit actual boundary flows so reported volume obeys the same balance law.
	_outflow_rate=minf(_outflow_rate,(_volume-MIN_VOLUME)/h+_inflow_rate)
	_inflow_rate=minf(_inflow_rate,(MAX_VOLUME-_volume)/h+_outflow_rate)
	_volume+=(_inflow_rate-_outflow_rate)*h
	_volume=clampf(_volume,MIN_VOLUME,MAX_VOLUME)

func metrics() -> Dictionary:
	var remaining := 0.0
	var finite := is_finite(_volume) and is_finite(_removed_mass) and is_finite(_inflow_rate) and is_finite(_outflow_rate)
	var neighbors: Array[Array] = []
	for i in range(particles.size()):
		neighbors.append([])
		var particle: Dictionary = particles[i]
		finite=finite and particle.position.is_finite() and particle.velocity.is_finite() and is_finite(float(particle.mass))
		if particle.active: remaining+=float(particle.mass)
	for bond in bonds:
		finite=finite and is_finite(float(bond.rest)) and is_finite(float(bond.damage))
		if bond.active and particles[bond.a].active and particles[bond.b].active:
			neighbors[bond.a].append(bond.b)
			neighbors[bond.b].append(bond.a)
	var visited := PackedByteArray()
	visited.resize(particles.size())
	visited.fill(0)
	var fragments := 0
	for i in range(particles.size()):
		if visited[i]!=0 or not particles[i].active: continue
		fragments+=1
		var pending: Array[int] = [i]
		visited[i]=1
		while not pending.is_empty():
			var index: int = pending.pop_back()
			for other in neighbors[index]:
				if visited[other]==0:
					visited[other]=1
					pending.append(other)
	return {"remaining_mass":remaining,"removed_mass":_removed_mass,"fragments":fragments,"volume":_volume,"pressure":pow(_volume,2.0),"inflow":_inflow_rate,"outflow":_outflow_rate,"finite":finite}
