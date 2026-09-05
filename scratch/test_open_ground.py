import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar

def find_open_ground_corridor(pos, current_hdg):
    """Find the widest, open-ground descent corridor ahead of the aircraft.
    Prioritizes directions directly ahead (within +/- 50°) with low ground and wide lateral open space.
    Zero hardcoding of waypoints or left-turn bias.
    """
    best_hdg = current_hdg
    best_score = -999999.0
    best_floor_z = 4000.0
    best_info = ""
    
    probe_dist = 4000.0
    
    # Forward-biased fan: -50° to +50° in 10° steps
    for deg in range(-50, 55, 10):
        test_hdg = (current_hdg + math.radians(deg)) % (2.0 * math.pi)
        fwd_dir = mathutils.Vector((math.sin(test_hdg), math.cos(test_hdg), 0.0)).normalized()
        
        # 1. Forward obstacle check along descent vector
        hit_obs, loc_obs, dist_obs, _ = radar.raycast(pos, fwd_dir, probe_dist)
        if hit_obs and dist_obs < 2500.0:
            continue # Ridge directly in front, avoid!
            
        probe_p = pos + fwd_dir * probe_dist
        hit_floor, loc_floor, _, _ = radar.raycast(probe_p + mathutils.Vector((0, 0, 500.0)), mathutils.Vector((0, 0, -1.0)), 5000.0)
        floor_z = loc_floor.z if hit_floor else 4500.0
        depth = max(0.0, 5800.0 - floor_z)
        
        # 2. Measure openness / valley width
        left_perp = mathutils.Vector((-fwd_dir.y, fwd_dir.x, 0.0)).normalized()
        right_perp = -left_perp
        wall_origin = mathutils.Vector((probe_p.x, probe_p.y, floor_z + 150.0))
        hit_wl, _, dist_wl, _ = radar.raycast(wall_origin, left_perp, 3000.0)
        hit_wr, _, dist_wr, _ = radar.raycast(wall_origin, right_perp, 3000.0)
        
        wl = min(3000.0, dist_wl if hit_wl else 3000.0)
        wr = min(3000.0, dist_wr if hit_wr else 3000.0)
        open_width = wl + wr
        side_margin = min(wl, wr)
        
        # Score: depth + openness - deviation from forward heading
        # Strongly prefers flying forward into open ground rather than turning
        turn_penalty = abs(deg) * 15.0 # mild penalty for turning
        score = (depth * 1.0) + (open_width * 1.2) + (side_margin * 1.5) - turn_penalty
        
        if score > best_score:
            best_score = score
            best_hdg = test_hdg
            best_floor_z = floor_z
            best_info = f"Offset {deg:+3d}°: Floor={floor_z:.0f}m, Width={open_width:.0f}m, Margin={side_margin:.0f}m"
            
    return best_hdg, best_floor_z, best_info

# Test at nominal heading 46°
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
best_hdg, floor_z, info = find_open_ground_corridor(pos, math.radians(46.0))
deg_turn = math.degrees((best_hdg - math.radians(46.0) + math.pi) % (2.0 * math.pi) - math.pi)
print(f"Spawn (-19500, 7000) Heading 46°: Selected {math.degrees(best_hdg):.1f}° (Turn: {deg_turn:+.1f}°) | {info}")

# Test at mid-flight
pos2 = mathutils.Vector((-17000.0, 9500.0, 5800.0))
best_hdg2, floor_z2, info2 = find_open_ground_corridor(pos2, math.radians(46.0))
deg_turn2 = math.degrees((best_hdg2 - math.radians(46.0) + math.pi) % (2.0 * math.pi) - math.pi)
print(f"Mid-flight (-17000, 9500) Heading 46°: Selected {math.degrees(best_hdg2):.1f}° (Turn: {deg_turn2:+.1f}°) | {info2}")
