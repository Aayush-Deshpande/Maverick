// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec3 vPosition;
varying vec3 vWorldPosition;
varying vec2 vUv;

uniform vec2 uResolution;
uniform float uDpr;
uniform float uHideRatio;
uniform float uGridDensity;
uniform float uOffsetZ;
uniform float uDotSize;
uniform float uDotOpacity;
uniform float uLateralFade;

vec2 computeScreenUv() {
    vec2 screenUv = gl_FragCoord.xy / uResolution;
    screenUv = (screenUv - 0.5) / sqrt(2.0) + 0.5;
    vec2 center = vec2(0.5);
    float angle = radians(5.0 * 45.0);
    vec2 rotatedUv;
    rotatedUv.x = cos(angle) * (screenUv.x - center.x) - sin(angle) * (screenUv.y - center.y) + center.x;
    rotatedUv.y = sin(angle) * (screenUv.x - center.x) + cos(angle) * (screenUv.y - center.y) + center.y;
    return rotatedUv;
}

float computeScanr(vec2 screenUv) {
    return screenUv.x < uHideRatio ? 1.0 : 0.0;
}

vec2 getGrid(in vec2 uv, vec2 lineWidth) {
    vec2 ddx = dFdx(uv);
    vec2 ddy = dFdy(uv);
    vec2 uvDeriv = vec2(length(vec2(ddx.x, ddy.x)), length(vec2(ddx.y, ddy.y)));
    bool invertLineX = lineWidth.x > 0.5;
    bool invertLineY = lineWidth.y > 0.5;
    vec2 targetWidth = vec2(invertLineX ? 1.0 - lineWidth.x : lineWidth.x, invertLineY ? 1.0 - lineWidth.y : lineWidth.y);
    vec2 drawWidth = clamp(targetWidth, uvDeriv, vec2(0.5));
    vec2 lineAA = uvDeriv * 1.5;
    vec2 gridUV = abs(fract(uv) * 2.0 - 1.0);
    gridUV.x = invertLineX ? gridUV.x : 1.0 - gridUV.x;
    gridUV.y = invertLineY ? gridUV.y : 1.0 - gridUV.y;
    vec2 grid2 = smoothstep(drawWidth + lineAA, drawWidth - lineAA, gridUV);
    grid2 *= clamp(targetWidth / drawWidth, 0.0, 1.0);
    grid2 = mix(grid2, targetWidth, clamp(uvDeriv * 2.0 - 1.0, 0.0, 1.0));
    grid2.x = invertLineX ? 1.0 - grid2.x : grid2.x;
    grid2.y = invertLineY ? 1.0 - grid2.y : grid2.y;
    return grid2;
}

float getDot(in vec2 gridUV, float size) {
    vec2 rounded = round(gridUV);
    vec2 distToIntersection = abs(gridUV - rounded);
    float dist = length(distToIntersection);
    vec2 ddx = dFdx(gridUV);
    vec2 ddy = dFdy(gridUV);
    vec2 uvDeriv = vec2(length(vec2(ddx.x, ddy.x)), length(vec2(ddx.y, ddy.y)));
    float maxDeriv = max(uvDeriv.x, uvDeriv.y);
    float dotAA = max(maxDeriv * 2.0, 0.01);
    return 1.0 - smoothstep(size - dotAA, size + dotAA, dist);
}

float computeFadeMultiplier(vec2 screenUvNormalized) {
    float leftFade   = smoothstep(0.0, uLateralFade, screenUvNormalized.x);
    float rightFade  = 1.0 - smoothstep(1.0 - uLateralFade, 1.0, screenUvNormalized.x);
    float aspect = uResolution.y / uResolution.x;
    float vFade = uLateralFade / aspect;
    float bottomFade = smoothstep(0.0, vFade, screenUvNormalized.y);
    float topFade    = 1.0 - smoothstep(1.0 - vFade, 1.0, screenUvNormalized.y);
    float lateralFadeFactor = min(min(leftFade, rightFade), min(topFade, bottomFade));
    
    return lateralFadeFactor;
}

vec3 applyBorderHighlight(vec3 color, vec2 screenUv, float fadeMultiplier) {
    float border = 1.0 / uResolution.x;
    if(screenUv.x < uHideRatio + border && screenUv.x > uHideRatio - border) {
        color += vec3(0.1, 0.1, 0.1) * fadeMultiplier;
    }
    return color;
}

vec3 computeGridColor(float grid, float dot, float fadeMultiplier) {
    vec3 gridLineColor = vec3(1., 1., 1.) * grid * fadeMultiplier;
    gridLineColor += vec3(1., 1., 1.) * dot * fadeMultiplier;
    return gridLineColor;
}

float computeAlpha(float gridColor, float dot, float fadeMultiplier) {
    float gridAlpha = gridColor * 0.01;
    float dotAlpha = dot * 0.8 * fadeMultiplier;
    return max(gridAlpha, dotAlpha);
}

void main() {
    if (uHideRatio <= 0.001) discard;
    
    vec2 screenUv = computeScreenUv();
    float scanr = computeScanr(screenUv);
    if (scanr < 0.5) discard;
    
    vec2 screenUvNormalized = gl_FragCoord.xy / uResolution;
    float fadeMultiplier = computeFadeMultiplier(screenUvNormalized);
    
    vec2 gridUV = uGridDensity * vec2(vWorldPosition.x, vWorldPosition.z + uOffsetZ);
    float lineWidth = mix(0.001, 0.05, scanr);
    vec2 grid2 = getGrid(gridUV, vec2(lineWidth));
    float grid = max(grid2.x, grid2.y);
    float dot = getDot(gridUV, uDotSize) * uDotOpacity;
    
    vec3 color = computeGridColor(grid, dot, fadeMultiplier);
    color = applyBorderHighlight(color, screenUv, fadeMultiplier);
    float alpha = computeAlpha(color.r, dot, fadeMultiplier);

    color = vec3(fadeMultiplier);
    
    gl_FragColor = vec4(color, alpha);
    // gl_FragColor = vec4(1.);
}
