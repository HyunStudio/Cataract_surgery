extends RefCounted
## Scalar double operations; Vector3 is a publication/input proxy only.
static func pack(points:PackedVector3Array)->PackedFloat64Array:
	var values:=PackedFloat64Array(); values.resize(points.size()*3)
	for i in range(points.size()):
		for axis in range(3): values[3*i+axis]=points[i][axis]
	return values
static func publish(values:PackedFloat64Array)->PackedVector3Array:
	var points:=PackedVector3Array(); points.resize(values.size()/3)
	for i in range(points.size()): points[i]=Vector3(values[3*i],values[3*i+1],values[3*i+2])
	return points
static func transfer(values:PackedFloat64Array,bindings:Array)->PackedFloat64Array:
	var result:=PackedFloat64Array(); result.resize(bindings.size()*3)
	for i in range(bindings.size()):
		var binding:Dictionary=bindings[i]
		var total:float=float(binding.weights.x)+binding.weights.y+binding.weights.z
		for axis in range(3):
			# Preserve identical source values exactly and affine constants despite
			# float32 barycentric storage in the existing incision geometry.
			var base:float=values[3*binding.ids.x+axis]
			result[3*i+axis]=base+((values[3*binding.ids.y+axis]-base)*binding.weights.y+(values[3*binding.ids.z+axis]-base)*binding.weights.z)/total
	return result
static func distance(values:PackedFloat64Array,a:int,b:int)->float:
	var squared:=0.
	for axis in range(3): squared+=pow(values[3*a+axis]-values[3*b+axis],2)
	return sqrt(squared)
