extends RefCounted
## Uncalibrated local exposure and bounded mesh damage, not tissue failure calibration.
const Shapes=preload("res://scripts/anatomy_surfaces.gd")
const LIMIT:=8192
const CUT_RADIUS:=.04
var surfaces:Dictionary={}
var _closed_shell:=false
var _shell_samples:Array[Dictionary]=[]
var _removed_shell_samples:Array[Dictionary]=[]
var _corneal_through_area:=0.
var _carve_surface:=""
var events:Array[Dictionary]=[]
var _exposure:Dictionary={}
var _initial_area:Dictionary={}
var _open_area:Dictionary={}
var _limited:Dictionary={}
var _work_points:=PackedVector3Array()
var _kept:=PackedInt32Array()
var _midpoints:Dictionary={}
var _removed:=0.
var _ok:=true
func _init()->void: reset()
func reset(source:Dictionary={})->void:
	surfaces=source.duplicate(true) if not source.is_empty() else {"cornea":Shapes.cornea(),"posterior":Shapes.posterior()}; events=[]
	_closed_shell=surfaces.cornea.get("closed_shell",false); _shell_samples=[]; _corneal_through_area=0.
	_exposure={"cornea":{},"posterior":{}}; _initial_area={}; _open_area={"cornea":0.,"posterior":0.}; _limited={"cornea":false,"posterior":false}
	for id in surfaces:
		surfaces[id]["revision"]=0
		var data:Dictionary=surfaces[id]; var area:=0.
		for i in range(0,data.triangles.size(),3): area+=_area(data.positions[data.triangles[i]],data.positions[data.triangles[i+1]],data.positions[data.triangles[i+2]])
		_initial_area[id]=area
func step(dt:float,records:Array)->void:
	if not is_finite(dt) or dt<=0. or dt>.05 or records.size()>16: return
	var jobs:Array[Dictionary]=[]
	for record in records:
		if not record is Dictionary or not record.get("surface") is String: return
		var id:String=record.surface
		if id not in surfaces: continue
		if not record.get("point") is Vector3 or not record.point.is_finite() or record.point.length_squared()>256.: return
		for key in ["load","energy"]:
			var v=record.get(key)
			if not (v is float or v is int) or not is_finite(v) or v<0. or v>4.: return
		if not record.get("cutting") is bool or not record.get("tool") is String or not record.get("triangle") is int or not record.get("revision") is int: return
		if record.tool not in ["knife","forceps","cannula","phaco","ia","injector","manipulator"]: return
		if record.energy>1. or (record.energy>0. and record.tool!="phaco") or (record.cutting and record.tool!="knife"): return
		var data:Dictionary=surfaces[id]
		if record.revision!=data.revision: continue
		var offset:int=record.triangle*3
		if offset<0 or offset+2>=data.triangles.size(): return
		var a:int=data.triangles[offset]; var b:int=data.triangles[offset+1]; var c:int=data.triangles[offset+2]
		if _distance(record.point,data.positions[a],data.positions[b],data.positions[c])>.025: return
		var ordered:Array=[a,b,c]; ordered.sort()
		var key:="%d:%d:%d"%ordered
		var exposure:float=record.load*3.+record.energy*dt*2.5
		if id=="cornea": exposure*=.5
		if record.cutting and record.tool=="knife" and record.load>.00001: exposure=maxf(1.,exposure)
		jobs.append({"surface":id,"key":key,"point":record.point,"exposure":exposure})
	# Validation above resolves all face identities before either hand can revise topology.
	for job in jobs:
		if job.exposure<=0.: continue
		var id:String=job.surface
		_exposure[id][job.key]=float(_exposure[id].get(job.key,0.))+job.exposure
		if _exposure[id][job.key]>=1.: _carve(id,job.point)
func _carve(id:String,center:Vector3)->void:
	if _limited[id]: return
	var data:Dictionary=surfaces[id]
	_carve_surface=id; _removed_shell_samples=[]
	_work_points=data.positions.duplicate(); _kept=PackedInt32Array(); _midpoints={}; _removed=0.; _ok=true
	for i in range(0,data.triangles.size(),3):
		_refine(data.triangles[i],data.triangles[i+1],data.triangles[i+2],center,0)
		if not _ok: _limited[id]=true; return
	if _removed<=.00000001: return
	if _shell_samples.size()+_removed_shell_samples.size()>512: _limited[id]=true; return
	data.positions=_work_points; data.triangles=_kept; data.revision+=1
	if id=="cornea" and _closed_shell:
		_shell_samples.append_array(_removed_shell_samples); _measure_shell()
	_open_area[id]=minf(_initial_area[id],_open_area[id]+_removed)
	var retained:Dictionary={}
	for offset in range(0,_kept.size(),3):
		var vertices:Array=[_kept[offset],_kept[offset+1],_kept[offset+2]]; vertices.sort()
		var key:="%d:%d:%d"%vertices
		if _exposure[id].has(key): retained[key]=_exposure[id][key]
	_exposure[id]=retained
	if events.size()<512: events.append({"surface":id,"point":center,"area":_removed,"revision":data.revision})
func _keep(a:int,b:int,c:int)->void:
	if _kept.size()/3>=LIMIT: _ok=false; return
	_kept.append_array(PackedInt32Array([a,b,c]))
func _mid(a:int,b:int)->int:
	var key:=Vector2i(mini(a,b),maxi(a,b))
	if _midpoints.has(key): return _midpoints[key]
	if _work_points.size()>=LIMIT: _ok=false; return a
	var id:=_work_points.size(); _work_points.append((_work_points[a]+_work_points[b])*.5); _midpoints[key]=id
	return id
func _refine(a:int,b:int,c:int,center:Vector3,depth:int)->void:
	if not _ok: return
	var pa:=_work_points[a]; var pb:=_work_points[b]; var pc:=_work_points[c]
	if _distance(center,pa,pb,pc)>CUT_RADIUS: _keep(a,b,c); return
	var longest:=maxf(pa.distance_to(pb),maxf(pb.distance_to(pc),pc.distance_to(pa)))
	if longest<.018 or depth>=4:
		if center.distance_to((pa+pb+pc)/3.)<CUT_RADIUS:
			var area:=_area(pa,pb,pc); _removed+=area
			var normal:=(pb-pa).cross(pc-pa).normalized()
			if _closed_shell and _carve_surface=="cornea" and normal.y>.1:
				_removed_shell_samples.append({"point":(pa+pb+pc)/3.,"normal":normal,"area":area})
		else: _keep(a,b,c)
		return
	var ab:=_mid(a,b); var bc:=_mid(b,c); var ca:=_mid(c,a)
	_refine(a,ab,ca,center,depth+1); _refine(ab,b,bc,center,depth+1)
	_refine(ca,bc,c,center,depth+1); _refine(ab,bc,ca,center,depth+1)
static func _area(a:Vector3,b:Vector3,c:Vector3)->float:
	return (b-a).cross(c-a).length()*.5
static func _distance(p:Vector3,a:Vector3,b:Vector3,c:Vector3)->float:
	var normal:=(b-a).cross(c-a)
	if normal.length_squared()>.000000000001:
		normal=normal.normalized(); var projected:=p-normal*(p-a).dot(normal)
		var v0:=b-a; var v1:=c-a; var v2:=projected-a
		var d00:=v0.dot(v0); var d01:=v0.dot(v1); var d11:=v1.dot(v1)
		var denominator:=d00*d11-d01*d01
		if absf(denominator)>.00000000000001:
			var u:=(d11*v2.dot(v0)-d01*v2.dot(v1))/denominator
			var v:=(d00*v2.dot(v1)-d01*v2.dot(v0))/denominator
			if u>=0. and v>=0. and u+v<=1.: return p.distance_to(projected)
	var distance:=INF
	for edge in [[a,b],[b,c],[c,a]]: distance=minf(distance,p.distance_to(Geometry3D.get_closest_point_to_segment(p,edge[0],edge[1])))
	return distance
func _measure_shell()->void:
	_corneal_through_area=0.
	var data:Dictionary=surfaces.cornea
	for sample in _shell_samples:
		var opened:=false
		for direction in [sample.normal,Vector3.UP]:
			if not _shell_blocked(sample.point+direction*.35,sample.point-direction*.65,data): opened=true; break
		if opened: _corneal_through_area+=sample.area

func _shell_blocked(start:Vector3,finish:Vector3,data:Dictionary)->bool:
	var lo:=start.min(finish); var hi:=start.max(finish)
	for offset in range(0,data.triangles.size(),3):
		var a:Vector3=data.positions[data.triangles[offset]]; var b:Vector3=data.positions[data.triangles[offset+1]]; var c:Vector3=data.positions[data.triangles[offset+2]]
		var face_lo:=a.min(b).min(c); var face_hi:=a.max(b).max(c)
		if face_hi.x<lo.x or face_lo.x>hi.x or face_hi.y<lo.y or face_lo.y>hi.y or face_hi.z<lo.z or face_lo.z>hi.z: continue
		if Geometry3D.segment_intersects_triangle(start,finish,a,b,c)!=null: return true
	return false

func metrics()->Dictionary:
	var corneal_area:float=_corneal_through_area if _closed_shell else _open_area.cornea
	return {"finite":true,"topology_limited":_limited.cornea or _limited.posterior,"last_event":events[-1].duplicate(true) if not events.is_empty() else {},"posterior_open_area":_open_area.posterior,"corneal_open_area":corneal_area,"corneal_damage_area":_open_area.cornea,"posterior_integrity":clampf(1.-_open_area.posterior/_initial_area.posterior,0.,1.),"corneal_integrity":clampf(1.-_open_area.cornea/_initial_area.cornea,0.,1.),"posterior_breached":_open_area.posterior>.00000001,"corneal_breached":corneal_area>.00000001,"rupture_conductance":clampf(_open_area.posterior*8.,0.,1.),"corneal_conductance":clampf(corneal_area*8.,0.,1.)}
