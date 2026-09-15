// Extracted from 6288-8ba84c795cccb5ec.js (vertexShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}