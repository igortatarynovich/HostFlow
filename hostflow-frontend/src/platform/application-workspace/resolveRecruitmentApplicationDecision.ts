import type { Application } from '../../api/types/application'
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
