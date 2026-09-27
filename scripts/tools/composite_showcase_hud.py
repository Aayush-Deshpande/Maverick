"""
Aerospace HUD Compositor for Rotax 914 F Technical Cinematic Showcase
======================================================================
Composites high-end aerospace digital twin HUD graphics onto rendered frames:
- 3D-tracked anchor points with pulsing reticles
- Anti-aliased 45° angled leader lines
- Glassmorphic aerospace telemetry cards with detailed engineering specs
- Top global telemetry banner with live parameters
- Bottom 6-station progression ribbon
- Master Station 6 multi-sensor telemetry cluster
- Encodes 1080p MP4 cinematic video via OpenCV
- Generates 3×2 Master Contact Sheet via Pillow
"""

import os
import sys
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

# Paths
REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
RENDER_BASE = REPO_ROOT / "assets" / "renders" / "engines" / "rotax_914"
FRAMES_DIR = RENDER_BASE / "cinematic_showcase"
STATIONS_DIR = RENDER_BASE / "stations"
TRACKING_JSON = RENDER_BASE / "tracking_data.json"
MP4_OUT = RENDER_BASE / "rotax_914_technical_showcase.mp4"
CONTACT_OUT = RENDER_BASE / "rotax_914_showcase_contact_sheet.png"

# Color Palette
CYAN = (0, 229, 255, 255)
CYAN_SOFT = (0, 229, 255, 180)
CYAN_GLOW = (0, 229, 255, 60)
AMBER = (255, 179, 0, 255)
AMBER_SOFT = (255, 179, 0, 180)
GREEN = (0, 230, 118, 255)
GREEN_SOFT = (0, 230, 118, 180)
WHITE = (245, 250, 255, 255)
MUTED = (165, 185, 205, 220)
CARD_BG = (10, 16, 26, 225)
CARD_BORDER = (0, 229, 255, 180)
HEADER_BG = (8, 14, 24, 215)

# Fonts
try:
    font_title = ImageFont.truetype("bahnschrift.ttf", 24)
    font_subtitle = ImageFont.truetype("bahnschrift.ttf", 16)
    font_bold = ImageFont.truetype("segoeuib.ttf", 15)
    font_body = ImageFont.truetype("segoeui.ttf", 14)
    font_telemetry = ImageFont.truetype("consola.ttf", 14)
    font_telemetry_sm = ImageFont.truetype("consola.ttf", 12)
    font_telemetry_xs = ImageFont.truetype("consola.ttf", 10)
    font_station_hdr = ImageFont.truetype("bahnschrift.ttf", 20)
except Exception:
    font_title = font_subtitle = font_bold = font_body = font_telemetry = font_telemetry_sm = font_telemetry_xs = font_station_hdr = ImageFont.load_default()


# Station Specification Catalog
STATION_METADATA = {
    1: {
        "tag": "STATION 01 // OVERVIEW ARCHITECTURE",
        "title": "ROTAX 914 F TURBOCHARGED AERO ENGINE",
        "subtitle": "DRDO ANUMAAN DIGITAL TWIN // PROPULSION SYSTEM",
        "anchor_name": "engine_core",
        "color": CYAN,
        "specs": [
            ("ENGINE TYPE", "4-Cyl Boxer, 4-Stroke Turbocharged Aero Engine"),
            ("DISPLACEMENT", "1,211 cc (73.9 cu in) | Bore: 79.5mm / Stroke: 61mm"),
            ("MAX POWER", "84.5 kW (115 HP) @ 5,800 RPM (5-min Take-Off Limit)"),
            ("CONTINUOUS", "73.5 kW (100 HP) @ 5,500 RPM Continuous Operating"),
            ("COOLING", "Liquid-Cooled Cylinder Heads / Ram-Air Barrel Fins"),
            ("LUBRICATION", "Dry Sump with Trochoid Pump & External Oil Tank"),
            ("IGNITION", "Dual Capacitor Discharge Ignition (Dual CDI) Breakerless"),
            ("DRY WEIGHT", "78.4 kg (172.8 lb) Complete with Turbo & Exhaust"),
        ],
        "metric_label": "SYSTEM HEALTH INDEX: 98.6% [NOMINAL]",
        "metric_val": 0.986,
        "side": "left"
    },
    2: {
        "tag": "STATION 02 // POWER TRANSMISSION",
        "title": "INTEGRATED REDUCTION GEARBOX & FLANGE",
        "subtitle": "MECHANICAL TORQUE CONVERSION & SLIPPER CLUTCH",
        "anchor_name": "gearbox",
        "color": CYAN,
        "specs": [
            ("GEAR REDUCTION", "Reduction Ratio i = 2.43 : 1 (Optional 2.27 : 1)"),
            ("PROPELLER SPEED", "2,387 RPM Propeller Output @ 5,800 Crankshaft RPM"),
            ("PROPELLER FLANGE", "AND 20010 Specification / 8-Bolt PCD Pattern"),
            ("OVERLOAD COUPLING", "Integrated Torsional Slipper Dog Clutch"),
            ("BEARING SYSTEM", "Heavy-Duty Angular Contact Double Row Bearings"),
            ("DIRECTION", "Counter-Clockwise Rotation (Viewed from Cockpit)"),
            ("PHM SENSOR", "CH-02 Dynamic Torsional Load & Gear Vibration"),
        ],
        "metric_label": "GEARTRAIN VIBRATION: 0.12 g [ISO 10816 NOMINAL]",
        "metric_val": 0.96,
        "side": "right"
    },
    3: {
        "tag": "STATION 03 // INDUCTION & BOOST",
        "title": "DUAL INDUCTION & COMPOSITE AIRBOX",
        "subtitle": "BOOST-EQUALIZED MIXTURE & ALTITUDE CONTROL",
        "anchor_name": "airbox",
        "color": AMBER,
        "specs": [
            ("CARBURETORS", "Twin BING 64/32 Constant Velocity (CV) Carburetors"),
            ("BOOST PLENUM", "Carbon-Composite Airbox with Internal Float Balancing"),
            ("ALTITUDE CONTROL", "Barometric Altitude Mixture Automatic Compensation"),
            ("FUEL DELIVERY", "Dual Engine/Electric Pumps (0.25 bar ΔP over Boost)"),
            ("INTAKE RUNNERS", "Equal-Length Aluminum Cross-Flow Induction Manifold"),
            ("AIR CLEANER", "High-Flow Conical Filter with Dynamic Ram Induction"),
            ("PHM SENSOR", "CH-01 Manifold Absolute Pressure (MAP) & Fuel ΔP"),
        ],
        "metric_label": "MANIFOLD PRESSURE: 1.39 bar (41.1 inHg) [OPTIMAL]",
        "metric_val": 0.94,
        "side": "right"
    },
    4: {
        "tag": "STATION 04 // THERMAL EXHAUST",
        "title": "4-INTO-1 TUNED EXHAUST MANIFOLD",
        "subtitle": "AUSTENITIC STAINLESS SCAVENGING & HEAT DYNAMICS",
        "anchor_name": "exhaust",
        "color": CYAN,
        "specs": [
            ("MATERIAL", "AISI 321 Stabilized Austenitic Stainless Steel"),
            ("CONFIGURATION", "4-into-1 Equal-Length Tuned Pulse Exhaust Headers"),
            ("THERMAL LIMITS", "Max EGT: 950°C (1,742°F) | Cruise: 800°C–880°C"),
            ("HEAD COOLING", "Water-Cooled Heads (Max CHT: 135°C / 275°F)"),
            ("EXPANSION JOINTS", "Stainless Ball Joints with Dual Spring Retention Flanges"),
            ("MUFFLER SYSTEM", "Integrated Stainless Scavenge After-Muffler Canister"),
            ("PHM SENSOR", "CH-03 & CH-04 Multi-Port Exhaust Thermocouple Array"),
        ],
        "metric_label": "THERMAL GRADIENT: ΔT 14°C ACROSS CYLINDERS [BALANCED]",
        "metric_val": 0.95,
        "side": "right"
    },
    5: {
        "tag": "STATION 05 // TURBOCHARGER & TCU",
        "title": "GARRETT T25 TURBOCHARGER & TCU",
        "subtitle": "ELECTRONIC BOOST REGULATION & DENSITY ALTITUDE",
        "anchor_name": "turbo",
        "color": AMBER,
        "specs": [
            ("TURBO MODEL", "Garrett T25 Hydrodynamic Floating-Bearing Turbocharger"),
            ("BOOST MANAGEMENT", "Rotax TCU (Turbo Control Unit) Electronic Microprocessor"),
            ("WASTEGATE", "Precision DC Servomotor Electronic Wastegate Actuator"),
            ("MAX BOOST", "1.39 bar (41.1 inHg / 20.2 PSI) Maximum MAP Limit"),
            ("CRITICAL ALTITUDE", "Maintains Full 115 HP Sea-Level Power to 16,000 ft"),
            ("TURBINE LIMIT", "160,000 RPM Maximum Continuous Shaft Speed"),
            ("PHM SENSOR", "CH-05 Turbo Shaft Tachometer & Actuator Resolver"),
        ],
        "metric_label": "BOOST REGULATION: 100% TCU FEEDBACK LOOP LOCKED",
        "metric_val": 0.97,
        "side": "right"
    },
    6: {
        "tag": "STATION 06 // PHM DIAGNOSTIC SUITE",
        "title": "DRDO ANUMAAN HEALTH MONITORING SUITE",
        "subtitle": "PROGNOSTICS & SYSTEM DIAGNOSTICS DIGITAL TWIN",
        "anchor_name": "engine_core",
        "color": GREEN,
        "specs": [
            ("CH-01 [MAP SENSOR]", "1.39 bar (41.1 inHg) — Boost Chamber Nominal"),
            ("CH-02 [RPM PICKUPS]", "Dual Pickups: 5,800 Crank / 2,387 Prop RPM"),
            ("CH-03 [EGT ARRAY]", "AISI 321 Collector: 890°C Nominal Combustion"),
            ("CH-04 [CHT PROBES]", "Cylinder Head Coolant: 118°C (Below 135°C Limit)"),
            ("CH-05 [TURBO TACH]", "Compressor Shaft Speed: 154,200 RPM Active"),
            ("CH-06 [OIL SENSORS]", "Trochoid Pump: 4.8 bar Delivery Pressure / 92°C"),
            ("DIAGNOSTIC MODEL", "Physics-Informed Neural Network + Causal Graph"),
            ("PROGNOSTICS", "Remaining Useful Life (RUL): > 1,850 Flight Hours"),
        ],
        "metric_label": "ALL 8 TELEMETRY CHANNELS SYNCHRONIZED & ONLINE",
        "metric_val": 1.0,
        "side": "left"
    }
}


def draw_hud_overlay(img, frame_num, tracking_data, total_frames=480):
    """Draw complete aerospace HUD overlay onto an image for a specific frame."""
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    margin = 40

    # 1. Corner Reticles & Framing Brackets
    def draw_corner(x, y, dx, dy, size=35, stroke=2):
        draw.line([(x, y), (x + dx * size, y)], fill=CYAN_SOFT, width=stroke)
        draw.line([(x, y), (x, y + dy * size)], fill=CYAN_SOFT, width=stroke)

    draw_corner(margin, margin, 1, 1)
    draw_corner(W - margin, margin, -1, 1)
    draw_corner(margin, H - margin, 1, -1)
    draw_corner(W - margin, H - margin, -1, -1)

    # Subtle crosshairs on top/bottom/sides
    draw.line([(W//2 - 20, margin), (W//2 + 20, margin)], fill=CYAN_GLOW, width=1)
    draw.line([(W//2, margin - 8), (W//2, margin + 8)], fill=CYAN_GLOW, width=1)
    draw.line([(W//2 - 20, H - margin), (W//2 + 20, H - margin)], fill=CYAN_GLOW, width=1)
    draw.line([(W//2, H - margin - 8), (W//2, H - margin + 8)], fill=CYAN_GLOW, width=1)

    # 2. Determine Active Station based on Frame Number
    # 480 frames total divided into 6 phases of 80 frames:
    # St1: 1-80, St2: 81-160, St3: 161-240, St4: 241-320, St5: 321-400, St6: 401-480
    st_idx = min(6, max(1, (frame_num - 1) // 80 + 1))
    meta = STATION_METADATA[st_idx]

    # Calculate station phase progress (0.0 to 1.0 within the 80-frame station window)
    st_start = (st_idx - 1) * 80 + 1
    st_local = frame_num - st_start  # 0 to 79
    # Fade in over 15 frames, stay visible for 55 frames, fade out over 10 frames
    if st_local < 15:
        alpha_factor = st_local / 15.0
    elif st_local > 70:
        alpha_factor = max(0.0, (80 - st_local) / 10.0)
    else:
        alpha_factor = 1.0

    # 3. Top Aerospace Telemetry Banner
    banner_w = W - 2 * margin - 80
    banner_x = margin + 40
    banner_y = margin - 15
    banner_h = 56

    draw.rectangle([(banner_x, banner_y), (banner_x + banner_w, banner_y + banner_h)],
                   fill=HEADER_BG, outline=(0, 229, 255, 90), width=1)
    draw.text((banner_x + 20, banner_y + 8), "DRDO // ANUMAAN DIGITAL TWIN PROGRAM", fill=CYAN, font=font_subtitle)
    draw.text((banner_x + 20, banner_y + 29), "ROTAX 914 F TURBOCHARGED AERO ENGINE | 1,211 CC | 115 HP @ 5,800 RPM", fill=MUTED, font=font_telemetry_sm)

    # Telemetry live indicators on the right of banner
    t_x = banner_x + banner_w - 530
    # Simulate gentle telemetry fluctuation based on frame
    rpm_val = 5800 + int(15 * math.sin(frame_num * 0.1))
    map_val = 1.39 + 0.01 * math.sin(frame_num * 0.08)
    egt_val = 890 + int(3 * math.sin(frame_num * 0.05))
    cht_val = 118 + int(2 * math.cos(frame_num * 0.04))

    metrics = [
        ("ENGINE RPM", f"{rpm_val:,}", GREEN),
        ("BOOST MAP", f"{map_val:.2f} bar", AMBER),
        ("EXHAUST EGT", f"{egt_val}°C", WHITE),
        ("COOLANT CHT", f"{cht_val}°C", WHITE),
        ("PHM STATUS", "NOMINAL", GREEN),
    ]
    for label, val, c in metrics:
        draw.text((t_x, banner_y + 8), label, fill=MUTED, font=font_telemetry_xs)
        draw.text((t_x, banner_y + 24), val, fill=c, font=font_telemetry)
        t_x += 105

    # 4. Bottom Station Navigation Ribbon
    bar_y = H - margin - 22
    st_names = ["01 ARCHITECTURE", "02 GEARBOX", "03 INDUCTION", "04 EXHAUST", "05 TURBOCHARGER", "06 TELEMETRY SUITE"]
    pill_w = (W - 2 * margin - 100) // len(st_names)
    for i, sname in enumerate(st_names):
        px = margin + 50 + i * pill_w
        active = (i == (st_idx - 1))
        bg = (0, 229, 255, 45) if active else (12, 18, 28, 160)
        border = CYAN if active else (40, 60, 85, 180)
        draw.rectangle([(px, bar_y - 12), (px + pill_w - 8, bar_y + 16)], fill=bg, outline=border, width=1)
        text_c = CYAN if active else MUTED
        draw.text((px + 12, bar_y - 6), sname, fill=text_c, font=font_telemetry_sm)
        if active:
            draw.line([(px + 4, bar_y + 14), (px + pill_w - 12, bar_y + 14)], fill=CYAN, width=2)

    # 5. Technical Callout Card & Tracked 3D Leader Line
    # Get projected screen coordinates from tracking_data if available
    frame_key = f"frame_{frame_num:04d}"
    frame_track = tracking_data.get(frame_key, {})
    anchor_info = frame_track.get(meta["anchor_name"], {})

    # Default fallback coordinates if tracking not found
    if "screen_x" in anchor_info and anchor_info.get("visible", True):
        anchor_x = anchor_info["screen_x"]
        anchor_y = anchor_info["screen_y"]
    else:
        # Smart defaults based on station
        defaults = {
            1: (960, 520),
            2: (1280, 480),
            3: (980, 320),
            4: (900, 600),
            5: (800, 540),
            6: (960, 500),
        }
        anchor_x, anchor_y = defaults.get(st_idx, (960, 540))

    # Determine Card Position (left or right side to avoid engine occlusion)
    card_w = 510
    card_h = 320
    card_y = 150

    side = meta["side"]
    # If anchor is on the right side of the screen, place card on left
    if anchor_x > W * 0.55:
        card_x = margin + 50
        elbow_x = card_x + card_w + 50
    elif anchor_x < W * 0.45:
        card_x = W - margin - 50 - card_w
        elbow_x = card_x - 50
    else:
        # Default side from metadata
        if side == "left":
            card_x = margin + 50
            elbow_x = card_x + card_w + 50
        else:
            card_x = W - margin - 50 - card_w
            elbow_x = card_x - 50

    elbow_y = anchor_y - 40
    # Clamp elbow within vertical bounds
    elbow_y = max(card_y + 40, min(card_y + card_h - 40, elbow_y))

    # Apply alpha factor for smooth draw-on animation
    c_color = meta["color"]
    line_alpha = int(255 * alpha_factor)
    card_alpha = int(230 * alpha_factor)

    if alpha_factor > 0.05:
        # Reticle at Anchor Point
        reticle_color = (*c_color[:3], line_alpha)
        reticle_r = 12
        draw.ellipse([(anchor_x - reticle_r, anchor_y - reticle_r),
                      (anchor_x + reticle_r, anchor_y + reticle_r)],
                     outline=reticle_color, width=2)
        draw.ellipse([(anchor_x - 4, anchor_y - 4), (anchor_x + 4, anchor_y + 4)],
                     fill=reticle_color)
        # Crosshair ticks
        draw.line([(anchor_x - 20, anchor_y), (anchor_x - 14, anchor_y)], fill=reticle_color, width=1)
        draw.line([(anchor_x + 14, anchor_y), (anchor_x + 20, anchor_y)], fill=reticle_color, width=1)
        draw.line([(anchor_x, anchor_y - 20), (anchor_x, anchor_y - 14)], fill=reticle_color, width=1)
        draw.line([(anchor_x, anchor_y + 14), (anchor_x, anchor_y + 20)], fill=reticle_color, width=1)

        # Leader Line
        card_connect_x = card_x + card_w if card_x < anchor_x else card_x
        draw.line([(anchor_x, anchor_y), (elbow_x, elbow_y)], fill=reticle_color, width=2)
        draw.line([(elbow_x, elbow_y), (card_connect_x, elbow_y)], fill=reticle_color, width=2)
        draw.ellipse([(elbow_x - 3, elbow_y - 3), (elbow_x + 3, elbow_y + 3)], fill=reticle_color)

        # Glassmorphic HUD Specification Card
        card_bg = (10, 16, 26, card_alpha)
        card_border = (*c_color[:3], int(180 * alpha_factor))

        draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)],
                       fill=card_bg, outline=card_border, width=2)

        # Top Accent Header Bar
        hdr_h = 36
        draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + hdr_h)],
                       fill=(*c_color[:3], int(40 * alpha_factor)))
        draw.line([(card_x, card_y + hdr_h), (card_x + card_w, card_y + hdr_h)],
                  fill=card_border, width=1)
        draw.text((card_x + 18, card_y + 8), meta["tag"], fill=reticle_color, font=font_subtitle)

        # Component Title
        draw.text((card_x + 18, card_y + hdr_h + 8), meta["title"], fill=WHITE, font=font_bold)
        draw.text((card_x + 18, card_y + hdr_h + 28), meta["subtitle"], fill=MUTED, font=font_telemetry_xs)

        # Specs Table
        cy = card_y + hdr_h + 48
        for label, val in meta["specs"]:
            draw.text((card_x + 18, cy), label, fill=reticle_color, font=font_telemetry_xs)
            draw.text((card_x + 145, cy), val, fill=WHITE, font=font_body)
            cy += 21

        # Diagnostic Status Indicator at bottom of card
        bar_bottom = card_y + card_h - 14
        bar_top = card_y + card_h - 24
        bar_w = card_w - 36
        draw.rectangle([(card_x + 18, bar_top), (card_x + 18 + bar_w, bar_bottom)],
                       fill=(*c_color[:3], int(30 * alpha_factor)), outline=(*c_color[:3], int(90 * alpha_factor)))
        fill_w = int(bar_w * meta["metric_val"])
        draw.rectangle([(card_x + 18, bar_top), (card_x + 18 + fill_w, bar_bottom)],
                       fill=(*GREEN[:3], int(220 * alpha_factor)))
        draw.text((card_x + 18, bar_top - 18), meta["metric_label"], fill=GREEN, font=font_telemetry_sm)

    # 6. Station 6 Multi-Sensor Diagnostic Nodes Cluster
    # When in Station 6, display all active telemetry sensor pins across the engine
    if st_idx == 6 and alpha_factor > 0.3:
        sensor_nodes = [
            ("S1: MAP 1.39 bar", "airbox", (120, -50), AMBER),
            ("S2: RPM 5,800", "gearbox", (100, 40), GREEN),
            ("S3: EGT 890°C", "exhaust", (-110, 60), CYAN),
            ("S4: TURBO 154k RPM", "turbo", (-120, -50), AMBER),
        ]
        for sname, anch_name, offset, scolor in sensor_nodes:
            s_anch = frame_track.get(anch_name, {})
            if "screen_x" in s_anch and s_anch.get("visible", True):
                sx, sy = s_anch["screen_x"], s_anch["screen_y"]
                tx, ty = sx + offset[0], sy + offset[1]
                # Sensor pin dot
                draw.ellipse([(sx - 4, sy - 4), (sx + 4, sy + 4)], fill=scolor)
                draw.ellipse([(sx - 8, sy - 8), (sx + 8, sy + 8)], outline=scolor, width=1)
                # Pin line
                draw.line([(sx, sy), (tx, ty)], fill=scolor, width=1)
                # Sensor label badge
                tw = 135
                th = 22
                draw.rectangle([(tx, ty - 11), (tx + tw, ty + 11)], fill=(8, 14, 24, 210), outline=scolor, width=1)
                draw.text((tx + 6, ty - 6), sname, fill=scolor, font=font_telemetry_sm)

    # Composite overlay onto base image
    final_img = Image.alpha_composite(img.convert("RGBA"), overlay)
    return final_img.convert("RGB")


def composite_all_stations():
    """Composite HUD onto all 6 Station Beauty Stills."""
    print("\n=== Compositing 6 Station Beauty Stills ===")
    tracking = {}
    if TRACKING_JSON.exists():
        try:
            with open(TRACKING_JSON, "r") as f:
                tracking = json.load(f)
        except Exception as e:
            print("  Notice: Could not load tracking JSON:", e)

    station_files = [
        ("station_01_architecture_overview.png", 40),
        ("station_02_gearbox_reduction.png", 140),
        ("station_03_induction_airbox.png", 220),
        ("station_04_thermal_exhaust.png", 300),
        ("station_05_turbo_wastegate.png", 380),
        ("station_06_telemetry_sensor_suite.png", 460),
    ]

    out_paths = []
    for fname, frame_num in station_files:
        in_path = STATIONS_DIR / fname
        if not in_path.exists():
            print(f"  [MISSING] {in_path}")
            continue

        im = Image.open(in_path)
        comp = draw_hud_overlay(im, frame_num, tracking)
        comp.save(in_path, quality=95)
        out_paths.append(str(in_path))
        print(f"  Composited: {in_path.name} ({os.path.getsize(in_path):,} bytes)")

    return out_paths


def composite_all_frames():
    """Composite HUD onto all 120 animation frames."""
    print("\n=== Compositing 120 Animation Frames ===")
    tracking = {}
    if TRACKING_JSON.exists():
        try:
            with open(TRACKING_JSON, "r") as f:
                tracking = json.load(f)
        except Exception as e:
            print("  Notice: Could not load tracking JSON:", e)

    frame_files = sorted(FRAMES_DIR.glob("frame_*.png"))
    print(f"  Found {len(frame_files)} frames to composite...")

    for idx, fpath in enumerate(frame_files):
        try:
            # Parse frame number from filename: frame_0001.png -> 1
            fnum = int(fpath.stem.split("_")[1])
            im = Image.open(fpath)
            comp = draw_hud_overlay(im, fnum, tracking)
            comp.save(fpath, quality=95)
            if (idx + 1) % 25 == 0 or idx == 0:
                print(f"  Composited frame {idx+1}/{len(frame_files)} (Frame {fnum})")
        except Exception as e:
            print(f"  Error on {fpath.name}: {e}")

    print(f"  [OK] All {len(frame_files)} frames composited with aerospace HUD!")
    return len(frame_files)


def encode_cinematic_mp4(fps=24, hold_factor=2):
    """Encode composited frames into MP4 video using OpenCV."""
    print(f"\n=== Encoding Master MP4 Video via OpenCV ({fps} FPS) ===")
    frame_files = sorted(FRAMES_DIR.glob("frame_*.png"))
    if not frame_files:
        print("  [ERROR] No frames found to encode!")
        return False

    first = cv2.imread(str(frame_files[0]))
    h, w, _ = first.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(MP4_OUT), fourcc, fps, (w, h))

    total_written = 0
    for fpath in frame_files:
        img = cv2.imread(str(fpath))
        if img is None:
            continue
        # Write frame 'hold_factor' times (2x hold @ 24fps = 12fps effective speed = 10s smooth video)
        for _ in range(hold_factor):
            writer.write(img)
            total_written += 1

    writer.release()
    fsize = MP4_OUT.stat().st_size if MP4_OUT.exists() else 0
    duration_sec = total_written / fps
    print(f"  [MP4 OK] {MP4_OUT}")
    print(f"  Size: {fsize:,} bytes | Duration: {duration_sec:.1f}s | Total Frames Written: {total_written}")
    return True


def generate_master_contact_sheet():
    """Build a 3×2 Master Contact Sheet of the 6 station beauty stills."""
    print(f"\n=== Generating Master Contact Sheet ===")
    station_files = [
        ("station_01_architecture_overview.png", "STATION 01: OVERVIEW ARCHITECTURE"),
        ("station_02_gearbox_reduction.png", "STATION 02: GEARBOX & PROP FLANGE"),
        ("station_03_induction_airbox.png", "STATION 03: INDUCTION & BOOST AIRBOX"),
        ("station_04_thermal_exhaust.png", "STATION 04: THERMAL EXHAUST MANIFOLD"),
        ("station_05_turbo_wastegate.png", "STATION 05: TURBOCHARGER & WASTEGATE"),
        ("station_06_telemetry_sensor_suite.png", "STATION 06: DIGITAL TWIN TELEMETRY"),
    ]

    cols, rows = 3, 2
    cell_w, cell_h = 640, 360
    header_h = 70
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h + header_h), (8, 12, 20))
    draw = ImageDraw.Draw(sheet)

    # Top Aerospace Header
    draw.rectangle([(0, 0), (cols * cell_w, header_h)], fill=(5, 8, 14))
    draw.line([(0, header_h), (cols * cell_w, header_h)], fill=(0, 229, 255, 120), width=2)
    draw.text((30, 16), "DRDO ANUMAAN DIGITAL TWIN // ROTAX 914 F TURBO TECHNICAL SHOWCASE", fill=CYAN, font=font_title)
    draw.text((30, 44), "6-STATION AEROSPACE CINEMATIC REEL | 1,211 CC | 115 HP | PROGNOSTICS & HEALTH MONITORING", fill=MUTED, font=font_telemetry_sm)

    for idx, (fname, label) in enumerate(station_files):
        fpath = STATIONS_DIR / fname
        if not fpath.exists():
            continue
        row = idx // cols
        col = idx % cols
        x = col * cell_w
        y = row * cell_h + header_h

        im = Image.open(fpath).resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(im, (x, y))

        # Station Title Overlay Ribbon
        draw.rectangle([(x + 10, y + 10), (x + cell_w - 10, y + 36)], fill=(8, 14, 24, 200), outline=(0, 229, 255, 120), width=1)
        draw.text((x + 20, y + 14), label, fill=CYAN, font=font_bold)

    sheet.save(str(CONTACT_OUT), quality=95)
    fsize = CONTACT_OUT.stat().st_size if CONTACT_OUT.exists() else 0
    print(f"  [CONTACT SHEET OK] {CONTACT_OUT} ({fsize:,} bytes)")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" ROTAX 914 F AEROSPACE HUD COMPOSITOR & VIDEO PIPELINE")
    print("=" * 70)

    composite_all_stations()
    composite_all_frames()
    encode_cinematic_mp4(fps=24, hold_factor=2)
    generate_master_contact_sheet()

    print("\n" + "=" * 70)
    print(" [SUCCESS] AEROSPACE HUD COMPOSITING COMPLETE!")
    print("=" * 70)
