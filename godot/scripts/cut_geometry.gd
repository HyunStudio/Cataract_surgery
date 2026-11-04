extends RefCounted
## Preserve the legacy vector path; physical arrays never enter a real_t vector.
static func make3(x:float,y:float,z:float,physical:bool):
 return PackedFloat64Array([x,y,z]) if physical else Vector3(x,y,z)
static func make2(x:float,y:float,physical:bool):
 return PackedFloat64Array([x,y]) if physical else Vector2(x,y)
static func sub(a,b):
 if a is Vector3 or a is Vector2:return a-b
 var out:=PackedFloat64Array();out.resize(a.size())
 for j in range(a.size()):out[j]=a[j]-b[j]
 return out
static func add(a,b):
 if a is Vector3 or a is Vector2:return a+b
 var out:=PackedFloat64Array();out.resize(a.size())
 for j in range(a.size()):out[j]=a[j]+b[j]
 return out
static func mul(a,t:float):
 if a is Vector3 or a is Vector2:return a*t
 var out:=PackedFloat64Array();out.resize(a.size())
 for j in range(a.size()):out[j]=a[j]*t
 return out
static func divide(a,t:float):
 if a is Vector3 or a is Vector2:return a/t
 var out:=PackedFloat64Array();out.resize(a.size())
 for j in range(a.size()):out[j]=a[j]/t
 return out
static func norm2(a)->float:
 if a is Vector3 or a is Vector2:return a.length_squared()
 var answer:=0.
 for x in a:answer+=x*x
 return answer
static func length(a)->float:
 if a is Vector3 or a is Vector2:return a.length()
 return sqrt(norm2(a))
static func distance(a,b)->float:
 if a is Vector3:return a.distance_to(b)
 return length(sub(a,b))
static func normalized(a):
 if a is Vector3:return a.normalized()
 return divide(a,length(a))
static func cross(a,b):
 if a is Vector3:return a.cross(b)
 return PackedFloat64Array([a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]])
static func lerp(a,b,t:float):
 if a is Vector3:return a.lerp(b,t)
 return add(a,mul(sub(b,a),t))
static func finite(a)->bool:
 if a is Vector3:return a.is_finite()
 for x in a:
  if not is_finite(x):return false
 return true
static func closest(p,a,b):
 if a is Vector3:return Geometry3D.get_closest_point_to_segment(p,a,b)
 var delta=sub(b,a);var squared:=norm2(delta)
 if squared==0.:return a.duplicate()
 var t:=0.
 for j in range(3):t+=(p[j]-a[j])*delta[j]
 return add(a,mul(delta,clampf(t/squared,0.,1.)))
