extends RefCounted
## Original procedural ocular appearance. Display only; no physical surface edits.
const INNER:=1.43
const OUTER:=1.92
const HEIGHT:=.71
const BULGE:=.075
const SIDES:=8

static func surface_point(radius:float,angle:float)->Vector3:
	var fraction:float=clampf((radius-INNER)/(OUTER-INNER),0.,1.)
	return Vector3(cos(angle)*radius,HEIGHT+BULGE*sin(fraction*PI),sin(angle)*radius)

static func surface_normal(point:Vector3)->Vector3:
	var radius:=Vector2(point.x,point.z).length()
	var fraction:float=clampf((radius-INNER)/(OUTER-INNER),0.,1.)
	var slope:float=BULGE*PI*cos(fraction*PI)/(OUTER-INNER)
	return Vector3(-slope*point.x/radius,1.,-slope*point.z/radius).normalized()

static func _tube(points:PackedVector3Array,start_radius:float,end_radius:float,vertices:PackedVector3Array,normals:PackedVector3Array,indices:PackedInt32Array)->void:
	var begin:=vertices.size()
	for i in range(points.size()):
		var tangent:Vector3=(points[mini(i+1,points.size()-1)]-points[maxi(i-1,0)]).normalized()
		var surface_up:=surface_normal(points[i])
		var side:Vector3=tangent.cross(surface_up).normalized()
		var up:Vector3=side.cross(tangent).normalized()
		var radius:float=lerpf(start_radius,end_radius,float(i)/(points.size()-1))
		for j in range(SIDES):
			var angle:float=TAU*j/SIDES
			var normal:Vector3=side*cos(angle)+up*sin(angle)
			vertices.append(points[i]+surface_up*(.35*radius)+normal*radius);normals.append(normal)
	for i in range(points.size()-1):
		for j in range(SIDES):
			var a:=begin+i*SIDES+j;var b:=begin+(i+1)*SIDES+j
			var an:=begin+i*SIDES+(j+1)%SIDES;var bn:=begin+(i+1)*SIDES+(j+1)%SIDES
			indices.append_array(PackedInt32Array([a,an,b,an,bn,b]))
	# Close the tapered ends without allocating a scene node per cap or branch.
	for endpoint in [0,points.size()-1]:
		var cap_radius:float=start_radius if endpoint==0 else end_radius
		var center:=vertices.size();vertices.append(points[endpoint]+surface_normal(points[endpoint])*(.35*cap_radius))
		var direction:Vector3=(points[0]-points[1]).normalized() if endpoint==0 else (points[-1]-points[-2]).normalized()
		normals.append(direction)
		for j in range(SIDES):
			var a:int=begin+endpoint*SIDES+j;var b:int=begin+endpoint*SIDES+(j+1)%SIDES
			indices.append_array(PackedInt32Array([center,b,a] if endpoint==0 else [center,a,b]))

static func vessel_mesh()->ArrayMesh:
	var vertices:=PackedVector3Array();var normals:=PackedVector3Array();var indices:=PackedInt32Array()
	for stem in range(25):
		var angle:float=stem*2.399963
		var start:float=1.89+.012*sin(stem*1.71)
		var finish:float=1.50+.07*(.5+.5*sin(stem*1.23))
		var points:=PackedVector3Array()
		for i in range(11):
			var t:=i/10.
			var theta:float=angle+.022*sin(t*5.+stem*.7)+.015*t
			points.append(surface_point(lerpf(start,finish,t),theta))
		_tube(points,.0048,.0011,vertices,normals,indices)
		for fork in [3,6]:
			var branch:=PackedVector3Array();var point:Vector3=points[fork]
			var radius:=Vector2(point.x,point.z).length();var theta:=atan2(point.z,point.x)
			var side:float=-1. if (stem+fork)%2==0 else 1.
			var reach:float=radius-.13-.04*sin(stem*.9+fork)
			for i in range(7):
				var t:=i/6.
				branch.append(surface_point(lerpf(radius,reach,t),theta+side*(.07*t+.01*sin(PI*t))))
			_tube(branch,.0027,.00075,vertices,normals,indices)
	var arrays:=[];arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_INDEX]=indices
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh
