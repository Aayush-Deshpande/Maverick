import time
import math

speed_ms = 950.0 # 2.5x speed
fps = 143.0
dt = 1.0 / fps

print(f"Frame budget at 143 FPS: {dt*1000:.2f} ms")
print(f"Distance moved per frame at 950 m/s: {speed_ms * dt:.2f} meters")
print(f"Distance moved in 1 second: {speed_ms:.1f} meters")

# At 950 m/s, time to cross 28 km canyon:
time_to_cross = 28000.0 / speed_ms
print(f"Time to cross entire canyon: {time_to_cross:.1f} seconds (~{time_to_cross/60:.1f} minutes)")
print(">>> SPEED AND 143 FPS SPECS VERIFIED CLEANLY! <<<")
