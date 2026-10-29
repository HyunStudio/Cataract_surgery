extends RefCounted
## Model-local value state only. Mutable child objects need explicit ownership.
static func clone_value(value:Variant)->Variant:
	if value is Array:
		var result:Array=value.duplicate()
		for i in range(result.size()): result[i]=clone_value(value[i])
		return result
	if value is Dictionary:
		var result:Dictionary=value.duplicate()
		for key in result: result[key]=clone_value(value[key])
		return result
	if typeof(value) in [TYPE_PACKED_BYTE_ARRAY,TYPE_PACKED_INT32_ARRAY,TYPE_PACKED_INT64_ARRAY,TYPE_PACKED_FLOAT32_ARRAY,TYPE_PACKED_FLOAT64_ARRAY,TYPE_PACKED_STRING_ARRAY,TYPE_PACKED_VECTOR2_ARRAY,TYPE_PACKED_VECTOR3_ARRAY,TYPE_PACKED_VECTOR4_ARRAY,TYPE_PACKED_COLOR_ARRAY]:
		return value.duplicate()
	return value

static func capture_model(model:Object,excluded:Array=[])->Dictionary:
	var state:Dictionary={}
	for property in model.get_property_list():
		if (int(property.usage)&PROPERTY_USAGE_SCRIPT_VARIABLE)==0 or property.name in excluded: continue
		var value:Variant=model.get(property.name)
		if typeof(value)==TYPE_OBJECT: continue
		state[property.name]=clone_value(value)
	return state

static func restore_model(model:Object,state:Dictionary)->void:
	for key in state: model.set(key,clone_value(state[key]))
