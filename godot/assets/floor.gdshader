shader_type spatial;
varying vec3 world_position;
void vertex(){world_position=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
void fragment(){
 vec2 cell=abs(fract(world_position.xz+vec2(0.5))-vec2(0.5));
 float distance_to_grout=min(cell.x,cell.y);
 float aa=max(fwidth(distance_to_grout),0.003);
 float grout=1.0-smoothstep(0.007-aa,0.007+aa,distance_to_grout);
 ALBEDO=mix(vec3(0.17,0.23,0.25),vec3(0.145,0.199,0.216),grout*0.5);
 ROUGHNESS=0.84;
}
