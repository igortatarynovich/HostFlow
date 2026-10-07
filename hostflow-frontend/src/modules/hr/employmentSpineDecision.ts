import type { ObjectDecision } from '../../platform/decision-model/types'

export const FORMALIZE_CONTRACT_ACTION = 'confirm_employment_contract_basis'

export type EmploymentFormalizeSnapshot = {
  decision?: string | null
  ready_to_formalize?: boolean | null
  ready_to_create_employee?: boolean | null
  primary_item?: { code?: string; message?: string } | null
  blockers?: Array<{ code?: string; message?: string }>
  next_action?: string | null
}

export type EmploymentStartedSnapshot = {
  decision?: string | null
  started?: boolean | null
  ready_to_create_employee?: boolean | null
  start_date?: string | null
  employment_context?: Record<string, unknown> | null
  primary_item?: { code?: string; message?: string } | null
  active_missing?: Array<{ code?: string; message?: string }>
}

type ResolveEmploymentSpineArgs = {
  busy: boolean
  onFormalize: () => void
  onConfirmStart: () => void
  formalize?: EmploymentFormalizeSnapshot | null
  started?: EmploymentStartedSnapshot | null
  t: (key: string, options?: Record<string, unknown>) => string
}

function asMessage(row: { message?: string; code?: string } | null | undefined): string {
  return String(row?.message || row?.code || '').trim()
}

function startedContextLine(started: EmploymentStartedSnapshot | null | undefined): string {
  const date = String(started?.start_date || '').trim()
  const ctx = started?.employment_context
  const country = ctx && typeof ctx === 'object' ? String(ctx.employment_country || ctx.country || '').trim() : ''
  const role = ctx && typeof ctx === 'object' ? String(ctx.role || ctx.position_category || '').trim() : ''
  return [date, country, role].filter(Boolean).join(' · ')
}

export function resolveEmploymentSpineDecision(args: ResolveEmploymentSpineArgs): ObjectDecision {
  const { busy, onFormalize, onConfirmStart, formalize, started, t } = args
  const disabled = busy
  const startedDone = Boolean(started?.started) || started?.decision === 'already_started' || started?.decision === 'started'

  if (startedDone) {
    const contextLine = startedContextLine(started)
    const body = contextLine
      || t('app.recruitment_inquiry.eso.started_body', {
        defaultValue: 'Физический выход подтверждён. Employee created ≠ Started.',
      })
    return {
      stateId: 'employment.started',
      currentState: t('app.recruitment_inquiry.eso.started_title', { defaultValue: 'Вышел' }),
      why: t('app.recruitment_inquiry.eso.started_why', {
        defaultValue: 'Работа по этому отклику закрыта. Employee created ≠ Started.',
      }),
      primaryAction: null,
      requiredContext: [],
      terminal: true,
      variant: 'success',
      outcome: {
        title: t('app.recruitment_inquiry.eso.started_title', { defaultValue: 'Вышел' }),
        body,
        why: t('app.recruitment_inquiry.eso.started_why', {
          defaultValue: 'Работа по этому отклику закрыта. Employee created ≠ Started.',
        }),
        variant: 'success',
      },
    }
  }

  if (formalize?.ready_to_create_employee || started?.ready_to_create_employee) {
    return {
      stateId: 'employment.confirm_start',
      currentState: t('app.recruitment_inquiry.eso.confirm_start_title', {
        defaultValue: 'Подтвердить выход',
      }),
      why: t('app.recruitment_inquiry.eso.confirm_start_body', {
        defaultValue: 'Дата и контекст уже известны. Подтвердите физический первый день.',
      }),
      primaryAction: {
        id: 'confirm_physical_start',
        label: t('app.recruitment_inquiry.eso.confirm_start', { defaultValue: 'Подтвердить выход' }),
        onClick: onConfirmStart,
        disabled,
      },
      requiredContext: [],
      variant: 'default',
    }
  }

  if (formalize?.ready_to_formalize) {
    const item = asMessage(formalize.primary_item)
    return {
      stateId: 'employment.formalize',
      currentState: t('app.recruitment_inquiry.eso.formalize_title', { defaultValue: 'Оформить' }),
      why:
        item
        || t('app.recruitment_inquiry.eso.formalize_body', {
          defaultValue: 'Подтвердите основание договора для этого трудоустройства.',
        }),
      primaryAction: {
        id: 'formalize',
        label: t('app.recruitment_inquiry.eso.formalize', { defaultValue: 'Оформить' }),
        onClick: onFormalize,
        disabled,
      },
      requiredContext: [],
      variant: 'default',
    }
  }

  const blocker = asMessage(formalize?.blockers?.[0]) || asMessage(formalize?.primary_item)
  return {
    stateId: 'employment.blocked',
    currentState: t('app.recruitment_inquiry.eso.blocked_title', {
      defaultValue: 'Трудоустройство — текущий блокер',
    }),
    why:
      blocker
      || t('app.recruitment_inquiry.eso.blocked_body', {
        defaultValue: 'Employment продолжает того же человека. Нет ритуального Accept.',
      }),
    primaryAction: null,
    requiredContext: [],
    variant: 'blocker',
  }
}
