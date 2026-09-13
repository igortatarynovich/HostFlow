/**
 * ESO-5 Started HR binding — pure UI decisions.
 * Entry only when ready_to_create_employee=true.
 * confirm_physical_start is human confirmation (never auto).
 * Terminal started/already_started stays on HR handoff host.
 * SoT: employment_started.v1
 */

import {
  isFormalizeTerminalAllowCreate,
  type FormalizeView,
} from './employmentFormalizeUi'

export type StartedDecision =
  | 'started'
  | 'already_started'
  | 'not_started'
  | 'blocked'
  | 'rejected_confirm'
  | string

export type StartedItem = {
  code?: string
  kind?: string
  message?: string
}

export type StartedView = {
  decision?: StartedDecision | null
  ready_to_create_employee?: boolean | null
  started?: boolean | null
  start_date?: string | null
  employment_context?: Record<string, unknown> | null
  employee_created?: boolean | null
  employee_id?: string | null
  mint_employee?: boolean | null
  hr_employee_card?: boolean | null
  primary_item?: StartedItem | null
  active_missing?: Array<StartedItem | Record<string, unknown>> | null
  start_event_emitted?: boolean | null
  idempotent_replay?: boolean | null
  audit_event_type?: string | null
  formalization_complete_implies_started?: boolean | null
  employee_created_implies_started?: boolean | null
  blockers?: Array<{ code?: string; message?: string } | Record<string, unknown>> | null
  rejection_reason?: string | null
  spine?: string | null
}

export const ACTION_CONFIRM_PHYSICAL_START = 'confirm_physical_start'
export const FACT_START_DATE = 'start_date'
export const FACT_EMPLOYMENT_CONTEXT = 'employment_context'

/** Runtime choice menus that must never appear on Started UI. */
export const FORBIDDEN_STARTED_RUNTIME_CHOICES = [
  'pathway',
  'person',
  'vacancy',
  'employer',
  'rates',
  'contract_subtype',
  'position',
] as const

export function normalizeStartedCode(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

/** Lock: ready_to_create_employee=true is the only entry into Started surface. */
export function shouldEnterStartedFromFormalize(
  formalize: FormalizeView | null | undefined,
): boolean {
  return isFormalizeTerminalAllowCreate(formalize)
}

/**
 * formalization_complete alone must not open Started.
 * ready_to_create_employee without complete decision also must not.
 */
export function formalizationCompleteImpliesStartedEntry(
  formalize: FormalizeView | null | undefined,
): boolean {
  void formalize
  return false
}

export function startedSurfaceMode(view: StartedView | null | undefined): {
  mode:
    | 'started'
    | 'already_started'
    | 'awaiting_confirm'
    | 'missing_fact'
    | 'blocked'
    | 'rejected'
    | 'unknown'
  started: boolean
  idempotentReplay: boolean
} {
  const d = normalizeStartedCode(view?.decision)
  const started = Boolean(view?.started) && (d === 'started' || d === 'already_started')
  const replay = Boolean(view?.idempotent_replay) || d === 'already_started'

  if (d === 'started') {
    return { mode: 'started', started: true, idempotentReplay: false }
  }
  if (d === 'already_started') {
    return { mode: 'already_started', started: true, idempotentReplay: true }
  }
  if (d === 'blocked') {
    return { mode: 'blocked', started: false, idempotentReplay: false }
  }
  if (d === 'rejected_confirm') {
    return { mode: 'rejected', started: false, idempotentReplay: false }
  }
  if (d === 'not_started') {
    const primary = primaryStartedItem(view)
    const code = normalizeStartedCode(primary?.code)
    if (code === ACTION_CONFIRM_PHYSICAL_START) {
      return { mode: 'awaiting_confirm', started: false, idempotentReplay: false }
    }
    if (code === FACT_START_DATE || code === FACT_EMPLOYMENT_CONTEXT) {
      return { mode: 'missing_fact', started: false, idempotentReplay: false }
    }
    if (primary?.code) {
      return { mode: 'missing_fact', started: false, idempotentReplay: false }
    }
    return { mode: 'awaiting_confirm', started: false, idempotentReplay: false }
  }
  return { mode: 'unknown', started, idempotentReplay: replay }
}

export function primaryStartedItem(view: StartedView | null | undefined): StartedItem | null {
  const item = view?.primary_item
  if (item && typeof item === 'object') {
    const code = String(item.code || '').trim()
    if (code) {
      return {
        code,
        kind: String(item.kind || '').trim() || undefined,
        message: String(item.message || '').trim() || undefined,
      }
    }
  }
  const missing = view?.active_missing
  if (Array.isArray(missing) && missing[0] && typeof missing[0] === 'object') {
    const row = missing[0] as StartedItem
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

/** Human confirm only — never auto from evaluate / formalize / employee mint. */
export function operatorCanConfirmPhysicalStart(
  view: StartedView | null | undefined,
): boolean {
  const { mode } = startedSurfaceMode(view)
  if (mode !== 'awaiting_confirm') return false
  const item = primaryStartedItem(view)
  if (!item?.code) {
    // Evaluate may leave empty missing when facts known but confirm still required.
    return normalizeStartedCode(view?.decision) === 'not_started'
  }
  return normalizeStartedCode(item.code) === ACTION_CONFIRM_PHYSICAL_START
}

export function needsStartDateInput(view: StartedView | null | undefined): boolean {
  const { mode } = startedSurfaceMode(view)
  if (mode !== 'missing_fact') return false
  return normalizeStartedCode(primaryStartedItem(view)?.code) === FACT_START_DATE
}

export function needsEmploymentContextOnly(view: StartedView | null | undefined): boolean {
  const { mode } = startedSurfaceMode(view)
  if (mode !== 'missing_fact') return false
  return normalizeStartedCode(primaryStartedItem(view)?.code) === FACT_EMPLOYMENT_CONTEXT
}

export function buildPhysicalStartConfirmation(opts?: {
  startDate?: string | null
}): { confirmed: true; start_date?: string } {
  const date = String(opts?.startDate || '').trim()
  if (date) return { confirmed: true, start_date: date.slice(0, 10) }
  return { confirmed: true }
}

export function isStartedTerminal(view: StartedView | null | undefined): boolean {
  const { mode, started } = startedSurfaceMode(view)
  return started && (mode === 'started' || mode === 'already_started')
}

/** Lock: after started / already_started stay on HR handoff host — never redirect to employee card. */
export function shouldRedirectToEmployeeCardFromHandoffHost(
  opts: {
    workforceEmployeeId?: string | null
    formalize?: FormalizeView | null
    started?: StartedView | null
    showStartedSurface?: boolean
  } | null | undefined,
): false {
  void opts
  return false
}

export function assertStartedNoAutoTransition(view: StartedView | null | undefined): boolean {
  if (!view) return true
  if (view.formalization_complete_implies_started === true) return false
  if (view.employee_created_implies_started === true) return false
  if (view.hr_employee_card === true) return false
  // Evaluate without confirm must not claim started.
  if (normalizeStartedCode(view.decision) === 'not_started' && view.started === true) return false
  return true
}

export function assertReplayEmitsNoSecondStartEvent(
  view: StartedView | null | undefined,
): boolean {
  if (normalizeStartedCode(view?.decision) !== 'already_started') return true
  if (view?.start_event_emitted === true) return false
  if (view?.idempotent_replay !== true) return false
  return true
}

/** Zero-choice: Started must never offer pathway/person/vacancy/employer/rates menus. */
export function shouldShowStartedRuntimeChoice(
  choice: (typeof FORBIDDEN_STARTED_RUNTIME_CHOICES)[number],
): false {
  void choice
  return false
}
