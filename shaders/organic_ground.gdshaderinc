// Organic ground colour (Stage B0.1, D-61), shared by organic_ground.gdshader
// (the meadow's ground plane) and organic_path.gdshader (path patches blend to
// exactly this colour at their rims, so a patch has no hard edge). Pure
// arithmetic in world space: no textures, no extra draw calls, the same value
// on every renderer. The average colour stays close to the old flat ground.

uniform vec3 grass_lush : source_color = vec3(0.29, 0.52, 0.23);
uniform vec3 grass_dry : source_color = vec3(0.54, 0.6, 0.3);
uniform vec3 grass_dark : source_color = vec3(0.22, 0.40, 0.19);
uniform vec3 soil_hint : source_color = vec3(0.45, 0.43, 0.27);

float wg_hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float wg_value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = wg_hash(i);
	float b = wg_hash(i + vec2(1.0, 0.0));
	float c = wg_hash(i + vec2(0.0, 1.0));
	float d = wg_hash(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float wg_fbm(vec2 p) {
	return wg_value_noise(p) * 0.5 + wg_value_noise(p * 2.03 + 17.1) * 0.3 + wg_value_noise(p * 4.11 - 9.7) * 0.2;
}

vec3 ground_colour(vec2 xz) {
	// Broad meadow patches (~12 m): lusher and drier grass.
	float broad = wg_fbm(xz * 0.085);
	vec3 col = mix(grass_lush, grass_dry, smoothstep(0.35, 0.68, broad));
	// Darker clover-like drifts (~4 m).
	float mid = wg_fbm(xz * 0.27 + 31.0);
	col = mix(col, grass_dark, smoothstep(0.52, 0.76, mid) * 0.7);
	// Rare bare-soil hints.
	float bare = wg_value_noise(xz * 0.5 - 7.0);
	col = mix(col, soil_hint, smoothstep(0.82, 0.95, bare) * 0.35);
	// Fine blade speckle (~0.3 m), small amplitude so it never shimmers.
	float fine = wg_value_noise(xz * 3.3) * 0.6 + wg_value_noise(xz * 7.9) * 0.4;
	col *= 0.86 + 0.28 * fine;
	return col;
}
