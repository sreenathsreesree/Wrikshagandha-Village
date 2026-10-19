shader_type spatial;
render_mode blend_mix, cull_back, diffuse_lambert, specular_disabled;

// Pond shoreline (W1, D-63): a ring of wet earth round the pond, drawn on the
// shore mesh made offline by tools/art/generate_pond_edge.gd. Its inner lip
// lies just above the water's highest wave, so its irregular inner outline
// becomes the pond's visible edge and the water disc's hard circular rim is
// covered — water.gdshader is unchanged. Visual only: no collider, no
// navigation, nothing reads it.
// The mesh's vertex colour carries the shape: r = earth weight (1 on the bank,
// 0 from 5.0 m out and beyond its irregular earth line), g = wetness (1 at the
// water's edge). Underneath, the colour is what the meadow shows there without
// the ring: the ground (organic_ground.gdshaderinc) or, over one of the path
// patches listed in path_patches, that patch's own colour (the same arithmetic
// as organic_path.gdshader, copied verbatim below and checked by
// tools/check_project.py). The mesh stays above every patch wherever it shows
// earth, and where its earth weight is 0 its colour and flat lighting equal what
// lies beneath, so the ring meets the ground and the paths with no seam.
// Opaque — no transparency or discard.

#include "res://shaders/organic_ground.gdshaderinc"

uniform vec3 mud_light : source_color = vec3(0.47, 0.41, 0.3);
uniform vec3 mud_dark : source_color = vec3(0.37, 0.32, 0.23);
uniform vec3 mud_wet : source_color = vec3(0.2, 0.19, 0.15);
uniform vec3 bank_pebble : source_color = vec3(0.6, 0.58, 0.52);
// The meadow's path patches under the ring, in world space: (centre x, centre z,
// scale x, scale z) of each Terrain/Path cylinder (radius 1, 10 segments), and
// each patch's yaw in degrees (its rotation_degrees.y).
uniform vec4 path_patches[3];
uniform float path_yaws[3];

// organic_path.gdshader's colours (the same defaults).
uniform vec3 earth_light : source_color = vec3(0.66, 0.53, 0.35);
uniform vec3 earth_mid : source_color = vec3(0.56, 0.44, 0.29);
uniform vec3 earth_dark : source_color = vec3(0.42, 0.32, 0.21);
uniform vec3 pebble : source_color = vec3(0.74, 0.69, 0.6);

varying vec3 v_world;
varying vec2 v_shape;

void vertex() {
	// Lit exactly like the flat ground (the lip too), so no slope or rim shows.
	NORMAL = vec3(0.0, 1.0, 0.0);
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_shape = COLOR.rg;
}

// A path patch's v_r at a point, as its own shader sees it: the cylinder top is
// a fan of 10 triangles from the centre (v_r 0) to the rim (v_r 1), rim corners
// at local x = sin(a), z = cos(a), a = k * 36°, interpolated linearly. The point
// is taken into the patch's frame (undo its yaw, then its scale).
float patch_r(vec2 xz, vec4 p, float yaw_degrees) {
	vec2 d = xz - p.xy;
	float c = cos(radians(yaw_degrees));
	float s = sin(radians(yaw_degrees));
	vec2 q = vec2(d.x * c - d.y * s, d.x * s + d.y * c) / p.zw;
	float a = atan(q.x, q.y);
	if (a < 0.0) {
		a += TAU;
	}
	float mid = (floor(a / (TAU / 10.0)) + 0.5) * (TAU / 10.0);
	return dot(q, vec2(sin(mid), cos(mid))) / cos(PI / 10.0);
}

// organic_path.gdshader's earth colour and weight for a patch point (verbatim).
vec3 path_earth(vec2 xz, float v_r, out float earth_w) {
	float tone = wg_fbm(xz * 0.6 + 5.0);
	vec3 earth = mix(earth_mid, earth_light, smoothstep(0.3, 0.75, tone));
	float band = wg_value_noise(xz * 1.4 + 2.0);
	earth = mix(earth, earth_dark, smoothstep(0.62, 0.85, band) * 0.5 * (1.0 - v_r));
	float grit = wg_value_noise(xz * 9.0);
	earth = mix(earth, pebble, smoothstep(0.86, 0.97, grit) * 0.6);
	earth *= 0.92 + 0.16 * wg_value_noise(xz * 4.7 + 3.0);
	float edge = v_r + (wg_fbm(xz * 1.7 + 11.0) - 0.5) * 0.55;
	earth_w = 1.0 - smoothstep(0.55, 0.92, edge);
	earth_w *= 1.0 - smoothstep(0.8, 0.95, wg_value_noise(xz * 5.5 - 4.0)) * 0.6;
	earth_w *= 1.0 - smoothstep(0.9, 0.99, v_r);
	return earth;
}

void fragment() {
	vec2 xz = v_world.xz;
	// What lies beneath: the ground, or the topmost path patch (the one whose
	// v_r is smallest is the highest, so it is the one drawn).
	vec3 below = ground_colour(xz);
	float v_r = 2.0;
	for (int i = 0; i < 3; i++) {
		v_r = min(v_r, patch_r(xz, path_patches[i], path_yaws[i]));
	}
	float path_w = 0.0;
	if (v_r < 1.0) {
		vec3 earth = path_earth(xz, v_r, path_w);
		below = mix(below, earth, path_w);
	}
	// The bank: broad tone, a few pebbles on the drier part, darker and wetter
	// towards the water.
	float wet = smoothstep(0.0, 1.0, v_shape.y + (wg_value_noise(xz * 2.3 + 1.0) - 0.5) * 0.4);
	vec3 mud = mix(mud_dark, mud_light, smoothstep(0.3, 0.75, wg_fbm(xz * 0.9 + 3.0)));
	mud = mix(mud, bank_pebble, smoothstep(0.88, 0.97, wg_value_noise(xz * 10.0)) * 0.5 * (1.0 - v_shape.y));
	mud = mix(mud, mud_wet, wet);
	mud *= 0.93 + 0.14 * wg_value_noise(xz * 4.7 + 9.0);
	// Ragged earth line: noise moves it by at most a quarter of the weight, so
	// a weight of 0 stays exactly 0; grass creeps onto the dry bank in tufts;
	// on a path only the wet edge shows (the path runs down to the water).
	float earth_w = smoothstep(0.25, 0.75, v_shape.x + (wg_fbm(xz * 1.8 + 7.0) - 0.5) * 0.5);
	earth_w *= 1.0 - smoothstep(0.72, 0.92, wg_value_noise(xz * 4.2 - 4.0)) * 0.75 * (1.0 - v_shape.y);
	earth_w *= mix(1.0, wet, path_w);
	ALBEDO = mix(below, mud, earth_w);
	ROUGHNESS = mix(mix(0.95, 1.0, path_w), 1.0, earth_w);
}
