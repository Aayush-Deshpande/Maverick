"""
Rotax 914 F Turbo — Technical Digital Twin Cinematic Showcase
=============================================================
Produces a 20-second (480 frames @ 24fps) cinematic engineering showcase:

Phase 1 (F1-80):   Hero orbit — sweeping 3/4 front establishing shot
Phase 2 (F81-160):  Nose dive — propeller reduction gearbox & flange close-up
Phase 3 (F161-240): Port bank — induction system & composite airbox tracking
Phase 4 (F241-320): Low sweep — 4-into-1 stainless exhaust manifold underbelly
Phase 5 (F321-400): Aft climb — Garrett T25 turbocharger & TCU wastegate
Phase 6 (F401-480): Pull-out master — full telemetry sensor suite overview

Pipeline:
  1. Blender renders clean 3D engine frames with studio lighting & reflective floor
  2. Blender computes 3D-to-2D screen projection matrix for all components (tracking_data.json)
  3. Python HUD Compositor paints aerospace HUD telemetry onto frames & station stills
  4. OpenCV encodes master 1080p MP4 cinematic video
  5. Pillow generates master 3×2 contact sheet
"""

import bpy
import bmesh
import mathutils
from bpy_extras.object_utils import world_to_camera_view
import math
import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(r"e:\backup-llm\backup-no-llm\3d_engine")
SOURCE_BLEND = REPO_ROOT / "assets" / "blender" / "rotax_914.blend"
OUT_BLEND = REPO_ROOT / "assets" / "blender" / "rotax_914_showcase.blend"

RENDER_BASE = REPO_ROOT / "assets" / "renders" / "engines" / "rotax_914"
FRAMES_DIR = RENDER_BASE / "cinematic_showcase"
STATIONS_DIR = RENDER_BASE / "stations"
TRACKING_JSON = RENDER_BASE / "tracking_data.json"
MP4_OUT = RENDER_BASE / "rotax_914_technical_showcase.mp4"
CONTACT_OUT = RENDER_BASE / "rotax_914_showcase_contact_sheet.png"

for d in [FRAMES_DIR, STATIONS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def compute_engine_bounds():
    """Find the bounding box center & radius of all Rotax914 mesh objects."""
    mesh_objs = [o for o in bpy.context.scene.objects
                 if o.type == 'MESH' and o.name.startswith('Rotax914')]
    if not mesh_objs:
        mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    mn = mathutils.Vector((1e9, 1e9, 1e9))
    mx = mathutils.Vector((-1e9, -1e9, -1e9))
    for o in mesh_objs:
        for corner in o.bound_box:
            wp = o.matrix_world @ mathutils.Vector(corner)
            mn.x = min(mn.x, wp.x); mn.y = min(mn.y, wp.y); mn.z = min(mn.z, wp.z)
            mx.x = max(mx.x, wp.x); mx.y = max(mx.y, wp.y); mx.z = max(mx.z, wp.z)

    center = (mn + mx) / 2.0
    diag = (mx - mn).length
    return center, diag, mn, mx


def orbit_point(center, radius, angle_deg, height):
    """Compute a point orbiting center at given radius, angle (degrees), and height."""
    rad = math.radians(angle_deg)
    return mathutils.Vector((
        center.x + radius * math.cos(rad),
        center.y + radius * math.sin(rad),
        height
    ))


# ──────────────────────────────────────────────────────────────────────
# Scene Setup
# ──────────────────────────────────────────────────────────────────────

def setup_world(scene):
    """Create a dark aerospace-grade world background with subtle blue ambient."""
    if not scene.world:
        scene.world = bpy.data.worlds.new("World_Showcase")

    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    node_out = nodes.new("ShaderNodeOutputWorld")
    node_bg = nodes.new("ShaderNodeBackground")
    node_bg.inputs["Color"].default_value = (0.012, 0.018, 0.030, 1.0)
    node_bg.inputs["Strength"].default_value = 0.15
    links.new(node_bg.outputs["Background"], node_out.inputs["Surface"])
    print("  [WORLD] Dark aerospace background set")


def setup_studio_lighting(scene, center, radius):
    """4-point studio lighting rig centered on the engine."""
    for obj in list(scene.objects):
        if obj.type == 'LIGHT' and obj.name.startswith("Showcase_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    def add_sun(name, energy, color, rot_euler):
        data = bpy.data.lights.new(name=name, type='SUN')
        data.energy = energy
        data.color = color
        data.angle = math.radians(3.0)  # Soft shadow spread
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.rotation_euler = rot_euler
        return obj

    # Key Light — warm sun from upper-right front
    add_sun("Showcase_Key_Sun", 5.0, (1.0, 0.97, 0.92),
            (math.radians(55), math.radians(15), math.radians(-40)))

    # Fill Light — cool blue from left
    add_sun("Showcase_Fill_Sun", 2.8, (0.78, 0.88, 1.0),
            (math.radians(45), math.radians(-25), math.radians(130)))

    # Rim Light — cyan accent from behind
    add_sun("Showcase_Rim_Sun", 4.2, (0.0, 0.85, 1.0),
            (math.radians(25), math.radians(10), math.radians(170)))

    # Bottom fill — very subtle warm uplighting
    add_sun("Showcase_Bottom_Fill", 1.2, (1.0, 0.90, 0.80),
            (math.radians(-70), 0, 0))

    print("  [LIGHTING] 4-light studio rig created (Key/Fill/Rim/Bottom)")


def setup_floor(scene, center, radius):
    """Large reflective dark floor plane under the engine."""
    old = bpy.data.objects.get("Showcase_Floor")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.mesh.primitive_circle_add(
        vertices=64, radius=radius * 3.5,
        fill_type='NGON',
        location=(center.x, center.y, center.z - radius * 0.55)
    )
    floor = bpy.context.active_object
    floor.name = "Showcase_Floor"

    mat = bpy.data.materials.new("M_Showcase_Floor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.025, 0.03, 0.04, 1.0)
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.7
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.15
    floor.data.materials.append(mat)
    print(f"  [FLOOR] Reflective dark floor at Z={center.z - radius * 0.55:.0f}")


# ──────────────────────────────────────────────────────────────────────
# Camera Choreography
# ──────────────────────────────────────────────────────────────────────

def setup_camera_choreography(scene, center, radius):
    """
    Build camera animation with 6 cinematic stations.
    Camera tracks target empty with smooth Bezier interpolation.
    """
    old_cam = bpy.data.objects.get("Showcase_Camera")
    if old_cam:
        bpy.data.objects.remove(old_cam, do_unlink=True)
    old_tgt = bpy.data.objects.get("Showcase_Cam_Target")
    if old_tgt:
        bpy.data.objects.remove(old_tgt, do_unlink=True)

    # Clean old HUD or text objects if present
    for o in list(scene.objects):
        if "HUD" in o.name or "Leader" in o.name or "Pin_" in o.name:
            bpy.data.objects.remove(o, do_unlink=True)

    # Camera
    cam_data = bpy.data.cameras.new("Showcase_Camera")
    cam_data.lens = 50.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 50000.0
    cam_data.dof.use_dof = False
    cam_obj = bpy.data.objects.new("Showcase_Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Target empty
    tgt = bpy.data.objects.new("Showcase_Cam_Target", None)
    scene.collection.objects.link(tgt)
    tgt.location = center

    # Track to target
    con = cam_obj.constraints.new('TRACK_TO')
    con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'

    orbit_wide = radius * 2.2
    orbit_mid = radius * 1.5
    orbit_close = radius * 1.35
    orbit_pull = radius * 2.6

    # 6 Cinematic Stations across 480 frames:
    # (frame, orbit_r, angle_degrees, cam_height, target_offset, lens)
    stations = [
        # Phase 1: Hero establishing shot — front-starboard 3/4 orbit (F1-80)
        (1,    orbit_wide, -40,  center.z + radius * 0.50, mathutils.Vector((25, 0, 15)),         36),
        (40,   orbit_wide, -25,  center.z + radius * 0.45, mathutils.Vector((25, 0, 15)),         38),
        (80,   orbit_wide,   0,  center.z + radius * 0.35, mathutils.Vector((50, 0, 20)),         40),

        # Phase 2: Nose close-up — gearbox & propeller flange (F81-160)
        (100,  orbit_mid,   15,  center.z + 120,           mathutils.Vector((266, 0, 138)),       46),
        (140,  orbit_close, 25,  center.z + 110,           mathutils.Vector((266, 0, 138)),       48),
        (160,  orbit_mid,   45,  center.z + 100,           mathutils.Vector((240, 0, 120)),       46),

        # Phase 3: Port side — induction airbox & carburetors (F161-240)
        (180,  orbit_mid,   80,  center.z + radius * 0.25, mathutils.Vector((-48, 60, 65)),       42),
        (220,  orbit_close, 115, center.z + radius * 0.35, mathutils.Vector((-48, 60, 65)),       44),
        (240,  orbit_mid,   150, center.z + radius * 0.25, mathutils.Vector((-48, 40, 50)),       42),

        # Phase 4: Underbelly sweep — exhaust manifold & muffler (F241-320)
        (260,  orbit_mid,   180, center.z - radius * 0.15, mathutils.Vector((-98, 0, -100)),      40),
        (300,  orbit_close, 210, center.z - radius * 0.22, mathutils.Vector((-98, 0, -100)),      42),
        (320,  orbit_mid,   245, center.z - radius * 0.10, mathutils.Vector((-98, 0, -80)),       38),

        # Phase 5: Aft turbo station — starboard rear turbocharger (F321-400)
        (340,  orbit_mid,   280, center.z - 40,            mathutils.Vector((-84, -120, -132)),   42),
        (380,  orbit_close, 300, center.z - 30,            mathutils.Vector((-84, -120, -132)),   45),
        (400,  orbit_mid,   320, center.z + radius * 0.20, mathutils.Vector((-80, -40, -50)),     40),

        # Phase 6: Master pull-out — high beauty drone overview (F401-480)
        (430,  orbit_wide,  340, center.z + radius * 0.65, mathutils.Vector((0, 0, 0)),           34),
        (460,  orbit_pull,  355, center.z + radius * 0.90, mathutils.Vector((0, 0, 0)),           30),
        (480,  orbit_pull,  370, center.z + radius * 1.05, mathutils.Vector((0, 0, 0)),           28),
    ]

    print(f"  [CAMERA] Orbit wide={orbit_wide:.0f}mm, mid={orbit_mid:.0f}mm, close={orbit_close:.0f}mm")
    print(f"  [CAMERA] Center: ({center.x:.0f}, {center.y:.0f}, {center.z:.0f})")

    for frame, orb_r, angle, cam_z, tgt_offset, lens in stations:
        cam_pos = orbit_point(center, orb_r, angle, cam_z)
        cam_obj.location = cam_pos
        cam_obj.keyframe_insert(data_path="location", frame=frame)

        tgt.location = center + tgt_offset
        tgt.keyframe_insert(data_path="location", frame=frame)

        cam_data.lens = lens
        cam_data.keyframe_insert(data_path="lens", frame=frame)

    # Bezier interpolation
    def set_bezier_handles(animated_obj):
        if not animated_obj.animation_data or not animated_obj.animation_data.action:
            return
        action = animated_obj.animation_data.action
        if hasattr(action, 'layers'):
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for bag in strip.channelbags:
                            if hasattr(bag, 'fcurves'):
                                for fc in bag.fcurves:
                                    for kf in fc.keyframe_points:
                                        kf.interpolation = 'BEZIER'
                                        kf.handle_left_type = 'AUTO_CLAMPED'
                                        kf.handle_right_type = 'AUTO_CLAMPED'

    set_bezier_handles(cam_obj)
    set_bezier_handles(tgt)
    if cam_data.animation_data and cam_data.animation_data.action:
        set_bezier_handles(cam_data)

    print(f"  [CAMERA] {len(stations)} keyframes set with Bezier interpolation")
    return cam_obj, tgt


# ──────────────────────────────────────────────────────────────────────
# 3D Tracking Projection Matrix Export
# ──────────────────────────────────────────────────────────────────────

def compute_and_save_tracking_data(scene, cam_obj, center):
    """
    Project exact 3D anchor points to 2D normalized screen space for every frame.
    Saves tracking_data.json so the HUD compositor can lock callouts onto components.
    """
    print("\n=== Computing 3D-to-2D Screen Tracking Matrix ===")
    anchors = {
        "engine_core": center + mathutils.Vector((25.0, 0.0, 30.0)),
        "gearbox": mathutils.Vector((170.0, 0.0, 90.0)),
        "airbox": mathutils.Vector((-120.0, 80.0, 100.0)),
        "exhaust": mathutils.Vector((-170.0, 0.0, -85.0)),
        "turbo": mathutils.Vector((-180.0, -120.0, -180.0)),
    }

    tracking = {}
    for f in range(1, 481):
        scene.frame_set(f)
        fkey = f"frame_{f:04d}"
        tracking[fkey] = {}
        for name, pt in anchors.items():
            co = world_to_camera_view(scene, cam_obj, pt)
            px = int(co.x * scene.render.resolution_x)
            py = int((1.0 - co.y) * scene.render.resolution_y)
            vis = bool(co.z > 0 and 0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0)
            tracking[fkey][name] = {
                "screen_x": px,
                "screen_y": py,
                "depth": float(co.z),
                "visible": vis
            }

    with open(TRACKING_JSON, "w") as fp:
        json.dump(tracking, fp, indent=2)

    print(f"  [TRACKING OK] Saved 480 frames tracking matrix -> {TRACKING_JSON}")
    return tracking


# ──────────────────────────────────────────────────────────────────────
# Render Configuration & Execution
# ──────────────────────────────────────────────────────────────────────

def configure_render(scene):
    """Configure render settings for EEVEE with 1080p quality."""
    avail = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in avail:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in avail:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = avail[0]

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False

    try:
        eevee = scene.eevee
        if hasattr(eevee, 'taa_render_samples'):
            eevee.taa_render_samples = 64
        if hasattr(eevee, 'use_bloom'):
            eevee.use_bloom = True
        if hasattr(eevee, 'use_ssr'):
            eevee.use_ssr = True
        if hasattr(eevee, 'use_gtao'):
            eevee.use_gtao = True
    except Exception:
        pass

    print(f"  [RENDER] Engine={scene.render.engine}, 1920x1080, Transparent=False")


def render_station_stills(scene):
    """Render 6 beauty stills at key station frames."""
    print("\n=== Rendering 6 Station Beauty Stills ===")
    station_frames = [
        ("01_architecture_overview", 40),
        ("02_gearbox_reduction", 140),
        ("03_induction_airbox", 220),
        ("04_thermal_exhaust", 300),
        ("05_turbo_wastegate", 380),
        ("06_telemetry_sensor_suite", 460),
    ]

    paths = []
    for sname, frame in station_frames:
        scene.frame_set(frame)
        out_path = str(STATIONS_DIR / f"station_{sname}.png")
        scene.render.filepath = out_path
        print(f"  Rendering Station '{sname}' @ Frame {frame}...")
        bpy.ops.render.render(write_still=True)
        fsize = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        print(f"    -> {out_path} ({fsize:,} bytes)")
        paths.append(out_path)

    return paths


def render_animation_frames(scene, step=4):
    """Render every Nth frame of the 480-frame animation (step=4 gives 120 frames)."""
    print(f"\n=== Rendering Animation Frames (step={step}) ===")
    rendered = 0
    for f in range(1, 481, step):
        scene.frame_set(f)
        out_path = str(FRAMES_DIR / f"frame_{f:04d}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        rendered += 1

        if rendered % 20 == 0 or f == 1:
            fsize = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            print(f"  Rendered frame {f}/480 ({rendered} total, {fsize:,} bytes)")

    print(f"  [ANIMATION] {rendered} frames rendered to {FRAMES_DIR}")
    return rendered


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 70)
    print(" ROTAX 914 F TURBO — CINEMATIC SHOWCASE 3D RENDER ENGINE")
    print("=" * 70)

    # 1. Open source blend
    print(f"\n[1/7] Opening source blend: {SOURCE_BLEND}")
    if not SOURCE_BLEND.exists():
        print(f"  ERROR: Source blend not found at {SOURCE_BLEND}")
        return
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 480
    scene.render.fps = 24

    # 2. Compute engine bounds
    print("\n[2/7] Computing engine geometry bounds...")
    center, diag, mn, mx = compute_engine_bounds()
    radius = diag / 2.0
    print(f"  Center: ({center.x:.0f}, {center.y:.0f}, {center.z:.0f})")
    print(f"  Size: {(mx-mn).x:.0f} x {(mx-mn).y:.0f} x {(mx-mn).z:.0f} mm")
    print(f"  Radius: {radius:.0f} mm")

    # 3. Setup world
    print("\n[3/7] Setting up dark aerospace world...")
    setup_world(scene)

    # 4. Studio lighting
    print("\n[4/7] Setting up 4-point studio lighting...")
    setup_studio_lighting(scene, center, radius)

    # 5. Floor
    print("\n[5/7] Creating reflective floor stage...")
    setup_floor(scene, center, radius)

    # 6. Camera choreography
    print("\n[6/7] Building camera choreography (6 stations, 480 frames)...")
    cam_obj, tgt = setup_camera_choreography(scene, center, radius)

    # 7. Configure render
    print("\n[7/7] Configuring render settings...")
    configure_render(scene)

    # Save showcase blend
    print(f"\n[SAVE] Saving showcase blend -> {OUT_BLEND}")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    print("[SAVE OK]")

    # 8. Compute and save tracking projection matrix
    compute_and_save_tracking_data(scene, cam_obj, center)

    # ── Render 3D Pipeline ──
    print("\n" + "=" * 70)
    print(" RENDER PIPELINE START")
    print("=" * 70)

    # Render clean station stills
    render_station_stills(scene)

    # Render clean animation frames
    render_animation_frames(scene, step=4)

    print("\n" + "=" * 70)
    print(" ✅ 3D RENDER COMPLETE — READY FOR HUD COMPOSITOR!")
    print("=" * 70)


if __name__ == "__main__":
    main()
