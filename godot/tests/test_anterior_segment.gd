extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func _initialize()->void: call_deferred("run")
func run()->void:
	check(FileAccess.file_exists("res://scripts/anterior_segment.gd"),"shared dimensioned anterior segment exists")
	if failures: quit(1); return
	var shape=load("res://scripts/anterior_segment.gd").new()
	check(absf(shape.lens_radius*2./shape.units_per_mm-9.2)<.001,"representative lens diameter uses explicit millimetre scale")
	check(absf(shape.lens_half_thickness*2./shape.units_per_mm-4.2)<.001,"lens has realistic volumetric aspect ratio instead of flat layers")
	check(absf((shape.cornea_inner(0.)-shape.bag_front(0.))/shape.units_per_mm-3.)<.001,"central anterior chamber clearance is explicit")
	for surface in [shape.cornea(),shape.posterior(),shape.iris(shape.pupil_radius(false))]:
		check(surface.positions.size()>50 and surface.triangles.size()>100,"dimensioned anatomy generates shared indexed surfaces")
		for p in surface.positions: check(p.is_finite(),"anatomical coordinates are finite")
		for id in surface.triangles: check(id>=0 and id<surface.positions.size(),"anatomical indices remain valid")
	var shell:Dictionary=shape.cornea()
	var edge_uses:Dictionary={}
	for i in range(0,shell.triangles.size(),3):
		var face:=Vector3i(shell.triangles[i],shell.triangles[i+1],shell.triangles[i+2])
		for pair in [Vector2i(face.x,face.y),Vector2i(face.y,face.z),Vector2i(face.z,face.x)]:
			var key:=Vector2i(mini(pair.x,pair.y),maxi(pair.x,pair.y))
			edge_uses[key]=int(edge_uses.get(key,0))+1
	for count in edge_uses.values(): check(count==2,"corneal inner/outer shell and rim are closed without boundary edges")
	var app=load("res://scripts/simulator.gd").new(); root.add_child(app); app.set_physics_process(false)
	await process_frame
	var lo:=INF; var hi:=-INF; var radius:=0.
	for p in app.lens.particles:
		lo=minf(lo,p.position.y); hi=maxf(hi,p.position.y)
		radius=maxf(radius,Vector2(p.position.x,p.position.z).length())
	check(absf((hi-lo)/shape.units_per_mm-4.2)<.02,"default running numerical lens has actual volumetric thickness")
	check(absf(radius*2./shape.units_per_mm-9.2)<.02,"default numerical lens has actual dimensioned radius")
	for p in app.lens.particles:
		var r:=Vector2(p.position.x,p.position.z).length()
		check(p.position.y<shape.bag_front(r) and p.position.y>shape.bag_back(r),"every rest particle is enclosed by the actual bag")
	var posterior:Dictionary=app.injury.surfaces.posterior
	var enclosed:=true
	for p in app.lens.particles:
		var upper:=height_at({"positions":app.capsule.positions,"triangles":app.capsule.triangles},p.position.x,p.position.z)
		var lower:=height_at(posterior,p.position.x,p.position.z)
		enclosed=enclosed and is_finite(upper) and is_finite(lower) and p.position.y<upper and p.position.y>lower
	check(enclosed,"all rest particles are enclosed by actual indexed bag faces, not just analytic profiles")
	var same_rim:=true
	for i in range(36):
		var a:Vector3=app.capsule.positions[app.capsule.positions.size()-36+i]
		var b:Vector3=posterior.positions[posterior.positions.size()-36+i]
		same_rim=same_rim and a.distance_to(b)<.00001
	check(same_rim,"anterior and posterior bag share the same equatorial ring")
	var coordinator=load("res://scripts/anatomy_contact.gd").new()
	coordinator.geometry=shape; coordinator.cornea=shape.cornea(); coordinator.posterior=shape.posterior(); coordinator.set_pupil(.96)
	var empty_cap:={"positions":PackedVector3Array(),"triangles":PackedInt32Array()}
	var wounds:=[[Vector3(1.32,.80,-.25),Vector3(1.32,.80,.25)]]
	var passage:Dictionary=coordinator.resolve(Vector3(1.32,.52,0),Vector3(1.32,.95,0),.07,"injector",false,empty_cap,wounds)
	check(not "cornea" in passage.contacts,"full-radius instrument fits the cylindrical wound through both sloped corneal surfaces")
	passage=coordinator.resolve(Vector3(1.36,.52,0),Vector3(1.36,.95,0),.07,"injector",false,empty_cap,wounds)
	check("cornea" in passage.contacts,"instrument footprint cannot overrun the dimensioned wound edge")
	app.start_practice(); app.choose_tool("phaco"); app._set_tip(0,Vector3(0,.20,0)); app.update_geometry()
	var model:Node3D=app.display.tool_models[0]["phaco"]
	var handle:Node3D=model.find_child("Handpiece",true,false)
	check(handle!=null and Vector2(handle.global_position.x,handle.global_position.z).length()>1.5,"handpiece body stays outside the operative eye field")
	check(app.tool_models==app.display.tool_models,"app tool references follow rebuilt dimensioned models")
	check(shape.has_method("tip_radius"),"dimensioned tools expose their actual contact radius")
	if DisplayServer.get_name()!="headless":
		app.start_practice(); app.update_geometry()
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/volumetric-anatomy.png")
		app.world.microscope.position=Vector3(2.4,3.8,2.4)
		app.world.microscope.look_at(Vector3(0,.35,0))
		await process_frame; await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://reports/volumetric-depth.png")
	app.queue_free(); await process_frame
	print("Anterior segment: ",failures," failures"); quit(1 if failures else 0)

func height_at(data:Dictionary,x:float,z:float)->float:
	# Independent vertical barycentric interpolation of actual indexed faces.
	for i in range(0,data.triangles.size(),3):
		var a:Vector3=data.positions[data.triangles[i]]; var b:Vector3=data.positions[data.triangles[i+1]]; var c:Vector3=data.positions[data.triangles[i+2]]
		var denominator:float=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z)
		if absf(denominator)<1e-12: continue
		var u:float=((b.z-c.z)*(x-c.x)+(c.x-b.x)*(z-c.z))/denominator
		var v:float=((c.z-a.z)*(x-c.x)+(a.x-c.x)*(z-c.z))/denominator
		if u>=-1e-6 and v>=-1e-6 and u+v<=1.+1e-6: return u*a.y+v*b.y+(1.-u-v)*c.y
	return NAN
