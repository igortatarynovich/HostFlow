import type { Application } from '../../api/types/application'
import type { ObjectDecision } from '../decision-model/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

function candidateDetailPath(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

export function applicationReadyForEmploymentPrep(application: Application): Record<string, unknown> | null {
  return asRecord(application.extensions?.ready_for_employment_prep_v1)
}

export type ApplicationEmploymentSpinePhase = 'recruitment' | 'employment'

export function applicationEmploymentSpinePhase(
  application: Application | null | undefined,
): ApplicationEmploymentSpinePhase {
  const prep = application ? applicationReadyForEmploymentPrep(application) : null
  const nextAction = String(prep?.next_action || '').trim()
  // Transfer result only. Do not read Employment Started out of Recruitment prep.
  if (Boolean(prep?.handoff_id) || nextAction === 'handed_off') return 'employment'
  return 'recruitment'
}

type ResolveRecruitmentDecisionArgs = {
  application: Application
  patching: boolean
  busy: boolean
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onCreateCandidate: () => void
  onFollowUp: () => void
  onReject: () => void
  onPool: () => void
  onTransferToEmployment?: () => void
  onRunFits?: () => void
  t: (key: string, options?: Record<string, unknown>) => string
}

export function resolveRecruitmentApplicationDecision(args: ResolveRecruitmentDecisionArgs): ObjectDecision {
  const {
    application,
    patching,
    busy,
    onCreateCandidate,
    onFollowUp,
    onReject,
    onPool,
    onRunFits,
    t,
  } = args
  const statusKey = application.status
  const terminal = statusKey === 'completed' || statusKey === 'rejected'
  const contactPhone = application.contact.phone
  const disabled = patching || busy
  const candidateId =
    application.outcome_entity_type === 'candidate' ? String(application.outcome_entity_id || '').trim() : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const callHref = contactPhone ? `tel:${contactPhone.replace(/\s/g, '')}` : null
  const prep = applicationReadyForEmploymentPrep(application)
  const nextAction = String(prep?.next_action || '').trim()
  const intakeNextAction = String(application.next_action || '').trim()

  // «Подходит» creates a candidate at stage new.
  if (candidateHref) {
    return {
      stateId: 'recruitment.candidate_created',
      currentState: t('app.recruitment_inquiry.outcome_title'),
      why: t('app.recruitment_inquiry.outcome_body'),
      primaryAction: {
        id: 'open_candidate',
        label: t('app.candidates.detail.open_full_profile'),
        href: candidateHref,
      },
      requiredContext: ['outcome'],
      variant: 'success',
    }
  }

  if (nextAction === 'ask_vacancy') {
    return {
      stateId: 'recruitment.ask_vacancy',
      currentState: t('app.recruitment_inquiry.rso.ask_vacancy_title', {
        defaultValue: 'Нужна вакансия',
      }),
      why: String(prep?.vacancy_prompt || '').trim()
        || t('app.recruitment_inquiry.rso.ask_vacancy_body', {
          defaultValue: 'Для какой вакансии подходит этот человек?',
        }),
      primaryAction: null,
      requiredContext: ['vacancy'],
      variant: 'blocker',
    }
  }

  if (nextAction === 'confirm_probable_duplicate') {
    const probable = asRecord(prep?.probable_duplicate)
    return {
      stateId: 'recruitment.confirm_probable_duplicate',
      currentState: t('app.recruitment_inquiry.rso.duplicate_title', {
        defaultValue: 'Возможный дубликат',
      }),
      why: String(probable?.prompt || '').trim()
        || t('app.recruitment_inquiry.rso.duplicate_body', {
          defaultValue: 'Это тот же человек?',
        }),
      primaryAction: candidateHref
        ? {
            id: 'open_candidate',
            label: t('app.candidates.detail.open_full_profile'),
            href: candidateHref,
          }
        : null,
      requiredContext: ['duplicate'],
      variant: 'blocker',
    }
  }

  // Intake Readiness: «Подходит» creates the candidate at stage new.
  const call = asRecord(application.extensions?.call_result_v1)
  const interested = String(call?.result || '').trim() === 'interested'
  const vacancyKnown = Boolean(String(application.extensions?.vacancy_id || '').trim())
  const convertToCandidate = onCreateCandidate
    ? {
        id: 'run_fits',
        label: t('app.recruitment_inquiry.rso.run_fits', { defaultValue: 'Подходит' }),
        onClick: onCreateCandidate,
        disabled,
      }
    : onRunFits
      ? {
          id: 'run_fits',
          label: t('app.recruitment_inquiry.rso.run_fits', { defaultValue: 'Подходит' }),
          onClick: onRunFits,
          disabled,
        }
      : null
  if ((intakeNextAction === 'fits' || interested) && convertToCandidate) {
    return {
      stateId: 'recruitment.fits_to_candidate',
      currentState: t('app.recruitment_inquiry.rso.fits_to_candidate_title', {
        defaultValue: 'Подходит',
      }),
      why: t('app.recruitment_inquiry.rso.fits_to_candidate_body', {
        defaultValue: 'Отклик переходит в кандидата со статусом «Новый».',
      }),
      primaryAction: convertToCandidate,
      secondaryActions: [
        { id: 'follow_up', label: t('app.recruitment_inquiry.follow_up'), onClick: onFollowUp, disabled },
        {
          id: 'reject',
          label: t('app.recruitment_inquiry.reject'),
          onClick: onReject,
          variant: 'danger',
          disabled,
        },
      ],
      requiredContext: vacancyKnown ? [] : ['vacancy'],
      variant: 'default',
    }
  }

  if (terminal) {
    return {
      stateId: 'recruitment.terminal',
      currentState: t('app.recruitment_inquiry.closed_title'),
      why:
        statusKey === 'rejected'
          ? t('app.recruitment_inquiry.rejected_body')
          : t('app.recruitment_inquiry.completed_body'),
      primaryAction: null,
      requiredContext: [],
      terminal: true,
      outcome: {
        title: t('app.recruitment_inquiry.closed_title'),
        body:
          statusKey === 'rejected'
            ? t('app.recruitment_inquiry.rejected_outcome_body')
            : t('app.recruitment_inquiry.completed_body'),
        variant: 'terminal',
      },
    }
  }

  return {
    stateId: 'recruitment.triage',
    currentState: t('app.recruitment_inquiry.process_title'),
    why: t('app.recruitment_inquiry.process_body'),
    primaryAction: callHref
      ? {
          id: 'call',
          label: t('app.recruitment_inquiry.call'),
          href: callHref,
          disabled,
        }
      : null,
    secondaryActions: [
      ...(convertToCandidate ? [convertToCandidate] : []),
      { id: 'follow_up', label: t('app.recruitment_inquiry.follow_up'), onClick: onFollowUp, disabled },
      { id: 'pool', label: t('app.recruitment_inquiry.pool'), onClick: onPool, disabled },
      {
        id: 'reject',
        label: t('app.recruitment_inquiry.reject'),
        onClick: onReject,
        variant: 'danger',
        disabled,
      },
    ],
    requiredContext: vacancyKnown ? [] : ['vacancy'],
    variant: callHref ? 'default' : 'blocker',
  }
}
