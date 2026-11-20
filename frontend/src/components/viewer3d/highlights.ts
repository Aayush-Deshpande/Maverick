import { PropertyBinding } from 'three';
import type { Highlight } from '../../api/state';

// Highest level wins when one part is named by several highlights (D4 alert order, then sensor, then training).
export const LEVEL_ORDER = ['INJECTED', 'SENSOR', 'ADVISORY', 'CAUTION', 'NO-GO'] as const;
export type HighlightLevel = (typeof LEVEL_ORDER)[number];

// D4 / D5 colours: red NO-GO, amber CAUTION, cyan ADVISORY, blue SENSOR, white INJECTED (training mode only)
export const LEVEL_COLOUR: Record<HighlightLevel, string> = {
  'NO-GO': '#d63a2f', CAUTION: '#e0a020', ADVISORY: '#22b8cf', SENSOR: '#4c7ff0', INJECTED: '#ffffff',
};

/** GLTFLoader stores node names through PropertyBinding.sanitizeNodeName (spaces -> underscores, etc.);
 *  manifest names are the raw glTF names, so both sides are compared in sanitized form. */
export const sanitize = (name: string): string => PropertyBinding.sanitizeNodeName(name);

/** node name (sanitized) -> the level it is drawn in. Only what the state message says: no other source. */
export function highlightMap(highlights: Highlight[] | undefined): Map<string, HighlightLevel> {
  const out = new Map<string, HighlightLevel>();
  for (const h of highlights ?? []) {
    const level = h.level as HighlightLevel;
    if (!LEVEL_ORDER.includes(level)) continue;
    for (const n of h.nodes ?? []) {
      const key = sanitize(n);
      const prev = out.get(key);
      if (!prev || LEVEL_ORDER.indexOf(level) > LEVEL_ORDER.indexOf(prev)) out.set(key, level);
    }
  }
  return out;
}
