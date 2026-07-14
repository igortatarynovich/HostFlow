import type { FacetFilterOption, FacetValue } from './types'

/** Build facet options with counts from current rows (client-side Phase 1). */
export function computeFacetCounts<TRow>(
  rows: TRow[],
  getValue: (row: TRow) => string | null | undefined,
  labelFor: (value: string) => string,
): FacetFilterOption[] {
  const counts = new Map<string, number>()
  for (const row of rows) {
    const raw = getValue(row)
    const value = String(raw ?? '').trim()
    if (!value) continue
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([value, count]) => ({
      value,
      label: labelFor(value),
      count,
    }))
}

/** Merge selected values that may not appear in current dataset (keep for active filter chips). */
export function mergeFacetOptionsWithSelected(
  options: FacetFilterOption[],
  selected: string[],
  labelFor: (value: string) => string,
): FacetFilterOption[] {
  const byValue = new Map(options.map((o) => [o.value, o]))
  for (const value of selected) {
    if (!byValue.has(value)) {
      byValue.set(value, { value, label: labelFor(value), count: 0 })
    }
  }
  return [...byValue.values()].sort((a, b) => (b.count ?? 0) - (a.count ?? 0) || a.label.localeCompare(b.label))
}

/** Only values present in dataset (+ counts). Selected-but-absent values excluded from menu. */
export function facetOptionsPresentOnly(options: FacetFilterOption[]): FacetFilterOption[] {
  return options.filter((o) => (o.count ?? 0) > 0)
}

export function facetValuesToOptions(values: FacetValue[]): FacetFilterOption[] {
  return values.map((v) => ({ value: v.value, label: v.label, count: v.count }))
}

export function formatFacetOptionLabel(option: FacetFilterOption): string {
  if (option.count != null && option.count > 0) {
    return `${option.label} (${option.count})`
  }
  return option.label
}
