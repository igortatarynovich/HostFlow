export type FieldOption = {
  value: string
  label: string
}

export function optionLabelForValue(
  options: FieldOption[] | undefined,
  value: unknown,
): string {
  const raw = String(value ?? '').trim()
  if (!raw) return ''
  const match = (options ?? []).find((opt) => opt.value === raw)
  if (match?.label) return match.label
  if (!raw.includes('_')) return raw.charAt(0).toUpperCase() + raw.slice(1)
  return raw
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatFieldDisplayValue(
  value: unknown,
  options?: FieldOption[],
): string {
  if (Array.isArray(value)) {
    return value
      .map((item) => optionLabelForValue(options, item))
      .filter(Boolean)
      .join(', ')
  }
  return optionLabelForValue(options, value)
}
