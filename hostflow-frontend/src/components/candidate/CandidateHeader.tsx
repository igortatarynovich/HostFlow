import { memo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconAlertTriangle, IconHistory, IconStar } from '@tabler/icons-react'
import type { Candidate } from '../../api/types'
import type { CandidateNextActionDTO } from '../../api/candidates'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import NextActionBadge from './NextActionBadge'
import { Button } from '../ui/Button'
import { EntitySummaryHeader } from '../ui/EntitySummaryHeader'
import { OverflowMenu, type OverflowMenuItem } from '../ui/OverflowMenu'
import { StatusBadge } from '../ui/StatusBadge'

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
  /** Identity facts under the name: citizenship, age, residence, languages, status. */
  meta?: ReactNode
  /** Operational context under the name: vacancy, stage, warnings. */
  summary?: ReactNode
  /** Recruitment context row: vacancy, employer, professional facts. */
  context?: ReactNode
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
  meta = null,
  summary = null,
  context = null,
  pipeline = null,
  ..._unusedHeaderProps
}: CandidateHeaderProps) {
  const { t } = useI18n()
  const [copied, setCopied] = useState(false)
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

  const name = displayName || '—'
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('') || '•'
  void compact

  const copyCode = async () => {
    if (!candidateCode) return
    try {
      await navigator.clipboard.writeText(candidateCode)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    } catch {
      setCopied(false)
    }
  }

  const actions = isNew ? (
    <>
      <Button type="button" variant="secondary" size="compact" onClick={onCancel}>
        {t('common.actions.cancel')}
      </Button>
      <Button type="button" variant="primary" size="compact" disabled={saving || !canEdit} onClick={onSave}>
        {saving ? t('common.saving') : t('common.actions.create')}
      </Button>
    </>
  ) : (
    <>
      {onFavoriteToggle ? (
        <Button
          type="button"
          variant="icon"
          size="compact"
          onClick={onFavoriteToggle}
          aria-label={
            candidate?.is_favorite
              ? t('app.candidate_card.actions.remove_favorite')
              : t('app.candidate_card.actions.add_favorite')
          }
        >
          <IconStar size={16} className={candidate?.is_favorite ? 'fill-amber-400 text-amber-500' : 'text-slate-500'} />
        </Button>
      ) : null}
      <OverflowMenu label={t('common.actions.more')} items={overflowItems} />
      {onOpenActivity ? (
        <Button type="button" variant="secondary" size="compact" onClick={onOpenActivity}>
          <IconHistory size={14} className="shrink-0" aria-hidden />
          {t('app.candidate_card.ia.activity_history', { defaultValue: 'Activity / History' })}
        </Button>
      ) : null}
      {handoffReadonlyText ? (
        <StatusBadge label={handoffReadonlyText} semantic="info" size="md" />
      ) : onOpenHandoff ? (
        <Button
          type="button"
          variant="primary"
          size="compact"
          onClick={onOpenHandoff}
          disabled={handoffDisabled}
          title={handoffDisabled && handoffDisabledTitle ? handoffDisabledTitle : undefined}
        >
          {handoffLabel || t('app.candidate_card.handoff.transfer_btn', { defaultValue: 'Transfer to client' })}
        </Button>
      ) : null}
      {onOpenHrTransfer ? (
        <Button type="button" variant="primary" size="compact" onClick={onOpenHrTransfer} disabled={handoffDisabled}>
          {hrTransferLabel || t('app.candidate_card.handoff.transfer_internal_hr_btn', { defaultValue: 'Передать в HR' })}
        </Button>
      ) : null}
    </>
  )

  return (
    <>
      {!hideBackLink && backPath ? (
        <div className="mb-1 text-[11px] text-slate-500">
          <Link className="hover:underline" to={backPath}>
            {backLabel || t('app.candidate_card.header.back')}
          </Link>
        </div>
      ) : null}
      <EntitySummaryHeader
        initials={initials}
        title={name}
        code={copied ? t('common.actions.copied', { defaultValue: 'Copied' }) : candidateCode}
        onCopyCode={candidateCode ? () => void copyCode() : undefined}
        copyLabel={t('common.actions.copy', { defaultValue: 'Copy' })}
        actions={actions}
        context={context}
        pipeline={pipeline}
        meta={
          <>
            {meta}
            {statusChip}
            {summary}
            {!isMasked && candidate?.intake_application_kind === 'client' ? (
              <StatusBadge label={t('app.candidate_card.labels.client_intake_badge')} semantic="info" size="sm" title={t('app.candidate_card.labels.client_intake_badge_hint')} />
            ) : null}
            {!isMasked && pipelineWaiverPendingCount > 0 ? (
              <StatusBadge
                semantic="warning"
                size="sm"
                icon={<IconAlertTriangle size={12} />}
                label={t('app.candidate_card.pipeline_override.badge_pending', {
                  defaultValue: 'Waiver pending ({count})',
                  values: { count: String(pipelineWaiverPendingCount) },
                })}
                title={t('app.candidate_card.pipeline_override.badge_pending_hint', {
                  defaultValue: 'Document waiver waiting for manager approval',
                })}
              />
            ) : null}
            {!isMasked && pipelineWaiverApprovedCount > 0 ? (
              <StatusBadge
                semantic="success"
                size="sm"
                label={t('app.candidate_card.pipeline_override.badge_active', {
                  defaultValue: 'Waiver active ({count})',
                  values: { count: String(pipelineWaiverApprovedCount) },
                })}
                title={t('app.candidate_card.pipeline_override.badge_active_hint', {
                  defaultValue: 'Approved document waiver(s) relax pipeline / handoff gates for listed types',
                })}
              />
            ) : null}
            {profileLoading ? <span className="text-[11px] text-slate-500">{t('common.loading')}</span> : null}
            {!profileLoading && !candidateProfile && candidate?.vacancy_id ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800" title={t('app.candidate_card.labels.no_profile')}>
                <IconAlertTriangle size={12} />
                {t('app.candidate_card.labels.no_profile_short')}
              </span>
            ) : null}
            {!isNew && candidate?.id && (actionableNext || nextActionError) ? (
              <NextActionBadge dto={actionableNext} loading={nextActionLoading} error={nextActionError} inverse={false} />
            ) : null}
          </>
        }
      />
      {focusContent ? <div className="mt-2 rounded-xl border border-slate-200 bg-white px-3 py-2">{focusContent}</div> : null}

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
