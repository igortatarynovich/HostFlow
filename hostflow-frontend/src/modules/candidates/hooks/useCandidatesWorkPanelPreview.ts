import { useCallback, useEffect, useState } from 'react'
import type { ReminderRecord } from '../../../api/types/notification'
import api, {
  createActivity,
  completeActivity,
  listReminders,
  getCandidateTimeline,
  snoozeActivity,
} from '../../../api/client'

type UseCandidatesWorkPanelPreviewArgs = {
  t: (key: string, options?: any) => string
  selectedCandidateId: string | null
}

export function useCandidatesWorkPanelPreview({ t, selectedCandidateId }: UseCandidatesWorkPanelPreviewArgs) {
  const [nextActionDetailsOpenTrigger] = useState(0)

  // Reminders (active reminder = next action editor content)
  const [previewRemindersLoading, setPreviewRemindersLoading] = useState(false)
  const [previewRemindersError, setPreviewRemindersError] = useState<string | null>(null)
  const [previewReminders, setPreviewReminders] = useState<ReminderRecord[]>([])

  const [previewReminderTitle, setPreviewReminderTitle] = useState('')
  const [previewReminderDueAt, setPreviewReminderDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [previewReminderBusy, setPreviewReminderBusy] = useState<string | null>(null)
  const [previewReminderOffset, setPreviewReminderOffset] = useState<number>(15)

  // Timeline
  const [previewTimelineLoading, setPreviewTimelineLoading] = useState(false)
  const [previewTimelineError, setPreviewTimelineError] = useState<string | null>(null)
  const [previewTimelineExpanded, setPreviewTimelineExpanded] = useState(false)
  const [previewTimelineItems, setPreviewTimelineItems] = useState<
    { at: string; kind: string; source: string; title?: string | null; description?: string | null }[]
  >([])

  // Docs blockers state (fed by CandidateDocsRailPanel)
  const [docsBlockers, setDocsBlockers] = useState<{
    missing: string[]
    problematic: string[]
    inProgress: string[]
  }>({ missing: [], problematic: [], inProgress: [] })
  const [docsBlockersLoading, setDocsBlockersLoading] = useState(false)

  /** Fields not present on list rows; merged into work-panel selected candidate (contact policy gate). */
  const [previewCandidateExtra, setPreviewCandidateExtra] = useState<{
    contact_policy_enabled: boolean
    contact_attempt_count: number
  } | null>(null)
  const [previewCandidateDetailLoading, setPreviewCandidateDetailLoading] = useState(false)

  useEffect(() => {
    if (!selectedCandidateId) {
      setPreviewCandidateExtra(null)
      setPreviewCandidateDetailLoading(false)
      return
    }
    let cancelled = false
    setPreviewCandidateDetailLoading(true)
    setPreviewCandidateExtra(null)
    void api
      .get(`/candidates/${selectedCandidateId}`)
      .then((res) => {
        if (cancelled) return
        const d = res.data as Record<string, unknown>
        const n = d?.contact_attempt_count
        setPreviewCandidateExtra({
          contact_policy_enabled: Boolean(d?.contact_policy_enabled),
          contact_attempt_count: typeof n === 'number' ? n : Number(n) || 0,
        })
      })
      .catch(() => {
        if (!cancelled) {
          setPreviewCandidateExtra({ contact_policy_enabled: false, contact_attempt_count: 0 })
        }
      })
      .finally(() => {
        if (!cancelled) setPreviewCandidateDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedCandidateId])

  const loadPreviewReminders = useCallback(
    async (candidateId: string) => {
      setPreviewRemindersLoading(true)
      setPreviewRemindersError(null)
      try {
        const res = await listReminders({ entityType: 'candidate', entityId: candidateId, status: ['pending', 'new', 'overdue'] })
        const list = Array.isArray(res?.items) ? (res.items as ReminderRecord[]) : []
        setPreviewReminders(list)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load reminders')
        setPreviewReminders([])
      } finally {
        setPreviewRemindersLoading(false)
      }
    },
    [],
  )

  const loadPreviewTimeline = useCallback(
    async (candidateId: string) => {
      setPreviewTimelineLoading(true)
      setPreviewTimelineError(null)
      try {
        const res = await getCandidateTimeline(candidateId)
        const items = Array.isArray(res?.items) ? res.items : []
        setPreviewTimelineItems(
          items.map((item: any) => ({
            at: item.at,
            kind: String(item.kind || ''),
            source: String(item.source || ''),
            title: item.title,
            description: item.description,
          })),
        )
      } catch (err: any) {
        setPreviewTimelineError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load timeline')
        setPreviewTimelineItems([])
      } finally {
        setPreviewTimelineLoading(false)
      }
    },
    [],
  )

  // Auto-load reminders/timeline on candidate change; also reset stale state.
  useEffect(() => {
    if (!selectedCandidateId) {
      setPreviewReminders([])
      setPreviewRemindersError(null)
      setPreviewRemindersLoading(false)
      return
    }
    void loadPreviewReminders(selectedCandidateId)
  }, [loadPreviewReminders, selectedCandidateId])

  useEffect(() => {
    if (!selectedCandidateId) {
      setPreviewTimelineItems([])
      setPreviewTimelineError(null)
      setPreviewTimelineLoading(false)
      return
    }
    setPreviewTimelineExpanded(false)
    void loadPreviewTimeline(selectedCandidateId)
  }, [loadPreviewTimeline, selectedCandidateId])

  // Reset docs blockers on candidate change to avoid showing stale UI.
  useEffect(() => {
    setDocsBlockers({ missing: [], problematic: [], inProgress: [] })
    setDocsBlockersLoading(false)
  }, [selectedCandidateId])

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
      await loadPreviewReminders(selectedCandidateId)
    } catch (err: any) {
      setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to create reminder')
    }
  }, [
    loadPreviewReminders,
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
        if (selectedCandidateId) await loadPreviewReminders(selectedCandidateId)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to complete reminder')
      } finally {
        setPreviewReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadPreviewReminders, selectedCandidateId],
  )

  const handlePreviewReminderSnooze = useCallback(
    async (id: string, minutes: number) => {
      try {
        setPreviewReminderBusy(id)
        await snoozeActivity(id, { minutes })
        if (selectedCandidateId) await loadPreviewReminders(selectedCandidateId)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to snooze reminder')
      } finally {
        setPreviewReminderBusy((prev) => (prev === id ? null : prev))
      }
    },
    [loadPreviewReminders, selectedCandidateId],
  )

  return {
    nextActionDetailsOpenTrigger,
    previewCandidateExtra,
    previewCandidateDetailLoading,
    previewReminders,
    previewRemindersLoading,
    previewRemindersError,
    previewReminderBusy,
    previewReminderTitle,
    previewReminderDueAt,
    previewReminderOffset,
    setPreviewReminderTitle,
    setPreviewReminderDueAt,
    setPreviewReminderOffset,
    previewTimelineItems,
    previewTimelineLoading,
    previewTimelineError,
    previewTimelineExpanded,
    setPreviewTimelineExpanded,
    loadPreviewTimeline,
    docsBlockers,
    docsBlockersLoading,
    setDocsBlockers,
    setDocsBlockersLoading,
    handleCreatePreviewReminder,
    handleDocsRequestCreate,
    handleCompletePreviewReminder,
    handlePreviewReminderSnooze,
  }
}

