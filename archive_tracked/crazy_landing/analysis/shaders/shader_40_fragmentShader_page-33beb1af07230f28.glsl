// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
uniform sampler2D uBase0;
uniform sampler2D uBase1;
uniform vec2 uMapSize;
uniform float uRatio;
void main() {
    vec2 uv = vUv;
    vec4 base0 = texture2D(uBase0, uv);
    //   vec4 base1 = texture2D(uBase1, uv);
    //   vec4 color = mix(base0, base1, uRatio);
    gl_FragColor = base0;
}