extends RefCounted
## Generic tool pose paths. Quaternion rotation preserves shaft length; each
## sampled interval is enclosed by a capsule with an explicit arc error bound.
const Profile=preload("res://scripts/instrument_profile.gd")
static func build(id:String,radius:float,tip0:Vector3,axis0:Vector3,grip0:bool,tip1:Vector3,axis1:Vector3,grip1:bool,cutting:bool)->Array:
	var out:Array=[]
	for axis in [axis0,axis1]:
		if not axis.is_finite() or not is_finite(axis.length_squared()) or axis.length_squared()<1e-12: return out
	if not tip0.is_finite() or not tip1.is_finite(): return out
	var old:Array=Profile.segments(id,radius,grip0); var current:Array=Profile.segments(id,radius,grip1)
	for i in range(current.size()):
		var part:Dictionary=current[i]
		if part.cutting and cutting: continue
		var route:={"tip0":tip0,"tip1":tip1,"rotation0":Profile.frame(axis0).get_rotation_quaternion(),"rotation1":Profile.frame(axis1).get_rotation_quaternion(),"a0":old[i].a,"b0":old[i].b,"a1":part.a,"b1":part.b}
		var segment:Dictionary=part.duplicate(); segment["path"]=route
		var start:=sample(segment,0.); var finish:=sample(segment,1.)
		segment.a=finish.a; segment.b=finish.b; segment["previous_a"]=start.a; segment["previous_b"]=start.b
		out.append(segment)
	return out

static func valid(part:Dictionary)->bool:
	if part.has("physical_radius"):
		var enclosure=part.get("radius",0.)
		if not (enclosure is float or enclosure is int) or not is_finite(enclosure) or enclosure<=0.: return false
		if not (part.physical_radius is float or part.physical_radius is int) or not is_finite(part.physical_radius) or part.physical_radius<=0. or part.physical_radius>enclosure: return false
	if part.has("sweep_padding"):
		if not (part.sweep_padding is float or part.sweep_padding is int) or not is_finite(part.sweep_padding) or part.sweep_padding<0.: return false
	if not part.has("path"): return true
	if not part.path is Dictionary: return false
	for key in ["tip0","tip1","a0","b0","a1","b1"]:
		if not part.path.get(key) is Vector3 or not part.path[key].is_finite() or part.path[key].length_squared()>256.: return false
	for key in ["rotation0","rotation1"]:
		if not part.path.get(key) is Quaternion or not part.path[key].is_finite() or not part.path[key].is_normalized(): return false
	return true

static func sample(part:Dictionary,t:float)->Dictionary:
	if not part.has("path"): return {"a":part.previous_a.lerp(part.a,t),"b":part.previous_b.lerp(part.b,t)}
	var p:Dictionary=part.path
	var frame:=Basis(p.rotation0.slerp(p.rotation1,t))
	var tip:Vector3=p.tip0.lerp(p.tip1,t)
	return {"a":tip+frame*p.a0.lerp(p.a1,t),"b":tip+frame*p.b0.lerp(p.b1,t)}

static func steps(body:Array)->int:
	var count:=1
	for part in body:
		if part.has("path"): count=maxi(count,ceili(part.path.rotation0.angle_to(part.path.rotation1)/.1))
	return count

static func interval(part:Dictionary,t0:float,t1:float)->Dictionary:
	var out:=part.duplicate(); var start:=sample(part,t0); var finish:=sample(part,t1)
	out.previous_a=start.a; out.previous_b=start.b; out.a=finish.a; out.b=finish.b
	# A temporal enclosure is deliberately wider than the physical endpoint
	# body. Keep its arc padding out of static unilateral force constraints.
	out.physical_radius=part.get("physical_radius",part.radius)
	out.sweep_padding=part.radius-out.physical_radius
	if part.has("path"):
		var p:Dictionary=part.path
		var angle:float=p.rotation0.angle_to(p.rotation1)*(t1-t0)
		var reach:float=maxf(maxf(p.a0.length(),p.a1.length()),maxf(p.b0.length(),p.b1.length()))
		var change:float=maxf(p.a0.distance_to(p.a1),p.b0.distance_to(p.b1))*(t1-t0)
		out.sweep_padding=reach*(1.-cos(angle*.5))+change*sin(angle*.5)
		out.radius=out.physical_radius+out.sweep_padding
	return out
