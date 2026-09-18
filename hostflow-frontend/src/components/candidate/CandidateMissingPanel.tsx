import EmptyStatePanel from '../EmptyStatePanel'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { recruitmentApplicationPath } from '../../app/recruitmentInboxPaths'
import { useI18n } from '../../i18n'
import type { CandidateMissingState } from '../../utils/candidateMissing'

type CandidateMissingPanelProps = {
  missing: CandidateMissingState
  recreating?: boolean
  onRecreate?: () => void
  backTo?: string
}

export default function CandidateMissingPanel({
  missing,
  recreating = false,
  onRecreate,
  backTo = CRM_APP_PATHS.candidates,
}: CandidateMissingPanelProps) {
  const { t } = useI18n()
  const deleted = missing.code === 'candidate_deleted'
  const title = deleted
    ? t('app.candidate_card.missing.deleted_title', { defaultValue: 'Candidate was deleted' })
    : t('app.candidate_card.missing.not_found_title', { defaultValue: 'Candidate does not exist' })
  const description = deleted
    ? missing.canRecreate
      ? t('app.candidate_card.missing.deleted_with_application_hint', {
          defaultValue: 'This candidate was deleted. The original application is still available — you can create the candidate again.',
        })
      : t('app.candidate_card.missing.deleted_hint', {
          defaultValue: 'This candidate was deleted and is no longer available.',
        })
    : t('app.candidate_card.missing.not_found_hint', {
        defaultValue: 'This candidate does not exist or is not available in the current workspace.',
      })

  const primaryAction =
    deleted && missing.canRecreate && onRecreate
      ? {
          label: recreating
            ? t('app.candidate_card.missing.recreating', { defaultValue: 'Creating…' })
            : t('app.candidate_card.missing.recreate', { defaultValue: 'Create again' }),
          onClick: recreating ? undefined : onRecreate,
        }
      : missing.applicationId
        ? {
            label: t('app.candidate_card.missing.open_application', { defaultValue: 'Open application' }),
            to: recruitmentApplicationPath(missing.applicationId),
          }
        : {
            label: t('app.candidate_card.missing.back_to_list', { defaultValue: 'Back to candidates' }),
            to: backTo,
          }

  const secondaryAction =
    deleted && missing.canRecreate && missing.applicationId
      ? {
          label: t('app.candidate_card.missing.open_application', { defaultValue: 'Open application' }),
          to: recruitmentApplicationPath(missing.applicationId),
        }
      : deleted && missing.canRecreate
        ? {
            label: t('app.candidate_card.missing.back_to_list', { defaultValue: 'Back to candidates' }),
            to: backTo,
          }
        : missing.applicationId
          ? {
              label: t('app.candidate_card.missing.back_to_list', { defaultValue: 'Back to candidates' }),
              to: backTo,
            }
          : undefined

  return (
    <EmptyStatePanel
      title={title}
      description={description}
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    />
  )
}
