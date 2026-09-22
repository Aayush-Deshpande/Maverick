// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vViewNormal;
varying vec2 vUv;
varying vec3 vModelPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;
varying vec3 vNormal;

uniform vec3 uColor;
uniform float uTime;

void main() {

    float fresnel = pow(
        1.0 - dot(
            normalize(vViewPosition),
            normalize(vViewNormal)
        ),
        3.0
    );
    
    float scan = vModelPosition.z * 7.0;
    scan -= uTime * 8.0;
    scan = fract(scan);
    scan = smoothstep(0.45, 0.55, scan);
    scan = 1.0 - scan;

    vec3 finalColor;

    float scanline = scan * 0.15;
    vec3 center = vec3(0., 0., -1.);
    float dist = distance(vModelPosition, center) * 0.8;
    
    finalColor = uColor - scanline;
    finalColor += dist * 0.45;

    gl_FragColor = vec4(finalColor, 1.);
}