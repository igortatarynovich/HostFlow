/** Shared date display for HR employee workspace panels. */
export function formatShortDateIso(value: string | null | undefined): string {
  if (value == null || value === '') return '—'
  const ms = Date.parse(value)
  if (Number.isNaN(ms)) return String(value)
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(ms)
  } catch {
    return String(value)
  }
}

export function humanizeToken(value: string | null | undefined): string {
  if (!value || !value.trim()) return '—'
  const s = value.trim().replace(/_/g, ' ')
  return s.replace(/\b\w/g, (c) => c.toUpperCase())
}
