extends SceneTree
func _initialize()->void:
 var old=load("res://old_cut.gd").new();var current=load("res://scripts/membrane_cut.gd").new();var failures:=0;var count:=0
 var points:=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
 var indices:=PackedInt32Array([0,2,1,0,3,2])
 for mode in [false,true]:
  for shift in [-.3,0.,.213]:
   var a:=Vector3(shift,-.2,-1.5);var b:=Vector3(shift,.2,-1.5);var c:=Vector3(shift,0,1.5)
   var before:Dictionary=old.slice_triangle(points,indices,a,b,c,4096,8192,mode)
   var after:Dictionary=current.slice_triangle(points,indices,a,b,c,4096,8192,mode);after.erase("points64")
   count+=1
   if before!=after:failures+=1;push_error("legacy finite patch differs at "+str(shift)+" mode "+str(mode))
 for start in [Vector3(-.2,0,-1.5),Vector3(.173,0,-1.5)]:
  var before:Dictionary=old.slice(points,indices,start,start+Vector3(0,0,3),Vector3.UP,.2)
  var after:Dictionary=current.slice(points,indices,start,start+Vector3(0,0,3),Vector3.UP,.2);after.erase("points64")
  count+=1
  if before!=after:failures+=1;push_error("legacy curtain differs")
 print("Legacy incision comparison: ",failures," failures; cases=",count)
 var file:=FileAccess.open("res://result.json",FileAccess.WRITE);file.store_string(JSON.stringify({"qualified":failures==0,"cases":count,"scope":"Exact legacy output dictionaries on six finite patches (geometric/material) and two curtains; no whole-route or clinical claim."}));file.close()
 quit(1 if failures else 0)
