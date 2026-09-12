import type { Application, RequirementsVerdict } from '../../api/types/application'
import type { ObjectDecision } from '../decision-model/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

function candidateDetailPath(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
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
  t: (key: string, options?: Record<string, unknown>) => string
}

function verdictOf(application: Application): RequirementsVerdict | null {
  const raw = application.requirements_verdict
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export function resolveRecruitmentApplicationDecision(args: ResolveRecruitmentDecisionArgs): ObjectDecision {
  const { application, patching, busy, onCreateCandidate, onFollowUp, onReject, onPool, t } = args
  const statusKey = application.status
  const terminal = statusKey === 'completed' || statusKey === 'rejected'
  const contactPhone = application.contact.phone
  const disabled = patching || busy
  const candidateId =
    application.outcome_entity_type === 'candidate' ? String(application.outcome_entity_id || '').trim() : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const callHref = contactPhone ? `tel:${contactPhone.replace(/\s/g, '')}` : null
  const verdict = verdictOf(application)

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

  // Vacancy Requirements verdict drives exactly one primary next action.
  if (verdict?.status === 'fit' && verdict.next_action?.code === 'fits') {
    return {
      stateId: 'recruitment.requirements.fit',
      currentState: t('app.recruitment.requirements.status.fit', { defaultValue: 'Подходит' }),
      why:
        verdict.next_action.message ||
        t('app.recruitment.requirements.why.fit', {
          defaultValue: 'Все требования вакансии выполнены по каноническим фактам.',
        }),
      primaryAction: {
        id: 'fits',
        label: t('app.recruitment.requirements.action.fits', { defaultValue: 'Подходит' }),
        onClick: onCreateCandidate,
        disabled,
      },
      secondaryActions: [
        { id: 'follow_up', label: t('app.recruitment_inquiry.follow_up'), onClick: onFollowUp, disabled },
        { id: 'pool', label: t('app.recruitment_inquiry.pool'), onClick: onPool, disabled },
      ],
      requiredContext: ['vacancy'],
      variant: 'success',
    }
  }

  if (verdict?.status === 'missing') {
    const fact = verdict.next_action?.fact_code || 'required_fact'
    return {
      stateId: 'recruitment.requirements.missing',
      currentState: t('app.recruitment.requirements.status.missing', {
        defaultValue: 'Не хватает данных',
      }),
      why:
        verdict.next_action?.message ||
        t('app.recruitment.requirements.why.missing', {
          defaultValue: 'Соберите недостающий факт: {{fact}}',
          fact,
        }),
      primaryAction: {
        id: 'collect_fact',
        label: t('app.recruitment.requirements.action.collect', {
          defaultValue: 'Получить: {{fact}}',
          fact: verdict.next_action?.requirement || fact,
        }),
        onClick: onFollowUp,
        disabled,
      },
      secondaryActions: [
        { id: 'pool', label: t('app.recruitment_inquiry.pool'), onClick: onPool, disabled },
        {
          id: 'reject',
          label: t('app.recruitment_inquiry.reject'),
          onClick: onReject,
          variant: 'danger',
          disabled,
        },
      ],
      requiredContext: ['vacancy'],
      variant: 'blocker',
    }
  }

  if (verdict?.status === 'not_fit') {
    return {
      stateId: 'recruitment.requirements.not_fit',
      currentState: t('app.recruitment.requirements.status.not_fit', {
        defaultValue: 'Не подходит',
      }),
      why:
        verdict.next_action?.message ||
        t('app.recruitment.requirements.why.not_fit', {
          defaultValue: 'Кандидат не соответствует требованиям вакансии.',
        }),
      primaryAction: {
        id: 'reject',
        label: t('app.recruitment.requirements.action.reject', { defaultValue: 'Не подходит' }),
        onClick: onReject,
        variant: 'danger',
        disabled,
      },
      secondaryActions: [
        { id: 'pool', label: t('app.recruitment_inquiry.pool'), onClick: onPool, disabled },
      ],
      requiredContext: ['vacancy'],
      variant: 'blocker',
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
      {
        id: 'create_candidate',
        label: t('app.recruitment_inquiry.create_candidate'),
        onClick: onCreateCandidate,
        disabled,
      },
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
    requiredContext: ['vacancy', 'assignee'],
    variant: callHref ? 'default' : 'blocker',
  }
}
