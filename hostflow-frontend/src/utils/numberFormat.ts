/** Centralized locale number formatting (ADR-011 §9: avoid ad-hoc `.toLocaleString` in UI). */

export function formatFixedDecimal(
  value: string | number | null | undefined,
  minFractionDigits = 2,
  maxFractionDigits = 2,
): string {
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return '—'
  return num.toLocaleString(undefined, { minimumFractionDigits: minFractionDigits, maximumFractionDigits: maxFractionDigits })
}
