/* Null-safe display formatting (P Part 0 D7): missing data shows NO DATA, never 0 or a default. */
export const NO_DATA = 'NO DATA';

export function num(v: number | null | undefined, digits = 1): string {
  return typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : NO_DATA;
}

/* A 0..1 fraction as a percentage string including the % sign, or NO DATA. */
export function pct(v: number | null | undefined, digits = 0): string {
  return typeof v === 'number' && Number.isFinite(v) ? `${(v * 100).toFixed(digits)}%` : NO_DATA;
}
