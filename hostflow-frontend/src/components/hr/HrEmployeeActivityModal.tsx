import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, listReminders } from '../../api/client'
import type { ReminderRecord } from '../../api/types'
import type { CandidateNote, StageHistoryEntry } from '../../modules/candidate-card/types'
import { useI18n } from '../../i18n'
import { useMetaStages } from '../../store/useMeta'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { translateStageLabel } from '../../utils/stageLabels'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import CandidateTimelinePanel from '../candidate/CandidateTimelinePanel'
import { activateClickOnSpaceEnter, runActionOnSpaceEnter } from '../../utils/a11yClick'
import { isUuidLike } from '../../modules/candidate-card/utils'

function handoffThresholdMs(handoffAt: string | null | undefined): number | null {
  if (!handoffAt || !String(handoffAt).trim()) return null
  const ts = Date.parse(String(handoffAt))
  return Number.isNaN(ts) ? null : ts
}

type Props = {
  locale: string
  candidateId: string | null | undefined
  open: boolean
  onClose: () => void
  /** Limit activity to events at/after internal HR handoff (employee.handoff_at). */
  activitySinceHandoffAt?: string | null
  refreshSignal?: number
}

export function HrEmployeeActivityModal({
  locale,
  candidateId,
  open,
  onClose,
  activitySinceHandoffAt = null,
  refreshSignal = 0,
}: Props) {
  const { t } = useI18n()
  const meta = useMetaStages()
  const scopeWorkspaceId = useCurrentTenantId()
  const apiScopeConfig = useMemo(() => {
    const tid = scopeWorkspaceId && isUuidLike(scopeWorkspaceId) ? String(scopeWorkspaceId).trim() : ''
    return tid ? { params: { scope_tenant_id: tid } } : {}
  }, [scopeWorkspaceId])

  const [stageHistory, setStageHistory] = useState<StageHistoryEntry[]>([])
  const [notes, setNotes] = useState<CandidateNote[]>([])
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [timelineError, setTimelineError] = useState<FriendlyErrorInfo | null>(null)

  const resolveStageLabel = useCallback(
    (code: string) => translateStageLabel(t, code, meta?.labels?.[code] || code),
    [meta?.labels, t],
  )

  const load = useCallback(async () => {
    if (!candidateId) return
    setLoading(true)
    setTimelineError(null)
    const fb = t('common.errors.request_failed', { defaultValue: 'Request failed' })
    try {
      const [{ data: hist }, { data: notesData }, res] = await Promise.all([
        api.get(`/candidates/${encodeURIComponent(candidateId)}/stage-history`, apiScopeConfig),
        api.get(`/candidates/${encodeURIComponent(candidateId)}/notes`, apiScopeConfig),
        listReminders({
          entityType: 'candidate',
          entityId: candidateId,
          status: ['pending', 'new', 'overdue', 'done', 'cancelled'],
        }),
      ])
      const entries = Array.isArray(hist) ? hist : []
      let normalized: StageHistoryEntry[] = entries.map((item: Record<string, unknown>, idx: number) => ({
        id: String(item?.id ?? `${item?.to_code ?? 'stage'}-${item?.at ?? idx}`),
        from_code: (item?.from_code as string | null) ?? null,
        to_code: (item?.to_code as string | null) ?? null,
        at: (item?.at as string | null) ?? null,
        actor: (item?.actor as string | null) ?? (item?.actor_name as string | null) ?? null,
        reason: (item?.reason as string | null) ?? null,
      }))
      let notesArr = Array.isArray(notesData) ? (notesData as CandidateNote[]) : []
      let items = Array.isArray(res?.items) ? res.items : []

      const sinceMs = handoffThresholdMs(activitySinceHandoffAt)
      if (sinceMs != null) {
        normalized = normalized.filter((h) => {
          if (!h.at) return false
          const ts = Date.parse(String(h.at))
          return !Number.isNaN(ts) && ts >= sinceMs
        })
        notesArr = notesArr.filter((n) => {
          const ts = Date.parse(String(n.created_at || ''))
          return !Number.isNaN(ts) && ts >= sinceMs
        })
        items = items.filter((r: ReminderRecord) => {
          const raw = r.created_at || r.due_at || r.remind_at
          const ts = raw ? Date.parse(String(raw)) : 0
          return ts >= sinceMs
        })
      }

      setStageHistory(normalized)
      setNotes(notesArr)
      setReminders(items)
    } catch (err: unknown) {
      setTimelineError(getFriendlyErrorInfo(err, fb, t))
    } finally {
      setLoading(false)
    }
  }, [candidateId, t, apiScopeConfig, activitySinceHandoffAt])

  useEffect(() => {
    if (!open || !candidateId) return
    void load()
  }, [open, candidateId, load, refreshSignal])

  if (!candidateId) return null

  return open ? (
    <div
      className="fixed inset-0 z-hf-overlay flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      onKeyDown={(e) => runActionOnSpaceEnter(e, onClose)}
      role="presentation"
    >
      <div
        role="presentation"
        className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => activateClickOnSpaceEnter(e, (ev) => ev.stopPropagation())}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="hr-employee-activity-title"
          className="flex min-h-0 flex-1 flex-col overflow-hidden outline-none"
        >
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
          <div id="hr-employee-activity-title" className="text-sm font-semibold text-slate-900">
            {t('app.hr.employee_detail.activity.title', {
              defaultValue: 'Activity since handoff',
            })}
          </div>
          <button type="button" className="btn-secondary btn-sm" onClick={onClose}>
            {t('common.actions.close', { defaultValue: 'Close' })}
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <p className="mb-2 text-[11px] leading-relaxed text-slate-500">
            {activitySinceHandoffAt
              ? t('app.hr.employee_detail.activity.since_handoff_hint', {
                  defaultValue: 'Only events after the internal HR transfer are shown.',
                })
              : t('app.hr.employee_detail.activity.all_hint', {
                  defaultValue: 'Full candidate activity (no handoff timestamp on record).',
                })}
          </p>
          <CandidateTimelinePanel
            locale={locale}
            stageHistory={stageHistory}
            notes={notes}
            reminders={reminders}
            loading={loading}
            timelineError={timelineError}
            resolveStageLabel={resolveStageLabel}
            onRequestLoad={load}
            includeStageChanges
            variant="info"
            collapsedCount={15}
            hideToggle
            expanded
            itemsMaxHeightClass="max-h-[min(70vh,28rem)]"
            stageHistoryShortcut
          />
        </div>
        </div>
      </div>
    </div>
  ) : null
}
