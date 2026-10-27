extends RefCounted
## Generic engineering contact envelopes in scene units, not manufacturer geometry
## or full mesh collision. Local +X runs from the working tip toward the handle.
## Rods use their rendered dimensions; the knife prism is conservatively bounded
## by a capsule. The decorative lumen is inside the working-tip envelope. External
## handles beyond x=3.05 are intentionally omitted from the inserted-body profile.

static func segments(id:String,tip_radius:float,grip:bool=false)->Array[Dictionary]:
	var result:Array[Dictionary]=[]
	if id not in ["knife","forceps","cannula","manipulator","phaco","ia","injector"]:
		return result
	if not is_finite(tip_radius) or tip_radius<=0.:
		return result
	match id:
		"knife":
			# Prism size (.18,.015,.12), centered at (.09,0,0):
			# radius includes its entire YZ cross section.
			result.append(_segment(Vector3.ZERO,Vector3(.18,0,0),sqrt(.06*.06+.0075*.0075),"blade",true))
		"forceps":
			var closure:=.35 if grip else 1.
			for side in [-1.,1.]:
				result.append(_segment(Vector3(0,0,side*.025*closure),Vector3(.22,0,side*.045*closure),.010,"jaw"))
		"cannula":
			result.append(_segment(Vector3.ZERO,Vector3(.18,.025,0),tip_radius,"bent_tip"))
		"manipulator":
			result.append(_segment(Vector3.ZERO,Vector3(.025,0,.06),.012,"hook"))
		_:
			result.append(_segment(Vector3.ZERO,Vector3(.22,0,0),tip_radius,"working_tip",false,id=="phaco"))
	var shaft_radius:=tip_radius if id in ["phaco","ia","injector"] else .020
	result.append(_segment(Vector3(.20,0,0),Vector3(3.05,0,0),shaft_radius,"shaft"))
	if id in ["phaco","ia"]:
		result.append(_segment(Vector3(.22,0,0),Vector3(.75,0,0),tip_radius*1.35,"sleeve"))
	return result

## Shared render/contact orientation: local +X is opposite the insertion axis.
static func frame(axis:Vector3)->Basis:
	if not axis.is_finite() or not is_finite(axis.length_squared()) or axis.length_squared()<1.e-12:
		return Basis.IDENTITY
	var toward:Vector3=-axis.normalized()
	var side:=toward.cross(Vector3.UP).normalized()
	if side.length_squared()<.01:
		side=Vector3.FORWARD
	return Basis(toward,side.cross(toward).normalized(),side)

## CylinderMesh uses local Y as its longitudinal axis.
static func rod_transform(a:Vector3,b:Vector3)->Transform3D:
	var axis:=(b-a).normalized()
	var side:=Vector3.FORWARD.cross(axis).normalized()
	if side.length_squared()<.01: side=Vector3.RIGHT
	return Transform3D(Basis(side,axis,side.cross(axis).normalized()),(a+b)*.5)

static func _segment(a:Vector3,b:Vector3,radius:float,part:String,cutting:bool=false,energy:bool=false)->Dictionary:
	return {"a":a,"b":b,"radius":radius,"part":part,"cutting":cutting,"energy":energy}
