extends RefCounted
## Generic engineering contact envelopes in scene units, not manufacturer geometry
## or full mesh collision. Local +X runs from the working tip toward the handle.
## Rods use their rendered dimensions; the pointed blade is conservatively bounded
## by a capsule. The decorative lumen is inside the working-tip envelope. External
## handles beyond x=3.05 are intentionally omitted from the inserted-body profile.

## Shared generic pointed blade. Leading edges lie in the midplane; upper and
## lower ridges form visible bevels. Conservative collision envelope is unchanged.
const BLADE_TIP:=Vector3.ZERO
const BLADE_LEFT:=Vector3(.18,0.,-.06)
const BLADE_RIGHT:=Vector3(.18,0.,.06)
static func blade_geometry()->Dictionary:
	return {"positions":PackedVector3Array([BLADE_TIP,BLADE_LEFT,BLADE_RIGHT,Vector3(.12,.0075,0),Vector3(.12,-.0075,0)]),"triangles":PackedInt32Array([0,1,3,1,2,3,2,0,3,0,4,1,1,4,2,2,4,0])}
static func cutting_edges(id:String)->Array[Dictionary]:
	if id!="knife":return []
	return [{"a":BLADE_TIP,"b":BLADE_LEFT},{"a":BLADE_TIP,"b":BLADE_RIGHT}]

static func segments(id:String,tip_radius:float,grip:bool=false)->Array[Dictionary]:
	var result:Array[Dictionary]=[]
	if id not in ["knife","forceps","cannula","manipulator","phaco","ia","injector"]:
		return result
	if not is_finite(tip_radius) or tip_radius<=0.:
		return result
	match id:
		"knife":
			# Blade envelope retains size (.18,.015,.12), centered at (.09,0,0):
			# radius includes its entire YZ cross section.
			result.append(_segment([0.,0.,0.],[.18,0.,0.],sqrt(.06*.06+.0075*.0075),"blade",true))
		"forceps":
			# Opposing round jaw envelopes meet at their tips when closed.
			# A smaller offset overlaps solid jaws and makes nearby tissue contact infeasible.
			var tip_offset:=.010 if grip else .025
			var base_offset:=.018 if grip else .045
			for side in [-1.,1.]:
				result.append(_segment([0.,0.,side*tip_offset],[.22,0.,side*base_offset],.010,"jaw"))
		"cannula":
			result.append(_segment([0.,0.,0.],[.18,.025,0.],tip_radius,"bent_tip"))
		"manipulator":
			result.append(_segment([0.,0.,0.],[.025,0.,.06],.012,"hook"))
		_:
			result.append(_segment([0.,0.,0.],[.22,0.,0.],tip_radius,"working_tip",false,id=="phaco"))
	var shaft_radius:=tip_radius if id in ["phaco","ia","injector"] else .020
	result.append(_segment([.20,0.,0.],[3.05,0.,0.],shaft_radius,"shaft"))
	if id in ["phaco","ia"]:
		result.append(_segment([.22,0.,0.],[.75,0.,0.],tip_radius*1.35,"sleeve"))
	return result

## Shared render/contact orientation: local +X is opposite the insertion axis.
static func frame(axis:Vector3,roll:float=0.)->Basis:
	if not axis.is_finite() or not is_finite(axis.length_squared()) or axis.length_squared()<1.e-12:
		return Basis.IDENTITY
	var toward:Vector3=-axis.normalized()
	var side:=toward.cross(Vector3.UP).normalized()
	if side.length_squared()<.01:
		side=Vector3.FORWARD
	return Basis(toward,side.cross(toward).normalized(),side)*Basis(Vector3.RIGHT,roll)

## CylinderMesh uses local Y as its longitudinal axis.
static func rod_transform(a:Vector3,b:Vector3)->Transform3D:
	var axis:=(b-a).normalized()
	var side:=Vector3.FORWARD.cross(axis).normalized()
	if side.length_squared()<.01: side=Vector3.RIGHT
	return Transform3D(Basis(side,axis,side.cross(axis).normalized()),(a+b)*.5)

static func _segment(a:Array,b:Array,radius:float,part:String,cutting:bool=false,energy:bool=false)->Dictionary:
	# Float32 vectors serve rendering/legacy contact; never recover precision
	# from them for the packed64 physical path.
	return {"a":Vector3(a[0],a[1],a[2]),"b":Vector3(b[0],b[1],b[2]),"physical_a":PackedFloat64Array(a),"physical_b":PackedFloat64Array(b),"radius":radius,"part":part,"cutting":cutting,"energy":energy}
