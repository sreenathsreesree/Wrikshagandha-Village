shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_schlick_ggx;

// Landmark foliage (Stage B0.1, D-60): organic foliage plus an optional
// see-through for very large crowns (the Great Tree). When fade_radius > 0,
// canopy fragments close to the line from the player to the camera, and
// higher than fade_min_height above the player, are dithered away, so a
// crown taller than the follow camera never hides the player. It reads only
// the existing global wg_player_position (set every frame by the vegetation
// controller) and the renderer's own camera position — no script or camera
// change. Off by default (fade_radius = 0): opaque, no discard.

#include "res://shaders/organic_foliage_common.gdshaderinc"

uniform float fade_radius = 0.0;
uniform float fade_min_height = 1.8;
uniform float fade_softness = 1.2;
uniform float fade_min_alpha : hint_range(0.0, 1.0) = 0.15;

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
	if (fade_radius > 0.0) {
		vec3 a = wg_player_position + vec3(0.0, 1.0, 0.0);
		vec3 ab = CAMERA_POSITION_WORLD - a;
		float t = clamp(dot(v_world - a, ab) / max(dot(ab, ab), 0.0001), 0.0, 1.0);
		float d = length(v_world - (a + ab * t));
		float keep = smoothstep(fade_radius - fade_softness, fade_radius, d);
		keep = max(keep, step(v_world.y, wg_player_position.y + fade_min_height));
		keep = max(keep, fade_min_alpha);
		// 4x4 ordered dither: opaque pipeline, no sorting, no transparency pass.
		ivec2 p = ivec2(FRAGCOORD.xy) % 4;
		int idx = p.x + p.y * 4;
		const float M[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
		if (keep < (M[idx] + 0.5) / 16.0) {
			discard;
		}
	}
}

void light() {
	organic_light(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO, DIFFUSE_LIGHT);
}
