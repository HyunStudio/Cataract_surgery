extends RefCounted
## One press belongs to one procedure/camera/tool context.
var allowed := false
var down := false
var needs_release := false

func press(inside: bool) -> void:
	down = true
	allowed = inside and not needs_release
	if not inside:
		needs_release = true

func release() -> void:
	down = false
	allowed = false
	needs_release = false

func block() -> void:
	allowed = false
	if down:
		needs_release = true

func sweep(previous: Vector3, current: Vector3) -> Array[Vector3]:
	var result: Array[Vector3] = []
	if not previous.is_finite() or not current.is_finite():
		return result
	var count: int = clampi(ceili(previous.distance_to(current) / .015), 1, 160)
	for i in range(1, count + 1):
		result.append(previous.lerp(current, float(i)/count))
	return result
