shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Organic foliage (Stage B0, D-60; B0.1 adds per-instance variation, wrapped
// diffuse and a faint rim — see organic_foliage_common.gdshaderinc). One
// shared material serves every canopy, bush and grass tuft.

#include "res://shaders/organic_foliage_common.gdshaderinc"

void vertex() {
	vec3 instance_tint;
	vec3 world;
	organic_vertex(VERTEX, MODEL_MATRIX, TIME, instance_tint, world);
	v_instance_tint = instance_tint;
	v_world = world;
}

void fragment() {
	ALBEDO = COLOR.rgb * tint.rgb * v_instance_tint;
	ROUGHNESS = roughness_value;
	RIM = 0.25;
	RIM_TINT = 0.6;
}

void light() {
	organic_light(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO, DIFFUSE_LIGHT);
}
