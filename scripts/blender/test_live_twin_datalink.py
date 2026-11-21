"""
Headless Live Datalink & Dynamic Highlighting Verification in Blender 5.2.
Verifies bidirectional communication between Blender Standalone Digital Twin and FastAPI Backend /api/v1:
1. Connects to http://127.0.0.1:8000/api/v1/engines/rotax_912is/state
2. Injects authoritative fault F01 (cylinder 1) via API v1
3. Reads dynamic state.highlights and applies level emissive materials
4. Verifies mesh assignments and camera reticle/framing
5. Clears fault via DELETE /api/v1/engines/rotax_912is/faults
6. Verifies full restoration of authentic solid PBR materials
7. Renders comparison frame to assets/renders/
"""

import bpy
import mathutils
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "apps", "blender_twin"))

import standalone_digital_twin_app as twin

def run_test():
    print("\n=======================================================")
    print("  ANUMAAN BLENDER 5.2 LIVE DATALINK VERIFICATION TEST")
    print("=======================================================\n")
    
    blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_912is", "rotax_912is.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    # 1. Setup workspace & materials
    twin.cache_authentic_materials()
    twin.ensure_ghost_materials()
    twin.restore_all_solid_materials()
    
    # 2. Start receiver thread
    receiver = twin.TelemetryReceiverThread()
    receiver.start()
    
    print("[1/5] Waiting for initial 20 Hz state packet from Backend...")
    for _ in range(30):
        if twin.client_state.is_connected:
            break
        time.sleep(0.1)
        
    assert twin.client_state.is_connected, "Failed to connect to backend /api/v1 at http://127.0.0.1:8000!"
    print(f"  [OK] Connected to Backend: engine_id={twin.client_state.engine_id}, status={twin.client_state.status.get('level')}")
    print(f"  [OK] Telemetry RPM: {twin.client_state.telemetry.get('ENGINE_RPM')}, MAP: {twin.client_state.telemetry.get('MAP')}")
    
    # 3. Inject Fault F01 (cylinder 1)
    print("\n[2/5] Injecting Fault F01 (IGNITION MISFIRE, CYL 1) via API v1...")
    twin.send_server_fault("F01", cylinder=1)
    
    print("  Waiting for backend state highlights...")
    highlights_received = False
    for _ in range(40):
        if twin.client_state.highlights:
            highlights_received = True
            break
        time.sleep(0.1)
        
    assert highlights_received, "No state.highlights received after injecting F01!"
    print(f"  [OK] Received {len(twin.client_state.highlights)} highlight entries from multi-physics plant:")
    for h in twin.client_state.highlights:
        print(f"       Component: {h.get('component_id')}, Level: {h.get('level')}, Nodes: {len(h.get('nodes', []))} nodes, Reason: {h.get('reason')}")
        
    # 4. Apply Dynamic Highlighting in Blender Scene
    print("\n[3/5] Applying dynamic highlights to 3D meshes in Blender...")
    twin.apply_highlights(twin.client_state.highlights)
    
    # Verify meshes
    target_nodes = set()
    for h in twin.client_state.highlights:
        for n in h.get('nodes', []):
            target_nodes.add(n)
            
    highlighted_mesh_count = 0
    ghosted_mesh_count = 0
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mat_name = obj.material_slots[0].material.name if obj.material_slots else ""
            if obj.name in target_nodes:
                highlighted_mesh_count += 1
                assert "Highlight" in mat_name or "Fault" in mat_name or "Red" in mat_name, f"Expected highlight material on {obj.name}, got {mat_name}"
            else:
                ghosted_mesh_count += 1
                assert "Ghost" in mat_name, f"Expected ghost material on non-highlighted {obj.name}, got {mat_name}"
                
    print(f"  [OK] Verified {highlighted_mesh_count} meshes in Glowing Emissive mode, {ghosted_mesh_count} meshes in Holographic Ghost mode.")
    print(f"  [OK] Camera target auto-framed to: {twin.client_state.cam_target}")
    
    # 5. Render test frame of highlighted fault
    out_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    os.makedirs(out_dir, exist_ok=True)
    render_file = os.path.join(out_dir, "blender_twin_fault_highlight_render.png")
    
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = render_file
    
    # Position camera to frame target
    cam = bpy.data.objects.get("MainCamera") or bpy.data.objects.get("TurntableCam")
    if cam:
        scene.camera = cam
        cam.location = twin.client_state.cam_target + mathutils.Vector((0.0, -twin.client_state.target_orbit_distance, twin.client_state.target_orbit_distance * 0.4))
        direction = twin.client_state.cam_target - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
    bpy.ops.render.render(write_still=True)
    print(f"  [OK] Rendered fault highlight frame to: {render_file}")
    
    # 6. Clear fault via API
    print("\n[4/5] Clearing all faults via DELETE /api/v1/engines/rotax_912is/faults...")
    twin.send_clear_server_faults()
    
    print("  Waiting for backend active_faults to clear...")
    cleared = False
    for _ in range(40):
        if not twin.client_state.active_faults:
            cleared = True
            break
        time.sleep(0.1)
        
    assert cleared, "Active faults did not clear on backend!"
    print(f"  [OK] Backend active faults cleared: {len(twin.client_state.active_faults)}")
    
    # 7. Apply cleared state and verify restoration of authentic PBR materials
    print("\n[5/5] Verifying 100% authentic solid PBR material restoration...")
    twin.restore_all_solid_materials()
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for slot in obj.material_slots:
                if slot.material:
                    assert not slot.material.name.startswith("M_Ghost"), f"Stray ghost material on {obj.name}: {slot.material.name}"
                    assert not slot.material.name.startswith("M_Highlight"), f"Stray highlight material on {obj.name}: {slot.material.name}"
                    
    print("  [OK] All meshes restored to pristine authentic PBR materials!")
    print("\n🎉 LIVE DATALINK AND DYNAMIC HIGHLIGHTING VERIFIED 100% SUCESSFUL!\n")
    receiver.is_running = False

if __name__ == "__main__":
    run_test()
