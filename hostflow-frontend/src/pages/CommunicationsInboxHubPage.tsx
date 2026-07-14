import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { IconBell, IconRefresh } from '@tabler/icons-react'
import {
  createCommunicationCommandAuditBatch,
  getCommunicationsSettings,
  listCommunicationCommandAudit,
  markCommunicationThreadRead,
  patchCommunicationThread,
  patchCommunicationsSettings,
  type CommunicationCommandAudit,
  type CommunicationCommandTemplate,
  type CommunicationThread,
} from '../api/communications'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { useCommunicationsSetupStatus } from '../hooks/useCommunicationsSetupStatus'
import { useEmailInboundSync } from '../hooks/useEmailInboundSync'
import InboxUnifiedThreadList, { type InboxHubFilter } from '../components/communications/InboxUnifiedThreadList'
import InboxEmailFolderRail from '../components/communications/InboxEmailFolderRail'
import { emailThreadInFolder, type EmailFolderKey } from '../utils/emailInboxFolders'
import { fetchInboxThreadPool } from '../utils/inboxThreadLoad'
import {
  inboxContextQueryString,
  inboxContextSearchParams,
  readInboxListQuery,
  type InboxChannelScope,
  type InboxListQuery,
} from '../utils/inboxUrlQuery'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../components/layout'
import { stashPendingGmailOAuthCode } from '../utils/oauthRedirectBridge'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { useToast } from '../components/Toast'

function isActiveThread(th: CommunicationThread): boolean {
  return !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted'
}

function canPatchCommunicationsSettings(role: string | undefined): boolean {
  const r = String(role || '').trim().toLowerCase()
  return r === 'administrator' || r === 'supervisor' || r === 'admin' || r === 'superadmin'
}

function bulkActionPreviewLabel(type: string, value?: string | null): string {
  if (type === 'mark_read') return 'Mark read'
  if (type === 'archive') return 'Archive'
  if (type === 'unarchive') return 'Unarchive'
  if (type === 'delete') return 'Delete'
  if (type === 'restore') return 'Restore'
  if (type === 'priority_high') return 'Priority high'
  if (type === 'priority_normal') return 'Priority normal'
  if (type === 'tag_add') return value ? `Add tag: ${value}` : 'Add tag'
  if (type === 'tag_remove') return value ? `Remove tag: ${value}` : 'Remove tag'
  if (type === 'move_folder') return value ? `Move to folder: ${value}` : 'Move to folder'
  return type || 'Unknown action'
}

type BulkUndoSnapshot = {
  id: string
  status: string
  is_archived: boolean
  priority: string
  tags_json: any[]
  unread_count: number
}

type LastBulkUndoState = {
  commandLabel: string
  expiresAtMs: number
  snapshots: BulkUndoSnapshot[]
  auditBatchId?: string
}

type BulkConflictItem = {
  threadId: string
  reason: string
}

type BulkConflictReport = {
  commandId: string
  commandLabel: string
  createdAtMs: number
  failed: BulkConflictItem[]
}

const LAST_BULK_UNDO_STORAGE_KEY = 'hostflow_inbox_last_bulk_undo_v1'

function normalizeLastBulkUndoState(raw: unknown): LastBulkUndoState | null {
  if (!raw || typeof raw !== 'object') return null
  const src = raw as Record<string, any>
  const commandLabel = String(src.commandLabel || '').trim()
  const expiresAtMs = Number(src.expiresAtMs || 0)
  const snapshotsRaw = Array.isArray(src.snapshots) ? src.snapshots : []
  const snapshots: BulkUndoSnapshot[] = snapshotsRaw
    .filter((x) => x && typeof x === 'object')
    .map((x) => {
      const row = x as Record<string, any>
      return {
        id: String(row.id || '').trim(),
        status: String(row.status || 'open'),
        is_archived: Boolean(row.is_archived),
        priority: String(row.priority || 'normal'),
        tags_json: Array.isArray(row.tags_json) ? row.tags_json : [],
        unread_count: Math.max(0, Number(row.unread_count || 0)),
      }
    })
    .filter((x) => Boolean(x.id))
  if (!commandLabel || !Number.isFinite(expiresAtMs) || expiresAtMs <= Date.now() || snapshots.length === 0) return null
  const auditBatchId = String(src.auditBatchId || '').trim() || undefined
  return { commandLabel, expiresAtMs, snapshots, auditBatchId }
}

function lastBulkUndoFromAudit(items: CommunicationCommandAudit[]): LastBulkUndoState | null {
  if (!Array.isArray(items) || items.length === 0) return null
  const now = Date.now()
  for (const row of items) {
    const payload = row && typeof row.payload === 'object' ? row.payload : {}
    const batchId = String((payload as any).bulk_batch_id || '').trim()
    const expiresAtRaw = String((payload as any).undo_expires_at || '').trim()
    const expiresAtMs = Date.parse(expiresAtRaw)
    if (!batchId || !Number.isFinite(expiresAtMs) || expiresAtMs <= now) continue
    const snapshotsByThread = ((payload as any).undo_snapshots_by_thread_id || {}) as Record<string, any>
    const snapshots = Object.entries(snapshotsByThread)
      .map(([threadId, snap]) => {
        const s = snap && typeof snap === 'object' ? (snap as Record<string, any>) : {}
        return {
          id: String(s.id || threadId || '').trim(),
          status: String(s.status || 'open'),
          is_archived: Boolean(s.is_archived),
          priority: String(s.priority || 'normal'),
          tags_json: Array.isArray(s.tags_json) ? s.tags_json : [],
          unread_count: Math.max(0, Number(s.unread_count || 0)),
        } satisfies BulkUndoSnapshot
      })
      .filter((x) => Boolean(x.id))
    if (snapshots.length === 0) continue
    return {
      commandLabel: String(row.command_label || row.command_id || 'Bulk command'),
      expiresAtMs,
      snapshots,
      auditBatchId: batchId,
    }
  }
  return null
}

export default function CommunicationsInboxHubPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const { me } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const listQuery = useMemo(() => readInboxListQuery(searchParams), [searchParams])
  const { canUseCommunicationsFeature, loading: accessLoading } = useCommunicationsAccess()
  const commSetup = useCommunicationsSetupStatus()
  const hasMessages = canUseCommunicationsFeature('messages')
  const hasEmail = canUseCommunicationsFeature('email')
  const anyChannel = hasMessages || hasEmail

  const effectiveChannel: InboxChannelScope = useMemo(() => {
    if (listQuery.channel === 'email' && !hasEmail && hasMessages) return 'messages'
    if (listQuery.channel === 'messages' && !hasMessages && hasEmail) return 'email'
    return listQuery.channel
  }, [hasEmail, hasMessages, listQuery.channel])

  const writeInboxQuery = useCallback(
    (next: InboxListQuery) => {
      setSearchParams(inboxContextSearchParams(next), { replace: true })
    },
    [setSearchParams],
  )

  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [hubFilter, setHubFilter] = useState<InboxHubFilter>('all')
  const [qDraft, setQDraft] = useState(listQuery.q)
  const [oauthRedirectNotice, setOauthRedirectNotice] = useState(false)
  const [serverIncomingEnabled, setServerIncomingEnabled] = useState<boolean | null>(null)
  const [enablingIncoming, setEnablingIncoming] = useState(false)
  const [commandTemplates, setCommandTemplates] = useState<CommunicationCommandTemplate[]>([])
  const [selectedCommandId, setSelectedCommandId] = useState('')
  const [selectedThreadIds, setSelectedThreadIds] = useState<string[]>([])
  const [applyingCommand, setApplyingCommand] = useState(false)
  const [lastBulkUndo, setLastBulkUndo] = useState<LastBulkUndoState | null>(null)
  const [bulkConflictReport, setBulkConflictReport] = useState<BulkConflictReport | null>(null)

  useEffect(() => setQDraft(listQuery.q), [listQuery.q])

  useEffect(() => {
    if (!listQuery.unlinkedOnly) return
    setHubFilter('unlinked')
  }, [listQuery.unlinkedOnly])

  useEffect(() => {
    const code = searchParams.get('code')?.trim()
    if (!code) return
    stashPendingGmailOAuthCode(code)
    const next = inboxContextSearchParams(readInboxListQuery(searchParams))
    next.delete('code')
    next.delete('state')
    next.delete('scope')
    setSearchParams(next, { replace: true })
    setOauthRedirectNotice(true)
  }, [searchParams, setSearchParams])

  useEffect(() => {
    const id = window.setTimeout(() => {
      const trimmed = qDraft.trim()
      if (trimmed === listQuery.q) return
      writeInboxQuery({ ...listQuery, q: trimmed })
    }, 400)
    return () => window.clearTimeout(id)
  }, [listQuery, qDraft, writeInboxQuery])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const items = await fetchInboxThreadPool({
        effectiveChannel,
        hasEmail,
        hasMessages,
        q: listQuery.q,
      })
      setThreads(items)
      const cfg = await getCommunicationsSettings().catch(() => null)
      const commandItems = Array.isArray(cfg?.commands?.items) ? cfg.commands.items : []
      setCommandTemplates(commandItems.filter((x) => x && x.enabled !== false))
      if (effectiveChannel === 'email' && hasEmail) {
        const emailCfg = (cfg as any)?.email || {}
        setServerIncomingEnabled(
          typeof emailCfg.incomingEnabled === 'boolean' ? emailCfg.incomingEnabled : Boolean(emailCfg.incomingEnabled),
        )
      } else {
        setServerIncomingEnabled(null)
      }
    } catch (err: unknown) {
      setThreads([])
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications_inbox_hub.error'))) {
        setError(getFriendlyErrorInfo(err, t('app.communications_inbox_hub.error'), t))
      }
    } finally {
      setLoading(false)
    }
  }, [effectiveChannel, hasEmail, hasMessages, listQuery.q, planLimitModal, t])

  useEffect(() => {
    void load()
  }, [load])

  const { pollBusy, pollErrors, fetchInboundNow } = useEmailInboundSync({
    enabled: effectiveChannel === 'email' && hasEmail && !accessLoading,
    listLoading: loading,
    busy: false,
    onAfterPoll: load,
  })

  const emailFolderFiltered = useMemo(() => {
    if (effectiveChannel !== 'email' || !hasEmail) return threads
    return threads.filter((th) => emailThreadInFolder(th, listQuery.folder))
  }, [effectiveChannel, hasEmail, listQuery.folder, threads])

  const assigneeFiltered = useMemo(() => {
    const meId = String(me?.id || '').trim()
    let rows = emailFolderFiltered
    if (effectiveChannel === 'email' && listQuery.assignedToMe && meId) {
      rows = rows.filter((th) => String(th.assignee_id || '').trim() === meId)
    }
    if (effectiveChannel === 'email' && listQuery.hasAssignee) {
      rows = rows.filter((th) => Boolean(String(th.assignee_id || '').trim()))
    }
    return rows
  }, [effectiveChannel, emailFolderFiltered, listQuery.assignedToMe, listQuery.hasAssignee, me?.id])

  const listForUi = useMemo(() => {
    if (effectiveChannel === 'email' && hasEmail) return assigneeFiltered
    return assigneeFiltered.filter(isActiveThread)
  }, [assigneeFiltered, effectiveChannel, hasEmail])

  const listQueryForLinks: InboxListQuery = useMemo(
    () => ({
      ...listQuery,
      channel: effectiveChannel,
    }),
    [effectiveChannel, listQuery],
  )
  const selectedThreadSet = useMemo(() => new Set(selectedThreadIds), [selectedThreadIds])
  const selectedCommand = useMemo(
    () => commandTemplates.find((x) => x.id === selectedCommandId) || null,
    [commandTemplates, selectedCommandId],
  )
  const selectedVisibleCount = useMemo(
    () => listForUi.filter((th) => selectedThreadSet.has(String(th.id))).length,
    [listForUi, selectedThreadSet],
  )
  const selectedThreadsForBulk = useMemo(
    () => listForUi.filter((th) => selectedThreadSet.has(String(th.id))),
    [listForUi, selectedThreadSet],
  )
  const selectedEligibleThreads = useMemo(() => {
    if (!selectedCommand) return []
    return selectedThreadsForBulk.filter((th) => {
      const channel = String(th.channel || '').toLowerCase()
      return selectedCommand.target === 'both' || channel === selectedCommand.target
    })
  }, [selectedCommand, selectedThreadsForBulk])
  const selectedMismatchCount = Math.max(0, selectedThreadsForBulk.length - selectedEligibleThreads.length)
  const failedVisibleThreadIds = useMemo(() => {
    if (!bulkConflictReport) return []
    const visible = new Set(listForUi.map((th) => String(th.id)))
    return bulkConflictReport.failed.map((x) => x.threadId).filter((id) => visible.has(id))
  }, [bulkConflictReport, listForUi])

  useEffect(() => {
    const allowed = new Set(listForUi.map((th) => String(th.id)))
    setSelectedThreadIds((prev) => prev.filter((id) => allowed.has(id)))
  }, [listForUi])

  useEffect(() => {
    if (!lastBulkUndo) return
    const delay = Math.max(0, lastBulkUndo.expiresAtMs - Date.now())
    const timer = window.setTimeout(() => {
      setLastBulkUndo((prev) => (prev && prev.expiresAtMs <= Date.now() ? null : prev))
    }, delay + 50)
    return () => window.clearTimeout(timer)
  }, [lastBulkUndo])

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(LAST_BULK_UNDO_STORAGE_KEY)
      if (!raw) return
      const parsed = normalizeLastBulkUndoState(JSON.parse(raw))
      if (parsed) {
        setLastBulkUndo(parsed)
      } else {
        window.localStorage.removeItem(LAST_BULK_UNDO_STORAGE_KEY)
      }
    } catch {
      window.localStorage.removeItem(LAST_BULK_UNDO_STORAGE_KEY)
    }
  }, [])

  useEffect(() => {
    if (lastBulkUndo) return
    let cancelled = false
    const hydrateUndoFromAudit = async () => {
      try {
        const audit = await listCommunicationCommandAudit({
          limit: 120,
          actor_user_id: String(me?.id || '').trim() || undefined,
        })
        if (cancelled) return
        const hydrated = lastBulkUndoFromAudit(Array.isArray(audit?.items) ? audit.items : [])
        if (hydrated) setLastBulkUndo(hydrated)
      } catch {
        // no-op: fallback only
      }
    }
    void hydrateUndoFromAudit()
    return () => {
      cancelled = true
    }
  }, [lastBulkUndo, me?.id])

  useEffect(() => {
    try {
      if (!lastBulkUndo || lastBulkUndo.expiresAtMs <= Date.now()) {
        window.localStorage.removeItem(LAST_BULK_UNDO_STORAGE_KEY)
        return
      }
      window.localStorage.setItem(LAST_BULK_UNDO_STORAGE_KEY, JSON.stringify(lastBulkUndo))
    } catch {
      // best-effort persistence
    }
  }, [lastBulkUndo])

  const enableServerIncoming = async () => {
    setEnablingIncoming(true)
    try {
      const cfg = await getCommunicationsSettings()
      const email = (cfg as any)?.email || {}
      await patchCommunicationsSettings({
        email: {
          ...email,
          incomingEnabled: true,
          syncIntervalMinutes: Number(email.syncIntervalMinutes) > 0 ? email.syncIntervalMinutes : 5,
        },
      })
      setServerIncomingEnabled(true)
    } catch {
      /* ignore */
    } finally {
      setEnablingIncoming(false)
    }
  }

  const setChannelTab = (c: InboxChannelScope) => {
    const base: InboxListQuery = { ...listQuery, channel: c, q: listQuery.q, candidateId: listQuery.candidateId }
    if (c !== 'email') {
      base.folder = 'inbox'
    }
    writeInboxQuery(base)
  }

  const onEmailFolderChange = (folder: EmailFolderKey) => {
    writeInboxQuery({ ...listQuery, channel: 'email', folder })
  }

  const toggleAssignedToMe = () => {
    writeInboxQuery({ ...listQuery, assignedToMe: !listQuery.assignedToMe })
  }

  const toggleHasAssignee = () => {
    writeInboxQuery({ ...listQuery, hasAssignee: !listQuery.hasAssignee })
  }

  const toggleSingleThread = (threadId: string, nextChecked: boolean) => {
    const id = String(threadId)
    setSelectedThreadIds((prev) => {
      const has = prev.includes(id)
      if (nextChecked && !has) return [...prev, id]
      if (!nextChecked && has) return prev.filter((x) => x !== id)
      return prev
    })
  }

  const toggleVisibleThreads = (threadIds: string[], nextChecked: boolean) => {
    const ids = [...new Set(threadIds.map((x) => String(x)).filter(Boolean))]
    if (!ids.length) return
    setSelectedThreadIds((prev) => {
      if (nextChecked) return [...new Set([...prev, ...ids])]
      const remove = new Set(ids)
      return prev.filter((x) => !remove.has(x))
    })
  }

  const applyCommandTemplateBulk = async () => {
    if (applyingCommand) return
    const command = selectedCommand
    if (!command) {
      notify({
        title: t('app.communications_inbox_hub.bulk.command_required', { defaultValue: 'Select a command template first.' }),
        variant: 'warning',
      })
      return
    }
    const picked = selectedThreadsForBulk
    if (!picked.length) {
      notify({
        title: t('app.communications_inbox_hub.bulk.no_threads', { defaultValue: 'Select at least one thread.' }),
        variant: 'warning',
      })
      return
    }
    const eligible = selectedEligibleThreads
    if (!eligible.length) {
      notify({
        title: t('app.communications_inbox_hub.bulk.no_eligible', { defaultValue: 'No selected threads match this command target.' }),
        variant: 'warning',
      })
      return
    }

    setApplyingCommand(true)
    try {
      const updatedById = new Map<string, CommunicationThread>()
      let skippedActions = 0
      const successThreadIds: string[] = []
      const failedThreadIds: string[] = []
      const failedReasons: string[] = []
      const failedItems: BulkConflictItem[] = []
      const undoSnapshotsById = new Map<string, BulkUndoSnapshot>()
      for (const thread of eligible) {
        try {
          undoSnapshotsById.set(String(thread.id), {
            id: String(thread.id),
            status: String(thread.status || 'open'),
            is_archived: Boolean(thread.is_archived),
            priority: String(thread.priority || 'normal'),
            tags_json: Array.isArray(thread.tags_json) ? [...thread.tags_json] : [],
            unread_count: Math.max(0, Number(thread.unread_count || 0)),
          })
          let current = thread
          for (const action of Array.isArray(command.actions) ? command.actions : []) {
            const type = String(action?.type || '')
            if (type === 'mark_read') {
              current = await markCommunicationThreadRead(current.id, { mark_thread: true })
              continue
            }
            if (type === 'archive' || type === 'unarchive') {
              current = await patchCommunicationThread(current.id, { is_archived: type === 'archive' })
              continue
            }
            if (type === 'priority_high' || type === 'priority_normal') {
              current = await patchCommunicationThread(current.id, { priority: type === 'priority_high' ? 'high' : 'normal' })
              continue
            }
            if (type === 'delete' || type === 'restore') {
              current = await patchCommunicationThread(current.id, { status: type === 'delete' ? 'deleted' : 'open' })
              continue
            }
            if (type === 'tag_add' || type === 'tag_remove' || type === 'move_folder') {
              const baseTags = (Array.isArray(current.tags_json) ? current.tags_json : [])
                .map((x) => String(x || '').trim())
                .filter(Boolean)
              let nextTags = [...baseTags]
              if (type === 'tag_add') {
                const value = String(action?.value || '').trim()
                if (value && !nextTags.includes(value)) nextTags.push(value)
              } else if (type === 'tag_remove') {
                const value = String(action?.value || '').trim()
                nextTags = value ? nextTags.filter((x) => x !== value) : nextTags
              } else {
                const value = String(action?.value || '').trim()
                nextTags = nextTags.filter((x) => !x.toLowerCase().startsWith('folder:'))
                if (value) nextTags.push(`folder:${value}`)
              }
              current = await patchCommunicationThread(current.id, { tags_json: nextTags })
              continue
            }
            skippedActions += 1
          }
          updatedById.set(String(current.id), current)
          successThreadIds.push(String(current.id))
        } catch (err: unknown) {
          const info = getFriendlyErrorInfo(err, t('app.communications_inbox_hub.bulk.apply_failed', { defaultValue: 'Failed to apply command template.' }), t)
          failedThreadIds.push(String(thread.id))
          const reason = info.detail || info.title || t('app.communications_inbox_hub.bulk.apply_failed', { defaultValue: 'Failed to apply command template.' })
          failedItems.push({ threadId: String(thread.id), reason })
          if (reason) failedReasons.push(reason)
        }
      }
      if (failedItems.length > 0) {
        setBulkConflictReport({
          commandId: command.id,
          commandLabel: command.label,
          createdAtMs: Date.now(),
          failed: failedItems,
        })
      } else {
        setBulkConflictReport(null)
      }

      if (updatedById.size > 0) {
        setThreads((prev) => prev.map((row) => updatedById.get(String(row.id)) || row))
      }
      const byChannel = new Map<string, string[]>()
      for (const th of eligible) {
        if (!successThreadIds.includes(String(th.id))) continue
        const ch = String(th.channel || '').toLowerCase()
        if (!ch) continue
        byChannel.set(ch, [...(byChannel.get(ch) || []), String(th.id)])
      }
      let auditCreated = 0
      const batchId = `bulk_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      for (const [channel, ids] of byChannel) {
        const undoByThreadId: Record<string, BulkUndoSnapshot> = {}
        for (const id of ids) {
          const snap = undoSnapshotsById.get(String(id))
          if (snap) undoByThreadId[String(id)] = snap
        }
        const res = await createCommunicationCommandAuditBatch({
          channel,
          thread_ids: ids,
          command_id: command.id,
          command_label: command.label,
          actions_json: command.actions as Array<Record<string, any>>,
          payload: {
            bulk_batch_id: batchId,
            undo_snapshots_by_thread_id: undoByThreadId,
            undo_expires_at: new Date(Date.now() + 60000).toISOString(),
          },
        })
        auditCreated += Number(res?.created || 0)
      }
      if (successThreadIds.length > 0) {
        setSelectedThreadIds((prev) => prev.filter((id) => !successThreadIds.includes(id)))
        const snapshots = successThreadIds
          .map((id) => undoSnapshotsById.get(id))
          .filter((x): x is BulkUndoSnapshot => Boolean(x))
        if (snapshots.length > 0) {
          setLastBulkUndo({
            commandLabel: command.label,
            expiresAtMs: Date.now() + 60000,
            snapshots,
            auditBatchId: batchId,
          })
        }
      }
      if (successThreadIds.length > 0 && failedThreadIds.length === 0) {
        notify({
          title: t('app.communications_inbox_hub.bulk.applied', {
            defaultValue: 'Applied "{label}" to {count} threads.',
            values: { label: command.label, count: successThreadIds.length },
          }),
          description:
            skippedActions > 0
              ? t('app.communications_inbox_hub.bulk.applied_note', {
                  defaultValue: 'Audit rows: {audit}. Skipped actions: {skipped}.',
                  values: { audit: auditCreated, skipped: skippedActions },
                })
              : t('app.communications_inbox_hub.bulk.applied_note_ok', {
                  defaultValue: 'Audit rows: {audit}.',
                  values: { audit: auditCreated },
                }),
          variant: 'success',
        })
      } else if (successThreadIds.length > 0) {
        notify({
          title: t('app.communications_inbox_hub.bulk.applied_partial', {
            defaultValue: 'Applied "{label}" to {ok}/{total} threads.',
            values: { label: command.label, ok: successThreadIds.length, total: eligible.length },
          }),
          description: t('app.communications_inbox_hub.bulk.applied_partial_note', {
            defaultValue: 'Failed: {failed}. Audit rows: {audit}. Skipped actions: {skipped}.',
            values: { failed: failedThreadIds.length, audit: auditCreated, skipped: skippedActions },
          }),
          variant: 'warning',
        })
      } else {
        notify({
          title: t('app.communications_inbox_hub.bulk.apply_failed_all', { defaultValue: 'Could not apply command to selected threads.' }),
          description: failedReasons[0] || t('app.communications_inbox_hub.bulk.apply_failed', { defaultValue: 'Failed to apply command template.' }),
          variant: 'error',
        })
      }
    } catch (err: unknown) {
      notify({
        title: t('app.communications_inbox_hub.bulk.apply_failed', { defaultValue: 'Failed to apply command template.' }),
        description: getFriendlyErrorInfo(err, t('app.communications_inbox_hub.bulk.apply_failed', { defaultValue: 'Failed to apply command template.' }), t).detail,
        variant: 'error',
      })
    } finally {
      setApplyingCommand(false)
    }
  }

  const revertLastBulk = async () => {
    if (!lastBulkUndo || applyingCommand) return
    if (lastBulkUndo.expiresAtMs <= Date.now()) {
      setLastBulkUndo(null)
      return
    }
    setApplyingCommand(true)
    try {
      const updated = new Map<string, CommunicationThread>()
      let ok = 0
      let failed = 0
      for (const snap of lastBulkUndo.snapshots) {
        try {
          const row = await patchCommunicationThread(snap.id, {
            status: snap.status,
            is_archived: snap.is_archived,
            priority: snap.priority,
            tags_json: snap.tags_json,
            unread_count: snap.unread_count,
          })
          updated.set(String(row.id), row)
          ok += 1
        } catch {
          failed += 1
        }
      }
      if (updated.size > 0) {
        setThreads((prev) => prev.map((row) => updated.get(String(row.id)) || row))
      }
      if (ok > 0 && failed === 0) {
        notify({
          title: t('app.communications_inbox_hub.bulk.reverted', {
            defaultValue: 'Reverted last bulk ({count} threads).',
            values: { count: ok },
          }),
          variant: 'success',
        })
      } else if (ok > 0) {
        notify({
          title: t('app.communications_inbox_hub.bulk.reverted_partial', {
            defaultValue: 'Reverted {ok}/{total} threads.',
            values: { ok, total: lastBulkUndo.snapshots.length },
          }),
          variant: 'warning',
        })
      } else {
        notify({
          title: t('app.communications_inbox_hub.bulk.revert_failed', {
            defaultValue: 'Failed to revert last bulk.',
          }),
          variant: 'error',
        })
      }
    } finally {
      setLastBulkUndo(null)
      setApplyingCommand(false)
    }
  }

  const retryFailedOnly = async () => {
    if (!bulkConflictReport || applyingCommand) return
    if (bulkConflictReport.commandId !== selectedCommandId) {
      setSelectedCommandId(bulkConflictReport.commandId)
    }
    const retryIds = failedVisibleThreadIds
    if (retryIds.length === 0) {
      notify({
        title: t('app.communications_inbox_hub.bulk.retry_no_visible', {
          defaultValue: 'No failed threads are visible in current filters.',
        }),
        variant: 'warning',
      })
      return
    }
    setSelectedThreadIds(retryIds)
    window.setTimeout(() => {
      void applyCommandTemplateBulk()
    }, 0)
  }

  const showLoading = accessLoading || loading

  return (
    <PageShell className="bg-slate-50">
      <PageShellHeader>
        <PageHeader
          title={t('app.communications_inbox_hub.title')}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void load()}
              disabled={showLoading}
            >
              {showLoading ? t('app.communications_inbox_hub.loading') : t('app.communications_inbox_hub.retry')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {oauthRedirectNotice && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
            <div className="font-medium">
              {t('app.communications.email.oauth_redirect_title')}
            </div>
            <p className="mt-1 text-xs text-emerald-900/90">
              {t('app.communications.email.oauth_redirect_body')}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Link to={CRM_APP_PATHS.settingsEmail} className="btn-primary btn-xs">
                {t('app.communications.email.oauth_redirect_open_setup')}
              </Link>
              <button type="button" className="btn-secondary btn-xs" onClick={() => setOauthRedirectNotice(false)}>
                {t('common.actions.dismiss')}
              </button>
            </div>
          </div>
        )}

        {pollErrors.length > 0 && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-950">
            <div className="font-medium">
              {t('app.communications.email.poll_error_title', { defaultValue: 'Не удалось обновить входящую почту' })}
            </div>
            <p className="mt-1 text-xs text-rose-900/90">{pollErrors[pollErrors.length - 1]}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Link to={CRM_APP_PATHS.settingsEmail} className="btn-primary btn-xs">
                {t('app.communications.email.oauth_redirect_open_setup', { defaultValue: 'Открыть настройки почты' })}
              </Link>
              <button type="button" className="btn-secondary btn-xs" onClick={() => void fetchInboundNow()}>
                {t('common.actions.retry', { defaultValue: 'Повторить' })}
              </button>
            </div>
          </div>
        )}

        {!commSetup.loading && !commSetup.isComplete && anyChannel && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div className="font-medium">{t('app.communications.setup.banner_incomplete')}</div>
            <div className="mt-2">
              <Link to={CRM_APP_PATHS.settingsIntegrations} className="btn-secondary btn-xs">
                {t('app.nav.items.settings_integrations')}
              </Link>
            </div>
          </div>
        )}

        {!commSetup.loading && commSetup.isComplete && effectiveChannel === 'email' && serverIncomingEnabled === false && hasEmail && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div className="font-medium">
              {t('app.communications.email.incoming_disabled_title')}
            </div>
            <p className="mt-1 text-xs text-amber-950/90">
              {t('app.communications.email.incoming_disabled_body_inbox')}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {canPatchCommunicationsSettings(me?.role) && (
                <button type="button" className="btn-primary btn-xs disabled:opacity-50" disabled={enablingIncoming} onClick={() => void enableServerIncoming()}>
                  {enablingIncoming
                    ? t('common.loading')
                    : t('app.communications.email.incoming_enable_cta')}
                </button>
              )}
              <Link to={CRM_APP_PATHS.settingsIntegrations} className="btn-secondary btn-xs">
                {t('app.nav.items.settings_integrations')}
              </Link>
            </div>
          </div>
        )}

        {hasMessages && hasEmail && anyChannel && (
          <Toolbar>
          <div className="flex flex-wrap gap-1">
            {(['all', 'messages', 'email'] as const).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setChannelTab(c)}
                className={clsx(
                  'btn-secondary btn-sm',
                  effectiveChannel === c && 'border-brand-600 bg-brand-50 text-brand-800',
                )}
              >
                {c === 'all' && t('app.communications_inbox_hub.channel_all')}
                {c === 'messages' && t('app.communications_inbox_hub.channel_messages')}
                {c === 'email' && t('app.communications_inbox_hub.channel_email')}
              </button>
            ))}
          </div>
          </Toolbar>
        )}

        {showLoading && <p className="text-sm text-slate-500">{t('app.communications_inbox_hub.loading')}</p>}

        {!showLoading && error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-800">
            <p className="font-medium">{error.title}</p>
            {error.detail ? <p className="mt-1 text-xs text-rose-900/90">{error.detail}</p> : null}
            <p className="mt-2 text-xs text-rose-800/85">{error.hint}</p>
            <button type="button" className="btn-secondary btn-sm mt-3" onClick={() => void load()}>
              {t('app.communications_inbox_hub.retry')}
            </button>
          </div>
        )}

        {!showLoading && !error && anyChannel && (
          <div className={clsx(effectiveChannel === 'email' && hasEmail && 'flex flex-col gap-4 lg:flex-row lg:items-start')}>
            {effectiveChannel === 'email' && hasEmail && (
              <div className="w-full shrink-0 lg:w-64">
                <InboxEmailFolderRail threads={threads} activeFolder={listQuery.folder} onFolderChange={onEmailFolderChange} />
              </div>
            )}
            <div className="min-w-0 flex-1 space-y-3">
              {listQuery.candidateId ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-blue-200 bg-blue-50/90 px-3 py-2 text-sm text-blue-950">
                  <span>{t('app.communications_inbox_hub.scoped_candidate_hint')}</span>
                  <Link
                    to={`${CRM_APP_PATHS.inbox}${inboxContextQueryString({ ...listQueryForLinks, candidateId: '' })}`}
                    className="font-medium text-brand-700 hover:underline"
                  >
                    {t('app.communications_inbox_hub.scoped_candidate_clear')}
                  </Link>
                </div>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={qDraft}
                  onChange={(e) => setQDraft(e.target.value)}
                  className="input min-w-[12rem] flex-1 py-2 text-sm"
                  placeholder={t('app.communications_inbox_hub.search_placeholder')}
                />
                {effectiveChannel === 'email' && hasEmail && (
                  <button
                    type="button"
                    onClick={() => void fetchInboundNow()}
                    disabled={pollBusy}
                    className="inline-flex shrink-0 items-center justify-center rounded-lg border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                    title={t('app.communications.email.sync.title')}
                    aria-label={t('app.communications.email.sync.title')}
                  >
                    <IconRefresh size={18} stroke={1.75} className={pollBusy ? 'animate-spin' : ''} />
                  </button>
                )}
              </div>

              {effectiveChannel === 'email' && hasEmail && (
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    onClick={toggleAssignedToMe}
                    disabled={!String(me?.id || '').trim()}
                    className={clsx(
                      'btn-secondary btn-xs disabled:opacity-40',
                      listQuery.assignedToMe && 'border-brand-600 bg-brand-50 text-brand-900',
                    )}
                  >
                    {t('app.communications.email.filters.assigned_to_me')}
                  </button>
                  <button
                    type="button"
                    onClick={toggleHasAssignee}
                    className={clsx(
                      'btn-secondary btn-xs',
                      listQuery.hasAssignee && 'border-slate-700 bg-slate-100 text-slate-900',
                    )}
                  >
                    {t('app.communications.email.filters.has_assignee')}
                  </button>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
                <select
                  className="input min-w-[12rem] py-2 text-sm"
                  value={selectedCommandId}
                  onChange={(e) => setSelectedCommandId(e.target.value)}
                >
                  <option value="">
                    {t('app.communications_inbox_hub.bulk.pick_command', { defaultValue: 'Bulk command template...' })}
                  </option>
                  {commandTemplates
                    .filter((cmd) => cmd.enabled !== false)
                    .map((cmd) => (
                      <option key={cmd.id} value={cmd.id}>
                        {cmd.label}
                      </option>
                    ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary btn-xs disabled:opacity-50"
                  onClick={() => void applyCommandTemplateBulk()}
                  disabled={applyingCommand || !selectedCommandId || selectedEligibleThreads.length === 0}
                >
                  {applyingCommand
                    ? t('common.loading')
                    : t('app.communications_inbox_hub.bulk.apply_selected', {
                        defaultValue: 'Apply to selected ({count})',
                        values: { count: selectedEligibleThreads.length },
                      })}
                </button>
                {selectedThreadIds.length > 0 && (
                  <button
                    type="button"
                    className="btn-secondary btn-xs"
                    onClick={() => setSelectedThreadIds([])}
                  >
                    {t('app.communications_inbox_hub.bulk.clear_selection', { defaultValue: 'Clear selection' })}
                  </button>
                )}
              </div>
              {selectedCommand && selectedVisibleCount > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span>
                      {t('app.communications_inbox_hub.bulk.preview_selected', {
                        defaultValue: 'Selected: {count}',
                        values: { count: selectedThreadsForBulk.length },
                      })}
                    </span>
                    <span>
                      {t('app.communications_inbox_hub.bulk.preview_eligible', {
                        defaultValue: 'Eligible: {count}',
                        values: { count: selectedEligibleThreads.length },
                      })}
                    </span>
                    {selectedMismatchCount > 0 && (
                      <span className="text-amber-700">
                        {t('app.communications_inbox_hub.bulk.preview_mismatch', {
                          defaultValue: 'Skipped by channel target: {count}',
                          values: { count: selectedMismatchCount },
                        })}
                      </span>
                    )}
                    <span className="text-slate-500">
                      {t('app.communications_inbox_hub.bulk.preview_target', {
                        defaultValue: 'Target: {target}',
                        values: { target: selectedCommand.target },
                      })}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(Array.isArray(selectedCommand.actions) ? selectedCommand.actions : []).map((action, idx) => (
                      <span key={`${selectedCommand.id}_action_${idx}`} className="rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px]">
                        {bulkActionPreviewLabel(String(action?.type || ''), String(action?.value || '').trim() || null)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {lastBulkUndo && lastBulkUndo.expiresAtMs > Date.now() && (
                <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  <span>
                    {t('app.communications_inbox_hub.bulk.undo_hint', {
                      defaultValue: 'Last bulk: {label}. You can revert recent changes.',
                      values: { label: lastBulkUndo.commandLabel },
                    })}
                  </span>
                  <button
                    type="button"
                    className="btn-secondary btn-xs border-amber-300 bg-white text-amber-900 hover:bg-amber-100"
                    disabled={applyingCommand}
                    onClick={() => void revertLastBulk()}
                  >
                    {t('app.communications_inbox_hub.bulk.undo_action', { defaultValue: 'Revert last bulk' })}
                  </button>
                </div>
              )}
              {bulkConflictReport && bulkConflictReport.failed.length > 0 && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900">
                  <div className="flex flex-wrap items-center gap-2">
                    <span>
                      {t('app.communications_inbox_hub.bulk.conflicts_title', {
                        defaultValue: 'Last run "{label}": {count} failed.',
                        values: { label: bulkConflictReport.commandLabel, count: bulkConflictReport.failed.length },
                      })}
                    </span>
                    <button
                      type="button"
                      className="btn-secondary btn-xs border-rose-300 bg-white text-rose-900 hover:bg-rose-100"
                      onClick={() => void retryFailedOnly()}
                      disabled={applyingCommand}
                    >
                      {t('app.communications_inbox_hub.bulk.retry_failed', { defaultValue: 'Retry failed only' })}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-xs"
                      onClick={() => setBulkConflictReport(null)}
                    >
                      {t('common.actions.dismiss', { defaultValue: 'Dismiss' })}
                    </button>
                  </div>
                  <ul className="mt-2 max-h-32 space-y-1 overflow-auto pr-1">
                    {bulkConflictReport.failed.map((item) => (
                      <li key={`${item.threadId}_${item.reason}`} className="rounded border border-rose-200 bg-white px-2 py-1 text-[11px]">
                        <span className="font-mono text-rose-800">{item.threadId}</span>
                        <span className="text-rose-700"> - {item.reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <InboxUnifiedThreadList
                threads={listForUi}
                hubFilter={hubFilter}
                onHubFilterChange={setHubFilter}
                hasMessages={effectiveChannel === 'email' ? false : hasMessages}
                hasEmail={effectiveChannel === 'messages' ? false : hasEmail}
                threadLinkPrefix={CRM_APP_PATHS.inboxThreadsBase}
                linkedCandidateId={listQuery.candidateId || undefined}
                hideSectionHeading
                listQuery={listQueryForLinks}
                selectedThreadIds={selectedThreadIds}
                onToggleThreadSelection={toggleSingleThread}
                onToggleAllVisibleSelection={toggleVisibleThreads}
              />
            </div>
          </div>
        )}

        {!showLoading && !error && !anyChannel && (
          <p className="mt-2 max-w-2xl text-sm text-slate-600">{t('app.communications_inbox_hub.unified_none_enabled')}</p>
        )}

        {!showLoading && !error && anyChannel && (
          <div>
            <Link
              to={CRM_APP_PATHS.slaIncidents}
              className="text-xs font-medium text-rose-700 hover:text-rose-800"
            >
              <span className="inline-flex items-center gap-1">
                <IconBell size={14} stroke={1.75} />
                {t('app.communications_inbox_hub.cta_sla')}
              </span>
            </Link>
          </div>
        )}
      </div>
    </PageShell>
  )
}
