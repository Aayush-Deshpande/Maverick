"""
ROTAX 912 iS SPORT — STANDALONE AEROSPACE DIGITAL TWIN & GCS APPLICATION
DRDO / iDEX Problem Statement ID: 26054

Standalone Desktop Window Application (Hardware-Accelerated 60-120 FPS)
Features:
- Dedicated 1280x760 Aerospace GCS Interface
- 120-Frame Raytraced EEVEE Turntable Engine with Inertial Drag Physics
- Real-Time Live Telemetry Dials (RPM, CHT, Oil Press, Fuel Flow, MAP, EGT, Voltage, Vibration)
- 8 DRDO PS-26054 Interactive Failure Modes with AI Diagnostic Reasoner
- Interactive Mouse Orbit, Pan, Hotkeys, and Auto Mission Simulation
"""

import pygame
import math
import time
import os
import sys

# Initialize Pygame
pygame.init()
pygame.font.init()

WIDTH = 1280
HEIGHT = 760
FPS = 60

# Colors
CLR_BG = (10, 14, 22)
CLR_PANEL_BG = (15, 23, 36, 220)
CLR_PANEL_BORDER = (0, 160, 220, 100)
CLR_CYAN = (0, 220, 255)
CLR_GREEN = (40, 220, 120)
CLR_RED = (255, 60, 60)
CLR_ORANGE = (255, 170, 30)
CLR_WHITE = (245, 245, 250)
CLR_GRAY = (140, 160, 180)
CLR_DARK_GRAY = (30, 45, 65)

# FAULT DATABASE (DRDO PS-26054)
FAULT_DATABASE = [
    {
        'id': 'FAULT_1',
        'key': pygame.K_1,
        'key_char': '1',
        'title': 'Cylinder #2 CHT Overheat',
        'short': 'CYL #2 OVERHEAT',
        'comp': 'Cylinder #2 Head Assembly',
        'target_frame': 0,
        'telemetry': {'cht': 148.6, 'oil_t': 118.4, 'rpm': 5120, 'vibe': 1.15},
        'sensor': 'CHT: 148.6 °C (Limit: 135.0 °C) | Cyl #2',
        'ai': 'Baffle seal deterioration causing acute cooling restriction & thermal runaway.',
        'action': '▸ Enrich fuel +12% / Throttle back 15% / Immediate RTB vector.',
        'severity': 'CRITICAL'
    },
    {
        'id': 'FAULT_2',
        'key': pygame.K_2,
        'key_char': '2',
        'title': 'Fuel Injector #1 Clog',
        'short': 'INJECTOR #1 CLOG',
        'comp': 'Electronic Fuel Injector #1 (Lane A)',
        'target_frame': 30,
        'telemetry': {'fuel_flow': 14.2, 'egt': 915.0, 'rpm': 4980, 'cht': 112.0},
        'sensor': 'Fuel Flow: 14.2 L/HR (-23% below nominal map)',
        'ai': 'Electromagnetic injector solenoid lag & partial nozzle deposit restriction.',
        'action': '▸ Switch to Lane B ECU backup map / Increase boost pump pressure.',
        'severity': 'WARNING'
    },
    {
        'id': 'FAULT_3',
        'key': pygame.K_3,
        'key_char': '3',
        'title': 'Ignition Spark Misfire',
        'short': 'IGNITION MISFIRE',
        'comp': 'Secondary Spark Lead Harness',
        'target_frame': 16,
        'telemetry': {'rpm': 4850, 'egt': 740.0, 'vibe': 2.30},
        'sensor': 'RPM Jitter: ±185 RPM | Crank Acceleration Dip',
        'ai': 'Secondary ignition lead insulation breakdown; intermittent spark discharge.',
        'action': '▸ Activate redundant Lane B ignition coil set.',
        'severity': 'WARNING'
    },
    {
        'id': 'FAULT_4',
        'key': pygame.K_4,
        'key_char': '4',
        'title': 'Oil Pressure Loss',
        'short': 'OIL PRESSURE LOSS',
        'comp': 'Dry-Sump Oil Reservoir & Scavenge Line',
        'target_frame': 76,
        'telemetry': {'oil_p': 1.8, 'oil_t': 124.0, 'rpm': 4600},
        'sensor': 'Oil Pressure: 1.8 BAR (Min Limit: 2.0 BAR)',
        'ai': 'Scavenge line aerated cavitation or pressure relief bypass leak.',
        'action': '▸ Immediate throttle reduction to 4,200 RPM / Precautionary landing.',
        'severity': 'CRITICAL'
    },
    {
        'id': 'FAULT_5',
        'key': pygame.K_5,
        'key_char': '5',
        'title': 'Gearbox Vibration',
        'short': 'GEARBOX VIBRATION',
        'comp': 'Propeller Reduction Gearbox (Type 2)',
        'target_frame': 108,
        'telemetry': {'vibe': 3.45, 'rpm': 5050},
        'sensor': 'Vibration RMS: 3.45 mm/s (Limit: 1.80 mm/s)',
        'ai': 'Overload dog clutch tooth wear & propeller shaft micro-misalignment.',
        'action': '▸ Limit rapid RPM transitions / Post-flight clutch overhaul.',
        'severity': 'WARNING'
    },
    {
        'id': 'FAULT_6',
        'key': pygame.K_6,
        'key_char': '6',
        'title': 'Exhaust EGT Imbalance',
        'short': 'EXHAUST EGT DELTA',
        'comp': 'Exhaust Runner Manifold (Runner #3)',
        'target_frame': 44,
        'telemetry': {'egt': 895.0, 'fuel_flow': 19.8},
        'sensor': 'EGT Runner #3: 895 °C (Delta > 65°C above baseline)',
        'ai': 'Uneven air-fuel mixture distribution or partial exhaust runner restriction.',
        'action': '▸ Adjust individual cylinder fuel trim on Cylinder #3.',
        'severity': 'WARNING'
    },
    {
        'id': 'FAULT_7',
        'key': pygame.K_7,
        'key_char': '7',
        'title': 'Alternator Voltage Sag',
        'short': 'ALTERNATOR SAG',
        'comp': 'Heavy-Duty Alternator & Belt Drive',
        'target_frame': 104,
        'telemetry': {'bus_v': 12.4, 'rpm': 5100},
        'sensor': 'DC Bus Voltage: 12.4 V (Nominal: 14.1 V)',
        'ai': 'Alternator stator winding phase drop or serpentine drive belt micro-slip.',
        'action': '▸ Shed non-essential ISR payload sensors / Switch to backup battery.',
        'severity': 'WARNING'
    },
    {
        'id': 'FAULT_8',
        'key': pygame.K_8,
        'key_char': '8',
        'title': 'Dual FADEC ECU Drift',
        'short': 'DUAL FADEC DRIFT',
        'comp': 'Lane A/B Engine Control Unit',
        'target_frame': 92,
        'telemetry': {'map_press': 108.5, 'rpm': 5180},
        'sensor': 'MAP Sensor Differential: 8.4 kPa (Lane A vs B Drift)',
        'ai': 'Manifold pressure transducer drift on Lane A ECU channel.',
        'action': '▸ Force FADEC arbitration to Lane B / Flag ECU for bench calibration.',
        'severity': 'WARNING'
    }
]

NOMINAL_TELEMETRY = {
    'rpm': 5200.0,
    'cht': 105.2,
    'oil_p': 4.2,
    'oil_t': 92.0,
    'fuel_flow': 18.4,
    'map_press': 98.2,
    'egt': 820.0,
    'bus_v': 14.2,
    'vibe': 0.85
}

class DigitalTwinApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.HWSURFACE)
        pygame.display.set_caption("Rotax 912 iS Sport — DRDO MALE UAV Digital Twin Simulator [PS-26054]")
        
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI", 12)
        self.font_small = pygame.font.SysFont("Segoe UI", 11)
        self.font_mono = pygame.font.SysFont("Consolas", 12)
        
        # Load Frames
        self.frames = []
        self.load_rendered_frames()
        
        # Simulation State
        self.current_frame = 0.0
        self.target_frame = 0.0
        self.velocity = 0.25
        self.is_auto_orbit = True
        self.is_dragging = False
        self.drag_start_x = 0
        self.last_mouse_x = 0
        
        self.active_fault = None
        self.mission_mode = False
        self.mission_step = 0
        self.mission_timer = 0.0
        self.start_time = time.time()
        
        self.telemetry = NOMINAL_TELEMETRY.copy()
        self.buttons = []

    def load_rendered_frames(self):
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(curr_dir, "..", ".."))
        candidates = [
            os.path.join(curr_dir, "..", "web_gcs", "frames"),
            os.path.join(project_root, "apps", "web_gcs", "frames"),
            os.path.join(project_root, "digital_twin_web", "frames"),
            os.path.join(curr_dir, "frames")
        ]
        frames_dir = None
        for cand in candidates:
            if os.path.isdir(cand):
                frames_dir = cand
                break
        
        if not frames_dir:
            frames_dir = os.path.join(curr_dir, "..", "web_gcs", "frames")

        print(f"Loading 3D raytraced EEVEE turntable frames from: {frames_dir}...")
        
        for i in range(120):
            fname = f"frame_{i:03d}.jpg"
            fpath = os.path.join(frames_dir, fname)
            if os.path.exists(fpath):
                img = pygame.image.load(fpath).convert()
                # Scale smoothly to fit viewport
                img = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
                self.frames.append(img)
            else:
                print(f"Warning: Missing {fname}")
                
        print(f"Successfully loaded {len(self.frames)} frames for 60 FPS hardware acceleration.")

    def trigger_fault(self, fault_data):
        self.active_fault = fault_data
        self.target_frame = fault_data['target_frame']
        self.is_auto_orbit = False
        for k, v in fault_data['telemetry'].items():
            self.telemetry[k] = v

    def reset_nominal(self):
        self.active_fault = None
        self.mission_mode = False
        self.telemetry = NOMINAL_TELEMETRY.copy()
        self.is_auto_orbit = True

    def draw_panel(self, rect, bg_color=CLR_PANEL_BG, border_color=CLR_PANEL_BORDER):
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        s.fill(bg_color)
        self.screen.blit(s, (rect[0], rect[1]))
        pygame.draw.rect(self.screen, border_color, rect, 1)

    def draw_gauge_bar(self, x, y, w, h, label, val_str, norm, warn=False, crit=False):
        # Track
        pygame.draw.rect(self.screen, (15, 25, 40), (x, y, w, h))
        pygame.draw.rect(self.screen, (40, 60, 90), (x, y, w, h), 1)
        
        # Fill
        fill_w = max(2, min(w, int(w * norm)))
        fill_col = CLR_RED if crit else (CLR_ORANGE if warn else CLR_CYAN)
        pygame.draw.rect(self.screen, fill_col, (x, y, fill_w, h))
        
        # Text
        lbl = self.font_small.render(label, True, CLR_WHITE)
        val = self.font_mono.render(val_str, True, (255, 255, 255))
        self.screen.blit(lbl, (x + 6, y + (h - lbl.get_height()) // 2))
        self.screen.blit(val, (x + w - val.get_width() - 6, y + (h - val.get_height()) // 2))

    def render(self):
        self.screen.fill(CLR_BG)
        self.buttons.clear()
        
        # 1. Draw 3D Viewport Frame
        if self.frames:
            idx = int(self.current_frame) % len(self.frames)
            self.screen.blit(self.frames[idx], (0, 0))

        # 2. TOP BAR
        self.draw_panel((0, 0, WIDTH, 48), bg_color=(10, 16, 26, 235), border_color=(0, 180, 240, 150))
        pygame.draw.line(self.screen, CLR_CYAN, (0, 47), (WIDTH, 47), 2)
        
        # Header Badge
        pygame.draw.rect(self.screen, CLR_CYAN, (15, 12, 6, 24))
        title1 = self.font_small.render("DRDO / iDEX PS-26054", True, CLR_CYAN)
        title2 = self.font_title.render("ROTAX 912 iS MALE UAV DIGITAL TWIN", True, CLR_WHITE)
        self.screen.blit(title1, (28, 9))
        self.screen.blit(title2, (28, 22))

        # Status Pill
        pill_rect = (WIDTH // 2 - 140, 10, 280, 28)
        if self.active_fault:
            self.draw_panel(pill_rect, bg_color=(200, 30, 30, 220), border_color=CLR_RED)
            st_text = self.font_sub.render(f"⚠ {self.active_fault['short']}", True, CLR_WHITE)
        elif self.mission_mode:
            self.draw_panel(pill_rect, bg_color=(20, 80, 160, 220), border_color=CLR_CYAN)
            st_text = self.font_sub.render(f"✈ AUTO MISSION: STAGE {self.mission_step+1}/5", True, CLR_WHITE)
        else:
            self.draw_panel(pill_rect, bg_color=(15, 80, 40, 220), border_color=CLR_GREEN)
            st_text = self.font_sub.render("● PROPULSION NOMINAL / CRUISE", True, (120, 255, 160))
        self.screen.blit(st_text, (pill_rect[0] + (pill_rect[2] - st_text.get_width()) // 2, 14))

        # Time & FPS
        elapsed = int(time.time() - self.start_time)
        m, s = divmod(elapsed, 60)
        t_str = f"MISSION T+{m//60:02d}:{m%60:02d}:{s:02d}"
        t_surf = self.font_mono.render(t_str, True, CLR_CYAN)
        fps_surf = self.font_small.render(f"{self.clock.get_fps():.1f} FPS (EEVEE)", True, CLR_GREEN)
        self.screen.blit(t_surf, (WIDTH - 280, 16))
        self.screen.blit(fps_surf, (WIDTH - 120, 16))

        # 3. LEFT TELEMETRY HUD
        hud_w = 250
        hud_h = 350
        hud_x = 15
        hud_y = 60
        self.draw_panel((hud_x, hud_y, hud_w, hud_h))
        
        hdr_lbl = self.font_sub.render("PROPULSION TELEMETRY", True, CLR_CYAN)
        self.screen.blit(hdr_lbl, (hud_x + 12, hud_y + 10))
        
        t = self.telemetry
        gauges = [
            ("ENGINE RPM", f"{t['rpm']:.0f} RPM", min(1.0, t['rpm'] / 5800.0), t['rpm'] > 5500, t['rpm'] < 4000),
            ("CYL #2 CHT", f"{t['cht']:.1f} °C", min(1.0, t['cht'] / 160.0), t['cht'] > 130.0, t['cht'] > 138.0),
            ("OIL PRESSURE", f"{t['oil_p']:.2f} BAR", min(1.0, t['oil_p'] / 6.0), t['oil_p'] < 2.5, t['oil_p'] < 2.0),
            ("OIL TEMP", f"{t['oil_t']:.1f} °C", min(1.0, t['oil_t'] / 140.0), t['oil_t'] > 115.0, t['oil_t'] > 125.0),
            ("FUEL FLOW", f"{t['fuel_flow']:.1f} L/H", min(1.0, t['fuel_flow'] / 30.0), t['fuel_flow'] < 15.0, False),
            ("MAP PRESSURE", f"{t['map_press']:.1f} kPa", min(1.0, t['map_press'] / 130.0), t['map_press'] > 105.0, False),
            ("EXHAUST EGT #3", f"{t['egt']:.0f} °C", min(1.0, t['egt'] / 1000.0), t['egt'] > 870.0, t['egt'] > 920.0),
            ("DC BUS VOLT", f"{t['bus_v']:.1f} V", min(1.0, t['bus_v'] / 16.0), t['bus_v'] < 13.0, t['bus_v'] < 12.5),
            ("VIBRATION RMS", f"{t['vibe']:.2f} mm/s", min(1.0, t['vibe'] / 4.0), t['vibe'] > 2.0, t['vibe'] > 3.0),
        ]
        
        gy = hud_y + 36
        for label, val_str, norm, warn, crit in gauges:
            self.draw_gauge_bar(hud_x + 10, gy, hud_w - 20, 22, label, val_str, norm, warn, crit)
            gy += 28

        # 4. RIGHT FAULT MATRIX DOCK
        dock_w = 250
        dock_h = 420
        dock_x = WIDTH - dock_w - 15
        dock_y = 60
        self.draw_panel((dock_x, dock_y, dock_w, dock_h))
        
        dock_hdr = self.font_sub.render("FAULT MATRIX (PS-26054)", True, CLR_CYAN)
        self.screen.blit(dock_hdr, (dock_x + 12, dock_y + 10))
        
        mx, my = pygame.mouse.get_pos()
        by = dock_y + 36
        for i, f_data in enumerate(FAULT_DATABASE):
            is_active = (self.active_fault == f_data)
            btn_rect = (dock_x + 10, by, dock_w - 20, 26)
            is_hover = (btn_rect[0] <= mx <= btn_rect[0] + btn_rect[2] and btn_rect[1] <= my <= btn_rect[1] + btn_rect[3])
            
            if is_active:
                bg = (200, 40, 40, 220)
                border = CLR_RED
            elif is_hover:
                bg = (30, 70, 110, 220)
                border = CLR_CYAN
            else:
                bg = (18, 28, 44, 180)
                border = (40, 70, 100, 150)
                
            self.draw_panel(btn_rect, bg_color=bg, border_color=border)
            
            # Badge
            pygame.draw.rect(self.screen, (0, 140, 200), (dock_x + 14, by + 3, 18, 20))
            k_surf = self.font_mono.render(f_data['key_char'], True, CLR_WHITE)
            lbl_surf = self.font_small.render(f_data['short'], True, CLR_WHITE)
            self.screen.blit(k_surf, (dock_x + 19, by + 4))
            self.screen.blit(lbl_surf, (dock_x + 38, by + 5))
            
            self.buttons.append((btn_rect, f_data))
            by += 31

        # Reset & Mission Buttons
        actions = [
            ("0", "NOMINAL RESET", 'RESET', (15, 90, 50, 200)),
            ("M", "AUTO MISSION SIM", 'MISSION', (20, 60, 130, 200)),
            ("SPACE", "PAUSE / ORBIT", 'ORBIT', (80, 50, 110, 200))
        ]
        by += 6
        for k_lbl, title, aid, bg in actions:
            btn_rect = (dock_x + 10, by, dock_w - 20, 24)
            is_hover = (btn_rect[0] <= mx <= btn_rect[0] + btn_rect[2] and btn_rect[1] <= my <= btn_rect[1] + btn_rect[3])
            self.draw_panel(btn_rect, bg_color=(40, 90, 150, 220) if is_hover else bg, border_color=CLR_CYAN if is_hover else (50, 90, 130, 150))
            t_s = self.font_small.render(f"[{k_lbl}] {title}", True, CLR_WHITE)
            self.screen.blit(t_s, (dock_x + 20, by + 4))
            self.buttons.append((btn_rect, aid))
            by += 28

        # 5. BOTTOM AI DIAGNOSTIC CARD
        bot_h = 100
        bot_y = HEIGHT - bot_h - 15
        bot_x = 15
        bot_w = WIDTH - 30
        
        if self.active_fault:
            f = self.active_fault
            self.draw_panel((bot_x, bot_y, bot_w, bot_h), bg_color=(20, 10, 15, 235), border_color=CLR_RED)
            pygame.draw.rect(self.screen, CLR_RED, (bot_x + 12, bot_y + 12, 10, 10))
            
            hdr = self.font_sub.render(f"AI DIAGNOSTIC REASONING: {f['title'].upper()}", True, CLR_RED)
            comp = self.font_small.render(f"TARGET COMPONENT: {f['comp']}", True, CLR_WHITE)
            sens = self.font_small.render(f"SENSOR TELEMETRY: {f['sensor']}", True, CLR_CYAN)
            root = self.font_small.render(f"ROOT CAUSE DEDUCTION: {f['ai']}", True, CLR_ORANGE)
            act = self.font_small.render(f"RECOMMENDED MITIGATION: {f['action']}", True, CLR_GREEN)
            
            self.screen.blit(hdr, (bot_x + 28, bot_y + 8))
            self.screen.blit(comp, (bot_x + 28, bot_y + 28))
            self.screen.blit(sens, (bot_x + 28, bot_y + 44))
            self.screen.blit(root, (bot_x + 28, bot_y + 60))
            self.screen.blit(act, (bot_x + 28, bot_y + 76))
        else:
            self.draw_panel((bot_x, bot_y, bot_w, bot_h), bg_color=(12, 18, 28, 235), border_color=(0, 140, 200, 150))
            pygame.draw.rect(self.screen, CLR_CYAN, (bot_x + 12, bot_y + 12, 10, 10))
            
            hdr = self.font_sub.render("AEROSPACE PROPULSION HEALTH MONITORING — ROTAX 912 iS SPORT", True, CLR_CYAN)
            st = self.font_small.render("STATUS: All 109 powertrain meshes and dual FADEC ECU sensors operating within certified envelope.", True, (180, 210, 240))
            ctrl = self.font_small.render("CONTROLS: [1-8] Trigger DRDO Faults | [0] Reset Nominal | [SPACE] Pause/Orbit | [M] Mission Sim | Mouse Drag to Rotate 360°", True, CLR_GRAY)
            
            self.screen.blit(hdr, (bot_x + 28, bot_y + 8))
            self.screen.blit(st, (bot_x + 28, bot_y + 36))
            self.screen.blit(ctrl, (bot_x + 28, bot_y + 64))

        pygame.display.flip()

    def update(self):
        # Frame Interpolation & Orbit
        if self.is_auto_orbit and not self.is_dragging:
            self.current_frame = (self.current_frame + self.velocity) % len(self.frames)
        elif not self.is_auto_orbit and not self.is_dragging:
            # Smooth camera glide to target frame
            diff = (self.target_frame - self.current_frame + 60) % 120 - 60
            self.current_frame = (self.current_frame + diff * 0.1) % 120

        # Mission Sim State Machine
        if self.mission_mode:
            self.mission_timer += 1 / FPS
            if self.mission_timer > 5.0:
                self.mission_timer = 0.0
                self.mission_step = (self.mission_step + 1) % 5
                sequence = [FAULT_DATABASE[0], FAULT_DATABASE[1], FAULT_DATABASE[3], FAULT_DATABASE[4], None]
                target = sequence[self.mission_step]
                if target is None:
                    self.reset_nominal()
                    self.mission_mode = True
                else:
                    self.trigger_fault(target)
                    self.mission_mode = True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Left click
                        mx, my = event.pos
                        clicked_btn = False
                        for rect, data in self.buttons:
                            if rect[0] <= mx <= rect[0] + rect[2] and rect[1] <= my <= rect[1] + rect[3]:
                                clicked_btn = True
                                if isinstance(data, dict):
                                    self.trigger_fault(data)
                                elif data == 'RESET':
                                    self.reset_nominal()
                                elif data == 'MISSION':
                                    self.mission_mode = not self.mission_mode
                                    self.mission_step = 0
                                    self.mission_timer = 0.0
                                elif data == 'ORBIT':
                                    self.is_auto_orbit = not self.is_auto_orbit
                                break
                        if not clicked_btn:
                            self.is_dragging = True
                            self.drag_start_x = mx
                            self.last_mouse_x = mx
                            self.is_auto_orbit = False

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.is_dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.is_dragging:
                        dx = event.pos[0] - self.last_mouse_x
                        self.last_mouse_x = event.pos[0]
                        self.current_frame = (self.current_frame - dx * 0.35) % len(self.frames)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.reset_nominal()
                    elif event.key == pygame.K_SPACE:
                        self.is_auto_orbit = not self.is_auto_orbit
                    elif event.key == pygame.K_0:
                        self.reset_nominal()
                    elif event.key == pygame.K_m:
                        self.mission_mode = not self.mission_mode
                        self.mission_step = 0
                        self.mission_timer = 0.0
                    else:
                        for f_data in FAULT_DATABASE:
                            if event.key == f_data['key']:
                                self.trigger_fault(f_data)
                                break

            self.update()
            self.render()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    app = DigitalTwinApp()
    app.run()
