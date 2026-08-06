import type { Application } from '../../api/types/application'
import type { TranslateFn } from '../../i18n'
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
  t: TranslateFn
}

export function resolveRecruitmentApplicationDecision(args: ResolveRecruitmentDecisionArgs): ObjectDecision {
  const { application, patching, busy, onStage, onCreateCandidate, onFollowUp, onReject, t } = args
  const statusKey = application.status
  const terminal = statusKey === 'completed' || statusKey === 'rejected'
  const contactPhone = application.contact.phone
  const disabled = patching || busy
  const candidateId =
    application.outcome_entity_type === 'candidate' ? String(application.outcome_entity_id || '').trim() : ''
  const candidateHref = candidateId ? candidateDetailPath(candidateId) : undefined
  const followUpLabel = t('app.recruitment_inquiry.follow_up', { defaultValue: 'Follow-up' })
  const rejectLabel = t('app.recruitment_inquiry.reject', { defaultValue: 'Reject' })

  const contactActions =
    !terminal && (contactPhone || application.contact.email)
      ? [
          ...(contactPhone
            ? [
                {
                  id: 'call',
                  label: t('app.recruitment_inquiry.call', { defaultValue: 'Call' }),
                  href: `tel:${contactPhone.replace(/\s/g, '')}`,
                  variant: 'primary' as const,
                  icon: 'phone' as const,
                },
              ]
            : []),
        ]
      : undefined

  if (candidateHref) {
    return {
      stateId: 'recruitment.candidate_created',
      currentState: t('app.recruitment_inquiry.outcome_title', { defaultValue: 'Candidate created' }),
      why: t('app.recruitment_inquiry.outcome_body', {
        defaultValue: 'Application processed. Continue in the candidate profile.',
      }),
      primaryAction: {
        id: 'open_candidate',
        label: t('app.candidates.detail.open_full_profile', {
          defaultValue: t('app.recruitment_inquiry.open_full_profile', { defaultValue: 'Open full profile' }),
        }),
        href: candidateHref,
      },
      requiredContext: ['outcome'],
      variant: 'success',
    }
  }

  if (terminal) {
    return {
      stateId: 'recruitment.terminal',
      currentState: t('app.recruitment_inquiry.closed_title', { defaultValue: 'Application closed' }),
      why:
        statusKey === 'rejected'
          ? t('app.recruitment_inquiry.rejected_body', { defaultValue: 'Application rejected.' })
          : t('app.recruitment_inquiry.completed_body', { defaultValue: 'Processing completed.' }),
      primaryAction: null,
      requiredContext: [],
      terminal: true,
      outcome: {
        title: t('app.recruitment_inquiry.closed_title', { defaultValue: 'Application closed' }),
        body:
          statusKey === 'rejected'
            ? t('app.recruitment_inquiry.rejected_body_terminal', {
                defaultValue: 'Application rejected. No further actions.',
              })
            : t('app.recruitment_inquiry.completed_body', { defaultValue: 'Processing completed.' }),
        variant: 'terminal',
      },
    }
  }

  if (statusKey === 'new' && contactPhone) {
    return {
      stateId: 'recruitment.first_contact',
      currentState: t('app.recruitment_inquiry.contact_title', { defaultValue: 'Contact the candidate' }),
      why: t('app.recruitment_inquiry.contact_why', {
        defaultValue: 'First contact has not been made yet.',
      }),
      primaryAction: {
        id: 'contacted',
        label: t('app.recruitment_inquiry.called', { defaultValue: 'Called' }),
        onClick: () => void onStage('contacted'),
        disabled,
      },
      secondaryActions: [
        { id: 'follow_up', label: followUpLabel, onClick: onFollowUp, disabled },
        {
          id: 'reject',
          label: rejectLabel,
          onClick: onReject,
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['vacancy', 'assignee'],
      afterActionHint: t('app.recruitment_inquiry.after_call_hint', {
        defaultValue: 'After the call, link a vacancy and create a candidate.',
      }),
    }
  }

  return {
    stateId: 'recruitment.process',
    currentState: t('app.recruitment_inquiry.process_title', { defaultValue: 'Process application' }),
    why: t('app.recruitment_inquiry.process_body', {
      defaultValue: 'Link a vacancy and create a candidate — or reject the application.',
    }),
    primaryAction: {
      id: 'create_candidate',
      label: t('app.recruitment_inquiry.create_candidate', { defaultValue: 'Create candidate' }),
      onClick: onCreateCandidate,
      disabled,
    },
    secondaryActions: [
      { id: 'follow_up', label: followUpLabel, onClick: onFollowUp, disabled },
      {
        id: 'reject',
        label: rejectLabel,
        onClick: onReject,
        variant: 'danger',
        disabled,
      },
    ],
    contactActions,
    requiredContext: ['vacancy', 'assignee'],
  }
}
