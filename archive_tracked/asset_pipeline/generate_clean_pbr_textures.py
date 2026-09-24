"""
=============================================================================
CLEAN 4K PBR TEXTURE & STENCIL MAP GENERATOR FOR BAYRAKTAR TB3
Creates dedicated, professional textures:
1. tb3_airframe_diffuse_4k.png - Clean tactical gray with panel lines, rivets, access hatches, and subtle weathering.
2. tb3_airframe_roughness_4k.png - Satin polyurethane roughness map with specular seams.
3. tb3_airframe_normal_4k.png - Fine recessed panel seams and rivet indents.
4. tb3_markings_decals.png - High-res vector stencils, Turkish flags, roundels, PT-2, danger bands.
=============================================================================
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

def generate():
    base_dir = r"e:\backup-llm\backup-no-llm\3d_engine"
    tex_dir = os.path.join(base_dir, "3d_models", "textures")
    os.makedirs(tex_dir, exist_ok=True)

    size = 4096
    print(f"Generating Clean 4K Airframe PBR Maps ({size}x{size})...")

    c_gray = (122, 127, 135, 255)         # Tactical Satin Gray #7a7f87
    c_seam = (68, 72, 78, 255)            # Recessed panel seam
    c_seam_hi = (152, 157, 165, 255)      # Specular bevel highlight
    c_rivet = (85, 90, 96, 255)           # Rivet head
    c_rivet_hi = (165, 170, 178, 255)     # Rivet specular rim
    c_white = (245, 245, 250, 255)
    c_black = (20, 22, 25, 255)
    c_turk_red = (227, 10, 23, 255)

    img_diff = Image.new("RGBA", (size, size), c_gray)
    draw_diff = ImageDraw.Draw(img_diff)

    img_rough = Image.new("L", (size, size), 108) # Satin roughness ~0.42
    draw_rough = ImageDraw.Draw(img_rough)

    img_height = Image.new("L", (size, size), 128)
    draw_height = ImageDraw.Draw(img_height)

    def draw_panel_line(x1, y1, x2, y2, width=3):
        draw_diff.line([(x1, y1), (x2, y2)], fill=c_seam, width=width)
        draw_diff.line([(x1, y1+1), (x2, y2+1)], fill=c_seam_hi, width=1)
        draw_rough.line([(x1, y1), (x2, y2)], fill=135, width=width)
        draw_height.line([(x1, y1), (x2, y2)], fill=80, width=width)
        draw_height.line([(x1, y1+1), (x2, y2+1)], fill=160, width=1)

    def draw_rivet_row(x1, y1, x2, y2, spacing=28, radius=3):
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
            draw_rough.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=135)
            draw_height.ellipse([rx-radius, ry-radius, rx+radius, ry+radius], fill=95)
            draw_height.point((rx+1, ry+1), fill=175)

    def draw_access_hatch(x, y, w, h, corner_r=10):
        draw_diff.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=c_seam, width=3)
        draw_diff.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=c_seam_hi, width=1)
        draw_rough.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=130, width=3)
        draw_height.rounded_rectangle([x, y, x+w, y+h], radius=corner_r, outline=75, width=3)
        draw_height.rounded_rectangle([x+1, y+1, x+w-1, y+h-1], radius=corner_r, outline=170, width=1)

        margin = 12
        corners = [(x+margin, y+margin), (x+w-margin, y+margin),
                   (x+margin, y+h-margin), (x+w-margin, y+h-margin)]
        if w > 120:
            corners.extend([(x+w//2, y+margin), (x+w//2, y+h-margin)])
        for cx, cy in corners:
            draw_diff.ellipse([cx-4, cy-4, cx+4, cy+4], fill=c_rivet)
            draw_diff.line([(cx-2, cy), (cx+2, cy)], fill=c_seam, width=1)
            draw_height.ellipse([cx-4, cy-4, cx+4, cy+4], fill=100)

    # 1. Subtle Procedural Noise Overlay across entire diffuse map
    print("  Adding procedural micro-surface grain...")
    noise = np.random.normal(0, 2.5, (size, size, 3)).astype(np.float32)
    arr_diff = np.array(img_diff, dtype=np.float32)
    arr_diff[:, :, :3] = np.clip(arr_diff[:, :, :3] + noise, 0, 255)
    img_diff = Image.fromarray(arr_diff.astype(np.uint8), "RGBA")
    draw_diff = ImageDraw.Draw(img_diff)

    # 2. Airframe Longitudinal and Transverse Panel Seams
    print("  Drawing aerodynamic panel seams & fasteners...")
    for y_pos in [450, 750, 1150, 1550, 1950, 2350, 2750, 3150, 3550]:
        draw_panel_line(100, y_pos, 3996, y_pos, width=3)
        draw_rivet_row(100, y_pos+14, 3996, y_pos+14, spacing=32)
        draw_rivet_row(100, y_pos-14, 3996, y_pos-14, spacing=32)

    for x_pos in range(250, 3950, 240):
        draw_panel_line(x_pos, 100, x_pos, 3996, width=3)
        draw_rivet_row(x_pos+14, 100, x_pos+14, 3996, spacing=30)

    # 3. Flank Access Hatches
    hatch_list = [
        (420, 520, 150, 95), (640, 520, 160, 95), (860, 520, 150, 95),
        (1080, 520, 160, 95), (1300, 520, 180, 115), (1540, 520, 150, 95),
        (520, 640, 220, 85), (780, 640, 240, 85), (1060, 640, 220, 85),
        (1340, 640, 180, 85), (1580, 560, 220, 140)
    ]
    for hx, hy, hw, hh in hatch_list:
        draw_access_hatch(hx, hy, hw, hh, corner_r=10)

    # Save Clean Airframe Maps
    diff_path = os.path.join(tex_dir, "tb3_airframe_diffuse_4k.png")
    img_diff.save(diff_path, "PNG")
    print(f"  -> Saved: {diff_path}")

    rough_path = os.path.join(tex_dir, "tb3_airframe_roughness_4k.png")
    img_rough.save(rough_path, "PNG")
    print(f"  -> Saved: {rough_path}")

    # Generate Normal Map
    print("  Calculating Normal Map...")
    h_blur = img_height.filter(ImageFilter.GaussianBlur(radius=0.8))
    arr_h = np.array(h_blur, dtype=np.float32)
    dx = (np.roll(arr_h, -1, axis=1) - np.roll(arr_h, 1, axis=1)) * 0.5
    dy = (np.roll(arr_h, -1, axis=0) - np.roll(arr_h, 1, axis=0)) * 0.5
    scale = 3.2
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
    norm_path = os.path.join(tex_dir, "tb3_airframe_normal_4k.png")
    img_norm.save(norm_path, "PNG")
    print(f"  -> Saved: {norm_path}")

    # =========================================================================
    # 4. GENERATE HIGH-RES TRANSPARENT MARKINGS ATLAS (2048x2048)
    # =========================================================================
    print("Generating Clean Decal Markings Atlas (2048x2048)...")
    d_size = 2048
    img_decal = Image.new("RGBA", (d_size, d_size), (0, 0, 0, 0))
    draw_dec = ImageDraw.Draw(img_decal)

    font_huge = None
    font_large = None
    font_med = None
    try:
        font_huge = ImageFont.truetype("arialbd.ttf", 96)
        font_large = ImageFont.truetype("arialbd.ttf", 64)
        font_med = ImageFont.truetype("arialbd.ttf", 44)
    except Exception:
        font_huge = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()

    # Turkish Flag: (x=100, y=100, w=480, h=320) -> UV: (0.0488, 0.7422, 0.2832, 0.8984)
    fx, fy, fw, fh = 100, 100, 480, 320
    draw_dec.rectangle([fx, fy, fx+fw, fy+fh], fill=c_turk_red)
    fc_x = fx + int(fw * 0.42)
    fc_y = fy + int(fh * 0.50)
    fc_r = int(fh * 0.32)
    draw_dec.ellipse([fc_x - fc_r, fc_y - fc_r, fc_x + fc_r, fc_y + fc_r], fill=c_white)
    fin_x = fc_x + int(fh * 0.10)
    fin_r = int(fh * 0.25)
    draw_dec.ellipse([fin_x - fin_r, fc_y - fin_r, fin_x + fin_r, fc_y + fin_r], fill=c_turk_red)
    fs_x = fc_x + int(fh * 0.26)
    fs_r = int(fh * 0.12)
    star_pts = []
    for i in range(10):
        r = fs_r if i % 2 == 0 else fs_r * 0.42
        ang = -math.pi/2 + i * (math.pi / 5)
        star_pts.append((fs_x + r * math.cos(ang), fc_y + r * math.sin(ang)))
    draw_dec.polygon(star_pts, fill=c_white)

    # PT-2: (x=700, y=160, w=380, h=160) -> UV: (0.3418, 0.8438, 0.5273, 0.9219)
    draw_dec.text((700, 160), "PT - 2", fill=c_black, font=font_huge)

    # Turkish Roundel: center=(340, 720), radius=220 -> box: (120, 500, 560, 940)
    rcx, rcy, rr = 340, 720, 200
    draw_dec.ellipse([rcx - rr, rcy - rr, rcx + rr, rcy + rr], fill=c_turk_red)
    draw_dec.ellipse([rcx - int(rr*0.66), rcy - int(rr*0.66), rcx + int(rr*0.66), rcy + int(rr*0.66)], fill=c_white)
    draw_dec.ellipse([rcx - int(rr*0.33), rcy - int(rr*0.33), rcx + int(rr*0.33), rcy + int(rr*0.33)], fill=c_turk_red)

    # Danger Propeller Warning Band: (x=700, y=550, w=750, h=160)
    bx, by, bw, bh = 700, 550, 750, 160
    band_w = 80
    draw_dec.rectangle([bx, by, bx+band_w, by+bh], fill=c_turk_red)
    draw_dec.rectangle([bx+bw-band_w, by, bx+bw, by+bh], fill=c_turk_red)
    draw_dec.rectangle([bx+band_w, by, bx+bw-band_w, by+bh], fill=(25, 28, 32, 255))
    draw_dec.text((bx + band_w + 24, by + 22), "DİKKAT PERVANE", fill=c_turk_red, font=font_large)
    draw_dec.text((bx + band_w + 24, by + 90), "DANGER PROPELLER", fill=c_white, font=font_large)

    # "BAYRAKTAR TB3": (x=100, y=1100, w=1100, h=120)
    draw_dec.text((100, 1100), "◄► BAYRAKTAR TB3", fill=(30, 32, 38, 255), font=font_huge)

    # "■ BAYKAR": (x=100, y=1300, w=500, h=100)
    draw_dec.text((100, 1300), "■ BAYKAR", fill=(20, 22, 25, 255), font=font_huge)

    decal_path = os.path.join(tex_dir, "tb3_master_decals_atlas.png")
    img_decal.save(decal_path, "PNG")
    print(f"  -> Saved Decal Atlas: {decal_path}")
    print("All Clean Textures & Decal Atlas Generated Successfully!")

if __name__ == "__main__":
    generate()
