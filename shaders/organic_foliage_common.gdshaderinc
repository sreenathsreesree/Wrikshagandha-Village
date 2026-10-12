// Organic foliage shared code (Stage B0.1, D-60), included by
// organic_foliage.gdshader and organic_foliage_landmark.gdshader. The same
// cheap per-vertex sway and "bend away from the player" as sway.gdshader
// (unchanged, still used by the grass/flower placeholders), plus the mesh's
// vertex colour (baked light and occlusion), a soft wrap-around diffuse so
// canopies never go black on the shadow side, a faint rim, and a small
// per-instance hue shift so repeated props don't read as clones. Sway scales
// with height above the mesh's own origin (the ground), so trunks never move.

uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float sway_speed = 1.2;
uniform float sway_amount = 0.02;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;
// How far each instance's colour may drift (0 = every instance identical).
uniform float instance_variation : hint_range(0.0, 0.3) = 0.08;

global uniform vec3 wg_player_position;

const float BEND_RADIUS = 1.35;
const float BEND_STRENGTH = 0.3;
// Bending is for low foliage only (grass, bushes); canopies far above the
// player don't lean away from them.
const float BEND_MAX_HEIGHT = 0.8;

// Set in vertex() from organic_vertex's outputs (a helper may not write varyings).
varying vec3 v_instance_tint;
varying vec3 v_world;

float organic_hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void organic_vertex(inout vec3 vertex, mat4 model, float time, out vec3 instance_tint, out vec3 world) {
	float phase = time * sway_speed + vertex.x * 3.0 + vertex.z * 3.0;
	float lever = clamp(vertex.y, 0.0, 4.0);
	vertex.x += sin(phase) * sway_amount * lever;
	vertex.z += cos(phase * 0.8) * sway_amount * 0.5 * lever;

	vec3 world_pos = (model * vec4(vertex, 1.0)).xyz;
	vec2 offset = world_pos.xz - wg_player_position.xz;
	float dist = length(offset);
	float bend = clamp(1.0 - dist / BEND_RADIUS, 0.0, 1.0);
	bend *= bend * step(vertex.y, BEND_MAX_HEIGHT);
	vec2 away = dist > 0.0001 ? normalize(offset) : vec2(0.0, 1.0);
	vertex.xz += away * bend * BEND_STRENGTH * lever;

	// One value per instance from its origin: warmer/yellower or cooler/bluer.
	float h = organic_hash(model[3].xz) * 2.0 - 1.0;
	float b = organic_hash(model[3].zx + 17.0) * 2.0 - 1.0;
	instance_tint = vec3(1.0 + h * instance_variation, 1.0 + b * instance_variation * 0.5, 1.0 - h * instance_variation)
		* (1.0 + b * instance_variation * 0.5);
	world = (model * vec4(vertex, 1.0)).xyz;
}

void organic_light(vec3 normal, vec3 light, vec3 light_color, float attenuation, vec3 albedo, inout vec3 diffuse) {
	// Wrapped Lambert: (n·l + w) / (1 + w), so the unlit side keeps some form.
	float wrap = 0.45;
	float d = max((dot(normal, light) + wrap) / (1.0 + wrap), 0.0);
	diffuse += light_color * attenuation * d * albedo / PI;
}
