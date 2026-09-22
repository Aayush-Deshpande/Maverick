"""
Shared helpers for the TEI-PD170 build.
exec() this inside Blender, then use pd.<fn>.

Key point: bpy Object.bound_box is NOT reliable for CURVE objects - it returns a
default ~2m cube. Anything that measures or frames the scene must evaluate the
object to a mesh and read real vertex positions instead.
"""
import bpy
import math
from mathutils import Vector


class _PD:
    # ------------------------------------------------------------ measuring
    @staticmethod
    def dg():
        return bpy.context.evaluated_depsgraph_get()

    @staticmethod
    def points(o, dg=None):
        """true world-space vertex positions (handles curves correctly)"""
        dg = dg or _PD.dg()
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except Exception:
            me = None
        if me is None:
            return []
        mw = ev.matrix_world
        pts = [mw @ v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        return pts

    @staticmethod
    def bounds(o, dg=None):
        pts = _PD.points(o, dg)
        if not pts:
            return None
        mn = Vector((min(p[i] for p in pts) for i in range(3)))
        mx = Vector((max(p[i] for p in pts) for i in range(3)))
        return mn, mx, (mx - mn)

    @staticmethod
    def visible(o):
        return not (o.hide_viewport or o.hide_render)

    @staticmethod
    def geo(vis_only=True):
        return [o for o in bpy.data.objects
                if o.type in ('MESH', 'CURVE') and (not vis_only or _PD.visible(o))]

    @staticmethod
    def scene_points(dg=None):
        dg = dg or _PD.dg()
        pts = []
        for o in _PD.geo():
            pts += _PD.points(o, dg)
        return pts

    @staticmethod
    def tris(o, dg=None):
        dg = dg or _PD.dg()
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except Exception:
            return 0
        if me is None:
            return 0
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        ev.to_mesh_clear()
        return n

    @staticmethod
    def total_tris(dg=None):
        dg = dg or _PD.dg()
        return sum(_PD.tris(o, dg) for o in _PD.geo())

    # ------------------------------------------------------------ camera
    @staticmethod
    def fit_camera(cam, direction, lens=80.0, margin=1.04, pts=None):
        sc = bpy.context.scene
        pts = pts or _PD.scene_points()
        mn = Vector((min(p[i] for p in pts) for i in range(3)))
        mx = Vector((max(p[i] for p in pts) for i in range(3)))
        centre = (mn + mx) / 2
        cam.data.lens = lens
        cam.data.sensor_width = 36.0
        d = Vector(direction).normalized()
        up_ref = Vector((0, 1, 0)) if abs(d.z) > 0.95 else Vector((0, 0, 1))
        right = d.cross(up_ref).normalized()
        up = right.cross(d).normalized()
        ar = sc.render.resolution_x / sc.render.resolution_y
        tan_h = (cam.data.sensor_width / 2) / cam.data.lens
        tan_v = tan_h / ar
        D = 0.0
        for p in pts:
            c = p - centre
            D = max(D,
                    c.dot(d) + abs(c.dot(right)) / tan_h,
                    c.dot(d) + abs(c.dot(up)) / tan_v)
        D *= margin
        cam.location = centre + d * D
        cam.rotation_euler = (centre - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
        sc.camera = cam
        return D

    @staticmethod
    def render(path, direction, lens=80.0, samples=200, res=1100, margin=1.04, pts=None):
        import time
        import os
        sc = bpy.context.scene
        sc.render.resolution_x = sc.render.resolution_y = res
        sc.cycles.samples = samples
        cam = bpy.data.objects.get("Cam_MCP_Hero")
        _PD.fit_camera(cam, direction, lens, margin, pts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sc.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        return time.time() - t

    # ------------------------------------------------------------ building
    @staticmethod
    def tube(name, pts, radius, mat, coll, res=12, bres=8, caps=True):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        cu = bpy.data.curves.new(name + "_crv", 'CURVE')
        cu.dimensions = '3D'
        cu.resolution_u = res
        cu.bevel_depth = radius
        cu.bevel_resolution = bres
        cu.use_fill_caps = caps
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            bp = sp.bezier_points[i]
            bp.co = Vector(p)
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = bpy.data.objects.new(name, cu)
        bpy.data.collections[coll].objects.link(ob)
        ob.data.materials.append(bpy.data.materials[mat])
        return ob

    @staticmethod
    def prim(name, kind, coll, mat, **kw):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        getattr(bpy.ops.mesh, kind)(**kw)
        o = bpy.context.active_object
        o.name = name
        for c in list(o.users_collection):
            c.objects.unlink(o)
        bpy.data.collections[coll].objects.link(o)
        if mat:
            o.data.materials.append(bpy.data.materials[mat])
        return o

    @staticmethod
    def save(path=r"E:\backup-llm\backup-no-llm\3d_engine\ANUMAAN\Models\engines\tei_pd170_lookdev.blend"):
        bpy.ops.wm.save_as_mainfile(filepath=path)
        return path


pd = _PD
