shader_type spatial;
render_mode cull_disabled;
uniform vec4 inner_color : source_color = vec4(0.18,0.28,0.25,1.0);
uniform vec4 outer_color : source_color = vec4(0.035,0.12,0.13,1.0);
void fragment(){
 vec2 p=UV-vec2(0.5); float r=length(p)*2.0; float a=atan(p.y,p.x);
 float fibers=sin(a*159.0+sin(r*23.0)*1.2)*0.5+0.5;
 float fine=sin(a*377.0+r*31.0)*0.5+0.5;
 float crypt=pow(sin(a*31.0+sin(r*17.0))*0.5+0.5,8.0);
 vec3 col=mix(inner_color.rgb,outer_color.rgb,smoothstep(0.48,1.0,r));
 col*=0.62+0.45*fibers+0.22*fine;
 col+=vec3(0.16,0.09,0.025)*exp(-pow((r-0.65)*11.0,2.0));
 col*=1.0-0.5*crypt*smoothstep(0.57,0.8,r);
 ALBEDO=col; ROUGHNESS=0.43; SPECULAR=0.42;
}
