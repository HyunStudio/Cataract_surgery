extends RefCounted
## Shared XZ footprint of the traced entry and its tunnel to the external portal.
static func contains(point:Vector3,paths:Array,radius:float,width:float,portals:Array)->bool:
	if not point.is_finite() or not is_finite(radius) or radius<=0. or radius>=width: return false
	var p:=Vector2(point.x,point.z)
	for hand in range(paths.size()):
		var path=paths[hand]
		if not (path is Array or path is PackedVector3Array) or path.size()<2: continue
		if not path[0] is Vector3 or not path[-1] is Vector3 or not path[0].is_finite() or not path[-1].is_finite(): continue
		var offset:=Vector2.ZERO
		if hand<portals.size() and portals[hand] is Vector3 and portals[hand].is_finite():
			var center:Vector3=(path[0]+path[-1])*.5
			offset=Vector2(portals[hand].x-center.x,portals[hand].z-center.z)
		for i in range(1,path.size()):
			if not path[i] is Vector3 or not path[i-1] is Vector3 or not path[i].is_finite() or not path[i-1].is_finite(): continue
			var a:=Vector2(path[i-1].x,path[i-1].z); var b:=Vector2(path[i].x,path[i].z)
			var polygon:=PackedVector2Array([a,b,b+offset,a+offset])
			var distance:=INF
			if offset.length_squared()>1e-12 and Geometry2D.is_point_in_polygon(p,polygon): distance=0.
			else:
				for edge in [[a,b],[b,b+offset],[b+offset,a+offset],[a+offset,a]]:
					distance=minf(distance,p.distance_to(Geometry2D.get_closest_point_to_segment(p,edge[0],edge[1])))
			if distance+radius<width: return true
	return false
