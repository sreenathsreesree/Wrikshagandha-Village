shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_disabled;

// Meadow ground (Stage B0.1, D-61): the same plane, now coloured with
// world-space patches of lush and dry grass and a fine speckle instead of one
// flat green. Visual only — the mesh, its collider and the navigation are
// untouched.

#include "res://shaders/organic_ground.gdshaderinc"

uniform float roughness_value : hint_range(0.0, 1.0) = 0.95;

varying vec3 v_world;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	ALBEDO = ground_colour(v_world.xz);
	ROUGHNESS = roughness_value;
}
