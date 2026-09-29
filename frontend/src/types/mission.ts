/**
 * Canonical Mission Definition & State Types (ARCH-2026-MP-001)
 */

export type MissionStatus = 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'ABORTED' | 'DERATED';

export type FlightPhase =
  | 'PREFLIGHT'
  | 'TAKEOFF'
  | 'CLIMB'
  | 'TRANSIT'
  | 'CRUISE'
  | 'LOITER'
  | 'RETURN_TRANSIT'
  | 'DESCENT'
  | 'LANDING'
  | 'COMPLETED';

export interface Waypoint {
  id: string;
  name: string;
  lat: number;
  lon: number;
  alt_msl_m: number;
  airspeed_ktas: number;
  loiter_radius_m?: number;
  loiter_duration_sec?: number;
  terrain_alt_m?: number;
}

export interface ScheduledEvent {
  trigger_time_sec: number;
  action: string;
  fault_mode?: string;
  cylinder?: number;
  severity: number;
  ramp_sec: number;
  target_value?: number;
  applied?: boolean;
}

export interface MissionPhaseSpec {
  name: string;
  duration_sec: number;
  start_alt_ft: number;
  end_alt_ft: number;
  throttle_pct: number;
  oat_c: number;
  dust_mg_m3?: number;
}

export interface PhaseScheduledEvent {
  phase_name: string;
  elapsed_in_phase_sec: number;
  action?: string;
  fault_mode?: string;
  cylinder?: number;
  severity?: number;
  ramp_sec?: number;
  applied?: boolean;
}

export interface EnvironmentalConditions {
  theater_name: string;
  qnh_hpa: number;
  isa_temp_offset_c: number;
  base_elevation_m: number;
  ambient_wind_kt: number;
  wind_direction_deg: number;
  dust_density_mg_m3: number;
}

export interface MissionDefinition {
  mission_id: string;
  name: string;
  engine_id: string;
  airframe_id: string;
  planned_duration_sec: number;
  environment: EnvironmentalConditions;
  phases?: MissionPhaseSpec[];
  phase_events?: PhaseScheduledEvent[];
  waypoints: Waypoint[];
  scheduled_events: ScheduledEvent[];
}

export interface MissionState {
  mission_id: string;
  status: MissionStatus;
  phase: FlightPhase;
  time_elapsed_sec: number;
  time_remaining_sec: number;
  time_scale: number;

  // Kinematics & Coordinates
  pos_x_m: number;
  pos_y_m: number;
  pos_z_m: number;
  ground_elevation_m: number;
  agl_m: number;
  ground_speed_mps: number;
  true_airspeed_ktas: number;
  indicated_airspeed_kias: number;
  heading_deg: number;
  pitch_deg: number;
  roll_bank_deg: number;
  current_waypoint_idx: number;
  waypoint_distance_remaining_m: number;
  path_progress_fraction: number;

  // Phase-based mission progress
  current_phase_idx?: number;
  elapsed_in_phase_sec?: number;
  phase_duration_sec?: number;

  // Atmospheric State
  ambient_oat_c: number;
  ambient_pressure_hpa: number;
  density_altitude_ft: number;

  // Commanded Propulsion Demand
  commanded_throttle_pct: number;
  effective_engine_load_pct: number;

  // Plant State
  engine_id: string;
  rpm: number;
  max_cht_c: number;
  max_egt_c: number;
  oil_press_bar: number;
  fuel_flow_kg_h: number;
  cht: number[];
  egt: number[];

  // PHM & Diagnostics
  active_faults: Array<{ mode?: string; cylinder?: number; severity?: number; origin?: string }>;
  residual_alarm: boolean;
  confirmed_anomaly: boolean;
  top_divergent_channel?: string | null;
  flyhash_novelty_score: number;
  is_novel_pattern: boolean;
  top_diagnostic_hypothesis?: string | null;
  diagnostic_confidence: number;
  limiting_component: string;
  mission_reliability: number;
  rul_hours?: number | null;
  prescriptive_advisory: string;
}
