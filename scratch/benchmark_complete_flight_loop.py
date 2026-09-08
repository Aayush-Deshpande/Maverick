"""
G10 Complete Flight Loop Performance Benchmark
Benchmarks the COMPLETE flight simulation loop across the required operational regimes:
  1. Stationary (Hovering/Stationary at Ingress)
  2. Straight Flight (High-speed sprint down Nubra corridor)
  3. Turning Flight (Coordinated 35 deg bank turn)
  4. Radar Active (RADAR_BACKEND = "heightfield")
  5. Radar Inactive (Radar disabled)
  6. Radar Active with Legacy Mesh (RADAR_BACKEND = "blender")

Measures:
  - FPS
  - Frame time (ms)
  - Radar execution time (ms)
  - Terrain sampling time (ms)
  - Physics/Guidance time (ms)
  - Memory consumption (MB)
  - Mesh vertex and polygon counts
"""

import os
import sys
import time
import math
import numpy as np
import bpy
import mathutils

# Add apps/blender_twin to sys.path
app_dir = os.path.abspath(r"apps/blender_twin")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

import standalone_canyon_flight_app as app

def run_benchmarks():
    print("=" * 85)
    print("G10: COMPLETE FLIGHT LOOP BENCHMARK")
    print("=" * 85)

    # 1. Load production blend file
    blend_path = r"Models/terrain.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    dem_obj = bpy.data.objects.get(app.DEM_NAME)
    uav_obj = bpy.data.objects.get(app.UAV_NAME)
    cam_obj = bpy.data.objects.get(app.CAM_NAME)

    v_count = len(dem_obj.data.vertices) if dem_obj else 0
    p_count = len(dem_obj.data.polygons) if dem_obj else 0
    print(f"Loaded Production Scene: {blend_path}")
    print(f"Terrain DEM: {dem_obj.name} | Vertices: {v_count:,} | Polygons: {p_count:,}")
    print(f"UAV Object:  {uav_obj.name}  | Scale: {uav_obj.scale} (Wingspan: {9.5535 * uav_obj.scale.x:.2f}m)")
    print("-" * 85)

    def benchmark_flight_condition(name, n_frames=300, backend="heightfield", radar_enabled=True, flight_mode="straight"):
        app.RADAR_BACKEND = backend
        st = app.FlightState()
        st.pos = app.INGRESS_POS.copy()
        st.heading_rad = math.radians(app.NOMINAL_HEADING_DEG)

        frame_times = []
        radar_times = []
        sampling_times = []
        physics_times = []

        # Warmup (10 frames)
        for _ in range(10):
            app.update_simulation(st)

        for frame in range(n_frames):
            t_frame_start = time.perf_counter()

            # Set operational regime inputs
            if flight_mode == "stationary":
                st.speed_ms = 0.0
                st.pitch_rad = 0.0
                st.roll_rad = 0.0
            elif flight_mode == "straight":
                st.speed_ms = app.CRUISE_SPEED_MS
                st.pitch_rad = 0.0
                st.roll_rad = 0.0
            elif flight_mode == "turning":
                st.speed_ms = app.CRUISE_SPEED_MS
                st.roll_rad = math.radians(35.0)
                st.heading_rad = (st.heading_rad + math.radians(1.5)) % (2.0 * math.pi)

            # Measure radar component independently
            t_radar_0 = time.perf_counter()
            if radar_enabled:
                # Simulate the radar probing slot for this frame
                slot = frame % 12
                probe_origin = st.pos + mathutils.Vector((0.0, 0.0, 2.0))
                if slot == 0:
                    app.radar.raycast(probe_origin, mathutils.Vector((0.0, 0.0, -1.0)), 8000.0)
                elif slot == 6:
                    fwd = mathutils.Vector((math.sin(st.heading_rad), math.cos(st.heading_rad), 0.0))
                    app.radar.raycast(probe_origin, fwd, app.MAX_RADAR_DIST)
                elif slot == 3:
                    fwd_dn = mathutils.Vector((math.sin(st.heading_rad)*0.95, math.cos(st.heading_rad)*0.95, -0.31)).normalized()
                    app.radar.raycast(probe_origin, fwd_dn, 3500.0)
                elif slot == 9:
                    fwd = mathutils.Vector((math.sin(st.heading_rad), math.cos(st.heading_rad), 0.0))
                    rgt = mathutils.Vector((fwd.y, -fwd.x, 0.0))
                    app.radar.raycast(probe_origin, (fwd * 0.7 - rgt * 0.7).normalized(), 4000.0)
                    app.radar.raycast(probe_origin, (fwd * 0.7 + rgt * 0.7).normalized(), 4000.0)
            t_radar_1 = time.perf_counter()

            # Measure direct terrain sampling component
            t_samp_0 = time.perf_counter()
            gz = app.radar.sample_terrain_z(st.pos.x, st.pos.y)
            t_samp_1 = time.perf_counter()

            # Run complete simulation tick
            t_sim_0 = time.perf_counter()
            app.update_simulation(st)
            # Update chase camera
            app.update_chase_camera(st)
            t_sim_1 = time.perf_counter()

            t_frame_end = time.perf_counter()

            frame_times.append((t_frame_end - t_frame_start) * 1e3)
            radar_times.append((t_radar_1 - t_radar_0) * 1e3)
            sampling_times.append((t_samp_1 - t_samp_0) * 1e3)
            physics_times.append((t_sim_1 - t_sim_0) * 1e3)

        mean_dt = np.mean(frame_times)
        mean_fps = 1000.0 / mean_dt if mean_dt > 0 else 999.0
        mean_radar = np.mean(radar_times)
        mean_samp = np.mean(sampling_times)
        mean_phys = np.mean(physics_times)

        # Query process memory in MB via Windows tasklist
        try:
            import csv
            raw_mem = os.popen(f'tasklist /FI "PID eq {os.getpid()}" /FO CSV /NH').read().strip()
            row = list(csv.reader([raw_mem]))[0]
            mem_str = row[4].replace(' K', '').replace(',', '').replace(' ', '').strip()
            mem_mb = float(mem_str) / 1024.0
        except Exception as e:
            mem_mb = 0.0

        return {
            "name": name,
            "fps": mean_fps,
            "frame_ms": mean_dt,
            "radar_ms": mean_radar,
            "sampling_ms": mean_samp,
            "physics_ms": mean_phys,
            "mem_mb": mem_mb,
            "v_count": v_count,
            "p_count": p_count
        }

    results = []
    # Test Condition 1: Stationary (Hovering at Ingress)
    print("Benchmarking Condition 1: Stationary...")
    r1 = benchmark_flight_condition("1. Stationary (Ingress Hover)", 300, backend="heightfield", radar_enabled=True, flight_mode="stationary")
    results.append(r1)

    # Test Condition 2: Straight Flight (Cruise sprint)
    print("Benchmarking Condition 2: Straight Flight (Cruise Sprint)...")
    r2 = benchmark_flight_condition("2. Straight Flight (Cruise)", 300, backend="heightfield", radar_enabled=True, flight_mode="straight")
    results.append(r2)

    # Test Condition 3: Turning Flight (Bank turn)
    print("Benchmarking Condition 3: Turning Flight (35 deg Bank)...")
    r3 = benchmark_flight_condition("3. Turning Flight (Bank 35°)", 300, backend="heightfield", radar_enabled=True, flight_mode="turning")
    results.append(r3)

    # Test Condition 4: Radar Active (Heightfield Backend)
    print("Benchmarking Condition 4: Radar Active (Heightfield)...")
    r4 = benchmark_flight_condition("4. Radar Active (Heightfield)", 300, backend="heightfield", radar_enabled=True, flight_mode="straight")
    results.append(r4)

    # Test Condition 5: Radar Inactive
    print("Benchmarking Condition 5: Radar Inactive (Disabled)...")
    r5 = benchmark_flight_condition("5. Radar Inactive (Bypassed)", 300, backend="heightfield", radar_enabled=False, flight_mode="straight")
    results.append(r5)

    # Test Condition 6: Radar Active with Legacy Blender Mesh Backend (for rigorous comparison)
    print("Benchmarking Condition 6: Radar Active (Legacy Blender BVH Backend)...")
    r6 = benchmark_flight_condition("6. Radar Active (Blender BVH)", 100, backend="blender", radar_enabled=True, flight_mode="straight")
    results.append(r6)

    # Print Formatted Results Table
    print("\n" + "=" * 105)
    print("G10 COMPLETE FLIGHT-LOOP BENCHMARK RESULTS")
    print("=" * 105)
    header = f"{'Flight Condition':<30} | {'FPS':<7} | {'Frame (ms)':<10} | {'Radar (ms)':<10} | {'Sample (ms)':<11} | {'Sim/Phys (ms)':<13} | {'Mem (MB)'}"
    print(header)
    print("-" * 105)
    for r in results:
        line = f"{r['name']:<30} | {r['fps']:>6.1f}  | {r['frame_ms']:>9.4f}  | {r['radar_ms']:>9.4f}  | {r['sampling_ms']:>10.4f}  | {r['physics_ms']:>12.4f}  | {r['mem_mb']:>6.1f}"
        print(line)
    print("=" * 105)

if __name__ == "__main__":
    run_benchmarks()
