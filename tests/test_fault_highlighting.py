import sys
import os
import math
import unittest.mock as mock

try:
    import bpy
except ImportError:
    mock_bpy = mock.MagicMock()
    sys.modules['bpy'] = mock_bpy
    sys.modules['gpu'] = mock.MagicMock()
    sys.modules['gpu_extras'] = mock.MagicMock()
    sys.modules['gpu_extras.batch'] = mock.MagicMock()
    sys.modules['blf'] = mock.MagicMock()
    sys.modules['bpy_extras'] = mock.MagicMock()
    sys.modules['bpy_extras.object_utils'] = mock.MagicMock()

try:
    import mathutils
except ImportError:
    class MockVector:
        def __init__(self, vals=(0, 0, 0)):
            self.vals = list(vals)
        @property
        def x(self): return self.vals[0]
        @x.setter
        def x(self, v): self.vals[0] = v
        @property
        def y(self): return self.vals[1]
        @y.setter
        def y(self, v): self.vals[1] = v
        @property
        def z(self): return self.vals[2]
        @z.setter
        def z(self, v): self.vals[2] = v
        def copy(self): return MockVector(self.vals.copy())
        @property
        def length(self): return math.sqrt(sum(v*v for v in self.vals))
        def normalized(self):
            l = self.length
            return MockVector([v/l for v in self.vals]) if l > 0 else MockVector((0,0,0))
        def lerp(self, o, factor):
            return MockVector([a + (b - a) * factor for a, b in zip(self.vals, o.vals)])
        def __add__(self, o): return MockVector([a + b for a, b in zip(self.vals, o.vals)])
        def __sub__(self, o): return MockVector([a - b for a, b in zip(self.vals, o.vals)])
        def __mul__(self, s): return MockVector([a * s for a in self.vals])
        def __rmul__(self, s): return MockVector([a * s for a in self.vals])
        def __repr__(self): return f"Vector(({self.x}, {self.y}, {self.z}))"
    class MockMathUtils:
        Vector = MockVector
    mathutils = MockMathUtils()
    sys.modules['mathutils'] = mathutils

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as app

class MockMaterialSlot:
    def __init__(self, mat=None):
        self.material = mat

class MockMeshObject:
    def __init__(self, name, mat_names=None):
        self.name = name
        self.type = 'MESH'
        self.hide_viewport = False
        self.hide_render = False
        self.matrix_world = mock.MagicMock()
        self.matrix_basis = mock.MagicMock()
        self.location = mathutils.Vector((0, 0, 0))
        self.parent = None
        self.bound_box = [(-1,-1,-1), (1,1,1)]
        mat_names = mat_names or ["M_PBR_Base"]
        self.material_slots = [MockMaterialSlot(mock.MagicMock(name=m)) for m in mat_names]
        for s, m in zip(self.material_slots, mat_names):
            s.material.name = m
        self.data = mock.MagicMock()
        self.data.materials = [s.material for s in self.material_slots]
        self.animation_data_clear = mock.MagicMock()

class MockCollections:
    def __init__(self, col_dict):
        self.col_dict = col_dict
    def get(self, name, default=None):
        return self.col_dict.get(name, default)
    def __iter__(self):
        return iter(self.col_dict.values())

def test_fault_highlighting_and_material_swaps():
    print("Testing 3D Fault Highlighting Across Engines...")
    
    ghost_mat = mock.MagicMock(name="M_GhostVision_XRay")
    ghost_mat.name = "M_GhostVision_XRay"
    fault_mat = mock.MagicMock(name="M_Fault_RedHighlight")
    fault_mat.name = "M_Fault_RedHighlight"

    app.ensure_ghost_materials = mock.MagicMock(return_value=(ghost_mat, fault_mat))

    for eid in ['rotax_912is', 'rotax_914', 'rotax_915is', 'austro_ae300', 'vrde_jayem_2_2l']:
        app.switch_engine(eid)
        prof = app.ENGINE_PROFILES[eid]
        faults = prof.get('faults', {})
        assert len(faults) >= 8, f"Engine {eid} must define 8 faults"

        # Create mock meshes for this engine
        mock_objs = []
        for fid, finfo in faults.items():
            for p in finfo.get('parts', []):
                mock_objs.append(MockMeshObject(p, ["M_AuthenticPBR"]))

        col = mock.MagicMock()
        col.name = prof.get('collection', 'Collection')
        col.objects = mock_objs
        
        mock_collections = MockCollections({col.name: col})
        mock.patch.object(app.bpy.data, 'collections', mock_collections).start()

        # Cache original materials
        app.ORIGINAL_PBR_MATERIALS.clear()
        app.cache_authentic_materials()

        # Test highlighting each fault
        for fid in range(1, 9):
            app.client_state.active_commanded_fault_id = fid
            app.apply_fault_highlight(fid)

            finfo = faults.get(fid, {})
            fparts = [p.lower() for p in finfo.get('parts', [])]

            for obj in mock_objs:
                is_f = any(p in obj.name.lower() for p in fparts)
                if is_f:
                    assert obj.material_slots[0].material == fault_mat, f"Object {obj.name} should have fault material"
                else:
                    assert obj.material_slots[0].material == ghost_mat, f"Object {obj.name} should have ghost material"

        # Test reset / nominal restores original materials
        app.client_state.active_commanded_fault_id = 0
        app.apply_fault_highlight(0)
        for obj in mock_objs:
            assert obj.material_slots[0].material.name == "M_AuthenticPBR", f"Object {obj.name} should be restored to authentic PBR"

        print(f"  [OK] Fault highlighting and nominal restore verified for {eid}")

if __name__ == "__main__":
    test_fault_highlighting_and_material_swaps()
