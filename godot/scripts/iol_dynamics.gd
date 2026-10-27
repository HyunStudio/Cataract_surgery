extends RefCounted
## Synthetic elastic implant experiment. No material calibration or clinical dimensions.
## The plunger meters release; damped elastic forces recover each released point.
var positions := PackedVector3Array()
var optic_count := 32
var _rest := PackedVector3Array()
var _velocity := PackedVector3Array()
var _delivered := 0.0
var _center := Vector3(0,.72,0)
var _center_velocity := Vector3.ZERO
var _started := false

func _init() -> void:
	reset()

func reset() -> void:
	_delivered = 0.; _started = false
	_center = Vector3(0,.72,0); _center_velocity = Vector3.ZERO
	_rest = PackedVector3Array()
	for i in range(optic_count):
		var a := TAU*i/optic_count
		_rest.append(Vector3(cos(a)*.5,0,sin(a)*.5))
	for side in [-1.,1.]:
		for i in range(12):
			var a := -.8+float(i)/11.*1.6
			_rest.append(Vector3(side*(.46+.24*sin(float(i)/11.*PI)),0,side*sin(a)*.52))
	positions.resize(_rest.size())
	_velocity.resize(_rest.size()); _velocity.fill(Vector3.ZERO)
	for i in range(positions.size()): positions[i] = _folded(i,_center)

func _folded(index: int, nozzle: Vector3) -> Vector3:
	var local := _rest[index]
	return nozzle+Vector3(.10+local.x*.09,local.z*.055,local.z*.08)

func step(dt: float, nozzle: Vector3, injecting: bool, tip: Vector3, manipulating: bool) -> void:
	if not is_finite(dt) or dt<=0. or dt>.05 or not nozzle.is_finite() or not tip.is_finite() or nozzle.length_squared()>64. or tip.length_squared()>64.:
		return
	if injecting and not _started:
		_started = true; _center = nozzle
	var count := ceili(dt/(1./120.))
	var h := dt/count
	for substep in range(count):
		if injecting: _delivered = minf(1.,_delivered+h*.65)
		var released := int(floor(_delivered*positions.size()+.000001))
		var force := Vector3.ZERO
		if manipulating and released>0:
			var nearest := .12
			var contact := -1
			for i in range(mini(released,optic_count)):
				var distance := positions[i].distance_to(tip)
				if distance<nearest: nearest=distance; contact=i
			if contact>=0:
				var away := positions[contact]-tip
				away.y=0.
				if away.length()>.000001: force=away.normalized()*(.12-nearest)*300.
		_center_velocity = (_center_velocity+force*h)*exp(-8.*h)
		_center_velocity = _center_velocity.limit_length(.7)
		_center += _center_velocity*h
		_center.x = clampf(_center.x,-1.,1.); _center.z = clampf(_center.z,-1.,1.)
		for i in range(positions.size()):
			if i>=released:
				positions[i]=_folded(i,nozzle); _velocity[i]=Vector3.ZERO
				continue
			var target := _center+_rest[i]
			var acceleration := (target-positions[i])*100.-_velocity[i]*18.
			_velocity[i] = (_velocity[i]+acceleration*h).limit_length(3.)
			positions[i] += _velocity[i]*h

func metrics() -> Dictionary:
	var finite := _center.is_finite() and _center_velocity.is_finite() and is_finite(_delivered)
	var centroid := Vector3.ZERO
	for i in range(positions.size()):
		finite = finite and positions[i].is_finite() and _velocity[i].is_finite()
		if i<optic_count: centroid+=positions[i]/optic_count
	var shape_error := 0.
	for i in range(positions.size()): shape_error=maxf(shape_error,positions[i].distance_to(_center+_rest[i]))
	var alignment := clampf(1.-Vector2(centroid.x,centroid.z).length()/.5-absf(centroid.y-.72),0.,1.)
	return {"delivered":_delivered,"deployed":_delivered>=1. and shape_error<.035,"alignment":alignment if _delivered>=1. else 0.,"finite":finite,"center":[centroid.x,centroid.y,centroid.z],"shape_error":shape_error}
