/** P10A — Presentation Rules evaluator (mirrors backend presentation_rules.py). */

export type PresentationRuleCondition = {
  source_field: string
  operator?: 'eq' | 'neq' | 'truthy' | 'falsy' | 'in'
  value?: unknown
}

export type PresentationRules = {
  show_if?: PresentationRuleCondition
  hide_if?: PresentationRuleCondition
  required_if?: PresentationRuleCondition
  readonly_if?: PresentationRuleCondition
}

export type PresentationFieldEvaluated = {
  visible: boolean
  readonly: boolean
  intake_level: string
  base_intake_level: string
}

export type PresentationFieldWithRules = {
  qualified_code: string
  sort_order: number
  intake_level: string
  label: string
  field_type?: string | null
  widget_hint?: string | null
  presentation_rules?: PresentationRules
  evaluated?: PresentationFieldEvaluated
}

function coerceBool(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  if (value == null) return false
  if (typeof value === 'number') return value !== 0
  const text = String(value).trim().toLowerCase()
  if (['true', '1', 'yes', 'y', 'on'].includes(text)) return true
  if (['false', '0', 'no', 'n', 'off', ''].includes(text)) return false
  return Boolean(text)
}

function normalizeScalar(value: unknown): unknown {
  return typeof value === 'string' ? value.trim() : value
}

export function evaluateRuleCondition(condition: PresentationRuleCondition | undefined, values: Record<string, unknown>): boolean {
  if (!condition?.source_field) return false
  const actual = values[condition.source_field]
  const operator = condition.operator || 'eq'
  const expected = condition.value

  if (operator === 'truthy') return coerceBool(actual)
  if (operator === 'falsy') return !coerceBool(actual)
  if (operator === 'eq') return normalizeScalar(actual) === normalizeScalar(expected)
  if (operator === 'neq') return normalizeScalar(actual) !== normalizeScalar(expected)
  if (operator === 'in') {
    if (!Array.isArray(expected)) return false
    const normalizedActual = normalizeScalar(actual)
    return expected.some((item) => normalizeScalar(item) === normalizedActual)
  }
  return false
}

export function evaluatePresentationFieldState(
  field: PresentationFieldWithRules,
  values: Record<string, unknown>,
): PresentationFieldEvaluated {
  const baseLevel = field.intake_level || 'optional'
  const rules = field.presentation_rules || {}
  let visible = baseLevel !== 'hidden'
  let readonly = false
  let effectiveLevel = baseLevel

  if (rules.show_if) visible = evaluateRuleCondition(rules.show_if, values)
  if (rules.hide_if && evaluateRuleCondition(rules.hide_if, values)) visible = false
  if (rules.readonly_if && evaluateRuleCondition(rules.readonly_if, values)) readonly = true
  if (visible && rules.required_if && evaluateRuleCondition(rules.required_if, values)) {
    effectiveLevel = 'required'
  }
  if (!visible) {
    effectiveLevel = 'hidden'
    readonly = false
  }

  return {
    visible,
    readonly,
    intake_level: effectiveLevel,
    base_intake_level: baseLevel,
  }
}

export function evaluatePresentationFields(
  fields: PresentationFieldWithRules[],
  values: Record<string, unknown>,
): Array<PresentationFieldWithRules & { evaluated: PresentationFieldEvaluated }> {
  return fields.map((field) => ({
    ...field,
    evaluated: evaluatePresentationFieldState(field, values),
  }))
}

/** Drop values for fields hidden by presentation_rules (e.g. after need_type branch switch). */
export function pruneHiddenPresentationValues(
  values: Record<string, unknown>,
  fields: Array<PresentationFieldWithRules & { evaluated: PresentationFieldEvaluated }>,
): Record<string, unknown> {
  const visible = new Set(fields.filter((field) => field.evaluated.visible).map((field) => field.qualified_code))
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(values)) {
    if (visible.has(key)) out[key] = value
  }
  return out
}
