extends RefCounted
## Bounded discrete face projection, not calibrated continuum mechanics.
## Previous-side swept candidates prevent a fast translating shaft from merely
## appearing on the opposite side. Unsatisfied constraints remain explicit.
const Kernel=preload("res://scripts/capsule_surface.gd")
var kernel:=Kernel.new()
func valid_body(body:Array)->bool:
	if body.size()>64: return false
	for part in body:
		if not part is Dictionary: return false
		for key in ["a","b","previous_a","previous_b"]:
			if not part.get(key) is Vector3 or not part[key].is_finite() or part[key].length_squared()>256.: return false
		if not (part.get("radius") is float or part.get("radius") is int) or not is_finite(part.radius) or part.radius<=0. or part.radius>.3: return false
	return true

func project(points:PackedVector3Array,faces:PackedInt32Array,masses:PackedFloat64Array,body:Array,previous:PackedVector3Array,max_correction:float=.04)->Dictionary:
	var out:={"valid":false,"positions":points.duplicate(),"contacts":0,"residual":0.,"uncertain":0}
	if not valid_body(body) or masses.size()!=points.size() or previous.size()!=points.size() or faces.size()%3!=0 or not is_finite(max_correction) or max_correction<=0. or max_correction>1.: return out
	for i in range(points.size()):
		if not points[i].is_finite() or points[i].length_squared()>256. or not previous[i].is_finite() or previous[i].length_squared()>256. or not is_finite(masses[i]) or masses[i]<0. or masses[i]>1e12: return out
	for id in faces:
		if id<0 or id>=points.size(): return out
	out.valid=true
	for off in range(0,faces.size(),3):
		var ids:=PackedInt32Array([faces[off],faces[off+1],faces[off+2]])
		for part in body:
			var current:=PackedVector3Array([out.positions[ids[0]],out.positions[ids[1]],out.positions[ids[2]]])
			var old:=PackedVector3Array([previous[ids[0]],previous[ids[1]],previous[ids[2]]])
			var lo:Vector3=part.a.min(part.b).min(part.previous_a).min(part.previous_b)-Vector3.ONE*part.radius
			var hi:Vector3=part.a.max(part.b).max(part.previous_a).max(part.previous_b)+Vector3.ONE*part.radius
			var flo:=current[0].min(current[1]).min(current[2]).min(old[0]).min(old[1]).min(old[2])
			var fhi:=current[0].max(current[1]).max(current[2]).max(old[0]).max(old[1]).max(old[2])
			if fhi.x<lo.x or flo.x>hi.x or fhi.y<lo.y or flo.y>hi.y or fhi.z<lo.z or flo.z>hi.z: continue
			var topology:=PackedInt32Array([0,1,2])
			var hit:Dictionary=kernel.query(part.a,part.b,part.radius,current,topology)
			var before:Dictionary=kernel.query(part.previous_a,part.previous_b,part.radius,old,topology)
			if not hit.valid or not before.valid:
				return {"valid":false,"positions":points.duplicate(),"contacts":0,"residual":0.,"uncertain":0}
			var witness:Vector3=hit.surface_point
			var witness_face:=current
			if not hit.hit:
				var swept:=_moving_hit(part,old,current)
				if not swept.valid: return {"valid":false,"positions":points.duplicate(),"contacts":0,"residual":0.,"uncertain":0}
				if swept.uncertain: out.uncertain+=1
				if not swept.hit: continue
				witness=swept.surface_point
				witness_face=swept.face
			# Keep the old side while this substep is being solved.
			var normal:Vector3=before.surface_point-before.axis_point
			if normal.length_squared()<1e-12:
				normal=(old[1]-old[0]).cross(old[2]-old[0])
				if normal.dot((old[0]+old[1]+old[2])/3.-(part.previous_a+part.previous_b)*.5)<0.: normal=-normal
			if normal.length_squared()<1e-16:
				out.uncertain+=1; out.residual=maxf(out.residual,part.radius); continue
			normal=normal.normalized()
			var weights:=_weights(witness,witness_face)
			if weights==Vector3.ZERO:
				out.uncertain+=1; out.residual=maxf(out.residual,part.radius); continue
			var surface:=Vector3.ZERO
			for i in range(3): surface+=out.positions[ids[i]]*weights[i]
			var axis:Vector3=Geometry3D.get_closest_point_to_segment(surface,part.a,part.b)
			var depth:float=part.radius-(surface-axis).dot(normal)
			if depth<=1e-7: continue
			out.contacts+=1
			var denominator:=0.; var largest:=0.
			for i in range(3):
				denominator+=masses[ids[i]]*weights[i]*weights[i]
				largest=maxf(largest,masses[ids[i]]*weights[i])
			if denominator<=1e-16: out.residual=maxf(out.residual,depth); continue
			var delta:float=minf(depth/denominator,max_correction/maxf(largest,1e-16))
			for i in range(3): out.positions[ids[i]]+=normal*(masses[ids[i]]*weights[i]*delta)
			out.residual=maxf(out.residual,maxf(0.,depth-denominator*delta))
	return out

## Relative distance is Lipschitz in the sum of maximum endpoint and vertex
## speeds. An inflated broadphase is never sufficient evidence for projection.
func _moving_hit(part:Dictionary,old:PackedVector3Array,current:PackedVector3Array)->Dictionary:
	var speed:float=maxf(part.previous_a.distance_to(part.a),part.previous_b.distance_to(part.b))
	var tissue_speed:=0.
	for i in range(3): tissue_speed=maxf(tissue_speed,old[i].distance_to(current[i]))
	speed+=tissue_speed
	var t:=0.
	for iteration in range(128):
		var face:=PackedVector3Array()
		for i in range(3): face.append(old[i].lerp(current[i],t))
		var hit:Dictionary=kernel.query(part.previous_a.lerp(part.a,t),part.previous_b.lerp(part.b,t),part.radius,face,PackedInt32Array([0,1,2]))
		if not hit.valid: return {"valid":false}
		if hit.hit: return {"valid":true,"hit":true,"uncertain":false,"surface_point":hit.surface_point,"face":face}
		var gap:float=hit.distance-part.radius
		if speed<1e-12 or gap>speed*(1.-t)+1e-7: return {"valid":true,"hit":false,"uncertain":false}
		var advance:float=.9*gap/speed
		if advance<1e-12: return {"valid":true,"hit":false,"uncertain":true}
		t+=advance
		if t>1.: return {"valid":true,"hit":false,"uncertain":false}
	return {"valid":true,"hit":false,"uncertain":true}

func _weights(p:Vector3,t:PackedVector3Array)->Vector3:
	var n:=(t[1]-t[0]).cross(t[2]-t[0])
	var omit:=n.abs().max_axis_index(); var i:=(omit+1)%3; var j:=(omit+2)%3
	var ux:float=float(t[1][i])-t[0][i]; var uy:float=float(t[1][j])-t[0][j]
	var vx:float=float(t[2][i])-t[0][i]; var vy:float=float(t[2][j])-t[0][j]
	var px:float=float(p[i])-t[0][i]; var py:float=float(p[j])-t[0][j]
	var area:float=ux*vy-uy*vx
	if area==0.: return Vector3.ZERO
	var b:float=(px*vy-py*vx)/area
	var c:float=(ux*py-uy*px)/area
	var result:=Vector3(maxf(0.,1.-b-c),maxf(0.,b),maxf(0.,c))
	return result/(result.x+result.y+result.z)
