import sys
import math
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar

# Test positions along nominal flight
test_cases = [
    ("Ingress Spawn", mathutils.Vector((-19500.0, 7000.0, 5800.0)), math.radians(46.0)),
    ("Mid Flight 1", mathutils.Vector((-18000.0, 8500.0, 5800.0)), math.radians(46.0)),
    ("Mid Flight 2", mathutils.Vector((-16000.0, 10500.0, 5800.0)), math.radians(46.0)),
]

def scan_open_valley(pos, current_hdg):
    best_hdg = current_hdg
    best_score = -999999.0
    best_floor_z = 3950.0
    best_width = 0.0
    
    probe_dist = 4500.0
    
    # Scan 36 azimuth bearings, prioritizing forward directions
    for deg in range(-120, 125, 10):
        ang_rad = (current_hdg + math.radians(deg)) % (2.0 * math.pi)
        fwd_dir = mathutils.Vector((math.sin(ang_rad), math.cos(ang_rad), 0.0)).normalized()
        probe_p = pos + fwd_dir * probe_dist
        
        hit_floor, loc_floor, _, _ = radar.raycast(probe_p + mathutils.Vector((0, 0, 500.0)), mathutils.Vector((0, 0, -1.0)), 5000.0)
        floor_z = loc_floor.z if hit_floor else 4800.0
        depth = max(0.0, max(pos.z, 5800.0) - floor_z)
        
        # Check lateral corridor width
        left_perp = mathutils.Vector((-fwd_dir.y, fwd_dir.x, 0.0)).normalized()
        right_perp = -left_perp
        wall_origin = mathutils.Vector((probe_p.x, probe_p.y, floor_z + 150.0))
        hit_wl, _, dist_wl, _ = radar.raycast(wall_origin, left_perp, 3500.0)
        hit_wr, _, dist_wr, _ = radar.raycast(wall_origin, right_perp, 3500.0)
        
        wl = min(3500.0, dist_wl if hit_wl else 3500.0)
        wr = min(3500.0, dist_wr if hit_wr else 3500.0)
        width = wl + wr
        margin = min(wl, wr)
        
        # Heading change penalty: favor smooth, natural turns instead of violent 180° backward turns
        turn_penalty = abs(math.radians(deg)) * 400.0
        
        # Disqualify narrow ravines (< 1400m) or tight side walls (< 400m)
        if width < 1400.0 or margin < 380.0:
            narrow_penalty = 4000.0
        else:
            narrow_penalty = 0.0
            
        score = (depth * 1.2) + (min(width, 5000.0) * 1.5) + (min(margin, 1500.0) * 2.0) - turn_penalty - narrow_penalty
        
        if score > best_score:
            best_score = score
            best_hdg = ang_rad
            best_floor_z = floor_z
            best_width = width
            
    return best_hdg, best_floor_z, best_width

for name, pos, hdg in test_cases:
    chosen_hdg, floor_z, width = scan_open_valley(pos, hdg)
    deg_diff = math.degrees((chosen_hdg - hdg + math.pi) % (2.0 * math.pi) - math.pi)
    chosen_deg = (math.degrees(chosen_hdg) + 360.0) % 360.0
    print(f"[{name}] Hdg nominal: {math.degrees(hdg):.0f}° -> Chosen Valley Hdg: {chosen_deg:.1f}° (Turn: {deg_diff:+.1f}°) | Floor Z: {floor_z:.1f}m | Width: {width:.1f}m")
