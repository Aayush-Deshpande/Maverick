// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
varying vec2 vUv;
varying vec3 vViewNormal;
varying vec3 vViewPosition;
varying vec3 vPosition;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;

uniform sampler2D uNoiseTexture;
uniform sampler2D uNormalMap;
uniform float uNormalScale;
uniform float uNormalIntensity;
uniform vec2 uNormalMapRepeat;

uniform vec2 uResolution;

uniform float uLightingIntensity;
uniform float uFresnelPower;
uniform float uNoiseInfluence;
uniform float uNoiseFrequency;
uniform float uLightingMix;
uniform vec3 uLightDirection;
uniform vec3 uLightColor;

const float PI = 3.14159265359;

vec3 inverseTransformDirection(in vec3 dir, in mat4 matrix) {
    return normalize((vec4(dir, 0.0) * matrix).xyz);
}

// Sample normal map with polar-aware blending to avoid pinching at top pole
vec3 sampleNormalMapPolarBlend(vec2 uv) {
    // Standard UV-based sample
    vec2 repeatedUv = uv * uNormalMapRepeat;
    vec3 uvSample = texture2D(uNormalMap, repeatedUv).xyz * 2.0 - 1.0;
    
    // Object-space XZ-based sample (rotates with sphere, avoids polar convergence)
    vec3 objectNormal = normalize(vPosition);  // For a sphere, normalized position = normal
    vec2 xzUv = objectNormal.xz * uNormalMapRepeat * 0.5 + 0.5;
    vec3 xzSample = texture2D(uNormalMap, xzUv).xyz * 2.0 - 1.0;
    
    // Only fix top pole: uv.y 1.0->0.9 = 100% XZ, 0.9->0.8 = blend, <0.8 = UV
    float polarBlend = smoothstep(0.8, 0.9, uv.y);
    
    return mix(uvSample, xzSample, polarBlend);
}

// Compute perturbed normal from normal map using tangent space
vec3 perturbNormal(vec3 worldNormal, vec3 worldPosition, vec2 uv) {
    // Sample normal map with polar-aware blending
    vec3 mapN = sampleNormalMapPolarBlend(uv);
    mapN.xy *= uNormalScale;
    
    // Compute tangent space basis using derivatives
    vec3 dp1 = dFdx(worldPosition);
    vec3 dp2 = dFdy(worldPosition);
    vec2 duv1 = dFdx(uv);
    vec2 duv2 = dFdy(uv);
    
    // Solve for tangent and bitangent
    vec3 dp2perp = cross(dp2, worldNormal);
    vec3 dp1perp = cross(worldNormal, dp1);
    vec3 T = dp2perp * duv1.x + dp1perp * duv2.x;
    vec3 B = dp2perp * duv1.y + dp1perp * duv2.y;
    
    // Construct TBN matrix
    float invmax = inversesqrt(max(dot(T, T), dot(B, B)));
    mat3 TBN = mat3(T * invmax, B * invmax, worldNormal);
    
    vec3 perturbedNormal = normalize(TBN * mapN);
    return normalize(mix(worldNormal, perturbedNormal, uNormalIntensity));
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
    
    // Compute aspect ratio from UV derivatives to correct stretching
    vec2 ddx = dFdx(gridUV);
    vec2 ddy = dFdy(gridUV);
    float scaleX = length(vec2(ddx.x, ddy.x));
    float scaleY = length(vec2(ddx.y, ddy.y));
    float aspect = scaleX / max(scaleY, 0.0001);
    
    // Apply aspect correction to make dots circular
    vec2 correctedDist = distToIntersection * vec2(1.0, aspect);
    float dist = length(correctedDist);
    
    vec2 uvDeriv = vec2(scaleX, scaleY);
    float maxDeriv = max(uvDeriv.x, uvDeriv.y);
    float dotAA = max(maxDeriv * 2.0, 0.01);
    return 1.0 - smoothstep(size - dotAA, size + dotAA, dist);
}

float computeGridMask() {
    // UV-based grid for sphere
    vec2 gridUV = vUv * vec2(40., 25.);

    float colat = vUv.y * PI;                
    float scaleFactor = max(sin(colat), 0.15);        // clamp to avoid blowing up at poles

    vec2 lineWidth = vec2(0.02 / scaleFactor, 0.02);
    lineWidth = min(lineWidth, vec2(0.49));   

    vec2 grid2 = getGrid(gridUV, lineWidth);
    float grid = max(grid2.x, grid2.y);

    float dotSize = 0.0175 / scaleFactor;
    dotSize = min(dotSize, 0.49);
    float d = getDot(gridUV, dotSize);

    return max(0.25 * grid, 0.75 * d);
}

vec3 modifyNormalWithNoise(vec3 vertexNormalWorld) {
    // Sample noise from normal direction for spherical coverage
    // Blend xz and xy projections based on normal.y to avoid seams at poles
    vec2 noiseUV1 = vertexNormalWorld.xz * uNoiseFrequency;
    vec2 noiseUV2 = vertexNormalWorld.xy * uNoiseFrequency;
    
    float blendFactor = abs(vertexNormalWorld.y);
    vec4 noiseSample1 = texture2D(uNoiseTexture, noiseUV1);
    vec4 noiseSample2 = texture2D(uNoiseTexture, noiseUV2);
    float noiseMask = mix(noiseSample1.r, noiseSample2.r, blendFactor);
    
    float noiseHoleMask = smoothstep(0.0, 1.0, noiseMask);

    float noiseMixFactor = mix(1.0, noiseHoleMask, uNoiseInfluence);
    
    // Mix toward -normal (into the sphere)
    vec3 inwardDir = -vertexNormalWorld;
    
    vec3 modifiedNormal = mix(normalize(mix(vertexNormalWorld, inwardDir, 1.0 - noiseHoleMask)), vertexNormalWorld, noiseMixFactor);
    return normalize(modifiedNormal);
}

vec3 computeFresnelLighting(vec3 modifiedNormal, vec3 viewDir, vec3 lightDir) {
    float vertexNdL = max(0.0, dot(modifiedNormal, lightDir));
    float vertexNdV = max(dot(modifiedNormal, viewDir), 0.0);

    float fresnel = pow(1.0 - vertexNdV, uFresnelPower);

    vec3 litColor = vec3(4.0) * pow(vertexNdL, 8.0);
    litColor += 2. * uLightColor * pow(vertexNdL, 40.0) * pow(1.0 - vertexNdV, 40.0);
    litColor = pow(litColor, vec3(4.)) * 0.05;
    litColor += vec3(1.0) * uLightColor * fresnel * pow(vertexNdL, 4.0);
    litColor = pow(litColor, vec3(0.8)) * 2.;

    // Extra brightness boost for areas directly facing the light
    float directLight = pow(vertexNdL, 2.0);  // Soft falloff
    float hotspot = pow(vertexNdL, 4.0);      // Tight hotspot for really direct areas
    litColor += uLightColor * directLight * 1.25;
    litColor += uLightColor * hotspot * 0.5;

    litColor += vec3(1.) * uLightingIntensity;

    return litColor;
}

vec3 applyFresnelLightingToColor(vec3 baseColor) {
    // Start with world normal and apply normal map first (like StandardMaterial)
    vec3 vertexNormalWorld = normalize(vWorldNormal);
    vertexNormalWorld = perturbNormal(vertexNormalWorld, vWorldPosition, vUv);
    
    // Then apply noise modification on top
    vec3 modifiedNormal = modifyNormalWithNoise(vertexNormalWorld);

    vec3 viewDirView = normalize(vViewPosition);
    vec3 viewDir = inverseTransformDirection(viewDirView, viewMatrix);
    vec3 lightDir = normalize(uLightDirection);

    vec3 litColor = computeFresnelLighting(modifiedNormal, viewDir, lightDir);
    
    // Boost brightness for areas facing the light (similar to terrain's yBasedIntensity)
    float NdL = max(0.0, dot(modifiedNormal, lightDir));
    float lightFacingIntensity = 0.3 + 0.7 * NdL;  // Range 0.3 to 1.0
    litColor = pow(litColor, vec3(lightFacingIntensity * 1.5));  // Power boost like terrain
    litColor *= lightFacingIntensity;
    
    return mix(baseColor, baseColor * litColor, uLightingMix);
}

void main() {
    vec3 N = normalize(vWorldNormal);
    N = perturbNormal(N, vWorldPosition, vUv);

    float gridMask = computeGridMask();

    vec3 color = vec3(1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0);
    color = applyFresnelLightingToColor(color);

    vec3 lightDir = normalize(uLightDirection);
    float diffuse = dot(N, lightDir);
    float g = gridMask * (diffuse * 0.75 + 0.5);
    color += g * 0.5;

    gl_FragColor = vec4(color, 1.0);
}
