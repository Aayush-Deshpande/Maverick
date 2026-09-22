// Extracted from 6288-8ba84c795cccb5ec.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
uniform sampler2D uLogoTexture;
uniform vec3 uColor;
uniform vec2 uResolution;
uniform vec2 uTextureSize;
uniform vec2 uMeshSize;

float sampleTextureAlpha(vec2 sampleUv) {
    vec2 clampedUv = clamp(sampleUv, 0.0, 1.0);
    return texture2D(uLogoTexture, clampedUv).a;
}

void main() {
    vec2 uv = vUv;
    vec4 logoColor = texture2D(uLogoTexture, uv);
    

    float centerAlpha = logoColor.a;
    

    if (centerAlpha <= 0.5) {
        gl_FragColor = vec4(uColor, 0.0);
        return;
    }

    vec2 uvStep = vec2(1.0) / uMeshSize;
    float strokeDist = 2.0;
    
    float minNeighborAlpha = 1.0;
    
    // Sample 4 cardinal directions
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(strokeDist * uvStep.x, 0.0)));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(-strokeDist * uvStep.x, 0.0)));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(0.0, strokeDist * uvStep.y)));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(0.0, -strokeDist * uvStep.y)));
    
    // Sample 4 diagonal directions
    vec2 diag = vec2(strokeDist * uvStep.x, strokeDist * uvStep.y) * 0.707;
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + diag));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(-diag.x, diag.y)));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + vec2(diag.x, -diag.y)));
    minNeighborAlpha = min(minNeighborAlpha, sampleTextureAlpha(uv + -diag));
    
    float outlineAlpha = smoothstep(0.2, 0.8, 1.0 - minNeighborAlpha);
    
    float gradientPos = vUv.y;
    
    float gradientAlpha = 0.0;
    if (gradientPos >= 0.1) {
        float t = (gradientPos - 0.1) / 0.9;
        gradientAlpha = mix(0.0, 0.6, t);
    } else {
        gradientAlpha = 0.0;
    }

    vec3 finalColor = uColor;
    float finalAlpha = outlineAlpha * gradientAlpha;
    finalAlpha  = finalAlpha * 0.5;
    
    gl_FragColor = vec4(finalColor, finalAlpha);
}