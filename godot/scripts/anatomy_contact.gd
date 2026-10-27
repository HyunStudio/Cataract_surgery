extends RefCounted
## Stateful geometry selection, with no tissue or instrument mutation.
const EntryWindow=preload("res://scripts/incision_window.gd")
const Shapes=preload("res://scripts/anatomy_surfaces.gd")
const Kernel=preload("res://scripts/surface_contact.gd")
var geometry:RefCounted
var cornea:Dictionary=Shapes.cornea()
var posterior:Dictionary=Shapes.posterior()
var iris:Dictionary=Shapes.iris(.98)
var pupil:=.98
var _kernel=Kernel.new()
func set_pupil(radius:float)->void:
	if not is_finite(radius): return
	radius=clampf(radius,.45,1.1)
	if geometry or not is_equal_approx(pupil,radius): pupil=radius; iris=geometry.iris(radius) if geometry else Shapes.iris(radius)
func resolve(start:Vector3,target:Vector3,radius:float,tool:String,cutting:bool,capsule,wounds:Array,hand:=-1,elastic_anterior:=false)->Dictionary:
	var result:={"valid":true,"position":target,"contacts":[],"normal":Vector3.ZERO,"records":[]}
	if not start.is_finite() or not target.is_finite() or not is_finite(radius) or radius<=0. or radius>.5: result.valid=false; result.position=start if start.is_finite() else Vector3.ZERO; return result
	if start.distance_squared_to(target)<.00000000000001: return result
	var current:=start; var desired:=target
	var cap_triangles:PackedInt32Array=capsule.collision_triangles(hand) if hand>=0 and capsule is Object and capsule.has_method("collision_triangles") else capsule.triangles
	var surfaces:={"cornea":cornea,"iris":iris,"posterior":posterior,"capsule":{"positions":capsule.positions,"triangles":cap_triangles}}
	for attempt in range(4):
		var first:Dictionary={}; var label:=""
		for id in surfaces:
			if id=="capsule" and elastic_anterior: continue
			if id=="capsule" and tool=="knife" and cutting: continue
			var surface:Dictionary=surfaces[id]
			var ignore:=Callable()
			if id=="cornea": ignore=func(hit): return _corneal_window(hit.position if geometry else hit.surface_point,wounds,tool=="knife" and cutting,radius)
			var hit:Dictionary=_kernel.sweep(current,desired,radius,surface.positions,surface.triangles,ignore)
			if not hit.valid: result.valid=false; result.position=start; return result
			if hit.hit and (first.is_empty() or hit.time<first.time): first=hit; label=id
		if first.is_empty(): current=desired; break
		if label not in result.contacts: result.contacts.append(label)
		result.normal=first.normal
		var remaining:Vector3=desired-first.position
		result.records.append({"surface":label,"point":first.surface_point,"center":first.position,"normal":first.normal,"triangle":first.triangle,"revision":surfaces[label].get("revision",0),"load":maxf(0.,-remaining.dot(first.normal))})
		current=first.position+first.normal*.00001
		# Slide the remaining movement along the contacted surface, then recast.
		var into:float=remaining.dot(first.normal)
		if into<0.: remaining-=first.normal*into
		desired=current+remaining
		if remaining.length_squared()<.000000000001: break
	result.position=current
	return result
func _corneal_window(point:Vector3,wounds:Array,cutting:bool,radius:float)->bool:
	if cutting:
		for portal in (geometry.portals if geometry else [Vector3(1.44,.86,0),Vector3(-1.44,.86,.25)]):
			if point.distance_to(portal)<.34: return true
	if geometry: return EntryWindow.contains(point,wounds,radius,geometry.wound_radius,geometry.portals)
	for path in wounds:
		if not (path is Array or path is PackedVector3Array): continue
		for i in range(1,path.size()):
			if not path[i] is Vector3 or not path[i-1] is Vector3: continue
			if not path[i].is_finite() or not path[i-1].is_finite(): continue
			var closest:=Geometry3D.get_closest_point_to_segment(point,path[i-1],path[i])
			var distance:=Vector2(closest.x-point.x,closest.z-point.z).length() if geometry else closest.distance_to(point)
			if distance+radius<(geometry.wound_radius if geometry else .052): return true
	return false

func lens_access(tip:Vector3,capsule,radius:=.018)->bool:
	if not tip.is_finite(): return false
	var floor:float=-geometry.bag_half_thickness if geometry else .53
	if geometry:
		var r:=Vector2(tip.x,tip.z).length()
		if r<geometry.bag_radius and tip.y<geometry.bag_front(r)-radius and tip.y>geometry.bag_back(r)+radius: return true
	elif tip.y<=floor: return true
	var hit:Dictionary=_kernel.sweep(tip,Vector3(tip.x,floor,tip.z),radius,capsule.positions,capsule.triangles)
	return hit.valid and not hit.hit

func stationary(tip:Vector3,radius:float,wounds:Array=[])->Array:
	var records:Array=[]
	for id in ["cornea","posterior"]:
		var surface:Dictionary=cornea if id=="cornea" else posterior
		var ignore:=Callable()
		if id=="cornea": ignore=func(hit): return _corneal_window(hit.position if geometry else hit.surface_point,wounds,false,radius)
		var hit:Dictionary=_kernel.overlap(tip,radius,surface.positions,surface.triangles,ignore)
		if hit.valid and hit.hit:
			records.append({"surface":id,"point":hit.surface_point,"center":tip,"normal":hit.normal,"triangle":hit.triangle,"revision":surface.get("revision",0),"load":0.})
	return records
