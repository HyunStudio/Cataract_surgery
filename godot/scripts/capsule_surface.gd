extends RefCounted
## Capsule axis versus a static indexed triangle mesh. No mesh mutation.
## Sweep is conservative: unresolved contact (including arbitrary ignored contact)
## returns hit=true with conservative=true, never an uncertified clear result.
const EPS := 0.00000001
const CONTACT_EPS := 0.0000001
const MAX_COORD := 1000000.0
const MAX_EVALUATIONS := 8192

func _empty()->Dictionary:
	return {"valid":true,"hit":false,"distance":INF,"penetration":0.0,"axis_point":Vector3.ZERO,"surface_point":Vector3.ZERO,"normal":Vector3.ZERO,"triangle":-1}

func _validate(a:Vector3,b:Vector3,radius:float,points:PackedVector3Array,indices:PackedInt32Array)->bool:
	if not _finite_point(a) or not _finite_point(b) or not is_finite(radius) or radius<=0.0 or radius>MAX_COORD or indices.size()%3!=0: return false
	for p in points:
		if not _finite_point(p): return false
	for index in indices:
		if index<0 or index>=points.size(): return false
	return true

func _finite_point(p:Vector3)->bool:
	return p.is_finite() and p.abs().x<=MAX_COORD and p.abs().y<=MAX_COORD and p.abs().z<=MAX_COORD

func query(a:Vector3,b:Vector3,radius:float,points:PackedVector3Array,indices:PackedInt32Array,ignore:Callable=Callable())->Dictionary:
	var result:=_empty()
	if not _validate(a,b,radius,points,indices): result.valid=false; return result
	var uncertain:Dictionary={}
	for offset in range(0,indices.size(),3):
		var x:=points[indices[offset]]; var y:=points[indices[offset+1]]; var z:=points[indices[offset+2]]
		# Filter individual feature witnesses, never discard a whole triangle after
		# one ignored witness. Arbitrary masks cannot be exhaustively represented.
		for candidate in _candidates(a,b,x,y,z):
			_complete(candidate,a,b,x,y,z,radius,int(offset/3))
			if ignore.is_valid() and ignore.call(candidate.duplicate()):
				if candidate.hit and (uncertain.is_empty() or candidate.distance<uncertain.distance): uncertain=candidate
				continue
			if candidate.distance<result.distance: result.merge(candidate,true)
	result.hit=result.distance<=radius+CONTACT_EPS
	if not result.hit and not uncertain.is_empty():
		result.merge(uncertain,true); result.hit=true
		result["conservative"]=true; result["reason"]="ignored_interval_uncertified"
	return result

func sweep(a0:Vector3,b0:Vector3,a1:Vector3,b1:Vector3,radius:float,points:PackedVector3Array,indices:PackedInt32Array,ignore:Callable=Callable())->Dictionary:
	var result:=_empty(); result["time"]=1.0; result["conservative"]=false; result["reason"]=""
	if not _validate(a0,b0,radius,points,indices) or not _finite_point(a1) or not _finite_point(b1): result.valid=false; return result
	var va:=a1-a0; var vb:=b1-b0
	var speed:=maxf(va.length(),vb.length())
	var evaluations:=0
	for offset in range(0,indices.size(),3):
		var x:=points[indices[offset]]; var y:=points[indices[offset+1]]; var z:=points[indices[offset+2]]
		if not _bounds_overlap(a0,b0,a1,b1,radius,x,y,z): continue
		var t:=0.0
		for iteration in range(128):
			if evaluations>=MAX_EVALUATIONS:
				return _blocked(result,{},0.0,"work_budget")
			evaluations+=1
			var a:=a0.lerp(a1,t); var b:=b0.lerp(b1,t)
			var contact:=_nearest(a,b,x,y,z)
			_complete(contact,a,b,x,y,z,radius,int(offset/3)); contact["time"]=t
			if t==0.0 and contact.distance<=radius+CONTACT_EPS and _recovering(contact,a,b,x,y,z,va,vb): break
			var gap:float=contact.distance-radius
			if gap<=CONTACT_EPS:
				if ignore.is_valid() and ignore.call(contact.duplicate()):
					# A Callable supplies no lower bound on distance to its mask's
					# intact boundary. Advancing through this interval is unprovable.
					if not result.hit or t<result.time: result=_blocked(result,contact,t,"ignored_interval_uncertified")
				elif not result.hit or t<result.time:
					result.merge(contact,true); result.hit=true
				break
			if speed<=EPS: break
			# Hausdorff speed of the segment is bounded by max endpoint speed.
			# Distance to a fixed triangle is therefore speed-Lipschitz.
			if gap>speed*(minf(1.0,result.time)-t)+CONTACT_EPS: break
			var step:=gap/speed*.9
			if step<=0.000000000001:
				if not result.hit or t<result.time: result=_blocked(result,contact,t,"convergence")
				break
			t+=step
			if t>minf(1.0,result.time): break
			if iteration==127:
				if not result.hit or t<result.time: result=_blocked(result,contact,t,"iteration_budget")
	return result

func _blocked(result:Dictionary,contact:Dictionary,t:float,reason:String)->Dictionary:
	result.merge(contact,true); result.hit=true; result.time=t
	result.conservative=true; result.reason=reason
	return result

func _recovering(c:Dictionary,a:Vector3,b:Vector3,x:Vector3,y:Vector3,z:Vector3,va:Vector3,vb:Vector3)->bool:
	var n:Vector3=c.normal
	# A separating supporting plane certifies that the whole shaft moves out.
	# Crossing/coplanar axes have zero distance and cannot use this exemption.
	if c.distance<=CONTACT_EPS: return false
	var surface:Vector3=c.surface_point
	if minf((a-surface).dot(n),(b-surface).dot(n))<c.distance-CONTACT_EPS: return false
	if maxf((x-surface).dot(n),maxf((y-surface).dot(n),(z-surface).dot(n)))>CONTACT_EPS: return false
	var outward:=minf(va.dot(n),vb.dot(n))
	return outward>EPS or (maxf(va.length_squared(),vb.length_squared())>EPS*EPS and va.dot(n)>=-EPS and vb.dot(n)>=-EPS and c.penetration<=CONTACT_EPS)

func _bounds_overlap(a:Vector3,b:Vector3,c:Vector3,d:Vector3,r:float,x:Vector3,y:Vector3,z:Vector3)->bool:
	var lo:=a.min(b).min(c).min(d)-Vector3.ONE*(r+CONTACT_EPS)
	var hi:=a.max(b).max(c).max(d)+Vector3.ONE*(r+CONTACT_EPS)
	var tl:=x.min(y).min(z); var th:=x.max(y).max(z)
	return th.x>=lo.x and tl.x<=hi.x and th.y>=lo.y and tl.y<=hi.y and th.z>=lo.z and tl.z<=hi.z

func _complete(c:Dictionary,a:Vector3,b:Vector3,x:Vector3,y:Vector3,z:Vector3,radius:float,triangle:int)->void:
	var delta:Vector3=c.axis_point-c.surface_point
	c["distance"]=delta.length(); c["penetration"]=maxf(0.0,radius-c.distance)
	var n:=delta.normalized()
	if delta.length_squared()<=EPS*EPS:
		n=(y-x).cross(z-x).normalized()
		if n.length_squared()<=EPS*EPS:
			var shaft:=b-a
			n=shaft.cross(Vector3.RIGHT).normalized()
			if n.length_squared()<=EPS*EPS: n=Vector3.UP
		elif (a-x).dot(n)<-EPS or (absf((a-x).dot(n))<=EPS and (b-x).dot(n)<0.0): n=-n
	c["normal"]=n; c["triangle"]=triangle; c["hit"]=c.distance<=radius+CONTACT_EPS

func _nearest(a:Vector3,b:Vector3,x:Vector3,y:Vector3,z:Vector3)->Dictionary:
	var nearest:Dictionary={}; var distance:=INF
	for candidate in _candidates(a,b,x,y,z):
		var d:float=candidate.axis_point.distance_squared_to(candidate.surface_point)
		if d<distance: distance=d; nearest=candidate
	return nearest

func _candidates(a:Vector3,b:Vector3,x:Vector3,y:Vector3,z:Vector3)->Array[Dictionary]:
	var result:Array[Dictionary]=[]
	var normal:Vector3=(y-x).cross(z-x)
	var denominator:float=normal.dot(b-a)
	if denominator!=0.0 and normal.length_squared()>1e-30:
		var t:float=normal.dot(x-a)/denominator
		if t>=0.0 and t<=1.0:
			var p:=a.lerp(b,t)
			if _inside(p,x,y,z): result.append({"axis_point":p,"surface_point":p})
	result.append({"axis_point":a,"surface_point":_closest(a,x,y,z)})
	result.append({"axis_point":b,"surface_point":_closest(b,x,y,z)})
	for edge in [[x,y],[y,z],[z,x]]:
		var pair:=_segments(a,b,edge[0],edge[1])
		result.append({"axis_point":pair[0],"surface_point":pair[1]})
	return result

func _inside(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->bool:
	# Avoid a Gram determinant: subtracting almost equal dot products rounds
	# valid skinny faces to zero in a single-precision Vector3 build.
	var normal:=(b-a).cross(c-a).abs()
	var omit:=normal.max_axis_index()
	var i:=(omit+1)%3; var j:=(omit+2)%3
	var area:float=(float(b[i])-a[i])*(float(c[j])-a[j])-(float(b[j])-a[j])*(float(c[i])-a[i])
	if area==0.: return false
	var first:float=(float(b[i])-a[i])*(float(p[j])-a[j])-(float(b[j])-a[j])*(float(p[i])-a[i])
	var second:float=(float(c[i])-b[i])*(float(p[j])-b[j])-(float(c[j])-b[j])*(float(p[i])-b[i])
	var third:float=(float(a[i])-c[i])*(float(p[j])-c[j])-(float(a[j])-c[j])*(float(p[i])-c[i])
	return (first>=0. and second>=0. and third>=0.) if area>0. else (first<=0. and second<=0. and third<=0.)

func _closest(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->Vector3:
	var normal:=(b-a).cross(c-a)
	if normal.length_squared()>1e-30:
		var projected:=p-normal*((p-a).dot(normal)/normal.length_squared())
		if _inside(projected,a,b,c): return projected
	var result:=a; var distance:=INF
	for edge in [[a,b],[b,c],[c,a]]:
		var q:=_on_segment(p,edge[0],edge[1])
		var d:=p.distance_squared_to(q)
		if d<distance: distance=d; result=q
	return result

func _on_segment(p:Vector3,a:Vector3,b:Vector3)->Vector3:
	var d:=b-a; var length_sq:=d.length_squared()
	return a if length_sq<=1e-30 else a+d*clampf((p-a).dot(d)/length_sq,0.0,1.0)

func _segments(a:Vector3,b:Vector3,c:Vector3,d:Vector3)->Array[Vector3]:
	var u:=b-a; var v:=d-c; var w:=a-c
	var aa:=u.dot(u); var ee:=v.dot(v); var ff:=v.dot(w)
	var s:=0.0; var t:=0.0
	if aa<=1e-30: return [a,_on_segment(a,c,d)]
	if ee<=1e-30: return [_on_segment(c,a,b),c]
	var cc:=u.dot(w); var bb:=u.dot(v)
	# Cross products preserve the small angle lost by aa*ee-bb*bb.
	var cross:=u.cross(v); var denominator:=cross.length_squared()
	if denominator>0.: s=clampf(v.cross(w).dot(cross)/denominator,0.0,1.0)
	t=(bb*s+ff)/ee
	if t<0.0: t=0.0; s=clampf(-cc/aa,0.0,1.0)
	elif t>1.0: t=1.0; s=clampf((bb-cc)/aa,0.0,1.0)
	return [a+u*s,c+v*t]
