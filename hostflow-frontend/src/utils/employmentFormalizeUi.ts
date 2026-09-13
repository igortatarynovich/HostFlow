/**
 * ESO-4 Formalize HR binding — pure UI decisions.
 * Context-required formal actions only → ready_to_create_employee.
 * No Employee mint, Started, rates/subtype/position menus, or universal checklist.
 * SoT: employment_formalize.v1
 */

export type FormalizeDecision =
  | 'formalization_complete'
  | 'missing'
  | 'blocked'
  | 'rejected_patch'
  | string

export type FormalizeItem = {
  code?: string
  kind?: string
  message?: string
}

export type FormalizeView = {
  decision?: FormalizeDecision | null
  ready_to_formalize?: boolean | null
  ready_to_create_employee?: boolean | null
  employee_created?: boolean | null
  employee_id?: string | null
  hr_employee_card?: boolean | null
  primary_item?: FormalizeItem | null
  active_missing?: Array<FormalizeItem | Record<string, unknown>> | null
  required_actions?: Array<FormalizeItem | Record<string, unknown>> | null
  blockers?: Array<{ code?: string; message?: string } | Record<string, unknown>> | null
  pathway_id?: string | null
  rejection_reason?: string | null
  confirmed_actions?: string[] | null
}

/** Operator-confirmable formal codes on this thin Formalize surface. */
export const CONFIRMABLE_FORMAL_CODES = new Set([
  'confirm_employment_contract_basis',
  'work_authorization_evidence',
])

/** Codes that are reuse checks — never render as input when already known. */
export const REUSE_ONLY_FORMAL_CODES = new Set(['identity_facts_present'])

/** Runtime choice menus that must never appear on Formalize UI. */
export const FORBIDDEN_FORMALIZE_RUNTIME_CHOICES = [
  'pathway',
  'person',
  'vacancy',
  'employer',
  'rates',
  'contract_subtype',
  'position',
] as const

export function normalizeFormalCode(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

export function formalizeSurfaceMode(view: FormalizeView | null | undefined): {
  mode: 'complete' | 'missing' | 'blocked' | 'rejected' | 'unknown'
  readyToCreateEmployee: boolean
} {
  const d = normalizeFormalCode(view?.decision)
  const ready = Boolean(view?.ready_to_create_employee) && d === 'formalization_complete'
  if (d === 'formalization_complete') return { mode: 'complete', readyToCreateEmployee: ready }
  if (d === 'missing') return { mode: 'missing', readyToCreateEmployee: false }
  if (d === 'blocked') return { mode: 'blocked', readyToCreateEmployee: false }
  if (d === 'rejected_patch') return { mode: 'rejected', readyToCreateEmployee: false }
  return { mode: 'unknown', readyToCreateEmployee: false }
}

export function primaryFormalItem(view: FormalizeView | null | undefined): FormalizeItem | null {
  const item = view?.primary_item
  if (item && typeof item === 'object') {
    const code = String(item.code || '').trim()
    if (code && normalizeFormalCode(code) !== 'ready_to_create_employee') {
      return {
        code,
        kind: String(item.kind || '').trim() || undefined,
        message: String(item.message || '').trim() || undefined,
      }
    }
  }
  const missing = view?.active_missing
  if (Array.isArray(missing) && missing[0] && typeof missing[0] === 'object') {
    const row = missing[0] as FormalizeItem
    const code = String(row.code || '').trim()
    if (!code) return null
    return {
      code,
      kind: String(row.kind || '').trim() || undefined,
      message: String(row.message || '').trim() || undefined,
    }
  }
  return null
}

export function operatorCanConfirmCurrentFormalItem(
  view: FormalizeView | null | undefined,
): boolean {
  const { mode } = formalizeSurfaceMode(view)
  if (mode !== 'missing') return false
  const item = primaryFormalItem(view)
  if (!item?.code) return false
  const code = normalizeFormalCode(item.code)
  if (REUSE_ONLY_FORMAL_CODES.has(code)) return false
  return CONFIRMABLE_FORMAL_CODES.has(code)
}

export function buildFormalizePatchForPrimary(
  primaryCode: string,
): { confirmed_actions: string[] } | null {
  const code = normalizeFormalCode(primaryCode)
  if (!CONFIRMABLE_FORMAL_CODES.has(code)) return null
  return { confirmed_actions: [code] }
}

/** Terminal slice result — never auto-open Employee/Started or mint HR card. */
export function isFormalizeTerminalAllowCreate(view: FormalizeView | null | undefined): boolean {
  const { mode, readyToCreateEmployee } = formalizeSurfaceMode(view)
  return mode === 'complete' && readyToCreateEmployee
}

export function assertFormalizeNoEmployeeSideEffects(
  view: FormalizeView | null | undefined,
): boolean {
  if (view?.employee_created === true) return false
  if (view?.hr_employee_card === true) return false
  if (view?.employee_id) return false
  return true
}

/** Zero-choice: Formalize must never offer pathway/person/vacancy/employer/rates menus. */
export function shouldShowFormalizeRuntimeChoice(
  choice: (typeof FORBIDDEN_FORMALIZE_RUNTIME_CHOICES)[number],
): false {
  void choice
  return false
}

export function shouldEnterFormalizeFromEmployability(emp: {
  decision?: string | null
} | null | undefined): boolean {
  return normalizeFormalCode(emp?.decision) === 'employable'
}
