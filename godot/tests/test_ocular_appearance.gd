extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func _initialize()->void:call_deferred("run")
func run()->void:
	var world=load("res://scripts/surgical_world.gd").new();root.add_child(world);world.build()
	var sclera:MeshInstance3D=world.find_child("Sclera",true,false)
	var data:Array=sclera.mesh.surface_get_arrays(0)
	var points:PackedVector3Array=data[Mesh.ARRAY_VERTEX];var normals:PackedVector3Array=data[Mesh.ARRAY_NORMAL]
	var stride:=161;var rows:=points.size()/stride-1
	for row in [1,rows-1]:
		for angle in [0,40,80,120]:
			var i:int=row*stride+angle
			var radial:Vector3=(points[i+stride]-points[i-stride]).normalized()
			check(absf(normals[i].dot(radial))<.025,"curved scleral normals follow the actual radial tangent")
			check(absf(normals[i].length()-1.)<1e-5 and normals[i].y>0.,"ocular normals remain finite unit outward vectors")
	var vessels=world.find_child("ScleralVasculature",true,false)
	check(vessels is MeshInstance3D,"surface-following vessels share a batched mesh")
	if vessels is MeshInstance3D:
		var mesh:Mesh=vessels.mesh;check(mesh.get_surface_count()==1,"vessel branches render in one surface")
		var arrays:Array=mesh.surface_get_arrays(0);var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var vn:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL];var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		check(vertices.size()>1000 and vertices.size()<20000 and indices.size()>vertices.size(),"vascular network is bounded detailed tubular geometry")
		for i in range(vertices.size()):
			var p:=vertices[i];var radius:=Vector2(p.x,p.z).length();var fraction:float=clampf((radius-1.43)/(.49),0.,1.)
			var surface_y:float=.71+sin(fraction*PI)*.075
			check(p.is_finite() and radius>1.43 and radius<1.93,"vessels stay on the exposed scleral annulus")
			check(p.y-surface_y>-.008 and p.y-surface_y<.018,"vascular tubes follow the curved sclera rather than floating or sinking")
			check(vn[i].is_finite() and absf(vn[i].length()-1.)<1e-4,"vessel normals are finite unit vectors")
		var wrong_winding:=0
		for i in range(0,indices.size(),3):
			var a:=indices[i];var b:=indices[i+1];var c:=indices[i+2]
			var face_normal:Vector3=(vertices[b]-vertices[a]).cross(vertices[c]-vertices[a])
			if face_normal.dot(vn[a]+vn[b]+vn[c])>=0.:wrong_winding+=1
		check(wrong_winding==0,"vascular tubes and closed end caps use visible outward winding")
	var node_count:=get_node_count();world.build();check(get_node_count()==node_count,"rebuilding the scene does not duplicate vascular geometry")
	world.free();print("Ocular appearance: ",failures," failures");quit(1 if failures else 0)
