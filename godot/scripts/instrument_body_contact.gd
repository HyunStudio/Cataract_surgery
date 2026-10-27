extends RefCounted
## Rigid generic-tool envelopes against actual indexed mesh surfaces. No masks,
## wounds, material changes, or elastic anterior-capsule handling live here.
const Profile=preload("res://scripts/instrument_profile.gd")
const Kernel=preload("res://scripts/capsule_surface.gd")
const CLEARANCE:=0.00001
const RIGID:=["cornea","iris","posterior"]
var kernel:=Kernel.new()

func resolve(from_tip:Vector3,from_axis:Vector3,to_tip:Vector3,to_axis:Vector3,tool:String,radius:float,grip:bool,surfaces:Dictionary)->Dictionary:
	var out:Dictionary={"valid":false,"tip":from_tip,"axis":from_axis,"fraction":0.,"contacts":[],"recovered":false,"reason":"invalid_input"}
	var body:Array[Dictionary]=Profile.segments(tool,radius,grip)
	if body.is_empty() or radius>1000000. or not _pose_valid(from_tip,from_axis) or not _pose_valid(to_tip,to_axis): return out
	var meshes:Dictionary={}
	for name in RIGID:
		if not surfaces.has(name): continue
		var data=surfaces[name]
		if not data is Dictionary: return out
		var points=data.get("positions",data.get("points",null))
		var triangles=data.get("triangles",data.get("indices",null))
		if not points is PackedVector3Array or not triangles is PackedInt32Array: return out
		var revision=data.get("revision",0)
		if not revision is int: return out
		var validation:Dictionary=kernel.query(from_tip,from_tip,radius,points,triangles)
		if not validation.valid: return out
		meshes[name]={"positions":points,"triangles":triangles,"revision":revision}
	out.valid=true; out.reason=""
	var start_frame:Basis=Profile.frame(from_axis)
	# An existing intersection must be repaired even when requested motion is zero.
	var recovered_tip:=from_tip
	for iteration in range(16):
		var correction:=Vector3.ZERO
		var deepest:=0.
		for name in meshes:
			var data:Dictionary=meshes[name]
			for part in body:
				var a:Vector3=recovered_tip+start_frame*part.a
				var b:Vector3=recovered_tip+start_frame*part.b
				var contact:Dictionary=kernel.query(a,b,part.radius,data.positions,data.triangles)
				if not contact.valid: out.valid=false; out.reason="invalid_geometry"; return out
				if not contact.hit: continue
				var n:Vector3=contact.normal
				var depth:float=part.radius-minf((a-contact.surface_point).dot(n),(b-contact.surface_point).dot(n))+CLEARANCE
				if depth>deepest:
					deepest=depth; correction=n*depth
					out.contacts=[_contact(name,part,contact,data.revision)]
		if deepest<=0.:
			if recovered_tip!=from_tip:
				out.tip=recovered_tip; out.axis=from_axis.normalized(); out.recovered=true; out.reason="overlap_recovered"
				return out
			break
		recovered_tip+=correction
		if iteration==15:
			out.valid=false; out.reason="overlap_unresolved"; return out
	var end_frame:Basis=Profile.frame(to_axis)
	var q0:=start_frame.get_rotation_quaternion()
	var q1:=end_frame.get_rotation_quaternion()
	var angle:=q0.angle_to(q1)
	var steps:=maxi(1,int(ceil(angle/.1)))
	var fraction:=1.
	var hits:Array=[]
	for step in range(steps):
		var t0:=float(step)/steps
		var t1:=float(step+1)/steps
		if t0>fraction: break
		var f0:=Basis(q0.slerp(q1,t0)); var f1:=Basis(q0.slerp(q1,t1))
		var p0:=from_tip.lerp(to_tip,t0); var p1:=from_tip.lerp(to_tip,t1)
		for part in body:
			# Enclose each off-axis endpoint in a centerline capsule. This also
			# covers world-up frame roll changes near vertical insertion axes.
			var local_a:=Vector3(part.a.x,0,0); var local_b:=Vector3(part.b.x,0,0)
			var radial:float=maxf(Vector2(part.a.y,part.a.z).length(),Vector2(part.b.y,part.b.z).length())
			# Every rotated endpoint arc lies within this sagitta of its chord.
			var sagitta:float=maxf(absf(part.a.x),absf(part.b.x))*(1.-cos(angle/(2.*steps)))
			for name in meshes:
				var data:Dictionary=meshes[name]
				var contact:Dictionary=kernel.sweep(p0+f0*local_a,p0+f0*local_b,p1+f1*local_a,p1+f1*local_b,part.radius+radial+sagitta,data.positions,data.triangles)
				if not contact.valid: out.valid=false; out.reason="invalid_geometry"; return out
				if not contact.hit: continue
				var time:float=lerpf(t0,t1,contact.time)
				if time<fraction-0.0000001:
					fraction=time; hits=[_contact(name,part,contact,data.revision)]
				elif absf(time-fraction)<0.0000001: hits.append(_contact(name,part,contact,data.revision))
	# Retreat a physical clearance from the conservative time of impact.
	if fraction<1.:
		var speed:float=from_tip.distance_to(to_tip)+3.1*angle
		fraction=maxf(0.,fraction-CLEARANCE/maxf(speed,CLEARANCE))
	out.fraction=fraction; out.tip=from_tip.lerp(to_tip,fraction)
	out.axis=-Basis(q0.slerp(q1,fraction)).x
	out.contacts=hits
	return out

func _pose_valid(tip:Vector3,axis:Vector3)->bool:
	return tip.is_finite() and maxf(absf(tip.x),maxf(absf(tip.y),absf(tip.z)))<999990. and axis.is_finite() and is_finite(axis.length_squared()) and axis.length_squared()>1.e-12

func _contact(surface:String,part:Dictionary,c:Dictionary,revision:int)->Dictionary:
	return {"surface":surface,"part":part.part,"point":c.surface_point,"triangle":c.triangle,"revision":revision,"cutting":part.cutting,"energy":part.energy,"normal":c.normal,"conservative":c.get("conservative",false)}
