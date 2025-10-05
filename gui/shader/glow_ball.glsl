uniform vec2 pos_uv;
uniform vec3 color;
uniform float size;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float distance = distance(v_uv, pos_uv);

    // Use an inverse 1/distance to set the fade
    float fade = 1.1;
    float strength = pow(1.0 / distance * size, fade);

    // Fade color
    vec3 rgb_color = strength * color;

    // Tone mapping
    rgb_color = 1.0 - exp( -rgb_color );

    // Output to the screen
    fragColor = vec4(rgb_color, strength);
}
