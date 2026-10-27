extends Node3D
## Rendering adapter only. Numerical solvers and captured frames remain read-only.
const Shapes=preload("res://scripts/anatomy_surfaces.gd")
const WorldScript=preload("res://scripts/surgical_world.gd")
const SurfaceScript=preload("res://scripts/lens_surface.gd")
var world: Node3D
var membrane: MeshInstance3D
var lens_display: MeshInstance3D
var iol_display: Node3D
var tool_models: Array[Dictionary]=[]
var wire_display: MeshInstance3D
var wound_display: MeshInstance3D
var debris: MultiMeshInstance3D
var _physical: Node3D
var _surface=SurfaceScript.new()
var _capsule_mesh:=ArrayMesh.new()
var _wire_mesh:=ArrayMesh.new()
var _wound_mesh:=ArrayMesh.new()
var _optic_mesh:=ArrayMesh.new()
var _haptic_mesh:=ArrayMesh.new()
var _optic: MeshInstance3D
var _haptics: MeshInstance3D
var _iris: MeshInstance3D
var _pupil_radius:float=-1.0
var _last_frame:Dictionary={}
var _built:=false
var _forceps_jaws:Array[Array]=[[],[]]
var _last_capsule_positions:=PackedVector3Array()
var _last_capsule_triangles:=PackedInt32Array()
var _last_lens_positions:=PackedVector3Array()
var _last_lens_active:=PackedByteArray()
var _last_bond_active:=PackedByteArray()

class CapturedIOL:
	extends RefCounted
	var positions:=PackedVector3Array()
	var optic_count:=32
	var values:Dictionary={}
	func metrics()->Dictionary: return values

func build()->void:
	if _built: return
	_built=true
	world=WorldScript.new()
	world.name="World"
	add_child(world)
	world.build()
	for label in ["CapsuleMembrane","LensRegions","CortexRegions","IOL","Iris","PupilRim","TutorialTargets","AspirationFragments","Cornea","Pupil"]:
		var old:Node3D=world.find_child(label,true,false)
		if old: old.visible=false
	_physical=Node3D.new()
	_physical.name="NumericalEye"
	add_child(_physical)
	var cornea_node:=_node("ComputedCornea",_physical)
	cornea_node.mesh=Shapes.mesh(Shapes.cornea())
	cornea_node.material_override=_material(Color(.68,.9,.97,.045),.08)
	var posterior_node:=_node("ComputedPosteriorCapsule",_physical)
	posterior_node.mesh=Shapes.mesh(Shapes.posterior())
	posterior_node.material_override=_material(Color(.045,.075,.07),.35)
	membrane=_node("ComputedCapsuleSurface",_physical)
	membrane.mesh=_capsule_mesh
	membrane.material_override=_material(Color(.76,.87,.88,.26),.24)
	lens_display=_node("ContinuousLens",_physical)
	wire_display=_node("CapsuleConstraints",_physical)
	wire_display.mesh=_wire_mesh
	wire_display.material_override=_material(Color("69cbb8"),.7,true)
	wound_display=_node("ActualIncisionPaths",_physical)
	wound_display.mesh=_wound_mesh
	wound_display.material_override=_material(Color("a96f62"),.7,true)
	_iris=_node("ComputedIris",_physical)
	var iris_material:=ShaderMaterial.new()
	iris_material.shader=load("res://assets/iris.gdshader")
	_iris.material_override=iris_material
	debris=MultiMeshInstance3D.new()
	debris.name="DetachedMaterialOnly"
	var multi:=MultiMesh.new()
	multi.transform_format=MultiMesh.TRANSFORM_3D
	var grain:=SphereMesh.new()
	grain.radius=.025
	grain.height=.05
	grain.radial_segments=10
	grain.rings=6
	grain.material=_material(Color("c7b281"),.45)
	multi.mesh=grain
	multi.instance_count=111
	multi.visible_instance_count=0
	debris.multimesh=multi
	_physical.add_child(debris)
	iol_display=Node3D.new()
	iol_display.name="ComputedIOL"
	_physical.add_child(iol_display)
	_optic=_node("Optic",iol_display)
	_optic.mesh=_optic_mesh
	_optic.material_override=_material(Color(.63,.85,.94,.40),.08)
	_haptics=_node("Haptics",iol_display)
	_haptics.mesh=_haptic_mesh
	_haptics.material_override=_material(Color("b1e0ec"),.18)
	iol_display.visible=false
	for hand in range(2):
		var models:Dictionary={}
		for id in world.tools:
			var model:Node3D=world.tools[id].duplicate()
			model.name="Hand%d_%s"%[hand,id]
			model.visible=false
			_physical.add_child(model)
			models[id]=model
			if id=="forceps":
				for child in model.get_children():
					if str(child.name).begins_with("Jaw"): _forceps_jaws[hand].append({"node":child,"rest":child.transform})
		tool_models.append(models)
	_set_view(false)

func _node(label:String,parent:Node3D)->MeshInstance3D:
	var node:=MeshInstance3D.new()
	node.name=label
	parent.add_child(node)
	return node
func _material(color:Color,roughness:float,unshaded:bool=false)->StandardMaterial3D:
	var mat:=StandardMaterial3D.new()
	mat.albedo_color=color
	mat.roughness=roughness
	mat.cull_mode=BaseMaterial3D.CULL_DISABLED
	if color.a<1: mat.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
	if unshaded: mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	return mat

func apply(capsule,lens,iol,rigs:Array,hand_tools:Array,selected:int,actions:Array,options:Dictionary)->void:
	if not _built: build()
	var iol_metrics:Dictionary=iol.metrics()
	_render_capsule(capsule,bool(options.get("wireframe",false)))
	_render_lens(lens)
	var free_count:=mini(111,_surface.detached_positions.size())
	debris.multimesh.visible_instance_count=free_count
	for i in range(free_count): debris.multimesh.set_instance_transform(i,Transform3D(Basis.IDENTITY,_surface.detached_positions[i]))
	_render_iol(iol.positions,int(iol.optic_count),iol_metrics)
	_render_tools(rigs,hand_tools,selected,actions)
	_render_wounds(options.get("wounds",[]))
	var radius:=clampf(float(options.get("pupil_radius",.98)),.55,1.15)
	if not is_equal_approx(radius,_pupil_radius):
		_pupil_radius=radius
		_iris.mesh=Shapes.mesh(Shapes.iris(radius))
	_set_view(bool(options.get("room",false)))
	var rig_data:Array=[]
	for rig in rigs: rig_data.append({"tip":rig.tip,"axis":rig.axis,"portal":rig.portal,"insertion":rig.insertion})
	_last_frame={"capsule":{"positions":capsule.positions.duplicate(),"triangles":capsule.triangles.duplicate(),"edges":capsule.edges.duplicate(true)},"lens":{"particles":lens.particles.duplicate(true),"bonds":lens.bonds.duplicate(true)},"iol":{"positions":iol.positions.duplicate(),"optic_count":int(iol.optic_count),"metrics":iol_metrics.duplicate(true)},"rigs":rig_data,"hand_tools":hand_tools.duplicate(true),"selected":selected,"actions":actions.duplicate(true),"options":options.duplicate(true)}

func _set_view(room:bool)->void:
	world.set_room_view(room)
	# World owns its legacy phase models; this adapter owns the actual tissue/tools.
	world.find_child("Instruments",true,false).visible=false
	_physical.visible=not room

func _render_capsule(capsule,wireframe:bool)->void:
	var positions:PackedVector3Array=capsule.positions
	var triangles:PackedInt32Array=capsule.triangles
	if positions!=_last_capsule_positions or triangles!=_last_capsule_triangles:
		var normals:=PackedVector3Array()
		normals.resize(positions.size())
		normals.fill(Vector3.ZERO)
		for i in range(0,triangles.size(),3):
			var a:=triangles[i]
			var b:=triangles[i+1]
			var c:=triangles[i+2]
			var normal:Vector3=-(positions[b]-positions[a]).cross(positions[c]-positions[a])
			for index in [a,b,c]: normals[index]+=normal
		for i in range(normals.size()): normals[i]=normals[i].normalized() if normals[i].length_squared()>.0000000001 else Vector3.UP
		_capsule_mesh.clear_surfaces()
		if not triangles.is_empty():
			var arrays:=[]
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=positions
			arrays[Mesh.ARRAY_NORMAL]=normals
			arrays[Mesh.ARRAY_INDEX]=triangles
			_capsule_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		_last_capsule_positions=positions.duplicate()
		_last_capsule_triangles=triangles.duplicate()
	wire_display.visible=wireframe
	if wireframe:
		var points:=PackedVector3Array()
		for edge in capsule.edges:
			if edge.active: points.append_array(PackedVector3Array([positions[edge.a]+Vector3(0,.003,0),positions[edge.b]+Vector3(0,.003,0)]))
		_lines(_wire_mesh,points)

func _render_lens(lens)->void:
	var positions:=PackedVector3Array()
	var active:=PackedByteArray()
	var links:=PackedByteArray()
	for particle in lens.particles:
		positions.append(particle.position)
		active.append(1 if particle.active else 0)
	for bond in lens.bonds: links.append(1 if bond.active else 0)
	if positions==_last_lens_positions and active==_last_lens_active and links==_last_bond_active: return
	lens_display.mesh=_surface.update_from_solver(lens)
	_last_lens_positions=positions
	_last_lens_active=active
	_last_bond_active=links
func _render_iol(positions:PackedVector3Array,optic_count:int,metrics:Dictionary)->void:
	iol_display.visible=float(metrics.get("delivered",0.0))>0.0 and positions.size()>=optic_count
	if not iol_display.visible: return
	var vertices:=PackedVector3Array()
	var normals:=PackedVector3Array()
	var indices:=PackedInt32Array()
	var center:=Vector3.ZERO
	for i in range(optic_count): center+=positions[i]/optic_count
	vertices.append(center)
	normals.append(Vector3.UP)
	for i in range(optic_count):
		vertices.append(positions[i])
		normals.append(Vector3.UP)
		indices.append_array(PackedInt32Array([0,1+(i+1)%optic_count,1+i]))
	_optic_mesh.clear_surfaces()
	var arrays:=[]
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_INDEX]=indices
	_optic_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	vertices=PackedVector3Array()
	normals=PackedVector3Array()
	indices=PackedInt32Array()
	for first in [-1,optic_count,optic_count+12]:
		var closed:bool=first==-1
		var count:int=optic_count+1 if closed else 12
		if not closed and positions.size()<first+12: continue
		var start:=vertices.size()
		for i in range(count):
			var index:int=i%optic_count if closed else first+i
			var previous:int=(i-1+optic_count)%optic_count if closed else first+maxi(0,i-1)
			var next:int=(i+1)%optic_count if closed else first+mini(11,i+1)
			var tangent:Vector3=(positions[next]-positions[previous]).normalized()
			if tangent.length_squared()<.01: tangent=Vector3.FORWARD
			var side:=tangent.cross(Vector3.UP).normalized()
			if side.length_squared()<.01: side=Vector3.RIGHT
			var up:=side.cross(tangent).normalized()
			for k in range(6):
				var normal:=side*cos(k*TAU/6.0)+up*sin(k*TAU/6.0)
				vertices.append(positions[index]+normal*(.007 if closed else .012))
				normals.append(normal)
		for i in range(count-1):
			for k in range(6):
				var a:=start+i*6+k
				var b:=start+i*6+(k+1)%6
				indices.append_array(PackedInt32Array([a,a+6,b,b,a+6,b+6]))
	_haptic_mesh.clear_surfaces()
	if not indices.is_empty():
		arrays[Mesh.ARRAY_VERTEX]=vertices
		arrays[Mesh.ARRAY_NORMAL]=normals
		arrays[Mesh.ARRAY_INDEX]=indices
		_haptic_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)

func _render_tools(rigs:Array,hand_tools:Array,selected:int,actions:Array)->void:
	for hand in range(2):
		for id in tool_models[hand]:
			var model:Node3D=tool_models[hand][id]
			model.visible=hand<rigs.size() and hand<hand_tools.size() and id==hand_tools[hand]
			if not model.visible: continue
			var toward:Vector3=-rigs[hand].axis.normalized()
			var side:=toward.cross(Vector3.UP).normalized()
			if side.length_squared()<.01: side=Vector3.FORWARD
			var frame:=Basis(toward,side.cross(toward).normalized(),side)
			model.basis=frame*Basis(Quaternion(Vector3(1.55,.52,.20).normalized(),Vector3.RIGHT))
			model.position=rigs[hand].tip
			model.set_meta("selected",hand==selected)
			model.set_meta("action",actions[hand].duplicate(true) if hand<actions.size() else {})
			if id=="forceps":
				var closed:bool=hand<actions.size() and bool(actions[hand].get("grip",false))
				for jaw in _forceps_jaws[hand]:
					jaw.node.transform=jaw.rest
					jaw.node.position.z*=.35 if closed else 1.0

func _render_wounds(wounds:Array)->void:
	var paths:Array=wounds
	if not wounds.is_empty() and (wounds[0] is Vector3 or _point_array(wounds[0])): paths=[wounds]
	var points:=PackedVector3Array()
	for p in range(mini(4,paths.size())):
		var path=paths[p]
		if not (path is Array or path is PackedVector3Array): continue
		var previous:=Vector3.ZERO
		var valid_previous:=false
		for i in range(mini(256,path.size())):
			var value=path[i]
			var point:Vector3
			if value is Vector3: point=value
			elif _point_array(value): point=Vector3(float(value[0]),float(value[1]),float(value[2]))
			else:
				valid_previous=false
				continue
			if not point.is_finite():
				valid_previous=false
				continue
			if valid_previous: points.append_array(PackedVector3Array([previous+Vector3(0,.004,0),point+Vector3(0,.004,0)]))
			previous=point
			valid_previous=true
	_lines(_wound_mesh,points)
func _point_array(value)->bool:
	return value is Array and value.size()>=3 and (value[0] is float or value[0] is int)
func _lines(mesh:ArrayMesh,points:PackedVector3Array)->void:
	mesh.clear_surfaces()
	if points.is_empty(): return
	var arrays:=[]
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=points
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_LINES,arrays)

func capture_frame()->Dictionary:
	return _last_frame.duplicate(true)
func apply_frame(frame:Dictionary)->void:
	if not frame.has_all(["capsule","lens","iol","rigs","hand_tools","selected","actions","options"]): return
	var copy:=frame.duplicate(true)
	var implant:=CapturedIOL.new()
	implant.positions=copy.iol.positions
	implant.optic_count=copy.iol.optic_count
	implant.values=copy.iol.metrics
	apply(copy.capsule,copy.lens,implant,copy.rigs,copy.hand_tools,copy.selected,copy.actions,copy.options)



