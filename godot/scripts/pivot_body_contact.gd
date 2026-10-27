extends RefCounted
## Rigid generic envelopes following a signed portal and linear tip path.
## Never repairs overlap by translating a tool off its incision pivot.
const Profile=preload("res://scripts/instrument_profile.gd")
const Kernel=preload("res://scripts/capsule_surface.gd")
const SURFACES:=["cornea","iris","posterior"]
const CLEARANCE:=.00001
const MAX_TRIANGLE_VISITS:=200000
var kernel:=Kernel.new()
var use_index:=true
var _cache:Dictionary={}

func _prepare(name:String,data:Dictionary)->Dictionary:
	if _cache.has(name):
		var old:Dictionary=_cache[name]
		if old.positions==data.positions and old.triangles==data.triangles:
			old.revision=data.get("revision",0); return old
	var validation:Dictionary=kernel.query(Vector3.ZERO,Vector3.ZERO,.01,data.positions,data.triangles)
	if not validation.valid: return {}
	var lo:=Vector3(INF,INF,INF); var hi:=-lo
	for p in data.positions: lo=lo.min(p); hi=hi.max(p)
	var lower:Array[Vector3]=[]; var upper:Array[Vector3]=[]
	for offset in range(0,data.triangles.size(),3):
		var a:Vector3=data.positions[data.triangles[offset]]; var b:Vector3=data.positions[data.triangles[offset+1]]; var c:Vector3=data.positions[data.triangles[offset+2]]
		lower.append(a.min(b).min(c)); upper.append(a.max(b).max(c))
	var out:={"positions":data.positions.duplicate(),"triangles":data.triangles.duplicate(),"revision":data.get("revision",0),"lo":lo,"hi":hi,"lower":lower,"upper":upper}
	_cache[name]=out; return out

func _subset(data:Dictionary,a0:Vector3,b0:Vector3,a1:Vector3,b1:Vector3,radius:float)->Dictionary:
	if not use_index: return data
	var lo:=a0.min(b0).min(a1).min(b1)-Vector3.ONE*(radius+1e-7)
	var hi:=a0.max(b0).max(a1).max(b1)+Vector3.ONE*(radius+1e-7)
	var points:=PackedVector3Array(); var indices:=PackedInt32Array(); var sources:=PackedInt32Array()
	for face in range(data.lower.size()):
		var lower:Vector3=data.lower[face]; var upper:Vector3=data.upper[face]
		if upper.x<lo.x or lower.x>hi.x or upper.y<lo.y or lower.y>hi.y or upper.z<lo.z or lower.z>hi.z: continue
		sources.append(face)
		for j in range(3): indices.append(points.size()); points.append(data.positions[data.triangles[face*3+j]])
	return {"positions":points,"triangles":indices,"sources":sources,"revision":data.revision}

## Unit-vector normalization has |u''| <= 6 |v|^2 / min(|p-portal|)^2.
## The endpoint's linear-chord error is therefore <= max(|f''|)/8.
## Off-axis part radii are handled separately, independent of frame roll.
func interval(portal:Vector3,p0:Vector3,p1:Vector3,fallback:Vector3,side:float,reach:float,t0:float,t1:float)->Dictionary:
	var a:=p0.lerp(p1,t0); var b:=p0.lerp(p1,t1)
	var da:=a-portal; var db:=b-portal
	var closest:=Geometry3D.get_closest_point_to_segment(portal,a,b)
	var minimum:float=closest.distance_to(portal)
	var error:=0.
	if minimum==0.:
		var spread:=0.
		for d in [da,db]:
			if d!=Vector3.ZERO: spread=maxf(spread,d.normalized().distance_to(fallback*side))
		if spread>1e-6 or da.dot(db)<0.: return {"valid":false}
		error=2.*reach*spread
	else: error=.75*reach*a.distance_squared_to(b)/(minimum*minimum)
	var ua:Vector3=da.normalized()*side if da!=Vector3.ZERO else fallback
	var ub:Vector3=db.normalized()*side if db!=Vector3.ZERO else fallback
	return {"valid":true,"a":a-ua*reach,"b":b-ub*reach,"error":error}

func resolve(portal:Vector3,start:Vector3,axis0:Vector3,finish:Vector3,axis1:Vector3,tool:String,radius:float,grip:bool,surfaces:Dictionary,previous_grip=null)->Dictionary:
	var out:={"valid":false,"tip":start,"axis":axis0,"fraction":0.,"contacts":[],"reason":"invalid_input"}
	for p in [portal,start,finish,axis0,axis1]:
		if not p.is_finite() or p.length_squared()>256.: return out
	if absf(portal.x)<1e-6 or axis0.length_squared()<1e-12 or axis1.length_squared()<1e-12 or not is_finite(radius) or radius<=0. or radius>.3: return out
	axis0=axis0.normalized(); axis1=axis1.normalized()
	var inward:=Vector3(-signf(portal.x),0,0)
	if axis0.dot(inward)<.28-1e-6 or axis1.dot(inward)<.28-1e-6: return out
	var d0:=start-portal; var d1:=finish-portal
	if (d0!=Vector3.ZERO and d0.normalized().cross(axis0).length()>1e-6) or (d1!=Vector3.ZERO and d1.normalized().cross(axis1).length()>1e-6): return out
	var side:=signf(d0.dot(axis0)) if d0!=Vector3.ZERO else signf(d1.dot(axis1))
	if side==0.: side=1.
	if d0.dot(axis0)*side<0. or d1.dot(axis1)*side<0.: return out
	for d in [d0,d1]:
		if d!=Vector3.ZERO and (d.normalized()*side).dot(inward)<.28-1e-6: return out
	var parts:=Profile.segments(tool,radius,grip)
	if parts.is_empty(): return out
	if previous_grip!=null and not previous_grip is bool: return out
	var old_parts:=Profile.segments(tool,radius,grip if previous_grip==null else previous_grip)
	var meshes:={}
	var triangles:=0; var vertices:=0
	for name in SURFACES:
		if not surfaces.has(name): continue
		var data=surfaces[name]
		if not data is Dictionary or not data.get("positions") is PackedVector3Array or not data.get("triangles") is PackedInt32Array or not data.get("revision",0) is int: return out
		triangles+=data.triangles.size()/3; vertices+=data.positions.size()
		if triangles>20000 or vertices>24000: out.reason="geometry_budget"; return out
		var prepared:=_prepare(name,data)
		if prepared.is_empty(): return out
		meshes[name]=prepared
	out.valid=true; out.reason=""
	if meshes.is_empty(): out.tip=finish; out.axis=axis1; out.fraction=1.; return out
	var steps:=maxi(1,ceili(axis0.angle_to(axis1)/.05))
	if steps>64: out.valid=false; out.reason="path_budget"; return out
	var query_visits:=0
	var fraction:=1.; var contacts:Array=[]
	for step in range(steps):
		var t0:=float(step)/steps; var t1:=float(step+1)/steps
		if t0>fraction: break
		for part_index in range(parts.size()):
			var part:Dictionary=parts[part_index]; var old_part:Dictionary=old_parts[part_index]
			var radial:float=maxf(maxf(Vector2(part.a.y,part.a.z).length(),Vector2(part.b.y,part.b.z).length()),maxf(Vector2(old_part.a.y,old_part.a.z).length(),Vector2(old_part.b.y,old_part.b.z).length()))
			var reach:float=maxf(part.a.x,part.b.x)
			var padding:float=part.radius+radial
			var lo:Vector3=start.min(finish)-Vector3.ONE*(reach+padding)
			var hi:Vector3=start.max(finish)+Vector3.ONE*(reach+padding)
			# Every valid inward axis has an outward handle component >= .28.
			# This halfspace also certifies external rotation at zero insertion.
			if portal.x>0.: lo.x=minf(start.x,finish.x)+minf(part.a.x,part.b.x)*(.28-1e-6)-padding
			else: hi.x=maxf(start.x,finish.x)-minf(part.a.x,part.b.x)*(.28-1e-6)+padding
			var nearby:Array=[]
			for name in meshes:
				var m:Dictionary=meshes[name]
				if m.hi.x<lo.x or m.lo.x>hi.x or m.hi.y<lo.y or m.lo.y>hi.y or m.hi.z<lo.z or m.lo.z>hi.z: continue
				nearby.append(name)
			if nearby.is_empty(): continue
			var ia:=interval(portal,start,finish,axis0,side,part.a.x,t0,t1)
			var ib:=interval(portal,start,finish,axis0,side,part.b.x,t0,t1)
			if not ia.valid or not ib.valid: out.valid=false; out.reason="pivot_rotation_unresolved"; return out
			var envelope:float=part.radius+radial+maxf(ia.error,ib.error)
			for name in nearby:
				var data:=_subset(meshes[name],ia.a,ib.a,ia.b,ib.b,envelope)
				if data.triangles.is_empty(): continue
				query_visits+=data.triangles.size()/3*4
				if query_visits>MAX_TRIANGLE_VISITS: out.valid=false; out.reason="query_budget"; return out
				# Sweep recovery exemptions cannot certify a curved path starting
				# inside an inflated envelope. Report that interval as blocked.
				var hit:Dictionary=kernel.query(ia.a,ib.a,envelope,data.positions,data.triangles)
				if not hit.valid: out.valid=false; out.reason="invalid_geometry"; return out
				if hit.hit:
					hit["time"]=0.; hit["conservative"]=true
				else: hit=kernel.sweep(ia.a,ib.a,ia.b,ib.b,envelope,data.positions,data.triangles)
				if not hit.valid: out.valid=false; out.reason="invalid_geometry"; return out
				if not hit.hit: continue
				if hit.triangle<0:
					out.valid=false; out.reason=hit.get("reason","missing_witness"); return out
				var time:float=lerpf(t0,t1,hit.time)
				# An inflated chord proves blocking, not tissue contact. Confirm
				# the nominal part at that time before publishing an injury witness.
				var tip_at:=start.lerp(finish,time); var delta_at:=tip_at-portal
				var axis_at:=delta_at.normalized()*side if delta_at!=Vector3.ZERO else axis0
				var frame_at:=Profile.frame(axis_at)
				var part_a:Vector3=old_part.a.lerp(part.a,time); var part_b:Vector3=old_part.b.lerp(part.b,time)
				var actual:Dictionary=kernel.query(tip_at+frame_at*part_a,tip_at+frame_at*part_b,part.radius,data.positions,data.triangles)
				if not actual.valid: out.valid=false; out.reason="invalid_geometry"; return out
				if actual.hit and not actual.get("conservative",false): hit=actual; hit["conservative"]=false
				else: hit["conservative"]=true
				if data.has("sources"): hit.triangle=data.sources[hit.triangle]
				var record:={"surface":name,"part":part.part,"point":hit.surface_point,"normal":hit.normal,"triangle":hit.triangle,"revision":data.get("revision",0),"cutting":part.cutting,"energy":part.energy,"conservative":hit.get("conservative",false),"load":0.}
				if not record.conservative:
					var local_point:Vector3=frame_at.inverse()*(actual.axis_point-tip_at)
					var local_segment:=part_b-part_a
					var along:float=clampf((local_point-part_a).dot(local_segment)/maxf(local_segment.length_squared(),1e-20),0.,1.)
					var old_local:Vector3=old_part.a.lerp(old_part.b,along); var new_local:Vector3=part.a.lerp(part.b,along)
					var witness_motion:Vector3=(finish+Profile.frame(axis1)*new_local)-(start+Profile.frame(axis0)*old_local)
					record.load=maxf(0.,-witness_motion.dot(record.normal))*(1.-time)
				if time<fraction-1e-7: fraction=time; contacts=[record]
				elif absf(time-fraction)<1e-7: contacts.append(record)
	if fraction<1.: fraction=maxf(0.,fraction-CLEARANCE/maxf(start.distance_to(finish),CLEARANCE))
	out.fraction=fraction; out.tip=start.lerp(finish,fraction)
	var delta:Vector3=out.tip-portal
	out.axis=delta.normalized()*side if delta!=Vector3.ZERO else axis0
	out.contacts=contacts
	return out
