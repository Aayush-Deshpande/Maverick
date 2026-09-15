// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vViewNormal;
varying vec2 vUv;
varying vec3 vModelPosition;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;

uniform sampler2D uSceneTexture;
uniform sampler2D uNoiseTexture;
uniform vec2 uResolution;
uniform float uTime;
uniform float uDistortionStrength;
uniform float uSpeedMultiplier;
uniform bool isMobile;

void main() {
    vec2 screenUv = gl_FragCoord.xy / uResolution;

    float noise = texture2D(uNoiseTexture, vec2(vUv.x, vUv.y * 3. - (uTime * 4.))).r;
    vec2 distortion = (vec2(noise, noise) - 0.5) * uDistortionStrength;

    float shake = (noise + sin(uTime * 99.0)) * 0.001;

    float fresnel = pow(1.0 - dot(normalize(vViewPosition), normalize(vViewNormal)), 2.0) - noise * 0.2;
    // Boost stretches the flame further down the cone (geometry has headroom past 0.5)
    float heightMask = smoothstep(0.5 + 0.35 * uSpeedMultiplier, 0., vUv.y + pow(noise, 4.) * 0.1);
    
    vec4 sceneColor = isMobile 
        ? vec4(0.0, 0.0, 0.0, 0.0) 
        : texture2D(uSceneTexture, screenUv + (distortion * 0.8 * heightMask));

    vec3 color = sceneColor.rgb;
    float radial = 1.0 - abs(vUv.x - 0.5) * 2.0;
    radial = clamp(radial, 0.0, 1.0);
    float ripple = cos((vUv.y * 100.0 - uTime * 8.0) + sin(uTime * 99.0)) * 0.5 + 0.5;
    float diamonds = pow(ripple * radial, 2.);
    vec3 gradientColor = vec3(251.0/255.0, 130.0/255.0, 3.0/255.0) + diamonds * (1.2 + 1.3 * uSpeedMultiplier); // #fb8203

    // Afterburner: flame body goes yellow, core goes blue under boost
    gradientColor = mix(gradientColor, vec3(1.3, 1.05, 0.35), uSpeedMultiplier * 0.5);
    gradientColor = mix(gradientColor, vec3(0.55, 0.75, 1.6), uSpeedMultiplier * pow(radial, 2.0) * 0.75);

    float gradientStrength = smoothstep(0.3 + 0.4 * uSpeedMultiplier, 0.0, vUv.y) * heightMask;

    vec3 flameColor = gradientColor * gradientStrength * pow(noise, 4.) * (1. - fresnel * noise -.5);
    color += flameColor * (3.0 + 16.0 * uSpeedMultiplier);

    float colorLum = dot(color, vec3(0.299, 0.587, 0.114));
    float a = isMobile ? smoothstep(0.0, 0.2, colorLum) : 1.;

    gl_FragColor = vec4(vec3(color * 1. - (fresnel *(0.02 * noise) + shake) * heightMask), a);
}
