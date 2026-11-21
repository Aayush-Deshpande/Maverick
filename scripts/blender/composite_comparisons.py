"""
Composite Before and After renders into side-by-side comparison images.
Copies result to artifact directory.
"""
import os
import shutil
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

ARTIFACT_DIR = r"C:\Users\Prasad\.gemini\antigravity\brain\eb7686ec-6c7e-42f5-a015-137bf9ffe74b"
RENDERS_DIR = os.path.join(PROJECT_ROOT, "assets", "renders")

ENGINES = {
    "austro_ae300": "Austro AE300 (167 Nodes, Aerospace PBR, VGT/Rad/Thermostat Added)",
    "vrde_jayem_2_2l": "VRDE Jayem 2.2L (455 Nodes, Aerospace PBR, Airbox/Rad/ECU Added)",
    "rotax_915is": "Rotax 915 iS (56 Decomposed Nodes from 1 Monolithic 1.6M Poly Mesh)",
    "rotax_914": "Rotax 914 (304 Nodes, 320 Wastegates Reassigned, Barrels/Heads Split)",
    "rotax_912is": "Rotax 912 iS (149 Nodes, 40 Placeholders Added, Geometry Preserved)",
}

BANNER_HEIGHT = 70
BG_COLOR = (20, 24, 30)

def composite_engine(eng_id, title_desc):
    before_path = os.path.join(RENDERS_DIR, f"{eng_id}_before.png")
    after_path = os.path.join(RENDERS_DIR, f"{eng_id}_after.png")
    out_path = os.path.join(RENDERS_DIR, f"{eng_id}_comparison_side_by_side.png")
    
    if not os.path.exists(before_path) or not os.path.exists(after_path):
        print(f"Skipping {eng_id}: missing before or after render.")
        return
        
    img_before = Image.open(before_path).convert("RGBA")
    img_after = Image.open(after_path).convert("RGBA")
    
    w, h = img_before.size
    total_w = w * 2 + 30
    total_h = h + BANNER_HEIGHT + 20
    
    comp = Image.new("RGBA", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(comp)
    
    # Try to load a nice default font
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_label = ImageFont.truetype("arialbd.ttf", 20)
        font_sub = ImageFont.truetype("arial.ttf", 15)
    except:
        font_title = font_label = font_sub = ImageFont.load_default()
        
    # Main Header
    draw.text((30, 15), f"ENGINE: {title_desc}", fill=(240, 245, 255), font=font_title)
    
    # Paste images
    # Left: Before
    bg_left = Image.new("RGBA", (w, h), (12, 14, 18))
    bg_left.paste(img_before, (0, 0), img_before)
    comp.paste(bg_left, (10, BANNER_HEIGHT))
    
    # Right: After
    bg_right = Image.new("RGBA", (w, h), (12, 14, 18))
    bg_right.paste(img_after, (0, 0), img_after)
    comp.paste(bg_right, (w + 20, BANNER_HEIGHT))
    
    # Badges
    # Before Badge (Warm Coral / Red)
    draw.rectangle([20, BANNER_HEIGHT + 10, 280, BANNER_HEIGHT + 42], fill=(180, 45, 45))
    draw.text((30, BANNER_HEIGHT + 14), "BEFORE (Original / CAD)", fill=(255, 255, 255), font=font_label)
    
    # After Badge (Aerospace Cyan / Teal)
    draw.rectangle([w + 30, BANNER_HEIGHT + 10, w + 350, BANNER_HEIGHT + 42], fill=(20, 140, 160))
    draw.text((w + 40, BANNER_HEIGHT + 14), "AFTER (Refined Twin / PBR)", fill=(255, 255, 255), font=font_label)
    
    # Divider line
    draw.line([(w + 15, BANNER_HEIGHT), (w + 15, total_h - 10)], fill=(60, 70, 85), width=2)
    
    comp = comp.convert("RGB")
    comp.save(out_path, quality=95)
    print(f"Generated composite: {out_path}")
    
    # Copy to artifact dir
    artifact_copy = os.path.join(ARTIFACT_DIR, f"{eng_id}_comparison_side_by_side.png")
    shutil.copy2(out_path, artifact_copy)
    print(f"  Copied to artifact: {artifact_copy}")

for eng_id, desc in ENGINES.items():
    composite_engine(eng_id, desc)

print("All composites generated and copied to artifact directory.")
