import { memo, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  IconAlertTriangle,
  IconBookmark,
  IconBookmarkFilled,
  IconClipboardList,
  IconHistory,
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
  onEditToggle?: () => void
  editMode?: boolean
  onOpenHandoff?: () => void
  handoffDisabled?: boolean
  handoffLabel?: string
  onDeleteRequest: () => void
  onCancel: () => void
  backPath?: string
  backLabel?: string
  onFavoriteToggle?: () => void
  candidateProfile?: import('../../api/candidate_profiles').CandidateProfile | null
  profileLoading?: boolean
  stageSinceAt?: string | null
  focusContent?: React.ReactNode
  /** Document pipeline waivers: show visible badges in header (plan: “override must be noticeable”). */
  pipelineWaiverPendingCount?: number
  pipelineWaiverApprovedCount?: number
  /** Opens candidate activity (timeline) in a modal. */
  onOpenActivity?: () => void
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
  onEditToggle,
  editMode = false,
  onOpenHandoff,
  handoffDisabled = false,
  handoffLabel,
  onDeleteRequest,
  onCancel,
  backPath = '/app/candidates',
  backLabel,
  onFavoriteToggle,
  candidateProfile,
  profileLoading,
  stageSinceAt = null,
  focusContent,
  pipelineWaiverPendingCount = 0,
  pipelineWaiverApprovedCount = 0,
  onOpenActivity,
}: CandidateHeaderProps) {
  const { t } = useI18n()

  const [nowTs, setNowTs] = useState<number>(0)
  useEffect(() => {
    setNowTs(Date.now())
  }, [stageSinceAt])

  const stageDays = useMemo(() => {
    if (!stageSinceAt || !nowTs) return null
    const ts = Date.parse(stageSinceAt)
    if (!ts || Number.isNaN(ts)) return null
    const days = Math.max(0, Math.floor((nowTs - ts) / (24 * 60 * 60 * 1000)))
    return days
  }, [nowTs, stageSinceAt])

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
      <div className="rounded-2xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="text-[11px] text-white/80">
              <Link className="hover:underline text-white" to={backPath}>
                {backLabel || t('app.candidate_card.header.back')}
              </Link>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold leading-tight">{candidateTitle}</h1>
              {candidate && <StageTag code={candidate.stage || 'new'} />}
              {!isMasked && pipelineWaiverPendingCount > 0 ? (
                <span
                  className="text-[11px] inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-400/90 px-2 py-0.5 font-semibold text-amber-950 shadow-sm"
                  title={t('app.candidate_card.pipeline_override.badge_pending_hint', {
                    defaultValue: 'Document waiver waiting for manager approval',
                  })}
                >
                  <IconAlertTriangle size={12} />
                  {t('app.candidate_card.pipeline_override.badge_pending', {
                    defaultValue: 'Waiver pending ({count})',
                    values: { count: String(pipelineWaiverPendingCount) },
                  })}
                </span>
              ) : null}
              {!isMasked && pipelineWaiverApprovedCount > 0 ? (
                <span
                  className="text-[11px] inline-flex items-center rounded-md border border-emerald-200 bg-emerald-500/90 px-2 py-0.5 font-semibold text-emerald-950 shadow-sm"
                  title={t('app.candidate_card.pipeline_override.badge_active_hint', {
                    defaultValue: 'Approved document waiver(s) relax pipeline / handoff gates for listed types',
                  })}
                >
                  {t('app.candidate_card.pipeline_override.badge_active', {
                    defaultValue: 'Waiver active ({count})',
                    values: { count: String(pipelineWaiverApprovedCount) },
                  })}
                </span>
              ) : null}
              {candidate && stageDays !== null && (
                <span
                  className="text-[11px] rounded-md border border-white/30 px-2 py-0.5 text-white/90"
                  title={stageSinceAt || undefined}
                >
                  {t('app.candidate_card.labels.stage_days', { defaultValue: '{days}d in stage', values: { days: String(stageDays) } })}
                </span>
              )}
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
            {!isNew && (
              <>
                <button
                  type="button"
                  className="rounded-lg border border-white bg-white px-3 py-1.5 font-semibold text-brand-700 shadow-sm transition hover:bg-white/90 disabled:opacity-60"
                  onClick={onOpenHandoff}
                  disabled={handoffDisabled}
                >
                  {handoffLabel || t('app.candidate_card.handoff.transfer_btn', { defaultValue: 'Transfer to client' })}
                </button>
                {onOpenActivity ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 font-medium text-white transition hover:bg-white/20"
                    onClick={onOpenActivity}
                    title={t('app.candidate_card.activity_feed.title', { defaultValue: 'Activity' })}
                  >
                    <IconHistory size={18} className="shrink-0 opacity-90" aria-hidden />
                    {t('app.candidate_card.activity_feed.title', { defaultValue: 'Activity' })}
                  </button>
                ) : null}
                <button
                  type="button"
                  className={clsx(
                    "rounded-lg border border-white/30 bg-white/10 px-3 py-1.5 font-medium text-white transition hover:bg-white/20",
                    editMode && "bg-amber-50 text-amber-900 border-amber-200 hover:bg-amber-100",
                  )}
                  onClick={onEditToggle}
                  disabled={!canEdit}
                >
                  {editMode
                    ? t('app.candidate_card.actions.cancel_edit', { defaultValue: 'Cancel edit' })
                    : t('app.candidate_card.actions.edit', { defaultValue: 'Edit' })}
                </button>
                <span className="mx-1 hidden h-6 w-px bg-white/30 md:inline-block" />
                {canDeleteDirect ? (
                  <button
                    className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-1.5 font-semibold text-rose-700 transition hover:bg-rose-100"
                    onClick={onDelete}
                  >
                    {t('common.actions.delete')}
                  </button>
                ) : null}
              </>
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
        {focusContent ? <div className="mt-3">{focusContent}</div> : null}
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
