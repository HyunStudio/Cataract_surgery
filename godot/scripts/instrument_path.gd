extends RefCounted
## Generic tool pose paths. Quaternion rotation preserves shaft length; each
## sampled interval is enclosed by a capsule with an explicit arc error bound.
const Profile=preload("res://scripts/instrument_profile.gd")
static func build(id:String,radius:float,tip0:Vector3,axis0:Vector3,grip0:bool,tip1:Vector3,axis1:Vector3,grip1:bool,cutting:bool,roll0:float=0.,roll1:float=0.)->Array:
	var out:Array=[]
	if not is_finite(roll0) or not is_finite(roll1):return out
	for axis in [axis0,axis1]:
		if not axis.is_finite() or not is_finite(axis.length_squared()) or axis.length_squared()<1e-12: return out
	if not tip0.is_finite() or not tip1.is_finite(): return out
	var old:Array=Profile.segments(id,radius,grip0); var current:Array=Profile.segments(id,radius,grip1)
	for i in range(current.size()):
		var part:Dictionary=current[i]
		if part.cutting and cutting: continue
		var route:={"tip0":tip0,"tip1":tip1,"rotation0":Profile.frame(axis0,roll0).get_rotation_quaternion(),"rotation1":Profile.frame(axis1,roll1).get_rotation_quaternion(),"a0":old[i].a,"b0":old[i].b,"a1":part.a,"b1":part.b}
		for endpoint in ["a","b"]:
			route["physical_"+endpoint+"0"]=old[i]["physical_"+endpoint]
			route["physical_"+endpoint+"1"]=part["physical_"+endpoint]
		var segment:Dictionary=part.duplicate(); segment["path"]=route
		var start:=sample(segment,0.); var finish:=sample(segment,1.)
		segment.a=finish.a; segment.b=finish.b; segment["previous_a"]=start.a; segment["previous_b"]=start.b
		var physical_start:=physical_sample(segment,0.); var physical_finish:=physical_sample(segment,1.)
		segment.physical_a=physical_finish.a; segment.physical_b=physical_finish.b
		segment["physical_previous_a"]=physical_start.a; segment["physical_previous_b"]=physical_start.b
		out.append(segment)
	return out

static func valid(part:Dictionary)->bool:
	var physical_keys:=["physical_a","physical_b","physical_previous_a","physical_previous_b"]
	var physical:=physical_keys.any(func(key):return part.has(key))
	if physical:
		if not part.has("path"): return false
		for key in physical_keys:
			if not _valid_physical_vector(part.get(key)): return false
	if part.has("physical_radius"):
		var enclosure=part.get("radius",0.)
		if not (enclosure is float or enclosure is int) or not is_finite(enclosure) or enclosure<=0.: return false
		if not (part.physical_radius is float or part.physical_radius is int) or not is_finite(part.physical_radius) or part.physical_radius<=0. or part.physical_radius>enclosure: return false
	if part.has("sweep_padding"):
		if not (part.sweep_padding is float or part.sweep_padding is int) or not is_finite(part.sweep_padding) or part.sweep_padding<0.: return false
	if not part.has("path"): return true
	for key in ["path_t0","path_t1"]:
		if part.has(key) and (not (part[key] is float or part[key] is int) or not is_finite(part[key])): return false
	if part.get("path_t0",0.)<0. or part.get("path_t1",1.)>1. or part.get("path_t0",0.)>=part.get("path_t1",1.): return false
	if not part.path is Dictionary: return false
	for key in ["tip0","tip1","a0","b0","a1","b1"]:
		if not part.path.get(key) is Vector3 or not part.path[key].is_finite() or part.path[key].length_squared()>256.: return false
	for key in ["rotation0","rotation1"]:
		if not part.path.get(key) is Quaternion or not part.path[key].is_finite() or not part.path[key].is_normalized(): return false
	var local_keys:=["physical_a0","physical_b0","physical_a1","physical_b1"]
	if physical or local_keys.any(func(key):return part.path.has(key)):
		for key in local_keys:
			if not _valid_physical_vector(part.path.get(key)): return false
	return true

static func _valid_physical_vector(value)->bool:
	if not value is PackedFloat64Array or value.size()!=3: return false
	for coordinate in value:
		if not is_finite(coordinate) or absf(coordinate)>16.: return false
	return true

static func _unit_rotation(rotation:Quaternion)->PackedFloat64Array:
	var out:=PackedFloat64Array([rotation.x,rotation.y,rotation.z,rotation.w])
	var squared:=0.
	for value in out: squared+=value*value
	var length:=sqrt(squared)
	for index in range(4): out[index]/=length
	return out

static func _physical_rotation(p:Dictionary,t:float)->PackedFloat64Array:
	var first:=_unit_rotation(p.rotation0); var last:=_unit_rotation(p.rotation1)
	var product:=0.
	for index in range(4): product+=first[index]*last[index]
	if product<0.:
		product=-product
		for index in range(4): last[index]=-last[index]
	var angle:=acos(clampf(product,0.,1.)); var out:=PackedFloat64Array(); out.resize(4)
	var squared:=0.
	for index in range(4):
		out[index]=first[index]+t*(last[index]-first[index]) if angle<1e-9 else (sin((1.-t)*angle)*first[index]+sin(t*angle)*last[index])/sin(angle)
		squared+=out[index]*out[index]
	var length:=sqrt(squared)
	for index in range(4): out[index]/=length
	return out

static func physical_sample(part:Dictionary,t:float)->Dictionary:
	if not part.has("path") or not part.path.has("physical_a0"):
		var legacy:=sample(part,t)
		return {"a":PackedFloat64Array([legacy.a.x,legacy.a.y,legacy.a.z]),"b":PackedFloat64Array([legacy.b.x,legacy.b.y,legacy.b.z])}
	var p:Dictionary=part.path; var rotation:=_physical_rotation(p,t); var out:={}
	for endpoint in ["a","b"]:
		var local0=p.get("physical_"+endpoint+"0",p[endpoint+"0"])
		var local1=p.get("physical_"+endpoint+"1",p[endpoint+"1"])
		var local:=PackedFloat64Array(); local.resize(3)
		for index in range(3): local[index]=float(local0[index])+t*(float(local1[index])-float(local0[index]))
		var x:float=rotation[0]; var y:float=rotation[1]; var z:float=rotation[2]; var w:float=rotation[3]
		var twice:=PackedFloat64Array([2.*(y*local[2]-z*local[1]),2.*(z*local[0]-x*local[2]),2.*(x*local[1]-y*local[0])])
		var rotated:=PackedFloat64Array([local[0]+w*twice[0]+y*twice[2]-z*twice[1],local[1]+w*twice[1]+z*twice[0]-x*twice[2],local[2]+w*twice[2]+x*twice[1]-y*twice[0]])
		for index in range(3): rotated[index]+=float(p.tip0[index])+t*(float(p.tip1[index])-float(p.tip0[index]))
		out[endpoint]=rotated
	return out

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
	if not valid(part): return {}
	var out:=part.duplicate(); var start:=sample(part,t0); var finish:=sample(part,t1)
	out.previous_a=start.a; out.previous_b=start.b; out.a=finish.a; out.b=finish.b
	# A temporal enclosure is deliberately wider than the physical endpoint
	# body. Keep its arc padding out of static unilateral force constraints.
	out.physical_radius=part.get("physical_radius",part.radius)
	out.sweep_padding=part.radius-out.physical_radius
	if part.has("path"):
		out.path_t0=t0; out.path_t1=t1
		var p:Dictionary=part.path
		if p.has("physical_a0"):
			var physical_start:=physical_sample(part,t0); var physical_finish:=physical_sample(part,t1)
			out.physical_a=physical_finish.a; out.physical_b=physical_finish.b
			out["physical_previous_a"]=physical_start.a; out["physical_previous_b"]=physical_start.b
		var angle:float=p.rotation0.angle_to(p.rotation1)*(t1-t0)
		var reach:float=maxf(maxf(p.a0.length(),p.a1.length()),maxf(p.b0.length(),p.b1.length()))
		var change:float=maxf(p.a0.distance_to(p.a1),p.b0.distance_to(p.b1))*(t1-t0)
		out.sweep_padding=reach*(1.-cos(angle*.5))+change*sin(angle*.5)
		out.radius=out.physical_radius+out.sweep_padding
	return out

static func motion_request(previous:PackedFloat64Array,current:PackedFloat64Array,faces:PackedInt32Array,body:Array)->Dictionary:
	var packets:=PackedFloat64Array(); var kinds:=PackedInt32Array()
	for part in body:
		var packet:=PackedFloat64Array(); packet.resize(41)
		var index:=0
		for point in [part.get("physical_previous_a",part.previous_a),part.get("physical_previous_b",part.previous_b),part.get("physical_a",part.a),part.get("physical_b",part.b)]:
			for axis in range(3): packet[index]=point[axis]; index+=1
		# Without a recorded pose, preserve any caller-supplied enclosure.
		packet[12]=part.radius
		kinds.append(1 if part.has("path") else 0)
		if part.has("path"):
			packet[12]=part.get("physical_radius",part.radius)
			var p:Dictionary=part.path
			index=13
			for point in [p.tip0,p.tip1]:
				for axis in range(3): packet[index]=point[axis]; index+=1
			for rotation in [p.rotation0,p.rotation1]:
				for value in [rotation.x,rotation.y,rotation.z,rotation.w]: packet[index]=value; index+=1
			for point in [p.get("physical_a0",p.a0),p.get("physical_b0",p.b0),p.get("physical_a1",p.a1),p.get("physical_b1",p.b1)]:
				for axis in range(3): packet[index]=point[axis]; index+=1
			packet[39]=part.get("path_t0",0.); packet[40]=part.get("path_t1",1.)
		packets.append_array(packet)
	return {"previous":previous,"current":current,"triangles":faces,"kinds":kinds,"packets":packets,"budget":128,"gap_tolerance":1e-9}
