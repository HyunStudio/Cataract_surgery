extends RefCounted
## Continuous swept sphere vs indexed triangles, including face/edge/vertex contact.
## Geometry only; no clinical dimensions, tissue damage, or solver mutation.
const EPS:=0.00000001
func sweep(start:Vector3,finish:Vector3,radius:float,points:PackedVector3Array,indices:PackedInt32Array,ignore:Callable=Callable())->Dictionary:
	var result:={"valid":true,"hit":false,"position":finish,"normal":Vector3.ZERO,"time":1.,"triangle":-1}
	if not start.is_finite() or not finish.is_finite() or not is_finite(radius) or radius<=0. or radius>.5 or indices.size()%3!=0 or start.length_squared()>256. or finish.length_squared()>256.:
		result.valid=false; result.position=start if start.is_finite() else Vector3.ZERO; return result
	var mesh_lo:=Vector3(INF,INF,INF); var mesh_hi:=-mesh_lo
	for point in points:
		if not point.is_finite() or point.length_squared()>256.: result.valid=false; result.position=start; return result
		mesh_lo=mesh_lo.min(point); mesh_hi=mesh_hi.max(point)
	for index in indices:
		if index<0 or index>=points.size(): result.valid=false; result.position=start; return result
	var delta:=finish-start
	if delta.length_squared()<EPS*EPS: return result
	var lo:=start.min(finish)-Vector3.ONE*radius
	var hi:=start.max(finish)+Vector3.ONE*radius
	if mesh_hi.x<lo.x or mesh_lo.x>hi.x or mesh_hi.y<lo.y or mesh_lo.y>hi.y or mesh_hi.z<lo.z or mesh_lo.z>hi.z: return result
	for offset in range(0,indices.size(),3):
		var a:=points[indices[offset]]; var b:=points[indices[offset+1]]; var c:=points[indices[offset+2]]
		var face_lo:=a.min(b).min(c); var face_hi:=a.max(b).max(c)
		if face_hi.x<lo.x or face_lo.x>hi.x or face_hi.y<lo.y or face_lo.y>hi.y or face_hi.z<lo.z or face_lo.z>hi.z: continue
		var candidates:Array[Dictionary]=[]
		var n:=(b-a).cross(c-a)
		if n.length_squared()>EPS*EPS:
			n=n.normalized()
			var d0:float=(start-a).dot(n); var d1:float=(finish-a).dot(n)
			var side:=1. if d0>=0. else -1.
			if (d1-d0)*side < -EPS:
				var t:=maxf(0.,(d0-side*radius)/(d0-d1))
				if t<=1.:
					var center:=start+delta*t
					var projected:=center-n*(center-a).dot(n)
					if _inside(projected,a,b,c):
						candidates.append({"time":t,"position":projected+n*side*radius,"normal":n*side})
		for edge in [[a,b],[b,c],[c,a]]:
			var contact:=_edge(start,delta,edge[0],edge[1],radius)
			if not contact.is_empty(): candidates.append(contact)
		for vertex in [a,b,c]:
			var contact:=_point(start,delta,vertex,radius)
			if not contact.is_empty(): candidates.append(contact)
		for contact in candidates:
			contact["surface_point"]=contact.position-n*(contact.position-a).dot(n) if n.length_squared()>.5 else contact.position
			if ignore.is_valid() and ignore.call(contact): continue
			if not result.hit or contact.time<result.time:
				result.merge(contact,true); result.hit=true; result.triangle=int(offset/3)
	return result
func _inside(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->bool:
	var v0:=b-a; var v1:=c-a; var v2:=p-a
	var d00:=v0.dot(v0); var d01:=v0.dot(v1); var d11:=v1.dot(v1)
	var denominator:=d00*d11-d01*d01
	if denominator<=maxf(.000000000000000000000001,d00*d11*.000000000001): return false
	var u:=(d11*v2.dot(v0)-d01*v2.dot(v1))/denominator
	var v:=(d00*v2.dot(v1)-d01*v2.dot(v0))/denominator
	return u>=-EPS and v>=-EPS and u+v<=1.+EPS
func _time(q:Vector3,v:Vector3,radius:float)->float:
	var a:=v.length_squared(); var b:=q.dot(v); var c:=q.length_squared()-radius*radius
	if c<=EPS: return 0. if b < -EPS else INF
	if a<EPS*EPS or b>=0.: return INF
	var discriminant:=b*b-a*c
	if discriminant<0.: return INF
	var t:=(-b-sqrt(discriminant))/a
	return t if t>=0. and t<=1. else INF
func _point(start:Vector3,delta:Vector3,point:Vector3,radius:float)->Dictionary:
	var t:=_time(start-point,delta,radius)
	if not is_finite(t): return {}
	var n:=(start+delta*t-point).normalized()
	if n.length_squared()<EPS: n=-delta.normalized()
	return {"time":t,"position":point+n*radius,"normal":n}
func _edge(start:Vector3,delta:Vector3,a:Vector3,b:Vector3,radius:float)->Dictionary:
	var axis:=b-a; var length_sq:=axis.length_squared()
	if length_sq<EPS*EPS: return {}
	var q:=start-a
	var perpendicular:=q-axis*q.dot(axis)/length_sq
	var speed:=delta-axis*delta.dot(axis)/length_sq
	var t:=_time(perpendicular,speed,radius)
	if not is_finite(t): return {}
	var center:=start+delta*t
	var u:=(center-a).dot(axis)/length_sq
	if u<0. or u>1.: return {}
	var closest:=a+axis*u
	var n:=(center-closest).normalized()
	if n.length_squared()<EPS: n=-speed.normalized()
	return {"time":t,"position":closest+n*radius,"normal":n}

func overlap(center:Vector3,radius:float,points:PackedVector3Array,indices:PackedInt32Array,ignore:Callable=Callable())->Dictionary:
	# Reuse complete atomic validation; the zero-length sweep does not manufacture motion.
	var result:=sweep(center,center,radius,points,indices)
	if not result.valid or points.is_empty(): return result
	var bounds:=AABB(points[0],Vector3.ZERO)
	for p in points: bounds=bounds.expand(p)
	if not bounds.grow(radius+.00005).has_point(center): return result
	var nearest:=radius+.00005
	for offset in range(0,indices.size(),3):
		var a:=points[indices[offset]]; var b:=points[indices[offset+1]]; var c:=points[indices[offset+2]]
		var lo:=a.min(b).min(c)-Vector3.ONE*nearest; var hi:=a.max(b).max(c)+Vector3.ONE*nearest
		if center.x<lo.x or center.x>hi.x or center.y<lo.y or center.y>hi.y or center.z<lo.z or center.z>hi.z: continue
		var closest:=_closest(center,a,b,c)
		var distance:=center.distance_to(closest)
		if distance>nearest: continue
		var normal:=(center-closest).normalized()
		if normal.length_squared()<EPS: normal=(b-a).cross(c-a).normalized()
		if normal.length_squared()<EPS: continue
		var candidate:={"hit":true,"position":center,"surface_point":closest,"normal":normal,"triangle":int(offset/3)}
		if ignore.is_valid() and ignore.call(candidate): continue
		nearest=distance
		result.merge(candidate,true)
	return result
func _closest(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->Vector3:
	var normal:=(b-a).cross(c-a)
	if normal.length_squared()>EPS*EPS:
		normal=normal.normalized()
		var projected:=p-normal*(p-a).dot(normal)
		if _inside(projected,a,b,c): return projected
	var closest:=a; var distance:=INF
	for edge in [[a,b],[b,c],[c,a]]:
		var candidate:=Geometry3D.get_closest_point_to_segment(p,edge[0],edge[1])
		var squared:=candidate.distance_squared_to(p)
		if squared<distance: distance=squared; closest=candidate
	return closest
