import { useCallback, useEffect, useState } from 'react'
import type { ReminderRecord } from '../../../api/types/notification'
import {
  createActivity,
  completeActivity,
  getCandidateWorkPanel,
  snoozeActivity,
} from '../../../api/client'
import { recordPerfMeasurement } from '../../../api/analytics'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { CandidateDocsRailSummarySnapshot } from '../../../components/candidate/CandidateDocsRailPanel'

/** Relative URLs from `GET .../work-panel` `comms` (snake_case in JSON). */
export type CandidatesWorkPanelCommsLinks = {
  messagesRelativeUrl: string
  emailRelativeUrl: string
  documentsRelativeUrl: string
}

function parseWorkPanelComms(raw: unknown): CandidatesWorkPanelCommsLinks | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  const m = o.messages_relative_url
  const e = o.email_relative_url
  const d = o.documents_relative_url
  if (typeof m !== 'string' || !m.trim()) return null
  if (typeof e !== 'string' || !e.trim()) return null
  if (typeof d !== 'string' || !d.trim()) return null
  return {
    messagesRelativeUrl: m.trim(),
    emailRelativeUrl: e.trim(),
    documentsRelativeUrl: d.trim(),
  }
}

function parseWorkPanelDocumentsSummary(ds: Record<string, unknown>): CandidateDocsRailSummarySnapshot {
  const missing = Array.isArray(ds.missing) ? ds.missing.filter((x): x is string => typeof x === 'string') : []
  const problematic = Array.isArray(ds.problematic)
    ? ds.problematic.filter((x): x is string => typeof x === 'string')
    : []
  const ready_types = Array.isArray(ds.ready_types)
    ? ds.ready_types.filter((x): x is string => typeof x === 'string')
    : []
  const in_progress_types = Array.isArray(ds.in_progress_types)
    ? ds.in_progress_types.filter((x): x is string => typeof x === 'string')
    : []
  const pr = ds.percent_ready
  const percent_ready = typeof pr === 'number' && !Number.isNaN(pr) ? pr : Number(pr) || 0
  const expiring_soon = Array.isArray(ds.expiring_soon)
    ? (ds.expiring_soon as unknown[])
        .filter((x): x is Record<string, unknown> => x !== null && typeof x === 'object' && !Array.isArray(x))
        .map((x) => ({
          type: String(x.type ?? ''),
          expires_at: String(x.expires_at ?? ''),
        }))
        .filter((x) => x.type)
    : []
  return {
    percent_ready,
    required: { missing, problematic, ready_types, in_progress_types },
    expiring_soon,
  }
}

type UseCandidatesWorkPanelPreviewArgs = {
  t: (key: string, options?: any) => string
  selectedCandidateId: string | null
  /** Matches list/reminders API: whose candidate reminders appear in the work-panel bundle. */
  workPanelAssigneeScope?: 'mine' | 'team'
}

export function useCandidatesWorkPanelPreview({
  t,
  selectedCandidateId,
  workPanelAssigneeScope = 'mine',
}: UseCandidatesWorkPanelPreviewArgs) {
  const [workPanelBundleLoading, setWorkPanelBundleLoading] = useState(false)

  /** Increment to expand next-action details in preview (context menu / shortcuts only — not name cell). */
  const [nextActionDetailsOpenTrigger, setNextActionDetailsOpenTrigger] = useState(0)
  const bumpNextActionDetailsOpen = useCallback(() => {
    setNextActionDetailsOpenTrigger((n) => n + 1)
  }, [])

  // Reminders (active reminder = next action editor content)
  const [previewRemindersError, setPreviewRemindersError] = useState<string | null>(null)
  const [previewReminders, setPreviewReminders] = useState<ReminderRecord[]>([])

  const [previewReminderTitle, setPreviewReminderTitle] = useState('')
  const [previewReminderDueAt, setPreviewReminderDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [previewReminderBusy, setPreviewReminderBusy] = useState<string | null>(null)
  const [previewReminderOffset, setPreviewReminderOffset] = useState<number>(15)

  // Timeline
  const [previewTimelineError, setPreviewTimelineError] = useState<string | null>(null)
  const [previewTimelineExpanded, setPreviewTimelineExpanded] = useState(false)
  const [previewTimelineItems, setPreviewTimelineItems] = useState<
    { at: string; kind: string; source: string; title?: string | null; description?: string | null }[]
  >([])

  // Docs blockers: seeded from work-panel bundle, then refined by CandidateDocsRailPanel.
  const [docsBlockers, setDocsBlockers] = useState<{
    missing: string[]
    problematic: string[]
    inProgress: string[]
  }>({ missing: [], problematic: [], inProgress: [] })
  const [docsRailLoading, setDocsRailLoading] = useState(false)
  const [docsSeededFromWorkPanel, setDocsSeededFromWorkPanel] = useState(false)
  const docsBlockersLoading = docsRailLoading && !docsSeededFromWorkPanel

  /** Full checklist snapshot for `CandidateDocsRailPanel` (skips duplicate getSummary when seeded). */
  const [previewDocumentsSummarySnapshot, setPreviewDocumentsSummarySnapshot] =
    useState<CandidateDocsRailSummarySnapshot | null>(null)

  const [previewCommsLinks, setPreviewCommsLinks] = useState<CandidatesWorkPanelCommsLinks | null>(null)

  /** Fields from work-panel bundle (contact policy + risk v1). */
  const [previewCandidateExtra, setPreviewCandidateExtra] = useState<{
    contact_policy_enabled: boolean
    contact_attempt_count: number
    risk_score?: number
    risk_band?: string
    risk_drivers?: string[]
    risk_updated_at?: string
    risk_version?: string
  } | null>(null)

  const loadWorkPanelBundle = useCallback(async (candidateId: string) => {
    setWorkPanelBundleLoading(true)
    setPreviewRemindersError(null)
    setPreviewTimelineError(null)
    const t0 = typeof performance !== 'undefined' ? performance.now() : 0
    try {
      const data = (await getCandidateWorkPanel(candidateId, {
        timelineLimit: 80,
        assigneeScope: workPanelAssigneeScope,
      })) as Record<string, unknown>
      const profile = (data?.profile ?? {}) as Record<string, unknown>
      const n = profile.contact_attempt_count
      const rs = profile.risk_score
      const driversRaw = profile.risk_drivers
      setPreviewCandidateExtra({
        contact_policy_enabled: Boolean(profile.contact_policy_enabled),
        contact_attempt_count: typeof n === 'number' ? n : Number(n) || 0,
        risk_score: typeof rs === 'number' && !Number.isNaN(rs) ? rs : undefined,
        risk_band: typeof profile.risk_band === 'string' ? profile.risk_band : undefined,
        risk_drivers: Array.isArray(driversRaw)
          ? (driversRaw as unknown[]).filter((x): x is string => typeof x === 'string')
          : undefined,
        risk_updated_at: typeof profile.risk_updated_at === 'string' ? profile.risk_updated_at : undefined,
        risk_version: typeof profile.risk_version === 'string' ? profile.risk_version : undefined,
      })

      const rawReminders = data.reminders
      const remList = Array.isArray(rawReminders) ? rawReminders : []
      setPreviewReminders(remList as ReminderRecord[])

      const timeline = (data.timeline ?? {}) as { items?: unknown[] }
      const items = Array.isArray(timeline.items) ? timeline.items : []
      setPreviewTimelineItems(
        items.map((item: any) => ({
          at: String(item?.at ?? ''),
          kind: String(item?.kind || ''),
          source: String(item?.source || ''),
          title: item?.title ?? null,
          description: item?.description ?? null,
        })),
      )

      const ds = data.documents_summary as Record<string, unknown> | null | undefined
      if (ds && typeof ds === 'object') {
        const snap = parseWorkPanelDocumentsSummary(ds)
        setDocsBlockers({
          missing: snap.required?.missing ?? [],
          problematic: snap.required?.problematic ?? [],
          inProgress: snap.required?.in_progress_types ?? [],
        })
        setDocsSeededFromWorkPanel(true)
        setPreviewDocumentsSummarySnapshot(snap)
      } else {
        setDocsSeededFromWorkPanel(false)
        setPreviewDocumentsSummarySnapshot(null)
        setDocsBlockers({ missing: [], problematic: [], inProgress: [] })
      }

      setPreviewCommsLinks(parseWorkPanelComms(data.comms))

      const elapsed =
        typeof performance !== 'undefined' ? Math.max(0, performance.now() - t0) : 0
      void recordPerfMeasurement({
        metricKey: 'candidates.work_panel.load',
        durationMs: Math.round(elapsed),
        route: CRM_APP_PATHS.candidates,
        meta: { candidateId, assigneeScope: workPanelAssigneeScope },
      })
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? 'Failed to load work panel'
      setPreviewRemindersError(msg)
      setPreviewTimelineError(msg)
      setPreviewCandidateExtra({ contact_policy_enabled: false, contact_attempt_count: 0 })
      setPreviewReminders([])
      setPreviewTimelineItems([])
      setDocsSeededFromWorkPanel(false)
      setPreviewDocumentsSummarySnapshot(null)
      setPreviewCommsLinks(null)
    } finally {
      setWorkPanelBundleLoading(false)
    }
  }, [workPanelAssigneeScope])

  useEffect(() => {
    if (!selectedCandidateId) {
      setPreviewCandidateExtra(null)
      setPreviewReminders([])
      setPreviewRemindersError(null)
      setPreviewTimelineItems([])
      setPreviewTimelineError(null)
      setWorkPanelBundleLoading(false)
      setPreviewDocumentsSummarySnapshot(null)
      setPreviewCommsLinks(null)
      return
    }
    void loadWorkPanelBundle(selectedCandidateId)
  }, [loadWorkPanelBundle, selectedCandidateId, workPanelAssigneeScope])

  // Auto-load reminders/timeline on candidate change; also reset stale state.
  useEffect(() => {
    if (!selectedCandidateId) {
      return
    }
    setPreviewTimelineExpanded(false)
  }, [selectedCandidateId])

  // Reset docs blockers on candidate change to avoid showing stale UI.
  useEffect(() => {
    setDocsBlockers({ missing: [], problematic: [], inProgress: [] })
    setDocsRailLoading(false)
    setDocsSeededFromWorkPanel(false)
    setPreviewDocumentsSummarySnapshot(null)
    setPreviewCommsLinks(null)
  }, [selectedCandidateId])

  const loadPreviewTimeline = useCallback(
    (candidateId: string) => {
      void loadWorkPanelBundle(candidateId)
    },
    [loadWorkPanelBundle],
  )

  const handleCreatePreviewReminder = useCallback(async () => {
    if (!selectedCandidateId || !previewReminderTitle || !previewReminderDueAt) return
    try {
      const due = new Date(previewReminderDueAt)
      const remindAt = new Date(due.getTime() - previewReminderOffset * 60 * 1000)
      await createActivity({
        title: previewReminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'candidate',
        entity_id: selectedCandidateId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        source: 'manual',
      })
      setPreviewReminderTitle('')
      setPreviewReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      await loadWorkPanelBundle(selectedCandidateId)
    } catch (err: any) {
      setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to create reminder')
    }
  }, [
    loadWorkPanelBundle,
    previewReminderDueAt,
    previewReminderOffset,
    previewReminderTitle,
    selectedCandidateId,
  ])

  const handleDocsRequestCreate = useCallback(() => {
    const dt = new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16)
    setPreviewReminderTitle(t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Request documents' }))
    setPreviewReminderDueAt(dt)
  }, [t])

  const handleCompletePreviewReminder = useCallback(
    async (id: string) => {
      try {
        setPreviewReminderBusy(id)
        await completeActivity(id)
        if (selectedCandidateId) await loadWorkPanelBundle(selectedCandidateId)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to complete reminder')
      } finally {
        setPreviewReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadWorkPanelBundle, selectedCandidateId],
  )

  const handlePreviewReminderSnooze = useCallback(
    async (id: string, minutes: number) => {
      try {
        setPreviewReminderBusy(id)
        await snoozeActivity(id, { minutes })
        if (selectedCandidateId) await loadWorkPanelBundle(selectedCandidateId)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to snooze reminder')
      } finally {
        setPreviewReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadWorkPanelBundle, selectedCandidateId],
  )

  return {
    nextActionDetailsOpenTrigger,
    bumpNextActionDetailsOpen,
    previewCandidateExtra,
    previewCandidateDetailLoading: workPanelBundleLoading,
    previewReminders,
    previewRemindersLoading: workPanelBundleLoading,
    previewRemindersError,
    previewReminderBusy,
    previewReminderTitle,
    previewReminderDueAt,
    previewReminderOffset,
    setPreviewReminderTitle,
    setPreviewReminderDueAt,
    setPreviewReminderOffset,
    previewTimelineItems,
    previewTimelineLoading: workPanelBundleLoading,
    previewTimelineError,
    previewTimelineExpanded,
    setPreviewTimelineExpanded,
    loadPreviewTimeline,
    docsBlockers,
    docsBlockersLoading,
    setDocsBlockers,
    setDocsBlockersLoading: setDocsRailLoading,
    previewDocumentsSummarySnapshot,
    previewCommsLinks,
    handleCreatePreviewReminder,
    handleDocsRequestCreate,
    handleCompletePreviewReminder,
    handlePreviewReminderSnooze,
  }
}
