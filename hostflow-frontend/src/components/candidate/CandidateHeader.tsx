import { memo } from 'react'
import { Link } from 'react-router-dom'
import {
  IconAlertTriangle,
  IconBookmark,
  IconBookmarkFilled,
  IconClipboardList,
} from '@tabler/icons-react'
import type { Candidate } from '../../api/types'
import StageTag from '../StageTag'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import type { CandidateProfile } from '../../api/candidate_profiles'

interface CandidateHeaderProps {
  candidate: Candidate | null
  isNew: boolean
  isMasked?: boolean
  canEdit?: boolean
  saving: boolean
  canDeleteDirect: boolean
  canRequestDelete: boolean
  deleteRequestLoading: boolean
  deleteRequestMessage: string | null
  deleteRequestError: string | null
  savedOk: boolean
  headerExpanded: boolean
  onHeaderExpandedChange: (expanded: boolean) => void
  onSave: () => void
  onDelete: () => void
  onDeleteRequest: () => void
  onCancel: () => void
  backPath?: string
  backLabel?: string
  onFavoriteToggle?: () => void
  candidateProfile?: import('../../api/candidate_profiles').CandidateProfile | null
  profileLoading?: boolean
}

function CandidateHeader({
  candidate,
  isNew,
  isMasked = false,
  canEdit = true,
  saving,
  canDeleteDirect,
  canRequestDelete,
  deleteRequestLoading,
  deleteRequestMessage,
  deleteRequestError,
  savedOk,
  headerExpanded,
  onHeaderExpandedChange,
  onSave,
  onDelete,
  onDeleteRequest,
  onCancel,
  backPath = '/app/candidates',
  backLabel,
  onFavoriteToggle,
  candidateProfile,
  profileLoading,
}: CandidateHeaderProps) {
  const { t } = useI18n()

  const candidateTitle = candidate
    ? isMasked
      ? (candidate.short_id
          ? t('app.candidate_card.header.masked_label_short_id', {
              defaultValue: 'Candidate {short_id}',
              values: { short_id: candidate.short_id },
            })
          : t('app.candidate_card.header.masked_label', {
              defaultValue: 'Candidate #{id}',
              values: { id: candidate.id?.slice(0, 8) ?? '' },
            }))
      : [candidate.first_name, candidate.last_name]
          .map((part) => (typeof part === 'string' ? part.trim() : ''))
          .filter((part) => part.length > 0)
          .join(' ') || t('app.candidate_card.header.new_label')
    : t('app.candidate_card.header.new_label')

  const phoneDisplay = !isMasked && candidate?.phone
    ? `${(candidate as any).phone_country_code || ''}${candidate.phone}`.trim()
    : null
  const telHref = phoneDisplay ? `tel:${phoneDisplay.replace(/\s/g, '')}` : null

  return (
    <>
      {/* Header */}
      <div className="rounded-2xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-4 text-white shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="text-[11px] text-white/80">
              <Link className="hover:underline text-white" to={backPath}>
                {backLabel || t('app.candidate_card.header.back')}
              </Link>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold leading-tight">{candidateTitle}</h1>
              {candidate && <StageTag code={candidate.stage || 'new'} />}
              {candidate?.short_id && (
                <span className="text-[11px] rounded-md border border-white/30 px-2 py-0.5">
                  {t('app.candidate_card.labels.short_id_badge', { values: { id: candidate.short_id } })}
                </span>
              )}
              {profileLoading && (
                <span className="text-[11px] rounded-md border border-white/30 px-2 py-0.5 text-white/70">
                  {t('common.loading')}
                </span>
              )}
              {!profileLoading && candidateProfile && (
                <Link
                  to={`/app/settings/candidate-profiles`}
                  className="text-[11px] inline-flex items-center gap-1 rounded-md border border-white/30 bg-white/20 px-2 py-0.5 transition-colors hover:bg-white/30"
                  title={candidateProfile.description || candidateProfile.name}
                  onClick={(e) => {
                    // Можно добавить логику для скролла к нужному профилю
                    e.stopPropagation()
                  }}
                >
                  <IconClipboardList size={13} />
                  <span>{candidateProfile.name}</span>
                </Link>
              )}
              {!profileLoading && !candidateProfile && candidate?.vacancy_id && (
                <span className="text-[11px] rounded-md border border-white/30 px-2 py-0.5 text-white/70" title={t('app.candidate_card.labels.no_profile')}>
                  <span className="inline-flex items-center gap-1">
                    <IconAlertTriangle size={12} />
                    {t('app.candidate_card.labels.no_profile_short')}
                  </span>
                </span>
              )}
              {!isNew && onFavoriteToggle && (
                <button
                  type="button"
                  className="text-[11px] inline-flex items-center gap-1 rounded-md border border-white/30 px-2 py-1 transition-colors hover:bg-white/10"
                  onClick={(e) => {
                    e.stopPropagation()
                    onFavoriteToggle()
                  }}
                  title={candidate?.is_favorite ? t('app.candidate_card.actions.remove_favorite') : t('app.candidate_card.actions.add_favorite')}
                >
                  {candidate?.is_favorite ? <IconBookmarkFilled size={13} /> : <IconBookmark size={13} />}
                  <span className="sr-only">{candidate?.is_favorite ? t('app.candidate_card.actions.remove_favorite') : t('app.candidate_card.actions.add_favorite')}</span>
                </button>
              )}
              <button
                type="button"
                className="text-[11px] rounded-md border border-white/30 px-3 py-1 hover:bg-white/10"
                onClick={() => onHeaderExpandedChange(!headerExpanded)}
              >
                {headerExpanded ? t('common.actions.collapse') : t('common.actions.expand')}
              </button>
            </div>
            {headerExpanded && candidate && !isMasked && (
              <div className="flex flex-wrap items-center gap-3 text-sm text-white/90">
                {candidate.email && (
                  <a className="hover:underline text-white" href={`mailto:${candidate.email}`}>
                    {candidate.email}
                  </a>
                )}
                {phoneDisplay && telHref && (
                  <a className="hover:underline text-white" href={telHref}>
                    {phoneDisplay}
                  </a>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {isNew && (
              <>
                <button
                  className="rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 font-medium text-white transition hover:bg-white/20"
                  onClick={onCancel}
                >
                  {t('common.actions.cancel')}
                </button>
                <button
                  className="rounded-lg border border-white bg-white px-3 py-1.5 font-semibold text-brand-700 shadow-sm transition hover:bg-white/90 disabled:opacity-60"
                  disabled={saving || !canEdit}
                  onClick={onSave}
                >
                  {saving ? t('common.saving') : t('common.actions.create')}
                </button>
              </>
            )}
            {!isNew && canDeleteDirect && (
              <button
                className="rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 font-medium text-rose-50 transition hover:bg-white/20"
                onClick={onDelete}
              >
                {t('common.actions.delete')}
              </button>
            )}
            {!isNew && !canDeleteDirect && canRequestDelete && (
              <button
                type="button"
                className="rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 font-medium text-white transition hover:bg-white/20"
                disabled={deleteRequestLoading}
                onClick={onDeleteRequest}
              >
                {deleteRequestLoading
                  ? t('app.candidate_card.actions.delete_request_loading')
                  : t('app.candidate_card.actions.delete_request')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Status Messages */}
      {deleteRequestMessage && (
        <div className="p-3 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
          {deleteRequestMessage}
        </div>
      )}
      {deleteRequestError && (
        <ErrorRecoveryBanner
          info={{
            title: deleteRequestError,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={onDeleteRequest}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
          compact
        />
      )}
      {savedOk && (
        <div className="p-3 rounded-lg bg-green-50 text-green-800 border border-green-200">
          {t('app.candidate_card.messages.saved')}
        </div>
      )}
    </>
  )
}

export default memo(CandidateHeader)
