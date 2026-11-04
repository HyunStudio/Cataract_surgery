extends RefCounted
## Finite sharp-edge sweep geometry in the same generic tool pose frame as render.
## Angular chords approximate the pose sweep; this is not exact-predicate CCD.
const Profile=preload("res://scripts/instrument_profile.gd")
const Path=preload("res://scripts/instrument_path.gd")
const MAX_STEPS:=64
const ANGULAR_STEP:=.05
const MAX_TRANSLATION:=.25
const RESOLUTION:=1e-7
static func invalid(reason:String)->Dictionary:
	return {"valid":false,"reason":reason,"patches":[],"steps":0}
static func _triangle(a:Vector3,b:Vector3,c:Vector3)->PackedVector3Array:
	var length:=a.distance_to(b)
	if length<=RESOLUTION or (b-a).cross(c-a).length()/length<=RESOLUTION:return PackedVector3Array()
	return PackedVector3Array([a,b,c])
static func build(id:String,tip0:Vector3,axis0:Vector3,tip1:Vector3,axis1:Vector3,active:bool)->Dictionary:
	var patches:Array[PackedVector3Array]=[];var edges:Array=Profile.cutting_edges(id)
	if not active or edges.is_empty():return {"valid":true,"reason":"","patches":patches,"steps":0}
	for point in [tip0,tip1]:
		if not point.is_finite() or point.length_squared()>256.:return invalid("pose")
	for axis in [axis0,axis1]:
		if not axis.is_finite() or not is_finite(axis.length_squared()) or axis.length_squared()<1e-12:return invalid("axis")
	if tip0.distance_to(tip1)>MAX_TRANSLATION:return invalid("sweep_distance")
	var first:Quaternion=Profile.frame(axis0).get_rotation_quaternion();var last:Quaternion=Profile.frame(axis1).get_rotation_quaternion()
	var steps:int=maxi(1,ceili(first.angle_to(last)/ANGULAR_STEP))
	if steps>MAX_STEPS:return invalid("sweep_budget")
	for edge in edges:
		var path:={"path":{"tip0":tip0,"tip1":tip1,"rotation0":first,"rotation1":last,"a0":edge.a,"b0":edge.b,"a1":edge.a,"b1":edge.b}}
		for i in range(steps):
			var old:Dictionary=Path.sample(path,float(i)/steps);var current:Dictionary=Path.sample(path,float(i+1)/steps)
			for point in [old.a,old.b,current.a,current.b]:
				if not point.is_finite() or point.length_squared()>256.:return invalid("coordinate")
			for triangle in [_triangle(old.a,old.b,current.b),_triangle(old.a,current.b,current.a)]:
				if not triangle.is_empty():patches.append(triangle)
	return {"valid":true,"reason":"","patches":patches,"steps":steps}
