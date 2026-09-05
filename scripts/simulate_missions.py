"""
Accelerated mission generator -> report_dump/
DRDO / iDEX Problem Statement ID: 26054

Runs the real deterministic digital twin (EngineStateService's 20 Hz physics,
detection pipeline and prognostics) over a set of mission profiles, then exports each
completed sortie as a report_dump/mission_NNN/ bundle for the 3D Mission Knowledge
Graph viewer.

Nothing here fabricates report content — every number comes out of the same tick loop
the live server runs. The only liberty taken is time: ticks are driven as fast as the
CPU allows instead of in real time, and each sortie's recorded epochs are then mapped
onto its nominal duration (an 18-hour ISR loiter is not going to be sat through). See
_apply_simulated_timescale().

Usage:
    python scripts/simulate_missions.py                 # the full 10-mission profile set
    python scripts/simulate_missions.py --missions 3    # just the first three
    python scripts/simulate_missions.py --ticks 900     # longer runs, more telemetry
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.server.engine_service import EngineStateService          # noqa: E402
from backend.server.schemas import ControlCommand                      # noqa: E402

# (name, region, planned duration hours, [(tick_fraction, fault_id), ...])
MISSION_PROFILES = [
    ("Ladakh nominal ISR loiter",        "LADAKH",      18.0, []),
    ("Ladakh Cyl #2 thermal runaway",    "LADAKH",      16.5, [(0.35, 1)]),
    ("Thar desert border patrol",        "THAR_DESERT", 12.0, []),
    ("Thar oil pressure decay",          "THAR_DESERT", 11.0, [(0.40, 4)]),
    ("Ladakh injector clog + misfire",   "LADAKH",      15.0, [(0.30, 2), (0.65, 3)]),
    ("Ladakh gearbox vibration",         "LADAKH",      14.0, [(0.45, 5)]),
    ("Thar EGT runner imbalance",        "THAR_DESERT", 13.0, [(0.38, 6)]),
    ("Thar alternator bus sag",          "THAR_DESERT", 10.5, [(0.50, 7)]),
    ("Ladakh dual-FADEC lane drift",     "LADAKH",      17.0, [(0.42, 8)]),
    ("Ladakh compound thermal + lube",   "LADAKH",      16.0, [(0.28, 1), (0.70, 4)]),
]


def simulate_mission(profile, ticks):
    """Run one sortie end to end and export its report bundle. Returns the bundle path."""
    name, region, duration_hours, fault_script = profile

    # PYTEST_CURRENT_TEST is only wanted for the duration of construction, where it gates
    # the model warm-up threads and fleet-graph persistence. The same flag also gates
    # per-tick telemetry logging, and that IS wanted here — readings/ is one of the seven
    # report categories — so it is cleared again the moment the service is built.
    os.environ["PYTEST_CURRENT_TEST"] = "scripts/simulate_missions.py"
    try:
        service = EngineStateService()
    finally:
        os.environ.pop("PYTEST_CURRENT_TEST", None)

    # Take ownership of the clock: stop the background 20 Hz thread and drive _tick()
    # directly, so a 16-hour sortie completes in seconds instead of in 16 hours.
    service.is_running = False
    time.sleep(0.15)
    # The RAG/Qwen reasoning layer is irrelevant to the exported reports and would load
    # a 4B model per fault onset; the deterministic pipeline is untouched by this.
    service._launch_ai_diagnosis = lambda *a, **kw: None

    service.handle_command(ControlCommand(action="SET_REGIME", region=region))
    service.handle_command(ControlCommand(action="START_ENGINE"))

    schedule = {int(fraction * ticks): fault_id for fraction, fault_id in fault_script}
    wall_start = time.time()

    for i in range(ticks):
        if i in schedule:
            service.handle_command(ControlCommand(action="SET_FAULT", fault_id=schedule[i]))
            continue
        with service.state_lock:
            service._tick(0.05)

    _apply_simulated_timescale(service, wall_start, duration_hours)

    with service.state_lock:
        service.export_debrief()

    _close_telemetry_log(service)
    return service.sortie_id, name


def _apply_simulated_timescale(service, wall_start, duration_hours):
    """
    Map the compressed wall-clock run onto the mission's nominal duration.

    Ticks ran as fast as the CPU allowed, so every recorded epoch is bunched into a few
    real seconds. Rescaling them linearly preserves event ordering and relative spacing
    while giving the timeline the T+HH:MM:SS structure of the sortie that was actually
    simulated. Only timestamps are touched — no telemetry, score or health value is.
    """
    sortie = service.graph.sorties.get(service.sortie_id)
    if sortie is None:
        return

    wall_span = max(1e-6, time.time() - wall_start)
    simulated_span = duration_hours * 3600.0
    end = time.time()
    start = end - simulated_span

    for event_id in service.graph.sortie_anomalies.get(service.sortie_id, []):
        anomaly = service.graph.anomalies.get(event_id)
        if anomaly is None:
            continue
        fraction = (anomaly.timestamp_epoch - wall_start) / wall_span
        anomaly.timestamp_epoch = start + max(0.0, min(1.0, fraction)) * simulated_span

    sortie.start_timestamp = start
    # export_debrief() derives flight_hours from start_timestamp, so this is all it takes
    # for the debrief and the timeline to agree on the sortie length.


def _close_telemetry_log(service):
    if service._telemetry_log_file is not None:
        try:
            service._telemetry_log_file.close()
        except OSError:
            pass
        service._telemetry_log_file = None


def main():
    parser = argparse.ArgumentParser(description="Generate report_dump/ mission bundles.")
    parser.add_argument("--missions", type=int, default=len(MISSION_PROFILES),
                        help="How many profiles to run (default: all).")
    parser.add_argument("--ticks", type=int, default=600,
                        help="20 Hz ticks per mission — more ticks means a longer telemetry log.")
    args = parser.parse_args()

    profiles = MISSION_PROFILES[:max(1, args.missions)]
    print(f"Simulating {len(profiles)} mission(s) at {args.ticks} ticks each...\n")

    for index, profile in enumerate(profiles, start=1):
        started = time.time()
        sortie_id, name = simulate_mission(profile, args.ticks)
        print(f"  [{index}/{len(profiles)}] {name:<34} {sortie_id}  "
              f"({time.time() - started:.1f}s)")

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "report_dump"))
    print(f"\nReport bundles written to {root}")
    print("Launch the 3D graph with launch_mission_graph.bat")


if __name__ == "__main__":
    main()
