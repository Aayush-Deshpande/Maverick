// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
varying vec3 vViewNormal;
varying vec3 vWorldPosition;
varying vec3 vViewPosition;
varying vec3 vPosition;

uniform sampler2D uNoiseTexture;

uniform sampler2D uBaseTexture;
uniform sampler2D uCityTexture;

uniform bool uisCity;

uniform vec2 uResolution;
uniform float uDpr;
uniform float uHideRatio;

uniform vec3 uBgColor;

uniform float uLightingIntensity;
uniform float uFresnelPower;
uniform float uNoiseInfluence;
uniform float uNoiseFrequency;
uniform float uLightingMix;
uniform vec3 uLightDirection;
uniform vec3 uLightColor;

uniform float uFogStart;
uniform float uFogEnd;
uniform float uFogDensity;
uniform float uFogExponent;
uniform vec3 uFogSkyColor;
uniform float uFogBlendFactor;

vec3 inverseTransformDirection(in vec3 dir, in mat4 matrix) {
    return normalize((vec4(dir, 0.0) * matrix).xyz);
}

vec2 computeScreenUv() {
    vec2 screenUv = gl_FragCoord.xy / uResolution;
    screenUv = (screenUv - 0.5) / sqrt(2.0) + 0.5;
    vec2 center = vec2(0.5);
    float angle = radians(5.0 * 45.0);
    vec2 rotatedUv;
    rotatedUv.x = cos(angle) * (screenUv.x - center.x) - sin(angle) * (screenUv.y - center.y) + center.x;
    rotatedUv.y = sin(angle) * (screenUv.x - center.x) + cos(angle) * (screenUv.y - center.y) + center.y;
    screenUv = rotatedUv;
    return screenUv;
}

float computeScanr(vec2 screenUv) {
    return screenUv.x < uHideRatio ? 1.0 : 0.0;
}

vec3 applyFog(vec3 color, float distance) {\\
    float fogStart = uFogStart;
    float fogEnd = uFogEnd;
    float fogCurve = uFogExponent;
    
    float fogDistance = clamp((distance - uFogStart) / max(0.0001, uFogEnd - uFogStart), 0.0, 1.0);
    float fogAmount = pow(fogDistance, uFogExponent);

    fogAmount *= uFogDensity;
   
    fogAmount = mix(fogAmount, fogAmount * uFogBlendFactor, uFogBlendFactor);
    
    vec3 foggedColor = mix(color, uFogSkyColor, fogAmount);
    
    return foggedColor;
}

vec3 sampleMaterials() {
    vec4 textureColor = texture(uBaseTexture, vUv);
    vec4 cityColor = texture(uCityTexture, vUv);
    vec3 baseColor = textureColor.rgb;

    if (uisCity) {
        baseColor = mix(baseColor, cityColor.rgb, cityColor.a);
    }

    float distance = length(vViewPosition);

    baseColor = applyFog(baseColor, distance);

    return baseColor;
}

vec3 modifyNormalWithNoise(vec3 vertexNormalWorld) {
    float noise = texture2D(uNoiseTexture, vPosition.xz * uNoiseFrequency).r;
    float influence = uNoiseInfluence * noise;
    vec3 perturbedNormal = mix(vertexNormalWorld, vec3(0.0, -1.0, 0.0), influence);
    return normalize(perturbedNormal);
}

vec3 computeFresnelLighting(vec3 modifiedNormal, vec3 viewDir, vec3 lightDir) {
    float vertexNdL = max(0.0, dot(modifiedNormal, lightDir));
    float vertexNdV = max(dot(modifiedNormal, viewDir), 0.0);

    float fresnel = pow(1.0 - vertexNdV, uFresnelPower);

    vec3 litColor = vec3(4.0) * pow(vertexNdL, 8.0);
    litColor += 2. * uLightColor * pow(vertexNdL, 40.0) * pow(1.0 - vertexNdV, 40.0);
    litColor = pow(litColor, vec3(4.)) * 0.05;
    litColor += vec3(1.0) * uLightColor * fresnel * pow(vertexNdL, 4.0);
    litColor *= 0.2 + 0.8 * clamp(pow(1.0 - modifiedNormal.z, 5.0), 0.0, 1.0);
    litColor = pow(litColor, vec3(0.8)) * 2.;

    litColor += vec3(1.) * uLightingIntensity;

    return litColor;
}

vec3 applyFresnelLightingToColor(vec3 baseColor) {
    vec3 vertexNormal = normalize(vViewNormal);
    vec3 vertexNormalWorld = inverseTransformDirection(vertexNormal, viewMatrix);
    vec3 modifiedNormal = modifyNormalWithNoise(vertexNormalWorld);

    vec3 viewDirView = normalize(-vViewPosition);
    vec3 viewDir = inverseTransformDirection(viewDirView, viewMatrix);
    vec3 lightDir = normalize(uLightDirection);

    vec3 litColor = computeFresnelLighting(modifiedNormal, viewDir, lightDir);

    float yBasedIntensity = 1. -vUv.y;
    litColor = pow(litColor, vec3(yBasedIntensity * 2.));
    litColor *= yBasedIntensity;
    litColor += vPosition.y * 0.01;

    vec3 blended = mix(baseColor, baseColor * litColor, uLightingMix);
    float gray = dot(blended, vec3(0.299, 0.587, 0.114));
    return vec3(gray);
}

vec3 renderMappedTextureMode() {
    vec3 baseColor = sampleMaterials();

    vec2 screenUv = computeScreenUv();

    vec3 colorFinal;

    if(computeScanr(screenUv) > 0.5) {
        vec3 scanGridColor = vec3(1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0);
        scanGridColor = applyFresnelLightingToColor(scanGridColor);

        float border = uDpr / uResolution.x * 2.0;
        if(screenUv.x < uHideRatio + border && screenUv.x > uHideRatio - border) {
            scanGridColor += vec3(0.1, 0.1, 0.1);
        }
        colorFinal = scanGridColor;
    } else {
        colorFinal = baseColor;
    }

    return colorFinal;
}

void main() {
    vec3 outColor = renderMappedTextureMode();
    gl_FragColor = vec4(outColor, 1.0);
}
