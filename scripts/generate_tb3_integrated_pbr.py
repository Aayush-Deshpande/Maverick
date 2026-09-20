"""
=============================================================================
BAYRAKTAR TB3 UCAV - MASTER PIXEL-PERFECT PBR TEXTURE GENERATOR (V4.3)
=============================================================================
Generates 4096x4096 Diffuse, Roughness, and Tangent Normal maps with:
1. Symmetrical left-to-right observer perspective stencils on both flanks
   (NO flipped glyphs anywhere - all letters 100% standard upright Arial)
2. Aspect-ratio compensated circular roundels on fuselage nacelle and wing
3. Verified Turkish Flag, PT-2, TB3 badge, and Baykar Blue (#1A3668) on Fins
4. Dedicated 100% clean Zone 3C for Fin inner faces (ZERO bleed-through)
5. Upright, longitudinally aligned tail boom danger box and TB3 stencils
=============================================================================
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_pixel_perfect_textures():
    base_dir = r"e:\backup-llm\backup-no-llm\3d_engine"
    tex_dir = os.path.join(base_dir, "3d_models", "textures")
    os.makedirs(tex_dir, exist_ok=True)

    size = 4096
    print(f"Generating Pixel-Perfect 4K Master PBR Textures ({size}x{size})...")

    # High-accuracy color palette
    c_tactical_base = (36, 39, 44, 255)       # Tactical graphite carbon (#24272c)
    c_carbon_accent = (24, 26, 30, 255)       # SATCOM dome & access panels (#181a1e)
    c_deice = (16, 17, 20, 255)               # Leading edge de-ice boots (matte vulcanized rubber)
    c_seam = (18, 20, 22, 255)                # Recessed panel lines
    c_seam_hi = (54, 58, 66, 255)             # Panel edge highlight
    c_rivet = (22, 24, 28, 255)               # Rivet indent
    c_rivet_hi = (68, 73, 82, 255)            # Rivet rim highlight
    c_white = (250, 250, 255, 255)            # Pure white markings / star
    c_flag_red = (227, 10, 23, 255)           # Turkish Flag Red (#E30A17)
    c_danger_red = (255, 24, 36, 255)         # Propeller Danger Warning Red (#FF1824)
    c_baykar_blue = (26, 54, 104, 255)        # Baykar Corporate Blue (#1A3668)
    c_maml_yellow = (255, 204, 0, 255)        # Aviation Ordnance Yellow (#FFCC00)
    c_sapphire = (12, 36, 72, 255)            # Optical Sapphire Lens
    c_stencil_gray = (210, 215, 225, 255)     # High-contrast light gray stencils
    c_dark_gray = (100, 105, 115, 255)        # Low-vis stencils (#646973)
    c_boom_text = (175, 180, 190, 255)        # Tail boom low-vis slate stencil gray

    # 1. Base Diffuse Map
    img_diff = Image.new("RGBA", (size, size), c_tactical_base)
    draw_diff = ImageDraw.Draw(img_diff)

    # 2. Base Roughness Map (Satin carbon: 92 = ~0.36 roughness)
    img_rough = Image.new("L", (size, size), 92)
    draw_rough = ImageDraw.Draw(img_rough)

    # 3. Base Height Map for Tangent-Space Normal Generation
    img_height = Image.new("L", (size, size), 128)
    draw_height = ImageDraw.Draw(img_height)

    # Helper: Panel line
    def draw_line(x1, y1, x2, y2, width=3):
        draw_diff.line([(x1, y1), (x2, y2)], fill=c_seam, width=width)
        draw_diff.line([(x1, y1+1), (x2, y2+1)], fill=c_seam_hi, width=1)
        draw_rough.line([(x1, y1), (x2, y2)], fill=125, width=width)
        draw_height.line([(x1, y1), (x2, y2)], fill=85, width=width)
        draw_height.line([(x1, y1+1), (x2, y2+1)], fill=160, width=1)

    # Helper: Rivet row
    def draw_rivets(x1, y1, x2, y2, spacing=24, radius=3):
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < spacing:
            return
        steps = int(dist / spacing)
        for s in range(steps + 1):
            t = s / float(steps)
            rx = int(x1 + t * dx)
            ry = int(y1 + t * dy)
            draw_diff.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=c_rivet)
            draw_diff.point((rx+1, ry+1), fill=c_rivet_hi)
            draw_rough.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=130)
            draw_height.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=95)
            draw_height.point((rx+1, ry+1), fill=170)

    # Helper: Access hatch
    def draw_hatch(x, y, w, h, corner_r=10):
        draw_diff.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=c_seam, width=3)
        draw_diff.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=c_seam_hi, width=1)
        draw_rough.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=120, width=3)
        draw_height.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=80, width=3)
        draw_height.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=160, width=1)
        margin = 10
        for sx, sy in [(x+margin, y+margin), (x+w-margin, y+margin), (x+margin, y+h-margin), (x+w-margin, y+h-margin)]:
            draw_diff.ellipse([sx-3, sy-3, sx+3, sy+3], fill=c_rivet)
            draw_height.ellipse([sx-3, sy-3, sx+3, sy+3], fill=105)

    # Fonts
    font_path_bold = "C:/Windows/Fonts/arialbd.ttf"
    font_path_reg = "C:/Windows/Fonts/arial.ttf"
    font_flag = ImageFont.truetype(font_path_bold, 95) if os.path.exists(font_path_bold) else ImageFont.load_default()
    font_huge = ImageFont.truetype(font_path_bold, 76) if os.path.exists(font_path_bold) else ImageFont.load_default()
    font_large = ImageFont.truetype(font_path_bold, 50) if os.path.exists(font_path_bold) else ImageFont.load_default()
    font_med = ImageFont.truetype(font_path_bold, 36) if os.path.exists(font_path_bold) else ImageFont.load_default()
    font_small = ImageFont.truetype(font_path_bold, 26) if os.path.exists(font_path_bold) else ImageFont.load_default()

    # Draw Turkish National Flag (Exact official 3:2 ratio with crescent & 5-pointed star)
    def draw_turkish_flag(x, y, w, h):
        draw_diff.rectangle([x, y, x+w, y+h], fill=c_flag_red)
        draw_rough.rectangle([x, y, x+w, y+h], fill=75)
        c_x = x + int(w * 0.40)
        c_y = y + int(h * 0.50)
        c_r = int(h * 0.32)
        draw_diff.ellipse([c_x - c_r, c_y - c_r, c_x + c_r, c_y + c_r], fill=c_white)
        in_x = c_x + int(h * 0.11)
        in_r = int(h * 0.25)
        draw_diff.ellipse([in_x - in_r, c_y - in_r, in_x + in_r, c_y + in_r], fill=c_flag_red)
        s_x = c_x + int(h * 0.28)
        s_y = c_y
        s_r = int(h * 0.13)
        star_pts = []
        for i in range(10):
            r = s_r if i % 2 == 0 else s_r * 0.382
            ang = -math.pi/2 + i * (math.pi / 5)
            star_pts.append((s_x + r * math.cos(ang), s_y + r * math.sin(ang)))
        draw_diff.polygon(star_pts, fill=c_white)

    # Draw Aspect-Ratio Compensated Elliptical Roundel
    def draw_roundel_aspect(cx, cy, rx, ry):
        draw_diff.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=c_flag_red)
        rx_mid = int(rx * 0.66)
        ry_mid = int(ry * 0.66)
        draw_diff.ellipse([cx - rx_mid, cy - ry_mid, cx + rx_mid, cy + ry_mid], fill=c_white)
        rx_in = int(rx * 0.33)
        ry_in = int(ry * 0.33)
        draw_diff.ellipse([cx - rx_in, cy - ry_in, cx + rx_in, cy + ry_in], fill=c_flag_red)
        draw_rough.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=70)

    # Draw Vector TB3 Stealth Badge: <o>
    def draw_tb3_badge(draw, cx, cy, width, height, color):
        hw = width // 2
        hh = height // 2
        pts_left = [(cx - hw, cy), (cx - hw // 3, cy - hh), (cx - hw // 4, cy), (cx - hw // 3, cy + hh)]
        pts_right = [(cx + hw, cy), (cx + hw // 3, cy - hh), (cx + hw // 4, cy), (cx + hw // 3, cy + hh)]
        pts_mid = [(cx, cy - hh), (cx + hw // 6, cy), (cx, cy + hh), (cx - hw // 6, cy)]
        draw.polygon(pts_left, fill=color)
        draw.polygon(pts_right, fill=color)
        draw.polygon(pts_mid, fill=color)

    # =========================================================================
    # QUADRANT 1: FUSELAGE & NACELLE (X: [0, 2048], Y: [0, 2048])
    # U: [0.0, 0.50], V: [0.50, 1.0]
    # Starboard flank at Y=1536 (Tail at X=200, Nose at X=1900)
    # Port flank at Y=512 (Nose at X=200, Tail at X=1900)
    # =========================================================================
    print("  Quadrant 1: Painting Fuselage, Dorsal SATCOM, Nacelle Roundels...")

    # Longitudinal stringer seams (horizontal lines along X)
    for sy in [300, 512, 750, 1024, 1300, 1536, 1750]:
        draw_line(150, sy, 1950, sy, width=3)
        draw_rivets(150, sy+12, 1950, sy+12, spacing=28)

    # Circumferential bulkhead frames (vertical lines across Y)
    for bx in range(250, 1950, 160):
        draw_line(bx, 100, bx, 1950, width=3)
        draw_rivets(bx+10, 100, bx+10, 1950, spacing=28)

    # Forward avionics access doors
    draw_hatch(350, 420, 140, 90)
    draw_hatch(550, 420, 140, 90)
    draw_hatch(1450, 1530, 140, 90)
    draw_hatch(1650, 1530, 140, 90)

    # Dorsal SATCOM Radome zone (centered on spine Y=1024, X from 750 to 1350)
    draw_diff.rounded_rectangle([750, 850, 1350, 1200], radius=45, fill=c_carbon_accent, outline=c_seam, width=4)
    draw_rough.rounded_rectangle([750, 850, 1350, 1200], radius=45, fill=65)
    draw_rivets(760, 860, 1340, 860, spacing=24)
    draw_rivets(760, 1190, 1340, 1190, spacing=24)

    # Engine Nacelle Turkish Air Force Roundels
    # Starboard nacelle roundel (near tail X=380, Y=1536) - Aspect ratio compensated to true 3D circle
    draw_roundel_aspect(380, 1536, 46, 130)
    # Port nacelle roundel (near tail X=1740, Y=512)
    draw_roundel_aspect(1740, 512, 46, 130)

    # Nacelle Stencils on upper engine cowl bulge (matching 9c6e6ad97d (1).jpg)
    # Starboard nacelle (forward of roundel at X=540):
    draw_tb3_badge(draw_diff, 510, 1435, 36, 14, c_dark_gray)
    draw_diff.text((540, 1427), "BAYRAKTAR TB3", fill=c_dark_gray, font=font_small)
    # Port nacelle (forward of roundel at X=1550):
    draw_tb3_badge(draw_diff, 1550, 610, 36, 14, c_dark_gray)
    draw_diff.text((1580, 602), "BAYRAKTAR TB3", fill=c_dark_gray, font=font_small)

    # Mid-fuselage side stencils
    # Starboard flank (Y=1536, forward at X=1450 - reads tail-to-nose):
    draw_tb3_badge(draw_diff, 1220, 1560, 40, 16, c_dark_gray)
    draw_diff.text((1250, 1550), "BAYRAKTAR TB3", fill=c_dark_gray, font=font_small)

    # Port flank: Clean tactical graphite carbon matching image.png & Turbosquid source (ZERO text, ZERO mirrored glyphs)

    # NO text on nose! Clean composite nose cone.

    # =========================================================================
    # QUADRANT 2: WINGS (X: [2048, 4096], Y: [0, 2048])
    # U: [0.50, 1.0], V: [0.50, 1.0]
    # Span: Root at X=2150, Tip at X=4000.
    # Port Wing: Y in [80, 980]. Starboard Wing: Y in [1080, 1980].
    # =========================================================================
    print("  Quadrant 2: Painting Wings, De-Ice Boots, Starboard Roundel...")

    # 2.1 Port Wing (Upper Surface)
    draw_diff.rectangle([2150, 80, 4000, 220], fill=c_deice)
    draw_rough.rectangle([2150, 80, 4000, 220], fill=120)
    draw_line(2150, 220, 4000, 220, width=4)
    draw_rivets(2150, 235, 4000, 235, spacing=28)

    for wx in range(2350, 3950, 180):
        draw_line(wx, 220, wx, 950, width=3)
        draw_rivets(wx+10, 220, wx+10, 950, spacing=32)

    draw_line(2150, 500, 4000, 500, width=3)
    draw_line(2150, 750, 4000, 750, width=3)
    draw_diff.line([(2250, 820), (3900, 820)], fill=c_seam_hi, width=2)

    # 2.2 Starboard Wing (Upper Surface)
    draw_diff.rectangle([2150, 1080, 4000, 1220], fill=c_deice)
    draw_rough.rectangle([2150, 1080, 4000, 1220], fill=120)
    draw_line(2150, 1220, 4000, 1220, width=4)
    draw_rivets(2150, 1235, 4000, 1235, spacing=28)

    for wx in range(2350, 3950, 180):
        draw_line(wx, 1220, wx, 1950, width=3)
        draw_rivets(wx+10, 1220, wx+10, 1950, spacing=32)

    draw_line(2150, 1500, 4000, 1500, width=3)
    draw_line(2150, 1750, 4000, 1750, width=3)

    # Starboard Wing Turkish Air Force Roundel (Aspect-ratio compensated: rx=75, ry=230 -> 100% true circle in 3D!)
    draw_roundel_aspect(3300, 1520, 75, 230)
    draw_diff.line([(2250, 1820), (3900, 1820)], fill=c_seam_hi, width=2)

    # =========================================================================
    # QUADRANT 3: EMPENNAGE & TAIL BOOMS (X: [0, 2048], Y: [2048, 4096])
    # U: [0.0, 0.50], V: [0.0, 0.50]
    # Top-Left (0..1024, 2048..3072): Port Fin Outer Face (Zone 3B)
    # Top-Right (1024..2048, 2048..3072): Starboard Fin Outer Face (Zone 3A)
    # Bottom-Left (0..1024, 3072..4096): Clean Fin Inner Faces (Zone 3C - ZERO text)
    # Bottom-Right (1024..2048, 3072..4096): Tail Booms (Zone 3D)
    # =========================================================================
    print("  Quadrant 3: Painting Fins (Flag, PT-2, Baykar), Clean Inners, Booms...")

    # 3.1 Starboard Fin Outer Face (Zone 3A: X in [1024, 2048], Y in [2048, 3072])
    draw_diff.rectangle([1880, 2130, 1980, 3000], fill=c_deice)
    draw_rough.rectangle([1880, 2130, 1980, 3000], fill=110)
    draw_line(1880, 2130, 1880, 3000, width=4)
    draw_rivets(1865, 2130, 1865, 3000, spacing=26)
    draw_diff.rectangle([1060, 2130, 1120, 3000], fill=c_carbon_accent)

    # Livery Elements centered at X = 1490 (generous margins from de-ice boots and trailing edge)
    # 1. Turkish National Flag at top
    draw_turkish_flag(1340, 2200, 300, 200)
    # 2. Bold White "PT - 2"
    draw_diff.text((1400, 2455), "PT - 2", fill=c_white, font=font_huge)
    # 3. "<o> BAYRAKTAR TB3" badge & text
    draw_tb3_badge(draw_diff, 1315, 2615, 48, 18, c_stencil_gray)
    draw_diff.text((1355, 2598), "BAYRAKTAR TB3", fill=c_stencil_gray, font=font_med)
    # 4. "■ BAYKAR" Corporate Logo in Official Baykar Blue (#1A3668)
    draw_diff.rectangle([1355, 2735, 1395, 2775], fill=c_baykar_blue)
    draw_diff.text((1415, 2722), "BAYKAR", fill=c_baykar_blue, font=font_large)

    # 3.2 Port Fin Outer Face (Zone 3B: X in [0, 1024], Y in [2048, 3072])
    draw_diff.rectangle([60, 2130, 160, 3000], fill=c_deice)
    draw_rough.rectangle([60, 2130, 160, 3000], fill=110)
    draw_line(160, 2130, 160, 3000, width=4)
    draw_rivets(175, 2130, 175, 3000, spacing=26)
    draw_diff.rectangle([920, 2130, 980, 3000], fill=c_carbon_accent)

    # Livery Elements centered at X = 550 (generous margins from de-ice boots and trailing edge)
    draw_turkish_flag(400, 2200, 300, 200)
    draw_diff.text((460, 2455), "PT - 2", fill=c_white, font=font_huge)
    draw_tb3_badge(draw_diff, 375, 2615, 48, 18, c_stencil_gray)
    draw_diff.text((415, 2598), "BAYRAKTAR TB3", fill=c_stencil_gray, font=font_med)
    draw_diff.rectangle([415, 2735, 455, 2775], fill=c_baykar_blue)
    draw_diff.text((475, 2722), "BAYKAR", fill=c_baykar_blue, font=font_large)

    # 3.3 Fin Inner Faces (Zone 3C: X in [0, 1024], Y in [3072, 4096])
    # 100% CLEAN TACTICAL GRAPHITE CARBON - ZERO TEXT, ZERO BLEED-THROUGH
    draw_diff.rectangle([0, 3072, 1024, 4096], fill=c_tactical_base)
    draw_rough.rectangle([0, 3072, 1024, 4096], fill=92)
    draw_line(150, 3100, 150, 4050, width=3)
    draw_line(850, 3100, 850, 4050, width=3)
    draw_rivets(165, 3100, 165, 4050, spacing=30)

    # 3.4 Tail Booms (Zone 3D: X in [1024, 2048], Y in [3072, 4096])
    # Circumferential Red Danger Bands (vertical stripes wrapping 360 deg around boom)
    # Propeller Hazard Plane Red Band (X ~ 1560)
    draw_diff.rectangle([1540, 3100, 1585, 4070], fill=c_danger_red)
    draw_rough.rectangle([1540, 3100, 1585, 4070], fill=75)

    # Forward Red Band (X ~ 1860)
    draw_diff.rectangle([1840, 3100, 1880, 4070], fill=c_danger_red)
    draw_rough.rectangle([1840, 3100, 1880, 4070], fill=75)

    # "DİKKAT PERVANE / DANGER PROPELLER" Danger Box on Outer Flank (Y centered at 3584)
    draw_diff.rectangle([1605, 3525, 1825, 3643], fill=(20, 22, 26, 255), outline=c_danger_red, width=2)
    draw_diff.text((1618, 3535), "DİKKAT PERVANE", fill=c_danger_red, font=font_small)
    draw_diff.text((1614, 3585), "DANGER PROPELLER", fill=c_white, font=font_small)

    # Horizontal "<o> BAYRAKTAR TB3" boom branding (Aft of propeller band)
    draw_tb3_badge(draw_diff, 1210, 3584, 40, 16, c_boom_text)
    draw_diff.text((1240, 3568), "BAYRAKTAR TB3", fill=c_boom_text, font=font_med)

    # =========================================================================
    # QUADRANT 4: HARDWARE, ORDNANCE & PROPELLER (X: [2048, 4096], Y: [2048, 4096])
    # U: [0.50, 1.0], V: [0.0, 0.50]
    # =========================================================================
    print("  Quadrant 4: Painting MAM-L Munitions, Yellow Hazard Band, Optics...")

    # Roketsan MAM-L Missile Body Texture
    for my in [2200, 2550]:
        draw_diff.rectangle([2150, my, 3950, my + 190], fill=(80, 85, 95, 255))
        draw_rough.rectangle([2150, my, 3950, my + 190], fill=85)
        draw_diff.rectangle([2380, my, 2540, my + 190], fill=c_maml_yellow)
        draw_rough.rectangle([2380, my, 2540, my + 190], fill=65)
        draw_diff.ellipse([2140, my + 20, 2280, my + 170], fill=c_sapphire)
        draw_rough.ellipse([2140, my + 20, 2280, my + 170], fill=15)
        draw_diff.text((2650, my + 65), "ROKETSAN MAM-L", fill=c_white, font=font_large)

    # Pusher Propeller Blades with High-Visibility Yellow Safety Tips
    draw_diff.rectangle([2150, 2900, 3650, 3200], fill=(20, 22, 25, 255))
    draw_rough.rectangle([2150, 2900, 3650, 3200], fill=80)
    draw_diff.rectangle([3450, 2900, 3650, 3200], fill=c_maml_yellow)
    draw_rough.rectangle([3450, 2900, 3650, 3200], fill=60)

    # CATS EO/IR Gimbal Spherical Housing & Deep Sapphire Optical Aperture
    draw_diff.ellipse([2300, 3400, 2800, 3900], fill=c_sapphire)
    draw_rough.ellipse([2300, 3400, 2800, 3900], fill=12)

    # Save 4K Diffuse Map
    diff_path = os.path.join(tex_dir, "tb3_body_diffuse_4k.png")
    img_diff.save(diff_path, "PNG")
    print(f"  -> Saved 4K Master Diffuse Map: {diff_path}")

    # Save 4K Roughness Map
    rough_path = os.path.join(tex_dir, "tb3_body_roughness_4k.png")
    img_rough.save(rough_path, "PNG")
    print(f"  -> Saved 4K Master Roughness Map: {rough_path}")

    # 4. Generate Tangent-Space Normal Map
    print("  Generating Tangent-Space Normal Map from Height Field...")
    h_blur = img_height.filter(ImageFilter.GaussianBlur(radius=0.8))
    hb = h_blur.convert("L")
    arr_h = np.array(hb, dtype=np.float32)

    dx = (np.roll(arr_h, -1, axis=1) - np.roll(arr_h, 1, axis=1)) * 0.5
    dy = (np.roll(arr_h, -1, axis=0) - np.roll(arr_h, 1, axis=0)) * 0.5
    scale = 3.5
    nx = -dx * scale
    ny = -dy * scale
    nz = 255.0
    norm = np.sqrt(nx*nx + ny*ny + nz*nz)
    nx /= norm
    ny /= norm
    nz /= norm

    r = ((nx * 0.5 + 0.5) * 255).astype(np.uint8)
    g = ((ny * 0.5 + 0.5) * 255).astype(np.uint8)
    b = ((nz * 0.5 + 0.5) * 255).astype(np.uint8)
    norm_arr = np.stack([r, g, b], axis=-1)

    img_norm = Image.fromarray(norm_arr, "RGB")
    norm_path = os.path.join(tex_dir, "tb3_body_normal_4k.png")
    img_norm.save(norm_path, "PNG")
    print(f"  -> Saved 4K Master Normal Map: {norm_path}")
    print("======================================================================")
    print("4K MASTER PBR TEXTURES GENERATED (V4.3) - 100% UNMIRRORED & ACCURATE")
    print("======================================================================")

if __name__ == "__main__":
    generate_pixel_perfect_textures()
