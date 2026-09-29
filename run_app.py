"""
ROTAX 912 iS SPORT — NATIVE AEROSPACE DIGITAL TWIN & GCS LAUNCHER
DRDO / iDEX Problem Statement ID: 26054

Unified entry point for Native 3D Engine, GCS, and Diagnostic applications:
  1. Canyon Sim        - 120 FPS Top Gun Dynamic Flight Simulation (Ladakh DEM)
  2. Blender Twin      - 100% Raytraced EEVEE 3D Engine CAD Viewport HUD & Diagnostics
  3. Pygame GCS        - Hardware-Accelerated Standalone Desktop GCS HUD
  4. System Audit      - Automated Geometry, Material, & Fault Target Verification
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

# Forces UTF-8 stdout/stderr for this process AND every subprocess it spawns (Blender,
# the pygame GCS) via environment inheritance. Without this, a bare Windows console (the
# default when this script isn't launched through a UTF-8-configured terminal) makes any
# print()/log of a non-ASCII character (an em dash, checkmark, or AI-generated reply)
# raise an uncaught UnicodeEncodeError - confirmed by direct repro on this project's own
# dev machine. See launch_backend_server.bat for the same fix on the .bat launch path.
# The env var alone only helps subprocesses (PYTHONUTF8 is read at interpreter startup,
# before this line runs) - reconfigure() below covers this same process too, since
# launch_backend_server() runs uvicorn in-process rather than as a subprocess.
os.environ.setdefault("PYTHONUTF8", "1")
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

PROJECT_ROOT = Path(__file__).resolve().parent

CANDIDATE_BLENDER_PATHS = [
    r"E:\Blender\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
]

def find_blender():
    for p in CANDIDATE_BLENDER_PATHS:
        if os.path.exists(p):
            return p
    which_b = shutil.which("blender")
    if which_b:
        return which_b
    return None

def launch_canyon_sim():
    blender_exe = find_blender()
    if not blender_exe:
        print("[ERROR] Blender executable could not be found.")
        return 1

    blend_file = PROJECT_ROOT / "assets" / "models" / "terrain.blend"
    if not blend_file.exists():
        blend_file = PROJECT_ROOT / "Models" / "terrain.blend"
    app_script = PROJECT_ROOT / "apps" / "blender_twin" / "standalone_canyon_flight_app.py"

    if not blend_file.exists():
        print(f"[ERROR] Terrain blend file not found: {blend_file}")
        return 1

    print("=" * 75)
    print("[RUN] LAUNCHING 120 FPS TOP GUN LADAKH CANYON FLIGHT SIMULATION")
    print("      DRDO / iDEX Problem Statement ID: 26054")
    print("=" * 75)
    print(f" * Engine: {blender_exe}")
    print(f" * World:  {blend_file}")
    print(f" * Script: {app_script}")
    print("=" * 75)
    
    cmd = [str(blender_exe), "--window-maximized", str(blend_file), "--python", str(app_script)]
    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\nFlight simulation closed.")
        return 0

def launch_blender_twin():
    blender_exe = find_blender()
    if not blender_exe:
        print("[ERROR] Blender executable could not be found.")
        return 1

    blend_file = PROJECT_ROOT / "assets" / "blender" / "rotax_912_is_sport.blend"
    if not blend_file.exists():
        blend_file = PROJECT_ROOT / "3d_models" / "rotax_912_is_sport.blend"
    app_script = PROJECT_ROOT / "apps" / "blender_twin" / "standalone_digital_twin_app.py"

    if not blend_file.exists():
        print(f"[ERROR] Master blend file not found: {blend_file}")
        return 1

    print("=" * 75)
    print("[RUN] LAUNCHING BLENDER 3D ENGINE CAD TWIN SIMULATOR")
    print("      DRDO / iDEX Problem Statement ID: 26054")
    print("=" * 75)
    print(f" * Engine: {blender_exe}")
    print(f" * Model:  {blend_file}")
    print(f" * Script: {app_script}")
    print("=" * 75)
    
    cmd = [str(blender_exe), str(blend_file), "--python", str(app_script)]
    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\nSimulator closed.")
        return 0

def launch_pygame_gcs():
    script = PROJECT_ROOT / "apps" / "desktop_gcs" / "standalone_gui_app.py"
    print("=" * 75)
    print("[RUN] LAUNCHING HARDWARE-ACCELERATED DESKTOP GCS")
    print("=" * 75)
    try:
        return subprocess.run([sys.executable, str(script)]).returncode
    except KeyboardInterrupt:
        print("\nPygame GCS closed.")
        return 0

def run_verification():
    blender_exe = find_blender()
    if not blender_exe:
        print("[ERROR] Blender executable needed for verification could not be found.")
        return 1

    blend_file = PROJECT_ROOT / "assets" / "blender" / "rotax_912_is_sport.blend"
    if not blend_file.exists():
        blend_file = PROJECT_ROOT / "3d_models" / "rotax_912_is_sport.blend"
    verify_script = PROJECT_ROOT / "apps" / "blender_twin" / "verify_app.py"

    print("=" * 75)
    print("[AUDIT] RUNNING SYSTEM AUDIT & SCENE VERIFICATION")
    print("=" * 75)
    cmd = [str(blender_exe), str(blend_file), "--background", "--python", str(verify_script)]
    return subprocess.run(cmd).returncode

def launch_backend_server():
    print("=" * 75)
    print("[RUN] LAUNCHING ROTAX DIGITAL TWIN LAPTOP BACKEND SERVER (0.0.0.0:8000)")
    print("      DRDO / iDEX Problem Statement ID: 26054")
    print("=" * 75)
    try:
        import uvicorn
        uvicorn.run("backend.server.main:app", host="0.0.0.0", port=8000, reload=False)
        return 0
    except KeyboardInterrupt:
        print("\nBackend server stopped.")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to start backend server: {e}")
        return 1

def show_menu():
    print("=" * 75)
    print("  ROTAX 912 iS SPORT — DEFENSE DIGITAL TWIN ARCHITECTURE")
    print("  DRDO / iDEX Problem Statement ID: 26054")
    print("=" * 75)
    print("  Select Application Target:")
    print("  [1] Authoritative Laptop Backend Server (20 Hz Telemetry & REST/WS)")
    print("  [2] Native Blender 3D Engine CAD Digital Twin Client (EEVEE)")
    print("  [3] 120 FPS Ladakh Canyon Dynamic Flight Simulation (Top Gun View)")
    print("  [4] Standalone Native Desktop Aerospace GCS (Hardware-Accelerated)")
    print("  [5] Run System Audit & 3D Model Verification")
    print("  [0] Exit")
    print("=" * 75)
    choice = input("Select [1-5, 0]: ").strip()
    return choice

def main():
    parser = argparse.ArgumentParser(description="Rotax 912 iS Sport Digital Twin Launcher")
    parser.add_argument(
        "target",
        nargs="?",
        choices=["server", "blender", "canyon", "pygame", "verify"],
        help="Target application to launch directly"
    )
    args = parser.parse_args()

    if args.target == "server":
        sys.exit(launch_backend_server())
    elif args.target == "canyon":
        sys.exit(launch_canyon_sim())
    elif args.target == "blender":
        sys.exit(launch_blender_twin())
    elif args.target == "pygame":
        sys.exit(launch_pygame_gcs())
    elif args.target == "verify":
        sys.exit(run_verification())

    # Interactive menu
    choice = show_menu()
    if choice == "1":
        sys.exit(launch_backend_server())
    elif choice == "2":
        sys.exit(launch_blender_twin())
    elif choice == "3":
        sys.exit(launch_canyon_sim())
    elif choice == "4":
        sys.exit(launch_pygame_gcs())
    elif choice == "5":
        sys.exit(run_verification())
    elif choice == "0":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("[ERROR] Invalid choice.")
        sys.exit(1)

if __name__ == "__main__":
    main()
