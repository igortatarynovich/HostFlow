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
  t: (key: string, options?: Record<string, unknown>) => string
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

  const contactActions =
    !terminal && (contactPhone || application.contact.email)
      ? [
          ...(contactPhone
            ? [
                {
                  id: 'call',
                  label: 'Позвонить',
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
      currentState: t('app.recruitment_inquiry.outcome_title', { defaultValue: 'Кандидат создан' }),
      why: t('app.recruitment_inquiry.outcome_body', {
        defaultValue: 'Отклик обработан. Продолжите в карточке кандидата.',
      }),
      primaryAction: {
        id: 'open_candidate',
        label: t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' }),
        href: candidateHref,
      },
      requiredContext: ['outcome'],
      variant: 'success',
    }
  }

  if (terminal) {
    return {
      stateId: 'recruitment.terminal',
      currentState: t('app.recruitment_inquiry.closed_title', { defaultValue: 'Отклик закрыт' }),
      why:
        statusKey === 'rejected'
          ? t('app.recruitment_inquiry.rejected_body', { defaultValue: 'Отклик отклонён.' })
          : t('app.recruitment_inquiry.completed_body', { defaultValue: 'Обработка завершена.' }),
      primaryAction: null,
      requiredContext: [],
      terminal: true,
      outcome: {
        title: t('app.recruitment_inquiry.closed_title', { defaultValue: 'Отклик закрыт' }),
        body:
          statusKey === 'rejected'
            ? t('app.recruitment_inquiry.rejected_body', { defaultValue: 'Отклик отклонён. Новых действий нет.' })
            : t('app.recruitment_inquiry.completed_body', { defaultValue: 'Обработка завершена.' }),
        variant: 'terminal',
      },
    }
  }

  if (statusKey === 'new' && contactPhone) {
    return {
      stateId: 'recruitment.first_contact',
      currentState: t('app.recruitment_inquiry.contact_title', { defaultValue: 'Связаться с кандидатом' }),
      why: t('app.recruitment_inquiry.contact_why', { defaultValue: 'Первый контакт ещё не выполнен.' }),
      primaryAction: {
        id: 'contacted',
        label: t('app.recruitment_inquiry.called', { defaultValue: 'Позвонил' }),
        onClick: () => void onStage('contacted'),
        disabled,
      },
      secondaryActions: [
        { id: 'follow_up', label: 'Follow-up', onClick: onFollowUp, disabled },
        {
          id: 'reject',
          label: t('app.recruitment_inquiry.reject', { defaultValue: 'Отклонить' }),
          onClick: onReject,
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['vacancy', 'assignee'],
      afterActionHint: t('app.recruitment_inquiry.after_call_hint', {
        defaultValue: 'После звонка привяжите подбор и создайте кандидата.',
      }),
    }
  }

  return {
    stateId: 'recruitment.process',
    currentState: t('app.recruitment_inquiry.process_title', { defaultValue: 'Обработать отклик' }),
    why: t('app.recruitment_inquiry.process_body', {
      defaultValue: 'Привяжите подбор и создайте кандидата — или отклоните отклик.',
    }),
    primaryAction: {
      id: 'create_candidate',
      label: t('app.recruitment_inquiry.create_candidate', { defaultValue: 'Создать кандидата' }),
      onClick: onCreateCandidate,
      disabled,
    },
    secondaryActions: [
      { id: 'follow_up', label: 'Follow-up', onClick: onFollowUp, disabled },
      {
        id: 'reject',
        label: t('app.recruitment_inquiry.reject', { defaultValue: 'Отклонить' }),
        onClick: onReject,
        variant: 'danger',
        disabled,
      },
    ],
    contactActions,
    requiredContext: ['vacancy', 'assignee'],
  }
}
