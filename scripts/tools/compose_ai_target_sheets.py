"""Composite the alpha renders onto the ai-tagert studio backdrop and build sheets."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
REF = Path(sys.argv[2])
BG = (241, 241, 241)
INK = (26, 26, 26)
SUB = (90, 90, 90)

F = "C:/Windows/Fonts/%s"
def font(name, size):
    return ImageFont.truetype(F % name, size)
BOLD, REG = "arialbd.ttf", "arial.ttf"

def flatten(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGB", im.size, BG)
    bg.paste(im, (0, 0), im)
    return bg

def trim(p, pad=0.03):
    """Crop to the alpha silhouette, then pad, so plates align on a sheet."""
    im = Image.open(p).convert("RGBA")
    bb = im.getchannel("A").getbbox()
    if not bb:
        return flatten(p)
    im = im.crop(bb)
    px = int(max(im.size) * pad)
    canv = Image.new("RGBA", (im.width + 2 * px, im.height + 2 * px), (0, 0, 0, 0))
    canv.paste(im, (px, px))
    bg = Image.new("RGB", canv.size, BG)
    bg.paste(canv, (0, 0), canv)
    return bg

def fit(img, box):
    w, h = box
    s = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                      Image.LANCZOS)

# ---- 1. flat-background plates ----------------------------------------
flat_dir = OUT / "flat"
flat_dir.mkdir(exist_ok=True)
plates = sorted(OUT.glob("tei_pd170_render_*.png"))
for p in plates:
    flatten(p).save(flat_dir / p.name, quality=95)
print("FLAT", len(plates))

# ---- 2. sheet builder --------------------------------------------------
def sheet(path, title, cells, size=(1920, 1080)):
    W, H = size
    canv = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canv)
    d.text((48, 34), title, font=font(BOLD, 30), fill=INK)
    d.line([(48, 82), (W - 48, 82)], fill=(200, 200, 200), width=2)

    n = len(cells)
    gut = 26
    cw = (W - 96 - gut * (n - 1)) // n
    top, bot = 118, H - 92
    ch = bot - top
    for i, (src, head, note) in enumerate(cells):
        x0 = 48 + i * (cw + gut)
        img = fit(trim(src, 0.02), (cw, ch))
        canv.paste(img, (x0 + (cw - img.width) // 2, top + (ch - img.height) // 2))
        d.text((x0, bot + 14), head, font=font(BOLD, 19), fill=INK)
        d.text((x0, bot + 42), note, font=font(REG, 15), fill=SUB)
    canv.save(path, quality=95)
    print("SHEET", path.name)

R = OUT
sheet(OUT / "tei_pd170_render_turnaround_sheet.jpg",
      "TEI-PD170  |  Digital Twin Render Turnaround  —  ANUMAAN tei_pd170.blend",
      [(R / "tei_pd170_render_front_ortho.png", "1) FRONT GEARBOX VIEW",
        "Conical reduction snout, prop hub flange, governor block"),
       (R / "tei_pd170_render_accessoryside_ortho.png", "2) ACCESSORY SIDE",
        "Stacked 28V alternators, drive pulleys, oil/fuel filters"),
       (R / "tei_pd170_render_turboside_ortho.png", "3) TURBO SIDE",
        "Two-stage sequential turbos, wastegate, exhaust, sump"),
       (R / "tei_pd170_render_three_quarter_hero.png", "4) THREE-QUARTER VIEW",
        "Hero perspective, 85 mm, studio 3-point rig")])

sheet(OUT / "tei_pd170_render_rear_top_sheet.jpg",
      "TEI-PD170  |  Rear & Top Plan Orthographic  —  ANUMAAN tei_pd170.blend",
      [(R / "tei_pd170_render_rear_ortho.png", "REAR ORTHOGRAPHIC",
        "Flywheel housing, starter interface, mount isolators"),
       (R / "tei_pd170_render_top_ortho.png", "TOP PLAN ORTHOGRAPHIC",
        "Common rail spine, injector hard lines, harness routing"),
       (R / "tei_pd170_render_turbo_hero.png", "TURBO-SIDE HERO",
        "Perspective plate for PBR / shading review")])

# ---- 3. render vs. ai-tagert reference ---------------------------------
pairs = [("tei_pd170_360_front_ortho.jpg", "tei_pd170_render_front_ortho.png",
          "FRONT GEARBOX"),
         ("tei_pd170_360_left_turbo_hero.jpg", "tei_pd170_render_turboside_ortho.png",
          "TURBO SIDE"),
         ("tei_pd170_360_front_right_hero.jpg", "tei_pd170_render_accessoryside_ortho.png",
          "ACCESSORY SIDE"),
         ("tei_pd170_360_top_ortho.jpg", "tei_pd170_render_top_ortho.png",
          "TOP PLAN")]
W, H = 2400, 1400
canv = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(canv)
d.text((48, 32), "TEI-PD170  |  ai-tagert reference (top)  vs.  ANUMAAN render (bottom)",
       font=font(BOLD, 34), fill=INK)
d.line([(48, 86), (W - 48, 86)], fill=(200, 200, 200), width=2)
n = len(pairs)
gut, cw = 24, (W - 96 - 24 * (n - 1)) // n
rh = (H - 200) // 2
for i, (ref_name, ren_name, head) in enumerate(pairs):
    x0 = 48 + i * (cw + gut)
    d.text((x0, 100), head, font=font(BOLD, 21), fill=INK)
    for row, src in enumerate((REF / ref_name, R / ren_name)):
        y0 = 132 + row * (rh + 40)
        if not src.exists():
            continue
        img = trim(src, 0.02) if src.suffix == ".png" else Image.open(src).convert("RGB")
        img = fit(img, (cw, rh))
        canv.paste(img, (x0 + (cw - img.width) // 2, y0 + (rh - img.height) // 2))
    d.text((x0, 132 + rh + 8), "REFERENCE", font=font(REG, 15), fill=SUB)
    d.text((x0, 132 + 2 * rh + 48), "RENDER", font=font(REG, 15), fill=SUB)
canv.save(OUT / "tei_pd170_render_vs_reference.jpg", quality=94)
print("SHEET tei_pd170_render_vs_reference.jpg")
print("COMPOSE_DONE")
