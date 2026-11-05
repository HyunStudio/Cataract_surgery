extends SceneTree
func encode(value):
 if value is PackedFloat64Array:return {"f64_le":"" if value.is_empty() else Marshalls.raw_to_base64(value.to_byte_array())}
 if value is PackedInt32Array:return Array(value)
 if value is Dictionary:
  var out:Dictionary={}
  for key in value:out[key]=encode(value[key])
  return out
 if value is Array:
  var out:Array=[]
  for entry in value:out.append(encode(entry))
  return out
 return value
func _initialize()->void:
 var file:="";var destination:=""
 for argument in OS.get_cmdline_user_args():
  if argument.begins_with("--case="):file=argument.trim_prefix("--case=")
  if argument.begins_with("--out="):destination=argument.trim_prefix("--out=")
 if file.is_empty() or destination.is_empty():push_error("--case and --out required");quit(1);return
 var input:=FileAccess.open(file,FileAccess.READ)
 if input==null:push_error("case could not be opened");quit(1);return
 var data:Dictionary=input.get_var()
 var out:={"scope":"Exact raw double captured native requests; no passing whole-step claim.","source_sha256":FileAccess.get_sha256(file),"native_history":encode(data.native_history),"guard_history":encode(data.guard_history),"result":encode(data.result),"state_summary":{"steps":data.state.steps,"staged_events":data.state.events,"fine_vertices":data.state.rest.size(),"faces":data.state.indices.size()/3,"controls":data.state.xyz.size()/3,"fine_point_limit":data.state.get("fine_point_limit",4096)}}
 DirAccess.make_dir_recursive_absolute(destination.get_base_dir())
 var output:=FileAccess.open(destination,FileAccess.WRITE)
 if output==null:push_error("output could not be opened");quit(1);return
 output.store_string(JSON.stringify(out,"",true,true))
 print("Owned native requests exported: ",out.state_summary)
 quit()
