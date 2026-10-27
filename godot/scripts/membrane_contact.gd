extends RefCounted
## Bounded discrete face projection, not calibrated continuum mechanics.
## Previous-side swept candidates prevent a fast translating shaft from merely
## appearing on the opposite side. Unsatisfied constraints remain explicit.
const Kernel=preload("res://scripts/capsule_surface.gd")
const Path=preload("res://scripts/instrument_path.gd")
var kernel:=Kernel.new()
var _previous_linearization:=false
func begin_substep(previous_linearization:bool=true)->void:
	# The experimental global XPBD backend uses a semi-implicit contact frame.
	# Recompute it from the new physical substep's previous geometry, never
	# change its gradient during the inner elastic/contact iterations.
	_previous_linearization=previous_linearization
func valid_body(body:Array)->bool:
	if body.size()>64: return false
	for part in body:
		if not part is Dictionary: return false
		if not Path.valid(part): return false
		if part.has("attachment") and (not part.attachment is int or part.attachment<0 or part.get("part","")!="jaw"): return false
		for key in ["a","b","previous_a","previous_b"]:
			if not part.get(key) is Vector3 or not part[key].is_finite() or part[key].length_squared()>256.: return false
		if not (part.get("radius") is float or part.get("radius") is int) or not is_finite(part.radius) or part.radius<=0. or part.radius>.3: return false
	return true

func project(points:PackedVector3Array,faces:PackedInt32Array,masses:PackedFloat64Array,body:Array,previous:PackedVector3Array,max_correction:float=.04)->Dictionary:
	var out:={"valid":false,"positions":points.duplicate(),"contacts":0,"residual":0.,"uncertain":0}
	if not valid_body(body) or masses.size()!=points.size() or previous.size()!=points.size() or faces.size()%3!=0 or not is_finite(max_correction) or max_correction<=0. or max_correction>1.: return out
	var mesh_lo:=Vector3(INF,INF,INF); var mesh_hi:=Vector3(-INF,-INF,-INF)
	for i in range(points.size()):
		if not points[i].is_finite() or points[i].length_squared()>256. or not previous[i].is_finite() or previous[i].length_squared()>256. or not is_finite(masses[i]) or masses[i]<0. or masses[i]>1e12: return out
		mesh_lo=mesh_lo.min(points[i]).min(previous[i]); mesh_hi=mesh_hi.max(points[i]).max(previous[i])
	for id in faces:
		if id<0 or id>=points.size(): return out
	for part in body:
		if part.has("attachment") and (part.attachment>=points.size() or masses[part.attachment]!=0.): return out
	out.valid=true
	# A vertex is kept within this total displacement budget for the entire
	# projection pass, so it cannot create contacts beyond these padded bounds.
	mesh_lo-=Vector3.ONE*max_correction; mesh_hi+=Vector3.ONE*max_correction
	var lower:Array[Vector3]=[]; var upper:Array[Vector3]=[]
	var active:Array=[]
	var constraints:Array=[]
	for part in body:
		var lo:Vector3=part.a.min(part.b).min(part.previous_a).min(part.previous_b)-Vector3.ONE*part.radius
		var hi:Vector3=part.a.max(part.b).max(part.previous_a).max(part.previous_b)+Vector3.ONE*part.radius
		if mesh_hi.x<lo.x or mesh_lo.x>hi.x or mesh_hi.y<lo.y or mesh_lo.y>hi.y or mesh_hi.z<lo.z or mesh_lo.z>hi.z: continue
		active.append(part); lower.append(lo); upper.append(hi)
	if active.is_empty(): return out
	for off in range(0,faces.size(),3):
		var ids:=PackedInt32Array([faces[off],faces[off+1],faces[off+2]])
		var oa:=previous[ids[0]]; var ob:=previous[ids[1]]; var oc:=previous[ids[2]]
		var old_lo:=oa.min(ob).min(oc); var old_hi:=oa.max(ob).max(oc)
		for part_index in range(active.size()):
			var lo:=lower[part_index]; var hi:=upper[part_index]
			var ca:Vector3=out.positions[ids[0]]; var cb:Vector3=out.positions[ids[1]]; var cc:Vector3=out.positions[ids[2]]
			var flo:=ca.min(cb).min(cc).min(old_lo)
			var fhi:=ca.max(cb).max(cc).max(old_hi)
			if fhi.x<lo.x or flo.x>hi.x or fhi.y<lo.y or flo.y>hi.y or fhi.z<lo.z or flo.z>hi.z: continue
			var part:Dictionary=active[part_index]
			var current:=PackedVector3Array([ca,cb,cc])
			var old:=PackedVector3Array([oa,ob,oc])
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
			# Follow the current nearest features as the membrane deforms. The
			# previous normal selects the retained material side, not a frozen
			# correction direction after a face has tilted.
			if hit.hit and not _previous_linearization:
				var separating:Vector3=hit.surface_point-hit.axis_point
				# Flipping an endpoint radial normal can turn it inward along
				# the finite shaft. A crossing retains its previous direction.
				if separating.length_squared()>1e-16 and separating.dot(normal)>0.:
					normal=separating.normalized()
			var weights:=_weights(witness,witness_face)
			if weights==Vector3.ZERO:
				out.uncertain+=1; out.residual=maxf(out.residual,part.radius); continue
			var attachment:int=part.get("attachment",-1)
			var local_attachment:int=ids.find(attachment)
			if local_attachment>=0 and witness.distance_to(witness_face[local_attachment])<=maxf(.025,part.radius*2.): continue
			var surface:=Vector3.ZERO
			for i in range(3): surface+=out.positions[ids[i]]*weights[i]
			# This supporting plane remains valid for the whole finite capsule,
			# including when a corrected witness changes its nearest axis feature.
			var axis:Vector3=part.a if part.a.dot(normal)>=part.b.dot(normal) else part.b
			constraints.append([ids,weights,normal,axis,part.radius])
			var depth:float=part.radius-(surface-axis).dot(normal)
			if depth<=1e-7: continue
			out.contacts+=1
			var denominator:=0.; var largest:=0.
			for i in range(3):
				denominator+=masses[ids[i]]*weights[i]*weights[i]
				largest=maxf(largest,masses[ids[i]]*weights[i])
			if denominator<=1e-16: out.residual=maxf(out.residual,depth); continue
			var delta:float=minf(depth/denominator,max_correction/maxf(largest,1e-16))
			var achieved:=0.
			for i in range(3):
				var id:=ids[i]; var original:Vector3=out.positions[id]
				var desired:Vector3=original+normal*(masses[id]*weights[i]*delta)
				out.positions[id]=points[id]+(desired-points[id]).limit_length(max_correction)
				achieved+=(out.positions[id]-original).dot(normal)*weights[i]
			out.residual=maxf(out.residual,maxf(0.,depth-achieved))
	# Later faces/parts can undo an earlier contact correction. Re-evaluate
	# every activated supporting plane against the final published positions;
	# per-correction achievement alone is not the final contact residual.
	for constraint in constraints:
		var ids:PackedInt32Array=constraint[0]; var weights:Vector3=constraint[1]
		var surface:=Vector3.ZERO
		for i in range(3): surface+=out.positions[ids[i]]*weights[i]
		out.residual=maxf(out.residual,maxf(0.,constraint[4]-(surface-constraint[3]).dot(constraint[2])))
	return out

func _relative_point(p0:Vector3,p1:Vector3,a0:Vector3,a1:Vector3,t:float)->Vector3:
	var out:=Vector3.ZERO
	for axis in range(3): out[axis]=lerpf(float(p0[axis])-a0[axis],float(p1[axis])-a1[axis],t)
	return out

## Every linear endpoint trajectory lies in the convex hull of its interval
## endpoints. A separating projection of those two hulls certifies the entire
## interval. Scalar doubles retain small gaps in translated float32 scenes.
func _interval_separated(part:Dictionary,old:PackedVector3Array,current:PackedVector3Array,lo:float,hi:float,query:Dictionary)->bool:
	var n:=PackedFloat64Array(); var squared:=0.
	for axis in range(3):
		var value:float=float(query.axis_point[axis])-query.surface_point[axis]
		n.append(value); squared+=value*value
	if not is_finite(squared) or squared<=0.: return false
	var length:=sqrt(squared)
	for axis in range(3): n[axis]/=length
	var body_lo:=0.; var body_hi:=0.; var face_lo:=INF; var face_hi:=-INF; var scale:=1.
	for t in [lo,hi]:
		var projection:=0.
		for axis in range(3):
			var value:float=lerpf(float(part.previous_b[axis])-part.previous_a[axis],float(part.b[axis])-part.a[axis],t)
			projection+=n[axis]*value; scale=maxf(scale,absf(value))
		body_lo=minf(body_lo,projection); body_hi=maxf(body_hi,projection)
		for vertex in range(3):
			projection=0.
			for axis in range(3):
				var value:float=lerpf(float(old[vertex][axis])-part.previous_a[axis],float(current[vertex][axis])-part.a[axis],t)
				projection+=n[axis]*value; scale=maxf(scale,absf(value))
			face_lo=minf(face_lo,projection); face_hi=maxf(face_hi,projection)
	var gap:=maxf(body_lo-face_hi,face_lo-body_hi)
	return gap>part.radius+Kernel.CONTACT_EPS+1e-12*scale

## Return a verified sampled contact, or clear only when every time interval
## has a whole-hull separation certificate. This is not an exact impact time.
func _moving_hit(part:Dictionary,old:PackedVector3Array,current:PackedVector3Array,max_queries:int=128)->Dictionary:
	if max_queries<1 or max_queries>128: return {"valid":false,"hit":false,"uncertain":true,"evaluations":0}
	var pending:Array=[[0.,1.,0]]; var evaluations:=0
	while not pending.is_empty():
		if evaluations>=max_queries: return {"valid":true,"hit":false,"uncertain":true,"evaluations":evaluations}
		var interval:Array=pending.pop_back(); var lo:float=interval[0]; var hi:float=interval[1]; var depth:int=interval[2]
		var t:float=(lo+hi)*.5
		var face:=PackedVector3Array()
		for i in range(3): face.append(_relative_point(old[i],current[i],part.previous_a,part.a,t))
		var end:=_relative_point(part.previous_b,part.b,part.previous_a,part.a,t)
		var hit:Dictionary=kernel.query(Vector3.ZERO,end,part.radius,face,PackedInt32Array([0,1,2]))
		evaluations+=1
		if not hit.valid: return {"valid":false,"evaluations":evaluations}
		if hit.hit:
			var world_face:=PackedVector3Array(); var witness:=Vector3.ZERO
			for i in range(3): world_face.append(old[i].lerp(current[i],t))
			for axis in range(3): witness[axis]=lerpf(part.previous_a[axis],part.a[axis],t)+hit.surface_point[axis]
			return {"valid":true,"hit":true,"uncertain":false,"surface_point":witness,"face":world_face,"evaluations":evaluations}
		if _interval_separated(part,old,current,lo,hi,hit): continue
		if depth>=32 or t<=lo or t>=hi: return {"valid":true,"hit":false,"uncertain":true,"evaluations":evaluations}
		pending.append([t,hi,depth+1]); pending.append([lo,t,depth+1])
	return {"valid":true,"hit":false,"uncertain":false,"evaluations":evaluations}

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
