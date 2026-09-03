import { memo } from 'react'
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
import type { CandidateNextActionDTO } from '../../api/candidates'
import StageTag from '../StageTag'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { CandidateProfile } from '../../api/candidate_profiles'
import NextActionBadge from './NextActionBadge'

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
  /** When set, replaces the handoff button with a read-only status line (active handoff). */
  handoffReadonlyText?: string | null
  handoffDisabled?: boolean
  handoffDisabledTitle?: string | null
  handoffLabel?: string
  onDeleteRequest: () => void
  onCancel: () => void
  backPath?: string
  backLabel?: string
  /** When true, hides the legacy back link (use PageHeader breadcrumb instead). */
  hideBackLink?: boolean
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
  /** G-8 stage 1b: backend-computed primary "next action" DTO for the
   *  candidate. Rendered as a single header pill via `NextActionBadge`.
   *  Skipped on `isNew` (no candidate id to query). */
  nextAction?: CandidateNextActionDTO | null
  nextActionLoading?: boolean
  nextActionError?: unknown
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
  onSave,
  onDelete,
  onEditToggle,
  editMode = false,
  onOpenHandoff,
  handoffReadonlyText = null,
  handoffDisabled = false,
  handoffDisabledTitle = null,
  handoffLabel,
  onDeleteRequest,
  onCancel,
  backPath = CRM_APP_PATHS.candidates,
  backLabel,
  hideBackLink = false,
  onFavoriteToggle,
  candidateProfile,
  profileLoading,
  focusContent,
  pipelineWaiverPendingCount = 0,
  pipelineWaiverApprovedCount = 0,
  onOpenActivity,
  nextAction = null,
  nextActionLoading = false,
  nextActionError = null,
  ..._unusedHeaderProps
}: CandidateHeaderProps) {
  const { t } = useI18n()
  void _unusedHeaderProps

  return (
    <>
      {/* Header */}
      <div className="min-w-0 rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            {!hideBackLink && backPath ? (
              <div className="text-[11px] text-white/80">
                <Link className="hover:underline text-white" to={backPath}>
                  {backLabel || t('app.candidate_card.header.back')}
                </Link>
              </div>
            ) : null}
            <div className="flex flex-wrap items-center gap-2">
              {candidate && <StageTag code={candidate.stage || 'new'} />}
              {!isNew && candidate?.id ? (
                <NextActionBadge
                  dto={nextAction}
                  loading={nextActionLoading}
                  error={nextActionError}
                  inverse
                />
              ) : null}
              {!isMasked && candidate?.intake_application_kind === 'client' && (
                <span
                  className="text-[11px] inline-flex items-center rounded-lg border border-blue-200/80 bg-blue-500/20 px-2 py-0.5 font-semibold text-white"
                  title={t('app.candidate_card.labels.client_intake_badge_hint')}
                >
                  {t('app.candidate_card.labels.client_intake_badge')}
                </span>
              )}
              {!isMasked && pipelineWaiverPendingCount > 0 ? (
                <span
                  className="text-[11px] inline-flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-400/90 px-2 py-0.5 font-semibold text-amber-950 shadow-sm"
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
                  className="text-[11px] inline-flex items-center rounded-lg border border-emerald-200 bg-emerald-500/90 px-2 py-0.5 font-semibold text-emerald-950 shadow-sm"
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
              {profileLoading && (
                <span className="text-[11px] rounded-lg border border-white/30 px-2 py-0.5 text-white/70">
                  {t('common.loading')}
                </span>
              )}
              {!profileLoading && candidateProfile && (
                <Link
                  to={CRM_APP_PATHS.settingsCandidateProfiles}
                  className="text-[11px] inline-flex items-center gap-1 rounded-lg border border-white/30 bg-white/20 px-2 py-0.5 transition-colors hover:bg-white/30"
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
                <span className="text-[11px] rounded-lg border border-white/30 px-2 py-0.5 text-white/70" title={t('app.candidate_card.labels.no_profile')}>
                  <span className="inline-flex items-center gap-1">
                    <IconAlertTriangle size={12} />
                    {t('app.candidate_card.labels.no_profile_short')}
                  </span>
                </span>
              )}
              {!isNew && onFavoriteToggle && (
                <button
                  type="button"
                  className="text-[11px] inline-flex items-center gap-1 rounded-lg border border-white/30 px-2 py-1 transition-colors hover:bg-white/10"
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
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {isNew && (
              <>
                <button
                  className="rounded-lg border border-white/30 bg-white/10 px-3 py-2 font-medium text-white transition hover:bg-white/20"
                  onClick={onCancel}
                >
                  {t('common.actions.cancel')}
                </button>
                <button
                  className="rounded-lg border border-white bg-white px-3 py-2 font-semibold text-brand-700 shadow-sm transition hover:bg-white/90 disabled:opacity-60"
                  disabled={saving || !canEdit}
                  onClick={onSave}
                >
                  {saving ? t('common.saving') : t('common.actions.create')}
                </button>
              </>
            )}
            {!isNew && (
              <>
                {handoffReadonlyText ? (
                  <div
                    className="max-w-md rounded-lg border border-white/40 bg-white/15 px-3 py-2 text-left text-xs font-medium leading-tight text-white"
                    role="status"
                  >
                    {handoffReadonlyText}
                  </div>
                ) : onOpenHandoff ? (
                  <button
                    type="button"
                    className="rounded-lg border border-white bg-white px-3 py-2 font-semibold text-brand-700 shadow-sm transition hover:bg-white/90 disabled:opacity-60"
                    onClick={onOpenHandoff}
                    disabled={handoffDisabled}
                    title={handoffDisabled && handoffDisabledTitle ? handoffDisabledTitle : undefined}
                  >
                    {handoffLabel || t('app.candidate_card.handoff.transfer_btn', { defaultValue: 'Transfer to client' })}
                  </button>
                ) : null}
                {onOpenActivity ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3 py-2 font-medium text-white transition hover:bg-white/20"
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
                    "rounded-lg border border-white/30 bg-white/10 px-3 py-2 font-medium text-white transition hover:bg-white/20",
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
                    className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 font-semibold text-rose-700 transition hover:bg-rose-100"
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
                className="rounded-lg border border-white/30 bg-white/10 px-3 py-2 font-medium text-white transition hover:bg-white/20"
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
        {focusContent ? <div className="mt-3 min-w-0">{focusContent}</div> : null}
      </div>

      {/* Status Messages */}
      {deleteRequestMessage && (
        <div className="p-3 rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
          {deleteRequestMessage}
        </div>
      )}
      {deleteRequestError && (
        <ErrorRecoveryBanner
          info={{
            title: deleteRequestError,
            hint: t('app.common.retry_hint'),
          }}
          onRetry={onDeleteRequest}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
          compact
        />
      )}
      {savedOk && (
        <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
          {t('app.candidate_card.messages.saved')}
        </div>
      )}
    </>
  )
}

export default memo(CandidateHeader)
