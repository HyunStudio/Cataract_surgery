extends RefCounted
## Incision-pivot constraint. Research model units, not calibrated instrument dimensions.
var allow_withdrawal:=false
var portal := Vector3(1.44,.86,0)
var insertion := 1.28
var axis := Vector3(-1,-.03,0).normalized()
var tip: Vector3:
	get: return portal+axis*insertion

func aim_at(target: Vector3) -> void:
	if not target.is_finite(): return
	var direction := target-portal
	if direction.length() < (.000001 if allow_withdrawal else .08): return
	var inward := Vector3(-signf(portal.x),0,0)
	var candidate := direction.normalized()
	if candidate.dot(inward) < .28: return
	axis = candidate

func set_insertion(value: float) -> void:
	if is_finite(value): insertion = clampf(value,-1.5 if allow_withdrawal else .05,2.7)

func adjust_pitch(delta: float) -> void:
	if not is_finite(delta): return
	var horizontal := Vector2(axis.x,axis.z)
	if horizontal.length() < .01: return
	var pitch := clampf(asin(axis.y)+delta,-.55,.35)
	horizontal = horizontal.normalized()*cos(pitch)
	axis = Vector3(horizontal.x,sin(pitch),horizontal.y)

func place_tip(target:Vector3)->void:
	if not target.is_finite(): return
	var delta:=target-portal
	var inward:=Vector3(-signf(portal.x),0,0)
	if allow_withdrawal and delta.dot(inward)<0.:
		aim_at(portal-delta); set_insertion(-delta.length())
	else:
		aim_at(target); set_insertion(delta.length())
