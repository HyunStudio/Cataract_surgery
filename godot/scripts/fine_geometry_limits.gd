extends RefCounted
## Separate bounded geometry storage from mechanical degrees of freedom.
const LEGACY_POINTS:=4096
const FINE_POINTS:=8192
const CONTROLS:=4096
const FACES:=8192
static func supported(value:int)->bool:return value in [LEGACY_POINTS,FINE_POINTS]
static func points(state:Dictionary)->int:
	var value=state.get("fine_point_limit",LEGACY_POINTS)
	return value if value is int and supported(value) else 0
