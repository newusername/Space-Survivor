uniform vec2 pos_uv;
uniform vec3 color;
uniform float size;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float distance = distance(v_uv, pos_uv);

    float fade = 1.5;
    float strength = pow(1.0 / distance * size, fade);

    vec3 rgb_color = strength * color;

    rgb_color = 1.0 - exp( -rgb_color );

    fragColor = vec4(rgb_color, strength);
}
