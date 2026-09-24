"""
=============================================================================
BAYRAKTAR TB3 UCAV - 4K MASTER PBR TEXTURE GENERATOR
Generates cinema-grade 4096x4096 Diffuse, Roughness, and Normal maps:
- Tactical military gray satin polyurethane (#787d85)
- Panel lines, flush counter-sunk rivet rows, and access hatches
- Stencil typography: "BAYRAKTAR TB3", "PT-2", "BAYKAR"
- Danger Propeller warning bands ("DİKKAT PERVANE / DANGER PROPELLER")
- High-res Turkish flags and Turkish Air Force roundels
- "NO STEP" warning zones and wing walkway markings
=============================================================================
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_textures():
    base_dir = r"e:\backup-llm\backup-no-llm\3d_engine"
    tex_dir = os.path.join(base_dir, "3d_models", "textures")
    os.makedirs(tex_dir, exist_ok=True)

    size = 4096
    print(f"Generating 4K Texture Maps ({size}x{size})...")

    # Colors (Linear & sRGB)
    c_gray = (122, 127, 135, 255)         # Tactical Satin Gray #7a7f87
    c_gray_dark = (95, 100, 108, 255)     # Darker composite panels
    c_deice = (28, 30, 34, 255)           # Leading edge de-icing boot
    c_seam = (70, 74, 80, 255)            # Recessed panel seam
    c_seam_hi = (155, 160, 168, 255)      # Panel edge highlight
    c_rivet = (85, 90, 96, 255)           # Rivet head indent
    c_rivet_hi = (165, 170, 178, 255)     # Rivet specular rim
    c_white = (245, 245, 250, 255)        # Stencils / markings
    c_black = (18, 18, 20, 255)           # Stencils / markings
    c_turk_red = (227, 10, 23, 255)       # Flag & Roundel Red
    c_hazard_yellow = (240, 195, 15, 255) # Hazard stripes

    # 1. Base Diffuse Map
    img_diff = Image.new("RGBA", (size, size), c_gray)
    draw_diff = ImageDraw.Draw(img_diff)

    # 2. Base Roughness Map (Grayscale: 0 = mirror, 255 = rough)
    # Tactical gray is satin: value ~105 (0.41 roughness)
    img_rough = Image.new("L", (size, size), 105)
    draw_rough = ImageDraw.Draw(img_rough)

    # 3. Base Bump/Height Map for Normal Map conversion
    img_height = Image.new("L", (size, size), 128)
    draw_height = ImageDraw.Draw(img_height)

    # Helper: draw a panel line with highlight and groove
    def draw_panel_line(x1, y1, x2, y2, width=3):
        draw_diff.line([(x1, y1), (x2, y2)], fill=c_seam, width=width)
        draw_diff.line([(x1, y1+1), (x2, y2+1)], fill=c_seam_hi, width=1)
        draw_rough.line([(x1, y1), (x2, y2)], fill=135, width=width)
        draw_height.line([(x1, y1), (x2, y2)], fill=80, width=width)
        draw_height.line([(x1, y1+1), (x2, y2+1)], fill=160, width=1)

    # Helper: draw a rivet row
    def draw_rivet_row(x1, y1, x2, y2, spacing=24, radius=3):
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
            draw_rough.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=140)
            draw_height.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=95)
            draw_height.point((rx+1, ry+1), fill=175)

    # Helper: draw an access door / hatch
    def draw_access_hatch(x, y, w, h, corner_r=12, has_screws=True):
        # Groove
        draw_diff.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=c_seam, width=3)
        draw_diff.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=c_seam_hi, width=1)
        draw_rough.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=130, width=3)
        draw_height.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=75, width=3)
        draw_height.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=170, width=1)

        if has_screws:
            margin = 12
            corners = [(x+margin, y+margin), (x+w-margin, y+margin),
                       (x+margin, y+h-margin), (x+w-margin, y+h-margin)]
            if w > 120:
                corners.extend([(x+w//2, y+margin), (x+w//2, y+h-margin)])
            for cx, cy in corners:
                draw_diff.ellipse([cx-4, cy-4, cx+4, cy+4], fill=c_rivet)
                draw_diff.line([(cx-2, cy), (cx+2, cy)], fill=c_seam, width=1)
                draw_height.ellipse([cx-4, cy-4, cx+4, cy+4], fill=100)

    # Fonts
    font_bold_huge = None
    font_bold_large = None
    font_bold_med = None
    font_small = None
    try:
        font_bold_huge = ImageFont.truetype("arialbd.ttf", 96)
        font_bold_large = ImageFont.truetype("arialbd.ttf", 64)
        font_bold_med = ImageFont.truetype("arialbd.ttf", 44)
        font_small = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font_bold_huge = ImageFont.load_default()
        font_bold_large = ImageFont.load_default()
        font_bold_med = ImageFont.load_default()
        font_small = ImageFont.load_default()

    def draw_turkish_flag(x, y, w, h):
        draw_diff.rectangle([x, y, x+w, y+h], fill=c_turk_red)
        draw_rough.rectangle([x, y, x+w, y+h], fill=95)
        c_x = x + int(w * 0.42)
        c_y = y + int(h * 0.50)
        c_r = int(h * 0.32)
        draw_diff.ellipse([c_x - c_r, c_y - c_r, c_x + c_r, c_y + c_r], fill=c_white)
        in_x = c_x + int(h * 0.10)
        in_r = int(h * 0.25)
        draw_diff.ellipse([in_x - in_r, c_y - in_r, in_x + in_r, c_y + in_r], fill=c_turk_red)
        s_x = c_x + int(h * 0.26)
        s_y = c_y
        s_r = int(h * 0.12)
        star_pts = []
        for i in range(10):
            r = s_r if i % 2 == 0 else s_r * 0.42
            ang = -math.pi/2 + i * (math.pi / 5)
            star_pts.append((s_x + r * math.cos(ang), s_y + r * math.sin(ang)))
        draw_diff.polygon(star_pts, fill=c_white)

    def draw_roundel(cx, cy, radius):
        draw_diff.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=c_turk_red)
        r_mid = int(radius * 0.66)
        draw_diff.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], fill=c_white)
        r_in = int(radius * 0.33)
        draw_diff.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=c_turk_red)
        draw_rough.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=90)

    def draw_propeller_warning_band(x, y, w, h):
        band_w = int(w * 0.12)
        draw_diff.rectangle([x, y, x + band_w, y + h], fill=c_turk_red)
        draw_diff.rectangle([x + w - band_w, y, x + w, y + h], fill=c_turk_red)
        draw_diff.rectangle([x + band_w, y, x + w - band_w, y + h], fill=(30, 32, 36, 255))
        draw_rough.rectangle([x, y, x + w, y + h], fill=110)
        draw_diff.text((x + band_w + 24, y + 16), "DİKKAT PERVANE", fill=c_turk_red, font=font_bold_med)
        draw_diff.text((x + band_w + 24, y + 68), "DANGER PROPELLER", fill=c_white, font=font_bold_med)

    print("  Drawing Fuselage Panel Lines & Inspection Hatches...")
    draw_panel_line(150, 450, 2000, 450, width=4)
    draw_panel_line(150, 750, 2000, 750, width=4)
    draw_rivet_row(150, 465, 2000, 465, spacing=32)
    draw_rivet_row(150, 735, 2000, 735, spacing=32)

    for fx in range(350, 1950, 220):
        draw_panel_line(fx, 300, fx, 900, width=3)
        draw_rivet_row(fx+15, 300, fx+15, 900, spacing=28)
        draw_rivet_row(fx-15, 300, fx-15, 900, spacing=28)

    hatch_configs = [
        (480, 520, 140, 90), (660, 520, 160, 90), (860, 520, 140, 90),
        (1040, 520, 150, 90), (1230, 520, 180, 110), (1450, 520, 140, 90),
        (580, 630, 220, 80), (840, 630, 240, 80), (1120, 630, 220, 80),
        (1380, 630, 180, 80), (1600, 550, 220, 140)
    ]
    for hx, hy, hw, hh in hatch_configs:
        draw_access_hatch(hx, hy, hw, hh, corner_r=10, has_screws=True)

    print("  Drawing Wings, Spar Lines, Rib Stations & De-Ice Boots...")
    for wy in [1250, 1550, 1850]:
        draw_panel_line(150, wy, 3950, wy, width=3)
        draw_rivet_row(150, wy+12, 3950, wy+12, spacing=36)
    for wx in range(300, 3900, 260):
        draw_panel_line(wx, 1100, wx, 2000, width=3)
        draw_rivet_row(wx+12, 1100, wx+12, 2000, spacing=32)

    draw_diff.rectangle([2100, 100, 3950, 380], fill=c_deice)
    draw_rough.rectangle([2100, 100, 3950, 380], fill=80)
    draw_panel_line(2100, 380, 3950, 380, width=4)
    draw_rivet_row(2100, 395, 3950, 395, spacing=28)

    print("  Drawing Tail Booms, Fins, Markings & Flags...")
    for by in [2200, 2450]:
        draw_panel_line(200, by, 2200, by, width=3)
        draw_rivet_row(200, by+15, 2200, by+15, spacing=30)
    draw_propeller_warning_band(800, 2180, 520, 140)
    draw_propeller_warning_band(800, 2430, 520, 140)

    draw_diff.text((1400, 2215), "BAYRAKTAR TB3", fill=c_black, font=font_bold_large)
    draw_diff.text((1400, 2465), "BAYRAKTAR TB3", fill=c_black, font=font_bold_large)

    draw_turkish_flag(2600, 2200, 340, 220)
    draw_turkish_flag(3300, 2200, 340, 220)

    draw_diff.text((2680, 2460), "PT - 2", fill=c_black, font=font_bold_huge)
    draw_diff.text((3380, 2460), "PT - 2", fill=c_black, font=font_bold_huge)

    draw_diff.text((2620, 2600), "BAYRAKTAR TB3", fill=(45, 48, 55, 255), font=font_bold_med)
    draw_diff.text((3320, 2600), "BAYRAKTAR TB3", fill=(45, 48, 55, 255), font=font_bold_med)
    draw_diff.text((2660, 2670), "■ BAYKAR", fill=c_black, font=font_bold_large)
    draw_diff.text((3360, 2670), "■ BAYKAR", fill=c_black, font=font_bold_large)

    draw_roundel(2750, 3200, 240)
    draw_roundel(3550, 3200, 240)
    draw_roundel(1100, 3200, 180)
    draw_roundel(1700, 3200, 180)

    draw_diff.text((400, 3500), "◄► BAYRAKTAR TB3", fill=(35, 38, 44, 255), font=font_bold_huge)
    draw_diff.text((400, 3700), "◄► BAYRAKTAR TB3", fill=(35, 38, 44, 255), font=font_bold_huge)

    for step_x in range(2100, 3800, 350):
        draw_diff.text((step_x, 1510), "NO STEP", fill=c_turk_red, font=font_small)
        draw_diff.line([(step_x - 40, 1500), (step_x + 160, 1500)], fill=c_turk_red, width=2)
        draw_diff.line([(step_x - 40, 1545), (step_x + 160, 1545)], fill=c_turk_red, width=2)

    diff_path = os.path.join(tex_dir, "tb3_master_diffuse_4k.png")
    img_diff.save(diff_path, "PNG")
    print(f"  -> Saved 4K Diffuse Map: {diff_path}")

    rough_path = os.path.join(tex_dir, "tb3_master_roughness_4k.png")
    img_rough.save(rough_path, "PNG")
    print(f"  -> Saved 4K Roughness Map: {rough_path}")

    print("  Calculating Tangent-Space Normal Map...")
    # Generate Normal map directly with PIL kernel
    # Faster normal map computation:
    h_blur = img_height.filter(ImageFilter.GaussianBlur(radius=0.8))
    hb = h_blur.convert("L")
    w, h = size, size

    import numpy as np
    arr_h = np.array(hb, dtype=np.float32)
    # Sobel kernels
    dx = (np.roll(arr_h, -1, axis=1) - np.roll(arr_h, 1, axis=1)) * 0.5
    dy = (np.roll(arr_h, -1, axis=0) - np.roll(arr_h, 1, axis=0)) * 0.5
    scale = 3.0
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
    norm_path = os.path.join(tex_dir, "tb3_master_normal_4k.png")
    img_norm.save(norm_path, "PNG")
    print(f"  -> Saved 4K Normal Map: {norm_path}")
    print("All 4K Master PBR Textures Generated Successfully!")

if __name__ == "__main__":
    generate_textures()
