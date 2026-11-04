extends SceneTree
var failures:=0
func check(ok:bool,message:String)->void:
	if not ok:failures+=1;push_error(message)
func area(points:PackedVector3Array,ids:PackedInt32Array)->float:
	var result:=0.
	for i in range(0,ids.size(),3):result+=(points[ids[i+1]]-points[ids[i]]).cross(points[ids[i+2]]-points[ids[i]]).length()*.5
	return result
func verify(result:Dictionary,points:PackedVector3Array,ids:PackedInt32Array)->void:
	check(result.valid,"finite blade patch produces verified topology: "+result.reason)
	if not result.valid:return
	check(absf(area(result.points,result.indices)-area(points,ids))<1e-6,"finite incision preserves all current material area")
	check(result.sources.size()*3==result.indices.size() and result.bindings.size()==result.points.size(),"all faces and vertices retain material provenance")
	for i in range(0,result.indices.size(),3):
		var f:int=result.sources[i/3]*3
		var original:Vector3=(points[ids[f+1]]-points[ids[f]]).cross(points[ids[f+2]]-points[ids[f]])
		var normal:Vector3=(result.points[result.indices[i+1]]-result.points[result.indices[i]]).cross(result.points[result.indices[i+2]]-result.points[result.indices[i]])
		check(original.dot(normal)>0.,"finite patch retains oriented nondegenerate material faces")
func _initialize()->void:
	var cutter=load("res://scripts/membrane_cut.gd").new()
	check(cutter.has_method("slice_triangle"),"membrane cutter supports finite swept blade triangles")
	if failures:quit(1);return
	var regression:Dictionary=FileAccess.open("res://tests/fixtures/blade-midpoint-edge-snap.bin",FileAccess.READ).get_var()
	var regression_patch:PackedVector3Array=regression.patch
	var replay:Dictionary=cutter.slice_triangle(regression.points,regression.indices,regression_patch[0],regression_patch[1],regression_patch[2])
	verify(replay,regression.points,regression.indices)
	check(replay.valid and replay.changed,"a thin transverse stroke keeps its interior midpoint inside the material face")
	var scaled:=PackedVector3Array([Vector3(-1.03,0,-.98),Vector3(1.03,0,-.98),Vector3(1.03,0,.98),Vector3(-1.03,0,.98)])
	var scaled_ids:=PackedInt32Array([0,2,1,0,3,2])
	var shared:Dictionary=cutter.slice_triangle(scaled,scaled_ids,Vector3(.25,-.2,-1.2),Vector3(.25,-.2,1.2),Vector3(.25,.4,0))
	verify(shared,scaled,scaled_ids)
	if shared.valid:
		var copies:=0
		for point in shared.points:
			if point.distance_to(Vector3(.25,0,.25*.98/1.03))<1e-6:copies+=1
		check(copies==2,"oppositely traversed original shared edge creates one intersection per open bank")
	var grazing:=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.BACK]);var grazing_ids:=PackedInt32Array([0,2,1])
	var shallow:Dictionary=cutter.slice_triangle(grazing,grazing_ids,Vector3(.2,-.1,1.5e-7),Vector3(.8,-.1,3e-7),Vector3(.5,.1,2.25e-7))
	verify(shallow,grazing,grazing_ids)
	if shallow.valid:
		for i in range(grazing.size(),shallow.points.size()):check(shallow.points[i].x>=.349999 and shallow.points[i].x<=.650001,"near-parallel source-edge snapping cannot extend the finite blade patch to a distant plane crossing")
	var points:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	var ids:=PackedInt32Array([0,2,1,0,3,2]);var original:=points.duplicate();var original_ids:=ids.duplicate()
	var a:=Vector3(-.5,-.2,0);var b:=Vector3(.5,-.2,0);var c:=Vector3(0,.2,0)
	var result:Dictionary=cutter.slice_triangle(points,ids,a,b,c)
	verify(result,points,ids)
	if result.valid:
		check(result.changed,"transverse blade sweep actually opens the sheet")
		var center_copies:=0
		for i in range(points.size(),result.points.size()):
			var p:Vector3=result.points[i]
			check(absf(p.x)<=.250001 and absf(p.y)<1e-6 and absf(p.z)<1e-6,"incision stops at triangle edges rather than its bounding rectangle")
			if p.length()<1e-6:center_copies+=1
		check(center_copies==2,"interior slit retains two separate material banks")
		var repeated:Dictionary=cutter.slice_triangle(result.points,result.indices,a,b,c)
		check(repeated.valid and not repeated.changed and repeated.points==result.points and repeated.indices==result.indices,"repeated blade patch cannot heal or re-refine an open seam")
	var near:=PackedVector3Array([Vector3(.35,0,-.1),Vector3(.45,0,-.1),Vector3(.4,0,.1)])
	var near_ids:=PackedInt32Array([0,2,1]);var missed:Dictionary=cutter.slice_triangle(near,near_ids,a,b,c)
	check(missed.valid and not missed.changed and missed.points==near and missed.indices==near_ids,"triangle patch AABB overlap alone cannot cut nearby tissue")
	var frame:=Transform3D(Basis(Vector3(1,2,3).normalized(),.6),Vector3(.1,.3,.2));var rotated:=PackedVector3Array()
	for p in points:rotated.append(frame*p)
	var moved:Dictionary=cutter.slice_triangle(rotated,ids,frame*a,frame*b,frame*c);verify(moved,rotated,ids)
	if moved.valid:
		check(moved.changed,"finite incision is invariant under rigid world pose")
		for i in range(rotated.size(),moved.points.size()):check(absf((frame.affine_inverse()*moved.points[i]).x)<=.250002,"rotated blade keeps its finite boundary")
	var coplanar:Dictionary=cutter.slice_triangle(points,ids,Vector3(-.2,0,-.2),Vector3(.2,0,-.2),Vector3(0,0,.2))
	check(coplanar.valid and not coplanar.changed and coplanar.points==points and coplanar.indices==ids,"coplanar blade sliding alone does not erase or sever tissue")
	for triangle in [[a,a,c],[a,b,Vector3(0,-.2,0)],[Vector3(NAN,0,0),b,c]]:
		var rejected:Dictionary=cutter.slice_triangle(points,ids,triangle[0],triangle[1],triangle[2])
		check(not rejected.valid and rejected.points.is_empty() and rejected.indices.is_empty(),"invalid or collapsed swept patch rejects atomically")
	var limited:Dictionary=cutter.slice_triangle(points,ids,a,b,c,4,2)
	check(not limited.valid and limited.points.is_empty() and limited.indices.is_empty(),"partial blade subdivision cannot escape a work/output budget failure")
	var doubled:=points.duplicate();doubled.append_array(points)
	var doubled_ids:=ids.duplicate()
	for id in ids:doubled_ids.append(id+points.size())
	var independent:Dictionary=cutter.slice_triangle(doubled,doubled_ids,a,b,c);verify(independent,doubled,doubled_ids)
	if independent.valid:
		var first_bank:={};var second_bank:={}
		for i in range(independent.sources.size()):
			for j in range(3):
				if independent.sources[i]<2:first_bank[independent.indices[3*i+j]]=true
				else:second_bank[independent.indices[3*i+j]]=true
		for v in first_bank:check(not second_bank.has(v),"coincident separate sheets never weld across material identity")
	var legacy:Dictionary=cutter.slice(points,ids,Vector3(-.2,0,0),Vector3(.2,0,0),Vector3.FORWARD,.1)
	check(not legacy.valid and legacy.reason=="coplanar_curtain","triangle contact behavior cannot leak into the rectangular incision contract")
	check(points==original and ids==original_ids,"blade patch never mutates caller tissue arrays")
	print("Membrane finite patch: ",failures," failures");quit(1 if failures else 0)
