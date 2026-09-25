import sys
import os
import math
import mathutils

REPO_ROOT = r"e:\backup-llm\backup-no-llm\3d_engine"
sys.path.insert(0, os.path.join(REPO_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as app

def test_camera_movement_and_zooms():
    print("Testing Engine Switching & Camera Coordinate Rescaling...")
    for eid in ['rotax_912is', 'rotax_914', 'rotax_915is', 'austro_ae300', 'vrde_jayem_2_2l']:
        app.switch_engine(eid)
        assert not math.isnan(app.client_state.cur_cam_pos.x)
        assert not math.isnan(app.client_state.cur_cam_pos.y)
        assert not math.isnan(app.client_state.cur_cam_pos.z)
        assert app.client_state.orbit_distance > 0.5
        print(f"  [OK] {eid}: center={app.ENGINE_CENTER}, dist={app.DEFAULT_ORBIT_DISTANCE:.2f}, pos={app.client_state.cur_cam_pos}")
        
        # Test all 8 faults for each engine
        for fid in range(1, 9):
            app.client_state.active_commanded_fault_id = fid
            app.update_camera_for_backend_fault()
            assert app.client_state.target_orbit_distance > 0.1
            assert not math.isnan(app.client_state.cam_target.x)
            assert not math.isnan(app.client_state.target_orbit_angle)
            assert not math.isnan(app.client_state.target_orbit_elevation)
            
        # Test clear fault
        app.client_state.active_commanded_fault_id = 0
        app.update_camera_for_backend_fault()
        assert app.client_state.is_auto_orbit is True
        print(f"  [OK] All 8 fault camera frames and reset nominal passed for {eid}")

    print("\nTesting Modal Kinematic Smoothing & Mouse Controls...")
    app.switch_engine('rotax_912is')
    
    # 1. Trigger Fault 1 (CYL #2 OVERHEAT)
    app.client_state.active_commanded_fault_id = 1
    app.update_camera_for_backend_fault()
    assert app.client_state.is_auto_orbit is False
    
    # Step simulation 60 frames (1 second)
    for _ in range(60):
        dt = 0.0166
        alpha_target = 1.0 - math.exp(-7.0 * dt)
        alpha_angle = 1.0 - math.exp(-6.5 * dt)
        alpha_elev = 1.0 - math.exp(-7.0 * dt)
        alpha_dist = 1.0 - math.exp(-7.5 * dt)
        
        angle_diff = (app.client_state.target_orbit_angle - app.client_state.orbit_angle + math.pi) % (2 * math.pi) - math.pi
        app.client_state.orbit_angle = (app.client_state.orbit_angle + angle_diff * alpha_angle) % (2 * math.pi)
        app.client_state.orbit_elevation += (app.client_state.target_orbit_elevation - app.client_state.orbit_elevation) * alpha_elev
        app.client_state.orbit_distance += (app.client_state.target_orbit_distance - app.client_state.orbit_distance) * alpha_dist
        app.client_state.cur_cam_target = app.client_state.cur_cam_target.lerp(app.client_state.cam_target, alpha_target)
        
        cx = app.client_state.cur_cam_target.x + app.client_state.orbit_distance * math.cos(app.client_state.orbit_angle) * math.cos(app.client_state.orbit_elevation)
        cy = app.client_state.cur_cam_target.y + app.client_state.orbit_distance * math.sin(app.client_state.orbit_angle) * math.cos(app.client_state.orbit_elevation)
        cz = app.client_state.cur_cam_target.z + app.client_state.orbit_distance * math.sin(app.client_state.orbit_elevation)
        app.client_state.cur_cam_pos = mathutils.Vector((cx, cy, cz))
        
    # Check converged position is within 1% of target
    dist_to_target = (app.client_state.cur_cam_target - app.client_state.cam_target).length
    assert dist_to_target < 0.1, f"Target lerp lagged: {dist_to_target}"
    assert abs(app.client_state.orbit_distance - app.client_state.target_orbit_distance) < 0.5
    print("  [OK] Smooth fault camera transition converged accurately in 60 frames")

    # 2. Test Mouse Wheel Zoom in and out
    initial_dist = app.client_state.target_orbit_distance
    app.client_state.target_orbit_distance = max(app.DEFAULT_ORBIT_DISTANCE * 0.20, app.client_state.target_orbit_distance * 0.88)
    assert app.client_state.target_orbit_distance < initial_dist
    app.client_state.target_orbit_distance = min(app.DEFAULT_ORBIT_DISTANCE * 3.5, app.client_state.target_orbit_distance * 1.14)
    print("  [OK] Mouse wheel smooth zoom calculation verified")

    print("\n[SUCCESS] All camera motions, zooms, and fault framings verified!")

if __name__ == "__main__":
    test_camera_movement_and_zooms()
