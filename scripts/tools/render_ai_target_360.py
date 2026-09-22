"""Render tei_pd170 at the angles defined by the ai-tagert 360 reference set."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

OUT = Path(sys.argv[sys.argv.index("--") + 1]); OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get

# ---- bounds ------------------------------------------------------------
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = (mn + mx) / 2.0
dim = mx - mn
# sampled world-space vertices: the bbox corners overshoot badly on 3/4 views
_dg = bpy.context.evaluated_depsgraph_get()
corners = []
for o in meshes:
    ev = o.evaluated_get(_dg)
    try:
        me = ev.to_mesh()
    except Exception:
        continue
    M = o.matrix_world
    step = max(1, len(me.vertices) // 400)
    for i in range(0, len(me.vertices), step):
        corners.append(M @ me.vertices[i].co)
    ev.to_mesh_clear()
print("FITPTS", len(corners))
print("CTR", [round(v, 4) for v in ctr], "DIM", [round(v, 4) for v in dim])

def side_of(keys):
    xs = [o.matrix_world.translation.x for o in meshes
          if any(k in o.name.lower() for k in keys)]
    return (sum(xs) / len(xs)) if xs else 0.0
print("ALT_X", round(side_of(("alternator", "generator")), 3),
      "TURBO_X", round(side_of(("turbo", "wastegate")), 3))

# ---- scene hygiene -----------------------------------------------------
env = bpy.data.collections.get("Environment")
if env:
    for o in env.objects:
        o.hide_render = True
for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
    o.hide_render = True

world = scene.world or bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bgn = world.node_tree.nodes.get("Background")
bgn.inputs[0].default_value = (0.58, 0.60, 0.64, 1.0)
bgn.inputs[1].default_value = 0.40

try:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE'
ee = scene.eevee
for attr, val in (("taa_render_samples", 192), ("use_raytracing", True),
                  ("use_shadows", True), ("use_gtao", True)):
    if hasattr(ee, attr):
        try: setattr(ee, attr, val)
        except Exception: pass
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
scene.render.filter_size = 1.4

# AgX rolls highlights off instead of clipping cast aluminium to paper white;
# keeping the rig dim keeps it out of the desaturating shoulder.
vs = scene.view_settings
for tf in ('AgX', 'Filmic', 'Standard'):
    try: vs.view_transform = tf; break
    except Exception: continue
for lk in ('AgX - Punchy', 'Punchy', 'Filmic - High Contrast', 'None'):
    try: vs.look = lk; break
    except Exception: continue
vs.exposure = 0.55

# ---- camera-locked light rig -------------------------------------------
rig = []
for name, energy, size in (("K_key", 260, 2.4), ("K_fill", 95, 3.2),
                           ("K_rim", 190, 1.8), ("K_top", 80, 3.2)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy; ld.size = size; ld.shape = 'SQUARE'
    ob = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(ob); rig.append(ob)

def aim(ob, target):
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()

def place_rig(cam_loc, target):
    fwd = (target - cam_loc).normalized()
    right = fwd.cross(Vector((0, 0, 1)))
    right = right.normalized() if right.length > 1e-4 else Vector((1, 0, 0))
    cu = right.cross(fwd).normalized()
    r = max(dim) * 3.0
    for ob, v in zip(rig, (-right * 1.0 + cu * 0.8 - fwd * 0.9,
                            right * 1.1 - cu * 0.35 - fwd * 0.7,
                            fwd * 1.1 + cu * 0.5,
                            cu * 1.4 - fwd * 0.2)):
        ob.location = target + v.normalized() * r
        aim(ob, target)

cam_d = bpy.data.cameras.new("RenderCam")
cam = bpy.data.objects.new("RenderCam", cam_d)
scene.collection.objects.link(cam); scene.camera = cam
cam_d.clip_start = 0.01; cam_d.clip_end = 100.0

def fits(margin):
    """True when every bbox corner lands inside the frame with `margin` slack."""
    bpy.context.view_layer.update()
    lo, hi = margin, 1.0 - margin
    for c in corners:
        p = world_to_camera_view(scene, cam, c)
        if not (lo <= p.x <= hi and lo <= p.y <= hi and p.z > 0):
            return False
    return True

def shoot(fname, direction, ortho=None, lens=70.0, res=(2048, 2048),
          margin=0.06, rot=None):
    d = Vector(direction).normalized()
    cam.location = ctr + d * (max(dim) * 4.0)
    if rot is not None:
        cam.rotation_euler = Euler(rot, 'XYZ')
    else:
        aim(cam, ctr)
    scene.render.resolution_x, scene.render.resolution_y = res
    if ortho:
        cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
    else:
        cam_d.type = 'PERSP'; cam_d.lens = lens
        # walk the camera back along its axis until the whole engine fits
        dist = max(dim) * 1.2
        for _ in range(140):
            cam.location = ctr + d * dist
            if fits(margin):
                break
            dist *= 1.04
        cam.location = ctr + d * dist
    place_rig(cam.location.copy(), ctr)
    scene.render.filepath = str(OUT / fname)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", fname, "dist", round((cam.location - ctr).length, 3))

R90 = math.radians(90)
pad = 1.12
def ortho_fit(ax_a, ax_b):
    ea = max(abs(p[ax_a] - ctr[ax_a]) for p in corners)
    eb = max(abs(p[ax_b] - ctr[ax_b]) for p in corners)
    return max(ea, eb) * 2.0 * pad
sq_front = ortho_fit(0, 2)
sq_side = ortho_fit(1, 2)
sq_top = ortho_fit(0, 1)
print("ORTHO", round(sq_front, 3), round(sq_side, 3), round(sq_top, 3))

shoot("tei_pd170_render_front_ortho.png", (0, -1, 0),
      ortho=sq_front, rot=(R90, 0, 0))
shoot("tei_pd170_render_rear_ortho.png", (0, 1, 0),
      ortho=sq_front, rot=(R90, 0, math.pi))
shoot("tei_pd170_render_turboside_ortho.png", (1, 0, 0),
      ortho=sq_side, rot=(R90, 0, R90))
shoot("tei_pd170_render_accessoryside_ortho.png", (-1, 0, 0),
      ortho=sq_side, rot=(R90, 0, -R90))
shoot("tei_pd170_render_top_ortho.png", (0, 0, 1),
      ortho=sq_top, rot=(0, 0, math.pi))

hero = (1920, 1080)
shoot("tei_pd170_render_accessory_hero.png", (-0.80, -0.70, 0.32),
      lens=85, res=hero, margin=0.04)
shoot("tei_pd170_render_turbo_hero.png", (0.92, 0.26, 0.24),
      lens=85, res=hero, margin=0.04)
shoot("tei_pd170_render_three_quarter_hero.png", (0.66, -0.80, 0.38),
      lens=85, res=hero, margin=0.04)

json.dump({"center": list(ctr), "dims": list(dim)},
          open(OUT / "render_geometry.json", "w"), indent=1)
print("ALL_DONE")
