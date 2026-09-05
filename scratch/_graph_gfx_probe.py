"""
GUI smoke test for the Mission Graph explorer.

Launches the real app, then drives it through every draw path (globe -> mission
expanded -> report panel open, with a hover active) and quits. Any exception in the
draw handler is printed once by the app itself, so a clean run means every GPU batch,
shader and text call in the renderer actually executed on this machine.

    blender --factory-startup --python scratch/_graph_gfx_probe.py
"""
import importlib.util
import os
import sys

import bpy

APP = os.path.abspath("apps/mission_graph_viewer/standalone_mission_graph_app.py")
sys.path.insert(0, os.path.dirname(APP))

spec = importlib.util.spec_from_file_location("mission_graph_app", APP)
app = importlib.util.module_from_spec(spec)
sys.modules["mission_graph_app"] = app
spec.loader.exec_module(app)

app.register()

_phase = [0]
SHOTS = os.path.abspath("scratch/graph_shots")
os.makedirs(SHOTS, exist_ok=True)


def _shot(name):
    try:
        bpy.ops.screen.screenshot(filepath=os.path.join(SHOTS, f"{name}.png"))
    except Exception as e:
        print(f"PROBE: screenshot {name} failed: {e}")


def _drive():
    """Step through the UI states, one per timer fire, then quit."""
    phase = _phase[0]
    _phase[0] += 1
    state = app.state

    if phase == 0:
        app.configure_viewport()
        print(f"PROBE: {len(state.graph.missions)} missions, "
              f"{len(state.graph.mission_nodes)} nodes, {len(state.graph.web_edges)} web edges")
        return 1.2

    if phase == 1:
        if not state.graph.mission_nodes:
            print("PROBE: no missions on disk — globe-only draw exercised")
            bpy.ops.wm.quit_blender()
            return None
        node = state.graph.mission_nodes[min(1, len(state.graph.mission_nodes) - 1)]
        state.open_mission(node)
        state.hover = node
        _shot("01_globe")
        print(f"PROBE: opened {node.label} with {len(state.report_nodes)} report nodes")
        return 1.6

    if phase == 2:
        if state.report_nodes:
            target = state.report_nodes[-1]
            state.open_report(target)
            print(f"PROBE: opened report {target.label} "
                  f"({len(state.viewer.lines)} formatted lines)")
        _shot("02_mission_expanded")
        return 1.6

    if phase == 3:
        state.viewer.scroll_by(600.0)
        _shot("03_report_open")
        print(f"PROBE: scrolled to {state.viewer.scroll:.0f} / {state.viewer.max_scroll:.0f}")
        return 1.2

    if phase == 4:
        _shot("04_report_scrolled")
        print(f"PROBE: draw_failed={app._draw_failed}")
        print("PROBE: OK" if not app._draw_failed else "PROBE: DRAW ERROR (traceback above)")
        bpy.ops.wm.quit_blender()
        return None

    return None


bpy.app.timers.register(_drive, first_interval=0.4)
