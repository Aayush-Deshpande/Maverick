/**
 * TypeScript Data Contracts for Rotax 912 iS MALE UAV Digital Twin
 * DRDO / iDEX Problem Statement ID: 26054
 */

export interface EngineTelemetry {
  ENGINE_RPM: number;
  PROP_RPM: number;
  TPS: number;
  CHT_1: number;
  CHT_2: number;
  CHT_3: number;
  CHT_4: number;
  EGT_1: number;
  EGT_2: number;
  EGT_3: number;
  EGT_4: number;
  OIL_PRESS: number;
  OIL_TEMP: number;
  FUEL_FLOW: number;
  FUEL_RAIL_P: number;
  MAP: number;
  VIB_GEARBOX_RMS: number;
  BUS_VOLTAGE: number;
  BATTERY_CURRENT: number;
  FADEC_ACTIVE_LANE: string;
  ALTITUDE_FT: number;
  OAT_C: number;
  TAS_KNOTS: number;
  FLIGHT_PHASE: string;
  THEATER: string;
  INJ_TIMING_BTDC?: number;
  INJ_PULSE_WIDTH_MS?: number;
  IGN_TIMING_BTDC?: number;
  LAMBDA_AFR?: number;
  BSFC_G_KWH?: number;
  POWER_KW?: number;
  THERMAL_EFFICIENCY?: number;
}

export interface EarlyWarningTrend {
  channel: string;
  drift_rate_per_hr: number;
  time_to_threshold_min: number;
  alert_level: string;
  message: string;
}

export interface SubsystemHealth {
  propulsion: number;
  fuel_system: number;
  electrical: number;
  thermal: number;
  mechanical: number;
}

export interface AIDiagnosis {
  status: 'IDLE' | 'THINKING' | 'READY' | 'ERROR';
  fault_name: string;
  explanation: string;
  citations: string[];
}

export interface SensorSanity {
  all_sensors_valid: boolean;
  drift_detected: boolean;
  failed_channels: string[];
  suppressed_anomaly: boolean;
  advisory: string;
}

export interface ComponentRUL {
  rul_p10_hours: number;
  rul_p50_hours: number;
  rul_p90_hours: number;
  confidence: number;
}

export interface AnalyticsState {
  residuals: Record<string, number>;
  anomaly_score: number;
  health_index: number;
  diagnosed_fault_id: number;
  diagnosed_fault_name: string;
  diagnosed_confidence: number;
  target_3d_mesh: string;
  target_parts: string[];
  ata_chapter: string;
  subsystem: string;
  severity: string;
  root_cause: string;
  prescriptive_action: string;
  emergency_checklist: string[];
  maintenance_order: string;
  go_no_go: 'GO' | 'CAUTION' | 'NO-GO';
  go_no_go_reason: string;
  rul_p10_hours: number;
  rul_p50_hours: number;
  limiting_component?: string | null;
  planned_sortie_hours?: number;
  rul_by_component?: Record<string, ComponentRUL>;
  sensor_sanity?: SensorSanity;
  early_warning_trend?: EarlyWarningTrend | null;
  threshold_baseline?: {
    conventional_breached: boolean;
    breached_parameters: string[];
    conventional_breach_timestamp?: number | null;
    twin_detect_timestamp?: number | null;
    lead_time_sec?: number | null;
    conventional_thresholds?: Record<string, number>;
  };
  conformal_rul?: Record<string, {
    rul_p10_hours: number;
    rul_p50_hours: number;
    rul_p90_hours: number;
    confidence_level: number;
    coverage_guarantee: string;
    calibrated?: boolean;
  }>;
  subsystem_health?: SubsystemHealth;
  causal_chain?: string[];
  ai_diagnosis?: AIDiagnosis;
}

export interface UnifiedTelemetryState {
  timestamp: number;
  sortie_id: string;
  is_engine_running: boolean;
  active_commanded_fault_id: number;
  active_commanded_fault_name: string;
  telemetry: EngineTelemetry;
  analytics: AnalyticsState;
}

export type GCSRole = 'OPERATOR' | 'PROPULSION_ENGINEER' | 'MAINTENANCE_CREW';

export interface ControlCommand {
  action: 'START_ENGINE' | 'STOP_ENGINE' | 'SET_FAULT' | 'CLEAR_FAULT' | 'SET_THROTTLE' | 'SET_ALTITUDE' | 'SET_OAT' | 'SET_REGIME' | 'SET_ROLE' | 'EXPORT_DEBRIEF';
  fault_id?: number;
  throttle?: number;
  altitude_ft?: number;
  oat_c?: number;
  region?: string;
  regime?: string;
  role?: GCSRole;
}
