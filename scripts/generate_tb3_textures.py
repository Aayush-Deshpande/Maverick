"""
=============================================================================
BAYRAKTAR TB3 UCAV - MASTER 4K PBR TEXTURE ASSET GENERATOR
Generates cinema-quality 4096 x 4096 PBR texture maps:
1. tb3_body_diffuse.png, tb3_body_normal.png, tb3_body_roughness.png
2. tb3_parts_diffuse.png, tb3_parts_normal.png, tb3_parts_roughness.png
Matching the Turbosquid / MOLEX reference specifications:
- Tactical aviation satin gray (#7a7f87)
- Panel lines, flush rivets, and maintenance access hatches
- Black wing leading edge de-icing boots
- Conforming tail boom danger propeller warning bands
- Turkish Air Force roundels, flag fin emblems, PT-2 callsigns, Baykar logos
- 10-spoke alloy wheel rims with lug nuts and treaded rubber tires
- Carbon fiber propeller with stainless steel erosion tape and yellow tips
- Roketsan MAM-L laser-guided smart bombs
=============================================================================
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

output_dir = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\textures"
os.makedirs(output_dir, exist_ok=True)

print("======================================================================")
print("GENERATING 4K PBR TEXTURE SUITE FOR BAYRAKTAR TB3")
print("======================================================================")

SIZE = 4096

def get_font(size):
    font_paths = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_huge = get_font(180)
font_large = get_font(120)
font_med = get_font(75)
font_small = get_font(48)
font_tiny = get_font(30)

# Colors (sRGB)
COL_BODY_GRAY = (122, 127, 135, 255)       # Tactical satin gray #7a7f87
COL_BODY_DARK = (45, 48, 52, 255)          # Dark carbon / panel seams
COL_BLACK_BOOT = (28, 30, 34, 255)         # Wing leading edge de-ice boot
COL_WHITE = (255, 255, 255, 255)
COL_TURKISH_RED = (227, 10, 23, 255)       # Flag & roundel red
COL_DANGER_RED = (235, 25, 25, 255)        # Danger propeller red
COL_MAML_BODY = (185, 188, 192, 255)       # Light munition gray
COL_MAML_YELLOW = (245, 195, 25, 255)      # Explosive code band
COL_CHROME = (220, 222, 225, 255)          # Hydraulic / hardware
COL_TIRE_RUBBER = (22, 24, 26, 255)        # Treaded tire rubber
COL_ALLOY_RIM = (195, 200, 206, 255)       # Wheel rim metal
COL_NORMAL_BASE = (128, 128, 255)          # Tangent flat normal (0, 0, 1)

# Helper: Draw Turkish Air Force Roundel
def draw_roundel(draw, x, y, radius):
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=COL_TURKISH_RED)
    r_mid = radius * 0.666
    draw.ellipse([x - r_mid, y - r_mid, x + r_mid, y + r_mid], fill=COL_WHITE)
    r_in = radius * 0.333
    draw.ellipse([x - r_in, y - r_in, x + r_in, y + r_in], fill=COL_TURKISH_RED)

# Helper: Draw Turkish National Flag
def draw_flag(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=COL_TURKISH_RED)
    c_x = x + w * 0.38
    c_y = y + h * 0.50
    r_outer = h * 0.30
    draw.ellipse([c_x - r_outer, c_y - r_outer, c_x + r_outer, c_y + r_outer], fill=COL_WHITE)
    c_in_x = c_x + r_outer * 0.28
    c_in_y = c_y
    r_inner = r_outer * 0.80
    draw.ellipse([c_in_x - r_inner, c_in_y - r_inner, c_in_x + r_inner, c_in_y + r_inner], fill=COL_TURKISH_RED)
    star_x = c_x + r_outer * 0.72
    star_y = c_y
    r_star = h * 0.12
    points = []
    angle_offset = -math.pi / 2
    for i in range(10):
        r = r_star if i % 2 == 0 else r_star * 0.42
        angle = angle_offset + i * (math.pi / 5)
        points.append((star_x + r * math.cos(angle), star_y + r * math.sin(angle)))
    draw.polygon(points, fill=COL_WHITE)

# Helper: Draw Bayraktar Logo with Chevron
def draw_bayraktar_logo(draw, x, y, text_size=100, dark=True):
    col = (30, 32, 36, 255) if dark else (230, 230, 230, 255)
    f = get_font(text_size)
    ew = text_size * 2.2
    eh = text_size * 0.45
    pts = [
        (x, y + eh * 0.5),
        (x + ew * 0.4, y),
        (x + ew * 0.5, y + eh * 0.4),
        (x + ew * 0.6, y),
        (x + ew, y + eh * 0.5),
        (x + ew * 0.6, y + eh),
        (x + ew * 0.5, y + eh * 0.6),
        (x + ew * 0.4, y + eh),
    ]
    draw.polygon(pts, fill=col)
    draw.text((x + ew + 25, y - eh * 0.25), "BAYRAKTAR TB3", font=f, fill=col)

# Helper: Draw Danger Propeller Band
def draw_danger_propeller_band(draw, x, y, w, h):
    bar_h = 24
    draw.rectangle([x, y, x + w, y + bar_h], fill=COL_DANGER_RED)
    draw.rectangle([x, y + h - bar_h, x + w, y + h], fill=COL_DANGER_RED)
    draw.text((x + 40, y + 30), "DİKKAT PERVANE", font=font_med, fill=COL_DANGER_RED)
    draw.text((x + 40, y + 120), "DANGER PROPELLER", font=font_med, fill=COL_DANGER_RED)


# ==============================================================================
# 1. GENERATE FUSELAGE PBR TEXTURE MAPS (tb3_body_*)
# ==============================================================================
print("1/2 Generating Fuselage & Airframe 4K Maps...")

body_diff = Image.new("RGBA", (SIZE, SIZE), COL_BODY_GRAY)
body_norm = Image.new("RGB", (SIZE, SIZE), COL_NORMAL_BASE)
body_rough = Image.new("L", (SIZE, SIZE), 97) # Roughness ~0.38 (97/255)

d_diff = ImageDraw.Draw(body_diff)
d_norm = ImageDraw.Draw(body_norm)
d_rough = ImageDraw.Draw(body_rough)

# Add subtle composite texture noise across diffuse & roughness
np_diff = np.array(body_diff, dtype=np.int16)
noise = np.random.randint(-4, 5, (SIZE, SIZE, 1), dtype=np.int16)
np_diff[:, :, :3] = np.clip(np_diff[:, :, :3] + noise, 0, 255)
body_diff = Image.fromarray(np_diff.astype(np.uint8), "RGBA")
d_diff = ImageDraw.Draw(body_diff)

np_rough = np.array(body_rough, dtype=np.int16)
noise_r = np.random.randint(-6, 7, (SIZE, SIZE), dtype=np.int16)
np_rough = np.clip(np_rough + noise_r, 75, 125)
body_rough = Image.fromarray(np_rough.astype(np.uint8), "L")
d_rough = ImageDraw.Draw(body_rough)

# --- A. NOSE & AVIONICS ACCESS PANELS ---
# Left & Right Avionics Panels
for y_panel in [800, 2200]:
    # Panel seam outline (dark line in diffuse, groove in normal, higher roughness)
    d_diff.rectangle([400, y_panel, 1600, y_panel + 600], outline=(60, 64, 70, 255), width=4)
    d_norm.rectangle([400, y_panel, 1600, y_panel + 600], outline=(100, 100, 230), width=4)
    d_rough.rectangle([400, y_panel, 1600, y_panel + 600], outline=140, width=4)
    
    # Flush counter-sunk screw heads along panel perimeter
    for px in range(430, 1580, 55):
        for py in [y_panel + 15, y_panel + 585]:
            d_diff.ellipse([px-4, py-4, px+4, py+4], fill=(70, 74, 80, 255), outline=(40, 42, 46, 255))
            d_norm.ellipse([px-4, py-4, px+4, py+4], fill=(115, 115, 240))
            d_rough.ellipse([px-4, py-4, px+4, py+4], fill=130)
    for py in range(y_panel + 40, y_panel + 570, 55):
        for px in [415, 1585]:
            d_diff.ellipse([px-4, py-4, px+4, py+4], fill=(70, 74, 80, 255), outline=(40, 42, 46, 255))
            d_norm.ellipse([px-4, py-4, px+4, py+4], fill=(115, 115, 240))
            d_rough.ellipse([px-4, py-4, px+4, py+4], fill=130)
            
    # Dual quick-release oval latches
    for lx in [750, 1250]:
        ly = y_panel + 300
        d_diff.rounded_rectangle([lx-45, ly-18, lx+45, ly+18], radius=8, fill=(160, 164, 170, 255), outline=(45, 48, 52, 255), width=3)
        d_diff.ellipse([lx-10, ly-6, lx+10, ly+6], fill=(50, 52, 56, 255))
        d_norm.rounded_rectangle([lx-45, ly-18, lx+45, ly+18], radius=8, fill=(145, 145, 255), outline=(90, 90, 210), width=3)
        d_rough.rounded_rectangle([lx-45, ly-18, lx+45, ly+18], radius=8, fill=45) # Shiny metal latch

# --- B. FORWARD OPTICAL FLIGHT CAMERA & SENSORS ---
# Optical flight camera slot
d_diff.rounded_rectangle([1900, 300, 2200, 420], radius=15, fill=(15, 20, 28, 255), outline=(80, 85, 92, 255), width=6)
d_norm.rounded_rectangle([1900, 300, 2200, 420], radius=15, outline=(90, 90, 220), width=6)
d_rough.rounded_rectangle([1900, 300, 2200, 420], radius=15, fill=10) # Glass reflection

# Dual circular headlights / sensors
for cx in [1780, 2320]:
    d_diff.ellipse([cx-40, 320, cx+40, 400], fill=(220, 225, 230, 255), outline=(60, 65, 72, 255), width=4)
    d_diff.ellipse([cx-20, 340, cx+20, 380], fill=(255, 255, 255, 255))
    d_norm.ellipse([cx-40, 320, cx+40, 400], outline=(100, 100, 230), width=4)
    d_rough.ellipse([cx-40, 320, cx+40, 400], fill=12)

# --- C. STENCILS & MARKINGS ON FUSELAGE ---
# Nose Bayraktar Logos
draw_bayraktar_logo(d_diff, 500, 650, text_size=110, dark=True)
draw_bayraktar_logo(d_diff, 500, 2050, text_size=110, dark=True)

# Engine Nacelle Side Roundels & Logos
draw_roundel(d_diff, 2800, 1000, 220)
draw_bayraktar_logo(d_diff, 2300, 1300, text_size=90, dark=True)

draw_roundel(d_diff, 2800, 2400, 220)
draw_bayraktar_logo(d_diff, 2300, 2700, text_size=90, dark=True)

# Tail Booms: Red Danger Propeller Bands & TB3 Logos
draw_danger_propeller_band(d_diff, 200, 3100, 1600, 220)
draw_danger_propeller_band(d_diff, 200, 3500, 1600, 220)

d_diff.text((2000, 3160), "BAYRAKTAR TB3", font=font_large, fill=(35, 38, 42, 255))
d_diff.text((2000, 3560), "BAYRAKTAR TB3", font=font_large, fill=(35, 38, 42, 255))

# --- D. VENTRAL RADIATOR MATRIX & LOUVERS ---
d_diff.rectangle([2500, 1600, 3800, 2000], fill=(25, 28, 32, 255), outline=(70, 74, 80, 255), width=6)
d_norm.rectangle([2500, 1600, 3800, 2000], outline=(80, 80, 210), width=6)
d_rough.rectangle([2500, 1600, 3800, 2000], fill=160)

for ly in range(1630, 1980, 25):
    d_diff.line([(2530, ly), (3770, ly)], fill=(90, 95, 102, 255), width=6)
    d_norm.line([(2530, ly), (3770, ly)], fill=(128, 160, 255), width=6)

# Save Fuselage Maps
p_body_diff = os.path.join(output_dir, "tb3_body_diffuse.png")
p_body_norm = os.path.join(output_dir, "tb3_body_normal.png")
p_body_rough = os.path.join(output_dir, "tb3_body_roughness.png")

body_diff.save(p_body_diff, "PNG")
body_norm.save(p_body_norm, "PNG")
body_rough.save(p_body_rough, "PNG")
print("Saved:", p_body_diff)


# ==============================================================================
# 2. GENERATE WINGS, TAIL, GEAR & WEAPONS MAPS (tb3_parts_*)
# ==============================================================================
print("2/2 Generating Wings, Tail, Undercarriage & Munitions 4K Maps...")

parts_diff = Image.new("RGBA", (SIZE, SIZE), COL_BODY_GRAY)
parts_norm = Image.new("RGB", (SIZE, SIZE), COL_NORMAL_BASE)
parts_rough = Image.new("L", (SIZE, SIZE), 97)

d_pdiff = ImageDraw.Draw(parts_diff)
d_pnorm = ImageDraw.Draw(parts_norm)
d_prough = ImageDraw.Draw(parts_rough)

# Add subtle composite noise
np_pdiff = np.array(parts_diff, dtype=np.int16)
noise_p = np.random.randint(-4, 5, (SIZE, SIZE, 1), dtype=np.int16)
np_pdiff[:, :, :3] = np.clip(np_pdiff[:, :, :3] + noise_p, 0, 255)
parts_diff = Image.fromarray(np_pdiff.astype(np.uint8), "RGBA")
d_pdiff = ImageDraw.Draw(parts_diff)

# --- A. WING LEADING EDGE BLACK DE-ICE BOOTS ---
d_pdiff.rectangle([100, 100, 3996, 320], fill=COL_BLACK_BOOT, outline=(20, 22, 24, 255), width=4)
d_pnorm.rectangle([100, 100, 3996, 320], outline=(100, 100, 220), width=4)
d_prough.rectangle([100, 100, 3996, 320], fill=135) # Matte rubber/carbon sheen

d_pdiff.rectangle([100, 380, 3996, 600], fill=COL_BLACK_BOOT, outline=(20, 22, 24, 255), width=4)
d_pnorm.rectangle([100, 380, 3996, 600], outline=(100, 100, 220), width=4)
d_prough.rectangle([100, 380, 3996, 600], fill=135)

# --- B. WING TOP ROUNDEL & NO STEP STENCILS ---
draw_roundel(d_pdiff, 800, 1100, 320)
draw_roundel(d_pdiff, 2800, 1100, 320)

for step_x in range(300, 3800, 450):
    d_pdiff.text((step_x, 800), "NO STEP", font=font_small, fill=(45, 48, 54, 255))
    d_pdiff.text((step_x, 1500), "NO STEP", font=font_small, fill=(45, 48, 54, 255))

# --- C. INVERTED-V TAIL FIN MARKINGS & DARK RUDDER EDGES ---
draw_flag(d_pdiff, 200, 1800, 650, 430)
draw_flag(d_pdiff, 1100, 1800, 650, 430)

d_pdiff.text((200, 2300), "PT - 2", font=font_huge, fill=(35, 38, 42, 255))
d_pdiff.text((200, 2520), "BAYRAKTAR TB3", font=font_med, fill=(35, 38, 42, 255))
d_pdiff.text((200, 2640), "■ BAYKAR", font=font_large, fill=(35, 38, 42, 255))

d_pdiff.text((1100, 2300), "PT - 2", font=font_huge, fill=(35, 38, 42, 255))
d_pdiff.text((1100, 2520), "BAYRAKTAR TB3", font=font_med, fill=(35, 38, 42, 255))
d_pdiff.text((1100, 2640), "■ BAYKAR", font=font_large, fill=(35, 38, 42, 255))

# Dark carbon trailing edge for ruddervators
d_pdiff.rectangle([200, 2800, 1800, 3050], fill=COL_BLACK_BOOT, outline=(15, 18, 20, 255), width=4)
d_prough.rectangle([200, 2800, 1800, 3050], fill=130)

# --- D. 10-SPOKE ALLOY WHEEL RIMS & TREADED TIRES ---
def draw_wheel_texture(cx, cy, r_out, r_rim):
    d_pdiff.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=COL_TIRE_RUBBER)
    d_prough.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=190)
    
    for tr in range(int(r_rim * 1.15), int(r_out * 0.95), 14):
        d_pdiff.ellipse([cx - tr, cy - tr, cx + tr, cy + tr], outline=(12, 14, 16, 255), width=4)
        d_pnorm.ellipse([cx - tr, cy - tr, cx + tr, cy + tr], outline=(100, 100, 210), width=4)
        
    d_pdiff.ellipse([cx - r_rim, cy - r_rim, cx + r_rim, cy + r_rim], fill=COL_ALLOY_RIM, outline=(50, 52, 56, 255), width=6)
    d_pnorm.ellipse([cx - r_rim, cy - r_rim, cx + r_rim, cy + r_rim], outline=(140, 140, 255), width=6)
    d_prough.ellipse([cx - r_rim, cy - r_rim, cx + r_rim, cy + r_rim], fill=50)
    
    for i in range(10):
        ang = i * (math.pi / 5.0)
        sx1 = cx + (r_rim * 0.35) * math.cos(ang)
        sy1 = cy + (r_rim * 0.35) * math.sin(ang)
        sx2 = cx + (r_rim * 0.90) * math.cos(ang)
        sy2 = cy + (r_rim * 0.90) * math.sin(ang)
        d_pdiff.line([(sx1, sy1), (sx2, sy2)], fill=(235, 238, 242, 255), width=18)
        d_pnorm.line([(sx1, sy1), (sx2, sy2)], fill=(160, 160, 255), width=18)
        
    d_pdiff.ellipse([cx - r_rim*0.35, cy - r_rim*0.35, cx + r_rim*0.35, cy + r_rim*0.35], fill=(45, 48, 52, 255))
    d_prough.ellipse([cx - r_rim*0.35, cy - r_rim*0.35, cx + r_rim*0.35, cy + r_rim*0.35], fill=70)
    for i in range(5):
        ang = i * (math.pi * 2.0 / 5.0)
        nx = cx + (r_rim * 0.22) * math.cos(ang)
        ny = cy + (r_rim * 0.22) * math.sin(ang)
        d_pdiff.ellipse([nx-8, ny-8, nx+8, ny+8], fill=COL_CHROME)
        d_prough.ellipse([nx-8, ny-8, nx+8, ny+8], fill=25)

draw_wheel_texture(2500, 2400, 450, 260)
draw_wheel_texture(3500, 2400, 360, 210)

# --- E. PROPELLER BLADES: CARBON WEAVE, EROSION STRIPS & YELLOW TIPS ---
d_pdiff.rectangle([2100, 3200, 3900, 3450], fill=(24, 25, 28, 255), outline=(15, 16, 18, 255), width=4)
d_prough.rectangle([2100, 3200, 3900, 3450], fill=70)

d_pdiff.rectangle([2100, 3200, 3900, 3240], fill=(210, 215, 220, 255))
d_prough.rectangle([2100, 3200, 3900, 3240], fill=35)

d_pdiff.rectangle([3720, 3200, 3900, 3450], fill=COL_MAML_YELLOW)
d_prough.rectangle([3720, 3200, 3900, 3450], fill=80)

# --- F. ROKETSAN MAM-L LASER-GUIDED BOMBS ---
d_pdiff.rectangle([200, 3400, 1800, 3700], fill=COL_MAML_BODY, outline=(55, 60, 65, 255), width=4)
d_prough.rectangle([200, 3400, 1800, 3700], fill=110)

d_pdiff.rectangle([550, 3400, 680, 3700], fill=COL_MAML_YELLOW)
d_pdiff.rectangle([200, 3400, 380, 3700], fill=(20, 22, 26, 255))
d_prough.rectangle([200, 3400, 380, 3700], fill=10)

d_pdiff.text((720, 3440), "MAM-L LASER GUIDED MUNITION", font=font_med, fill=(25, 28, 32, 255))
d_pdiff.text((720, 3530), "■ ROKETSAN   HE-FRAG WARHEAD", font=font_small, fill=(25, 28, 32, 255))

# Save Parts Maps
p_parts_diff = os.path.join(output_dir, "tb3_parts_diffuse.png")
p_parts_norm = os.path.join(output_dir, "tb3_parts_normal.png")
p_parts_rough = os.path.join(output_dir, "tb3_parts_roughness.png")

parts_diff.save(p_parts_diff, "PNG")
parts_norm.save(p_parts_norm, "PNG")
parts_rough.save(p_parts_rough, "PNG")
print("Saved:", p_parts_diff)

print("======================================================================")
print("SUCCESS: 4K PBR TEXTURE ASSETS GENERATED SUCCESSFULLY")
print("======================================================================")
