/** Shared presentation helpers for Source cards (no JSX). */
export function humanizeMetaPlaceholder(
  name: string | null | undefined,
  formId?: string | null,
): string | null {
  const n = String(name || '').trim()
  if (!n) return null
  if (formId && n === `Meta form ${formId}`) return null
  if (/^meta form \d+$/i.test(n)) return null
  return n
}

export function sourceMappingReady(row: {
  mapping_headline?: string | null
}): boolean {
  return String(row.mapping_headline || '').trim() === 'all_set'
}
