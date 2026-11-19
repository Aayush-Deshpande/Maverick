/* Generated from configs/schema/state.schema.json by npm run gen:types (card M0-05). Do not edit. */

export type Channel = string | null;
/**
 * resolved component ids (training mode display only, D5)
 */
export type Components = string[];
export type Cylinder = number | null;
export type FaultId = string;
export type Kind = "PHYSICAL" | "SENSOR";
export type MarkerFor = string | null;
export type Name = string;
export type RampS = number;
export type Severity = number;
export type Simulated = boolean;
export type Source = string;
export type T0S = number;
export type Uuid = string;
export type ActiveFaults = ActiveFaultOut[];
export type Acknowledged = boolean;
/**
 * operator action (U3: every alert has one)
 */
export type Action = string;
export type Active = boolean;
export type Channel1 = string | null;
export type Code = string;
export type Count = number;
export type FaultId1 = string | null;
export type FirstS = number;
/**
 * root cause: the fault id of a hypothesis, else the channel's subsystem
 */
export type Group = string;
export type Id = string;
export type LastS = number;
export type Level = "NO-GO" | "CAUTION" | "ADVISORY";
export type ShelvedUntil = number | null;
export type Text = string;
export type Alerts = AlertOut[];
export type Detections = {
  [k: string]: unknown;
} | null;
export type EngineId = string;
export type EngineState = ("OFF" | "CRANKING" | "RUNNING" | "DEGRADED" | "FAILED" | "CALIBRATING") | null;
export type Seq = number;
export type Source1 = string | null;
export type TS = number;
export type Text1 = string;
export type Type = string;
export type EventsSince = EventOut[];
export type EvidenceClass = "SIMULATION" | "PUBLIC_PROXY" | "REAL_FLIGHT";
export type ComponentId = string;
export type Level1 = "NO-GO" | "CAUTION" | "ADVISORY" | "SENSOR" | "INJECTED";
export type MarkerFor1 = string | null;
export type Nodes = string[];
export type Reason = string;
export type Highlights = Highlight[];
export type Channel2 = string;
export type Z = number;
export type Contradicting = Evidence[];
export type Cylinder1 = number | null;
export type FaultId2 = string | null;
export type Name1 = string;
export type Posterior = number | null;
export type Supporting = Evidence[];
export type Hypotheses = Hypothesis[];
export type Maintenance = {
  [k: string]: unknown;
}[];
export type Prognostics = {
  [k: string]: unknown;
} | null;
export type RateHzActual = number | null;
export type AgeMs = number | null;
export type Quality = "OK" | "SUSPECT" | "QUARANTINED" | "VIRTUAL" | "NO_DATA";
export type Unit = string;
/**
 * null when there is no data (never a default)
 */
export type Value = number | null;
export type Reliability = {
  [k: string]: unknown;
} | null;
export type SchemaVersion = 1;
export type Seq1 = number;
export type SimTimeS = number;
export type Source2 = "SIM" | "REPLAY" | "CAN" | "MAVLINK";
export type Acknowledged1 = boolean;
export type Latched = boolean;
/**
 * UNKNOWN until the status evaluator (card M2-01) runs
 */
export type Level2 = "ENGINE_OFF" | "GO" | "ADVISORY" | "CAUTION" | "NO-GO" | "UNKNOWN";
export type Channel3 = string | null;
export type Code1 = string;
export type FaultId3 = string | null;
export type Limit = number | null;
export type Text2 = string;
export type Value1 = number | null;
export type Reasons = Reason1[];
export type TimeScale = number;
export type Twin = {
  [k: string]: unknown;
} | null;
export type WallTimeIso = string;

export interface StateMessage {
  active_faults?: ActiveFaults;
  alerts?: Alerts;
  derived?: Derived;
  detections?: Detections;
  engine_id: EngineId;
  engine_state?: EngineState;
  environment?: Environment;
  events_since?: EventsSince;
  evidence_class?: EvidenceClass;
  highlights?: Highlights;
  hypotheses?: Hypotheses;
  levers?: Levers;
  maintenance?: Maintenance;
  master?: Master;
  prognostics?: Prognostics;
  rate_hz_actual?: RateHzActual;
  readings?: Readings;
  reliability?: Reliability;
  residuals?: Residuals;
  schema_version?: SchemaVersion;
  seq: Seq1;
  sim_time_s: SimTimeS;
  source?: Source2;
  status: Status;
  time_scale?: TimeScale;
  twin?: Twin;
  vibration_orders?: VibrationOrders;
  virtual_sensors?: VirtualSensors;
  wall_time_iso: WallTimeIso;
}
export interface ActiveFaultOut {
  channel?: Channel;
  components?: Components;
  cylinder?: Cylinder;
  fault_id: FaultId;
  kind: Kind;
  marker_for?: MarkerFor;
  name: Name;
  ramp_s: RampS;
  severity: Severity;
  simulated: Simulated;
  source: Source;
  t0_s: T0S;
  uuid: Uuid;
}
export interface AlertOut {
  acknowledged: Acknowledged;
  action: Action;
  active: Active;
  channel?: Channel1;
  code: Code;
  count: Count;
  fault_id?: FaultId1;
  first_s: FirstS;
  group: Group;
  id: Id;
  last_s: LastS;
  level: Level;
  shelved_until?: ShelvedUntil;
  text: Text;
}
export interface Derived {
  [k: string]: number | null;
}
export interface Environment {
  [k: string]: number | null;
}
export interface EventOut {
  seq: Seq;
  source?: Source1;
  t_s: TS;
  text: Text1;
  type: Type;
}
export interface Highlight {
  component_id: ComponentId;
  level: Level1;
  marker_for?: MarkerFor1;
  nodes: Nodes;
  reason: Reason;
}
export interface Hypothesis {
  contradicting?: Contradicting;
  cylinder?: Cylinder1;
  fault_id: FaultId2;
  name: Name1;
  posterior?: Posterior;
  supporting?: Supporting;
}
export interface Evidence {
  channel: Channel2;
  z: Z;
}
export interface Levers {
  [k: string]: number | null;
}
/**
 * master warning / caution (unacknowledged)
 */
export interface Master {
  [k: string]: boolean;
}
export interface Readings {
  [k: string]: Reading;
}
export interface Reading {
  age_ms?: AgeMs;
  quality?: Quality;
  unit: Unit;
  value: Value;
}
export interface Residuals {
  [k: string]: number;
}
export interface Status {
  acknowledged?: Acknowledged1;
  latched?: Latched;
  level: Level2;
  reasons?: Reasons;
}
export interface Reason1 {
  channel?: Channel3;
  code: Code1;
  fault_id?: FaultId3;
  limit?: Limit;
  text: Text2;
  value?: Value1;
}
export interface VibrationOrders {
  [k: string]: number;
}
export interface VirtualSensors {
  [k: string]: number;
}
