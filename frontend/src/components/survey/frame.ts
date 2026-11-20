/* Frame shape the landing survey was written against (main's legacy EngineFrame), and the adapter that maps
   Beta's /api/engines/{id}/state payload onto it at this one boundary, so the landing components stay as on main. */

export interface EngineFrame {
  engine_id: string;
  t: number;
  source: string;
  evidence_class: string;
  channels: Record<string, number>;
  cht: number[];
  egt: number[];
  detection: null | { scores: Record<string, number>; ratios: Record<string, number>; raw_alarm: boolean; confirmed: boolean; top_channels: Array<string | [string, number]> };
  heavy: null | { label: string; classes: string[]; scores: number[] };
  diagnosis?: null | { fault_name: string; ata_chapter: string; manual_reference?: string; subsystem?: string; severity: string; root_cause_explanation?: string; causal_chain?: string[]; prescriptive_action?: string; maintenance_order?: string; confidence?: number; cylinder?: number | null };
  prognostics?: null | { damage?: { damage_total: number; life_remaining_fraction: number; component?: string }; rul?: { rul_p_lower: number; rul_point: number; rul_p_upper: number; nominal_coverage: number } };
  reliability?: null | { mission_reliability: number; limiting_component: string; mission_hours: number };
  glide?: null | { altitude_ft: number; ld_ratio?: number; glide_range_nm: number; time_aloft_min: number; sink_rate_fpm?: number; reachable_count: number; recommended_diversion: null | string | { name?: string; airfield_id?: string }; airfields: Array<{ airfield_id: string; name: string; distance_nm: number; alt_required_ft?: number; alt_margin_ft: number; is_reachable: boolean; status: string }> };
}

const KM_PER_NM = 1.852;                                  // nautical mile in km (definition)

type Raw = Record<string, any>;

/** Beta payload -> survey frame. Renamed fields are mapped; missing ones stay undefined (the survey shows a dash). */
export function toSurveyFrame(raw: Raw): EngineFrame {
  const g = raw.glide as Raw | null | undefined;
  const rul = raw.prognostics?.rul as Raw | undefined;
  return {
    ...(raw as EngineFrame),
    prognostics: raw.prognostics ? {
      ...raw.prognostics,
      rul: rul && rul.status === 'OK' ? { rul_point: rul.rul_h, rul_p_lower: rul.rul_lower_h, rul_p_upper: rul.rul_upper_h,
        nominal_coverage: rul.coverage_target } : undefined,
    } : raw.prognostics,
    glide: g ? {
      altitude_ft: g.altitude_ft, ld_ratio: g.glide_ratio, sink_rate_fpm: g.sink_rate_fpm, time_aloft_min: g.time_aloft_min,
      glide_range_nm: g.still_air_range_km == null ? undefined as unknown as number : g.still_air_range_km / KM_PER_NM,
      reachable_count: g.reachable_count, recommended_diversion: g.recommended_diversion,
      airfields: (g.reachable_airfields ?? []).map((a: Raw) => ({ ...a, distance_nm: a.distance_km / KM_PER_NM })),
    } : g,
  };
}
