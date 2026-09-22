// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vViewNormal;
varying vec2 vUv;
varying vec3 vModelPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;
varying vec3 vNormal;

uniform vec2 uResolution;
uniform float uDpr;
uniform vec3 uColor;
uniform vec3 uRed;
uniform vec3 uBlue;
uniform float uRedMixer;
uniform float uBlueMixer;
uniform vec3 uSunDirection;
uniform float uAlpha;
uniform float uTime;

const float PI = 3.14159265359;

#define saturate(x) clamp(x, 0.0, 1.0)

vec3 inverseTransformDirection(in vec3 dir, in mat4 matrix) {
    return normalize((vec4(dir, 0.0) * matrix).xyz);
}

void main() {

    
    float fresnel = pow(
        1.0 - dot(
            normalize(vViewPosition),
            normalize(vViewNormal)
        ),
    5.0
    );

    float scan = vModelPosition.z * 7.0;
    scan -= uTime * 4.0;

    scan = fract(scan);
    scan = smoothstep(0.45, 0.55, scan);
    scan = 1.0 - scan;

    float scanline = scan * 0.1;

    vec3 N = inverseTransformDirection(normalize(vViewNormal), viewMatrix);
    vec3 V = normalize(cameraPosition - vWorldPosition);
    vec3 L = uSunDirection;

    float NdL = max(0.0, dot(N, L));
    float NdV = max(0.0, dot(N, V));
    vec3 col = mix(uColor, uRed, uRedMixer);
    col = mix(col, uBlue, uBlueMixer);
    vec3 color = col * (0.3 + 0.7 * NdL);
    color += fresnel * 2.;
    color -= scanline * 0.2;

    float border = uDpr / uResolution.x;

    gl_FragColor = vec4(color, uAlpha);
}
