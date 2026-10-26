shader_type spatial;
render_mode cull_disabled;
void fragment(){
 vec2 p=UV-vec2(0.5); float r=length(p)*2.0;
 float cloud=sin(p.x*29.0+sin(p.y*37.0)*0.8)*sin(p.y*19.0+p.x*11.0);
 float speck=sin(p.x*247.0+p.y*173.0)*sin(p.y*221.0-p.x*161.0);
 float density=clamp(0.5+cloud*0.16+speck*0.025-r*0.1,0.0,1.0);
 ALBEDO=mix(vec3(0.48,0.38,0.20),vec3(0.83,0.75,0.52),density);
 ROUGHNESS=0.52; SPECULAR=0.26;
}
