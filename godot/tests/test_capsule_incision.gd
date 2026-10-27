extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok: failures+=1; push_error(message)
func total(values:PackedFloat64Array)->float:
	var result:=0.
	for v in values: result+=v
	return result
func _initialize()->void:
	var shape=load("res://scripts/anterior_segment.gd").new()
	var model=load("res://scripts/capsule_solver.gd").new(); model.geometry=shape; model.reset()
	check(model.has_method("incise"),"capsule integrates area-preserving incision state")
	if failures: quit(1); return
	var original:Dictionary=model.metrics()
	var contact_point:Vector3=model.positions[0]
	var contact_tools:Array[Dictionary]=[{"hand":0,"tip":contact_point+Vector3(0,.025,0),"radius":.065,"contact_radius":.018,"grip":true,"cut":false}]
	model.step_tools(1./60.,contact_tools)
	check(model.metrics().grasped==0 and model.positions[0].distance_to(contact_point)<.000001,"grasp acquisition preserves material contact offset without snapping tissue to tool center")
	model.reset()
	model.pressure_load=.2
	var ordinary_force:PackedVector3Array=model._pressure_acceleration(); var old_area:float=model._rest_area[0]
	model._rest_area[0]=1e-10
	var tiny_force:PackedVector3Array=model._pressure_acceleration()
	check(tiny_force[0].distance_to(ordinary_force[0]*float(old_area/1e-10))<1.,"accepted tiny areal support receives force divided by its actual mass")
	model.reset()
	model._edge_active.fill(0); model._edge_active[0]=1
	var first:int=model._edge_a[0]; var second:int=model._edge_b[0]
	model.positions[second]=model.positions[first]+Vector3(.00000005,0,0); model._previous=model.positions.duplicate()
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.positions[first].distance_to(model.positions[second])>.001,"short nonzero current distance still receives its accepted XPBD edge constraint")
	model.reset()
	model._rest_area[0]=1e-12; model.surface_density=.01
	var domain_before:Dictionary=model.visual_state(); var inverse_before:PackedFloat64Array=model._inverse_mass.duplicate()
	model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.metrics().integration_steps==0 and model.visual_state()==domain_before and model._inverse_mass==inverse_before,"density change beyond supported inverse mass rejects before any numerical mutation")
	model.reset()
	var captured:Dictionary=model.visual_state(); var captured_points:PackedVector3Array=captured.positions.duplicate()
	var initial_mass:float=total(model._rest_area)
	# A uniform existing velocity must survive refinement without an impulse.
	for i in range(model.positions.size()): model._previous[i]=model.positions[i]-Vector3(.001,.002,-.001)
	var radius:=.4; var y:float=shape.bag_front(radius); var prior:=Vector3(radius,y,0.)
	for i in range(1,65):
		var next:=Vector3(radius*cos(TAU*i/64.),y,radius*sin(TAU*i/64.))
		var result:Dictionary=model.incise(prior,next,Vector3.UP,.05)
		check(result.valid,"curved state incision %d: %s"%[i,result.reason])
		if not result.valid: break
		prior=next
	var metrics:Dictionary=model.metrics()
	check(model.detached_components().size()==1,"closed incision makes one real retained material flap")
	check(absf(metrics.retained_area-original.initial_area)<1e-10 and metrics.cut_loss_area<1e-10,"incision preserves authoritative material rest area without cut loss")
	check(absf(total(model._rest_area)-initial_mass)<1e-10,"lumped areal mass is conserved through refinement")
	for i in range(model.positions.size()):
		check((model.positions[i]-model._previous[i]).distance_to(Vector3(.001,.002,-.001))<.000001,"refined history retains existing uniform velocity")
		if model._rest_area[i]>0.: check(model._inverse_mass[i]>=0. and is_finite(model._inverse_mass[i]) and model._inverse_mass[i]<=1e12,"supported inverse mass stays within the contact solver domain")
	check(captured.positions==captured_points,"old captured positions remain immutable after topology refinement")
	var before:Dictionary=model.visual_state(); var history:PackedVector3Array=model._previous.duplicate(); var mass_before:PackedFloat64Array=model._rest_area.duplicate()
	var rejected:Dictionary=model.incise(Vector3(NAN,0,0),Vector3.ZERO,Vector3.UP,.05)
	check(not rejected.valid and before==model.visual_state() and model._previous==history and model._rest_area==mass_before,"invalid incision leaves topology/history/mass unchanged")
	# Return to rest before actual XPBD evolution; cutting is not a time step.
	model._previous=model.positions.duplicate()
	for i in range(30): model.step(1./60.,Vector3(3,3,3),.018,false,false)
	check(model.metrics().finite and model.metrics().cut_loss_area<1e-10,"refined rest specimen evolves without spontaneous material loss")
	var pieces:Array=model.detached_components()
	check(pieces.size()==1 and model.metrics().extracted_flaps==0,"free intraocular tissue stays retained")
	var fine_tools:Array[Dictionary]=[{"hand":0,"tip":model.positions[1]+Vector3(0,.025,0),"radius":.065,"contact_radius":.018,"grip":true,"cut":false}]
	model.step_tools(1./60.,fine_tools); fine_tools[0].tip.y+=.005; model.step_tools(1./60.,fine_tools)
	check(model.metrics().cut_loss_area<1e-10,"small traction on a free refined flap does not fracture from pre-solve transient stretch")
	model.pressure_load=.2
	var acceleration:PackedVector3Array=model._pressure_acceleration()
	if not pieces.is_empty():
		for v in pieces[0].vertices: check(acceleration[v].length()<1e-12,"new detached flap is wetted on both sides, without compartment pressure")
	model.reset()
	var center:Vector3=model.positions[0]
	model.step(1./60.,center,.018,true,false)
	var hand:int=model.metrics().grasped
	check(hand>=0,"material grasp acquired before incision")
	var incised:Dictionary=model.incise(Vector3(-1.3,.4,0),Vector3(1.3,.4,0),Vector3.UP,.6)
	check(incised.valid,"incision through held vertex transfers its material bank: "+incised.reason)
	if incised.valid:
		var held:int=model.metrics().grasped
		check(held>=0 and model.positions[held].distance_to(center)<.00001,"grasp keeps the original material point without snapping")
		check(model._faces[model._grasp_faces[0]].has(held),"held vertex remains in its original grasp material face")
		model.release_hand(0); check(model.metrics().grasped==-1,"release clears remapped grasp")
	model.reset()
	model.step(1./60.,model.positions[0],.018,true,false)
	var direction:=Vector3(cos(deg_to_rad(5.)),0,sin(deg_to_rad(5.)))
	incised=model.incise(-direction*1.3+Vector3(0,.4,0),direction*1.3+Vector3(0,.4,0),Vector3.UP,.6)
	check(incised.valid and model.metrics().grasped==-1,"cut through both attachment-face banks releases an ambiguous severed grasp")
	model.reset()
	for i in range(model.positions.size()):
		if not model.anchored[i]: model.positions[i].y+=.02*(1.-Vector2(model.positions[i].x,model.positions[i].z).length()/shape.bag_radius)
	model._previous=model.positions.duplicate()
	var previous_energy:float=model.metrics().strain_energy
	incised=model.incise(Vector3(-1.3,.4,0),Vector3(1.3,.4,0),Vector3.UP,.6)
	check(incised.valid and previous_energy>0. and model.metrics().strain_energy>0.,"refinement transfers strained material rest lengths instead of resetting strain")
	model.reset()
	check(model.metrics().incision_events==0 and model.metrics().vertices==217 and model.detached_components().is_empty(),"reset clears refinement topology, history and incision events")
	print("Capsule incision: ",failures," failures"); quit(1 if failures else 0)
