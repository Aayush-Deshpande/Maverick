import sys
import time
import mathutils

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

radar = app.radar

# First call (BVH build)
t0 = time.time()
radar.raycast(mathutils.Vector((0, 0, 6000)), mathutils.Vector((0, 0, -1)), 1000)
t_first = (time.time() - t0) * 1000.0

# 10 subsequent calls
times = []
for _ in range(10):
    t = time.time()
    radar.raycast(mathutils.Vector((0, 0, 6000)), mathutils.Vector((0, 0, -1)), 1000)
    times.append((time.time() - t) * 1000.0)

avg_subsequent = sum(times) / len(times)
print(f"First raycast (BVH build): {t_first:.2f} ms")
print(f"Subsequent raycast average: {avg_subsequent:.4f} ms")
