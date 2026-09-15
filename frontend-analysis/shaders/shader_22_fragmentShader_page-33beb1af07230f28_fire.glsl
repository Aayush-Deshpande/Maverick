// Extracted from page-33beb1af07230f28.js (fragmentShader)
// -----------------------------------------
#define GLSLIFY 1
uniform sampler2D uFireTexture;
uniform float uTime;
uniform float uSpeed;
uniform float uFramesPerRow;
uniform float uTextureColumns;
uniform float uColumnOffset;
uniform int uOffset;
uniform float uOpacity;
uniform float uHideRatio;
uniform vec2 uResolution;

varying vec2 vUv;

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

void main() {
    vec2 screenUv = computeScreenUv();
    float hideMask = screenUv.x < uHideRatio ? 0.0 : 1.0;
    
    if (hideMask < 0.001) {
        discard;
    }
    
    float totalFrames = uFramesPerRow * uFramesPerRow;
    float frameIndex = mod(floor(uTime * uSpeed) + float(uOffset), totalFrames);
    
    float row = floor(frameIndex / uFramesPerRow);
    float col = mod(frameIndex, uFramesPerRow);
    
    vec2 frameSize = vec2(1.0 / uTextureColumns, 1.0 / uFramesPerRow);
    vec2 frameOffset = vec2((uColumnOffset + col) / uTextureColumns, row / uFramesPerRow);

    vec2 frameUv = vUv * frameSize + frameOffset;
    
    vec4 color = texture2D(uFireTexture, frameUv);
    
    gl_FragColor = color;

    gl_FragColor.a *= uOpacity ;
}
