import { memo, type ReactNode } from 'react'
import clsx from 'clsx'
import { IconAlertTriangle, IconHistory } from '@tabler/icons-react'
import type { Candidate } from '../../api/types'
import type { CandidateNextActionDTO } from '../../api/candidates'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import NextActionBadge from './NextActionBadge'
import { EntityRecordHeader } from '../../platform/entity-workspace/EntityRecordHeader'
import { OverflowMenu, type OverflowMenuItem } from '../ui/OverflowMenu'

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
  onOpenHrTransfer?: () => void
  hrTransferLabel?: string
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
  onGenerateShortId?: () => void
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
  compact?: boolean
  displayName?: string | null
  candidateCode?: string | null
  statusChip?: ReactNode
  /** Operational context under the name: vacancy, stage, warnings. */
  summary?: ReactNode
  /** Stage track. Rendered as the last row of the same hero. */
  pipeline?: ReactNode
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
  onOpenHrTransfer,
  hrTransferLabel,
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
  onGenerateShortId,
  candidateProfile,
  profileLoading,
  focusContent,
  pipelineWaiverPendingCount = 0,
  pipelineWaiverApprovedCount = 0,
  onOpenActivity,
  nextAction = null,
  nextActionLoading = false,
  nextActionError = null,
  compact = false,
  displayName = null,
  candidateCode = null,
  statusChip = null,
  summary = null,
  pipeline = null,
  ..._unusedHeaderProps
}: CandidateHeaderProps) {
  const { t } = useI18n()
  void _unusedHeaderProps

  const actionableNext =
    nextAction && nextAction.kind !== 'idle' && nextAction.kind !== 'done' ? nextAction : null
  const overflowItems: OverflowMenuItem[] = []
  if (!isNew && onFavoriteToggle) {
    overflowItems.push({
      id: 'favorite',
      label: candidate?.is_favorite
        ? t('app.candidate_card.actions.remove_favorite')
        : t('app.candidate_card.actions.add_favorite'),
      onSelect: onFavoriteToggle,
    })
  }
  if (!isNew && !candidate?.short_id && onGenerateShortId) {
    overflowItems.push({
      id: 'short-id',
      label: t('app.candidate_card.actions.generate_short_id'),
      onSelect: onGenerateShortId,
    })
  }
  if (!isNew && editMode && onEditToggle) {
    overflowItems.push({
      id: 'cancel-edit',
      label: t('app.candidate_card.actions.cancel_edit', { defaultValue: 'Cancel edit' }),
      onSelect: onEditToggle,
    })
  }
  if (!isNew && canDeleteDirect) {
    overflowItems.push({
      id: 'delete',
      label: t('common.actions.delete'),
      onSelect: onDelete,
      tone: 'danger',
    })
  }
  if (!isNew && !canDeleteDirect && canRequestDelete) {
    overflowItems.push({
      id: 'delete-request',
      label: deleteRequestLoading
        ? t('app.candidate_card.actions.delete_request_loading')
        : t('app.candidate_card.actions.delete_request'),
      onSelect: onDeleteRequest,
      disabled: deleteRequestLoading,
      tone: 'danger',
    })
  }

  const actionClass = clsx(
    'rounded-lg border font-medium transition disabled:opacity-60',
    compact ? 'px-2 py-1 text-xs' : 'px-3 py-2 text-sm',
  )

  const showSummary = Boolean(
    summary || statusChip || actionableNext || pipelineWaiverPendingCount > 0 || pipelineWaiverApprovedCount > 0,
  )

  return (
    <>
      <EntityRecordHeader
        compact={compact}
        title={displayName || '—'}
        code={candidateCode}
        back={!hideBackLink && backPath ? { to: backPath, label: backLabel || t('app.candidate_card.header.back') } : null}
        actions={
          isNew ? (
                <>
                  <button type="button" className={clsx(actionClass, 'border-white/30 bg-white/10 text-white hover:bg-white/20')} onClick={onCancel}>
                    {t('common.actions.cancel')}
                  </button>
                  <button
                    type="button"
                    className={clsx(actionClass, 'border-white bg-white font-semibold text-brand-700 shadow-sm hover:bg-white/90')}
                    disabled={saving || !canEdit}
                    onClick={onSave}
                  >
                    {saving ? t('common.saving') : t('common.actions.create')}
                  </button>
                </>
              ) : (
                <>
                  {onOpenActivity ? (
                    <button
                      type="button"
                      className={clsx(actionClass, 'inline-flex items-center gap-1.5 border-white/30 bg-white/10 text-white hover:bg-white/20')}
                      onClick={onOpenActivity}
                    >
                      <IconHistory size={16} className="shrink-0 opacity-90" aria-hidden />
                      {t('app.candidate_card.ia.activity_history', { defaultValue: 'Activity / History' })}
                    </button>
                  ) : null}
                  {handoffReadonlyText ? (
                    <div className="max-w-xs rounded-lg border border-white/40 bg-white/15 px-2 py-1 text-left text-xs font-medium leading-tight text-white" role="status">
                      {handoffReadonlyText}
                    </div>
                  ) : onOpenHandoff ? (
                    <button
                      type="button"
                      className={clsx(actionClass, 'border-white bg-white font-semibold text-brand-700 shadow-sm hover:bg-white/90')}
                      onClick={onOpenHandoff}
                      disabled={handoffDisabled}
                      title={handoffDisabled && handoffDisabledTitle ? handoffDisabledTitle : undefined}
                    >
                      {handoffLabel || t('app.candidate_card.handoff.transfer_btn', { defaultValue: 'Transfer to client' })}
                    </button>
                  ) : null}
                  {onOpenHrTransfer ? (
                    <button
                      type="button"
                      className={clsx(actionClass, 'border-white bg-white font-semibold text-brand-700 shadow-sm hover:bg-white/90')}
                      onClick={onOpenHrTransfer}
                      disabled={handoffDisabled}
                    >
                      {hrTransferLabel || t('app.candidate_card.handoff.transfer_internal_hr_btn', { defaultValue: 'Передать в HR' })}
                    </button>
                  ) : null}
                  <OverflowMenu
                    label={t('common.actions.more')}
                    items={overflowItems}
                    appearance="inverse"
                  />
                </>
              )
        }
        summary={showSummary ? (
          <>
            {summary}
            {statusChip}
            {!isMasked && candidate?.intake_application_kind === 'client' ? (
              <span
                className="inline-flex items-center rounded-lg border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-800"
                title={t('app.candidate_card.labels.client_intake_badge_hint')}
              >
                {t('app.candidate_card.labels.client_intake_badge')}
              </span>
            ) : null}
            {!isMasked && pipelineWaiverPendingCount > 0 ? (
              <span
                className="inline-flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-950"
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
                className="inline-flex items-center rounded-lg border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-900"
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
            {profileLoading ? (
              <span className="text-[11px] text-slate-500">{t('common.loading')}</span>
            ) : null}
            {!profileLoading && !candidateProfile && candidate?.vacancy_id ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800" title={t('app.candidate_card.labels.no_profile')}>
                <IconAlertTriangle size={12} />
                {t('app.candidate_card.labels.no_profile_short')}
              </span>
            ) : null}
            {!isNew && candidate?.id && (actionableNext || nextActionError) ? (
              <NextActionBadge
                dto={actionableNext}
                loading={nextActionLoading}
                error={nextActionError}
                inverse={false}
              />
            ) : null}
          </>
        ) : null}
        pipeline={pipeline}
        extra={focusContent}
      />

      {deleteRequestMessage ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-blue-700">{deleteRequestMessage}</div>
      ) : null}
      {deleteRequestError ? (
        <ErrorRecoveryBanner
          info={{
            title: deleteRequestError,
            hint: t('app.common.retry_hint'),
          }}
          onRetry={onDeleteRequest}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
          compact
        />
      ) : null}
      {savedOk ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">
          {t('app.candidate_card.messages.saved')}
        </div>
      ) : null}
    </>
  )
}

export default memo(CandidateHeader)
