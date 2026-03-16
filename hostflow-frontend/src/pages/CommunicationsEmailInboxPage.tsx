import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  createCommunicationCommandAuditBatch,
  getCommunicationsSettings,
  runCommunicationEmailPollWorker,
  type CommunicationCommandAction,
  type CommunicationCommandTemplate,
  createCommunicationMessage,
  dispatchCommunicationMessage,
  listCommunicationThreads,
  markCommunicationThreadRead,
  patchCommunicationThread,
  type CommunicationThread,
} from '../api/communications'
import { useI18n } from '../i18n'
import { useCommunicationsSetupStatus } from '../hooks/useCommunicationsSetupStatus'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'

const LS_KEY = 'hf:email-workspace:v2'
const LS_POLL_KEY = 'hf:email-workspace:last-poll-at'
const FOLDER_TAG_PREFIX = 'folder:'

type SystemFolder = 'inbox' | 'unread' | 'sent' | 'assigned' | 'archive' | 'trash' | 'all'
type FolderKey = SystemFolder | `custom:${string}`
type BulkCommand = 'mark_read' | 'archive' | 'unarchive' | 'delete' | 'restore' | 'priority_high' | 'priority_normal'

function errorTextFrom(err: any, fallback: string) {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const msg = d.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (d && typeof d === 'object') {
    if (typeof d.msg === 'string') return d.msg
    try {
      return JSON.stringify(d)
    } catch {
      // ignore
    }
  }
  return err?.message || fallback
}

function dt(value?: string | null): number {
  if (!value) return 0
  const t = Date.parse(value)
  return Number.isNaN(t) ? 0 : t
}

function formatDateTime(value?: string | null): string {
  const ts = dt(value)
  if (!ts) return '—'
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(ts))
}

function nowIso(): string {
  return new Date().toISOString()
}

function shouldAutoPoll(lastPollAt: string | null, minMinutes: number): boolean {
  if (!lastPollAt) return true
  const last = dt(lastPollAt)
  if (!last) return true
  return Date.now() - last > minMinutes * 60_000
}

function tagsOf(th: CommunicationThread): string[] {
  return (Array.isArray(th.tags_json) ? th.tags_json : []).map((x) => String(x || '').trim()).filter(Boolean)
}

function customFolderNameOf(th: CommunicationThread): string | null {
  const tag = tagsOf(th).find((x) => x.toLowerCase().startsWith(FOLDER_TAG_PREFIX))
  if (!tag) return null
  const raw = tag.slice(FOLDER_TAG_PREFIX.length).trim()
  return raw || null
}

function threadInFolder(th: CommunicationThread, folder: FolderKey): boolean {
  if (folder === 'all') return true
  if (folder === 'trash') return String(th.status || '').toLowerCase() === 'deleted'
  if (folder === 'archive') return Boolean(th.is_archived) && String(th.status || '').toLowerCase() !== 'deleted'
  if (folder === 'unread') return Number(th.unread_count || 0) > 0 && !th.is_archived
  if (folder === 'sent') return (Boolean(th.last_outbound_at) || String(th.direction_hint || '') === 'outbound') && !th.is_archived
  if (folder === 'assigned') return Boolean(String(th.assignee_id || '').trim()) && !th.is_archived
  if (folder === 'inbox') return !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted' && !customFolderNameOf(th)
  if (folder.startsWith('custom:')) {
    const folderName = folder.slice('custom:'.length)
    return customFolderNameOf(th) === folderName && !th.is_archived
  }
  return false
}

function titleOf(th: CommunicationThread): string {
  return String(th.subject || '').trim() || String(th.last_message_preview || '').trim() || th.id
}

export default function CommunicationsEmailInboxPage() {
  const { t } = useI18n()
  const commSetup = useCommunicationsSetupStatus()

  const saved = useMemo(() => {
    try {
      const raw = window.localStorage.getItem(LS_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }, [])

  const savedLastPollAt = useMemo(() => {
    try {
      const raw = window.localStorage.getItem(LS_POLL_KEY)
      return raw ? String(raw) : null
    } catch {
      return null
    }
  }, [])

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [folder, setFolder] = useState<FolderKey>((saved.folder as FolderKey) || 'inbox')
  const [q, setQ] = useState(String(saved.q || ''))
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const [newFolderName, setNewFolderName] = useState('')
  const [customFolders, setCustomFolders] = useState<string[]>(Array.isArray(saved.customFolders) ? saved.customFolders : [])

  const [bulkCommand, setBulkCommand] = useState<BulkCommand>('archive')
  const [commandTemplates, setCommandTemplates] = useState<CommunicationCommandTemplate[]>([])
  const [commandId, setCommandId] = useState('')
  const [moveTarget, setMoveTarget] = useState<FolderKey>('inbox')
  const [tagInput, setTagInput] = useState('')

  const [composeRecipient, setComposeRecipient] = useState('')
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')
  const [isMobile, setIsMobile] = useState(false)
  const [mobilePane, setMobilePane] = useState<'list' | 'preview'>('list')
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [pollBusy, setPollBusy] = useState(false)
  const [pollNote, setPollNote] = useState<string | null>(null)
  const [pollDetails, setPollDetails] = useState<Array<Record<string, any>>>([])
  const [lastPollAt, setLastPollAt] = useState<string | null>(savedLastPollAt)
  const pollInFlightRef = useRef(false)
  const mountedRef = useRef(true)

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    setErrorText(null)
    try {
      const th = await listCommunicationThreads({ limit: 300, channel: 'email', includeArchived: true })
      setThreads(Array.isArray(th.items) ? th.items : [])
      const cfg = await getCommunicationsSettings().catch(() => null)
      const templates = Array.isArray(cfg?.commands?.items)
        ? cfg!.commands.items.filter((cmd) => cmd.enabled && (cmd.target === 'email' || cmd.target === 'both'))
        : []
      setCommandTemplates(templates)
      if (templates.length && !commandId) setCommandId(templates[0].id)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load email inbox'))
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    mountedRef.current = true
    void load()
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void load(true)
    }, 15000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(max-width: 1023px)')
    const apply = () => {
      const nextMobile = mq.matches
      setIsMobile(nextMobile)
      if (!nextMobile) setMobilePane('list')
    }
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_KEY, JSON.stringify({ folder, q, customFolders }))
    } catch {
      // ignore storage errors
    }
  }, [customFolders, folder, q])

  useEffect(() => {
    try {
      if (lastPollAt) window.localStorage.setItem(LS_POLL_KEY, lastPollAt)
    } catch {
      // ignore
    }
  }, [lastPollAt])

  const allCustomFolders = useMemo(() => {
    const fromThreads = threads.map((th) => customFolderNameOf(th)).filter(Boolean) as string[]
    return Array.from(new Set([...customFolders, ...fromThreads])).sort((a, b) => a.localeCompare(b))
  }, [customFolders, threads])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return threads
      .filter((th) => threadInFolder(th, folder))
      .filter((th) => {
        if (!needle) return true
        const hay = [titleOf(th), th.last_message_preview, th.id, th.assignee_id, th.status, tagsOf(th).join(' ')].join(' ').toLowerCase()
        return hay.includes(needle)
      })
      .sort((a, b) => {
        const ak = Math.max(dt(a.last_message_at), dt(a.updated_at))
        const bk = Math.max(dt(b.last_message_at), dt(b.updated_at))
        return bk - ak
      })
  }, [folder, q, threads])

  const folderItems = useMemo(() => {
    const system: Array<{ key: FolderKey; label: string; count: number }> = [
      { key: 'inbox', label: 'Inbox', count: threads.filter((x) => threadInFolder(x, 'inbox')).length },
      { key: 'unread', label: 'Unread', count: threads.filter((x) => threadInFolder(x, 'unread')).length },
      { key: 'sent', label: 'Sent', count: threads.filter((x) => threadInFolder(x, 'sent')).length },
      { key: 'assigned', label: 'Assigned', count: threads.filter((x) => threadInFolder(x, 'assigned')).length },
      { key: 'archive', label: 'Archive', count: threads.filter((x) => threadInFolder(x, 'archive')).length },
      { key: 'trash', label: 'Deleted', count: threads.filter((x) => threadInFolder(x, 'trash')).length },
      { key: 'all', label: 'All', count: threads.length },
    ]
    const custom = allCustomFolders.map((name) => ({
      key: `custom:${name}` as FolderKey,
      label: name,
      count: threads.filter((x) => threadInFolder(x, `custom:${name}`)).length,
    }))
    return [...system, ...custom]
  }, [allCustomFolders, threads])

  useEffect(() => {
    if (!filtered.length) {
      setSelectedThreadId(null)
      return
    }
    if (!selectedThreadId || !filtered.some((x) => x.id === selectedThreadId)) {
      setSelectedThreadId(filtered[0].id)
    }
  }, [filtered, selectedThreadId])

  useEffect(() => {
    setSelectedIds((prev) => prev.filter((id) => filtered.some((x) => x.id === id)))
  }, [filtered])

  const selectedThread = useMemo(
    () => filtered.find((x) => x.id === selectedThreadId) || null,
    [filtered, selectedThreadId],
  )

  useEffect(() => {
    if (!selectedThread) return
    setComposeSubject((prev) => prev || `Re: ${selectedThread.subject || titleOf(selectedThread)}`)
  }, [selectedThread])

  useEffect(() => {
    if (!isMobile || !selectedThreadId) return
    setMobilePane('preview')
  }, [isMobile, selectedThreadId])

  const applyToSelected = async (worker: (id: string) => Promise<void>) => {
    if (!selectedIds.length) return
    setBusy(true)
    setErrorText(null)
    try {
      await Promise.all(selectedIds.map((id) => worker(id)))
      await load()
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Bulk action failed'))
    } finally {
      setBusy(false)
    }
  }

  const runBulkCommand = async () => {
    if (!selectedIds.length) return
    if (bulkCommand === 'mark_read') return applyToSelected((id) => markCommunicationThreadRead(id, { mark_thread: true }).then(() => {}))
    if (bulkCommand === 'archive') return applyToSelected((id) => patchCommunicationThread(id, { is_archived: true, status: 'archived' }).then(() => {}))
    if (bulkCommand === 'unarchive') return applyToSelected((id) => patchCommunicationThread(id, { is_archived: false, status: 'open' }).then(() => {}))
    if (bulkCommand === 'delete') return applyToSelected((id) => patchCommunicationThread(id, { is_archived: true, status: 'deleted' }).then(() => {}))
    if (bulkCommand === 'restore') return applyToSelected((id) => patchCommunicationThread(id, { is_archived: false, status: 'open' }).then(() => {}))
    if (bulkCommand === 'priority_high') return applyToSelected((id) => patchCommunicationThread(id, { priority: 'high' }).then(() => {}))
    if (bulkCommand === 'priority_normal') return applyToSelected((id) => patchCommunicationThread(id, { priority: 'normal' }).then(() => {}))
  }

  const applyActionToThread = async (id: string, action: CommunicationCommandAction) => {
    if (action.type === 'mark_read') {
      await markCommunicationThreadRead(id, { mark_thread: true })
      return
    }
    if (action.type === 'archive') {
      await patchCommunicationThread(id, { is_archived: true, status: 'archived' })
      return
    }
    if (action.type === 'unarchive') {
      await patchCommunicationThread(id, { is_archived: false, status: 'open' })
      return
    }
    if (action.type === 'delete') {
      await patchCommunicationThread(id, { is_archived: true, status: 'deleted' })
      return
    }
    if (action.type === 'restore') {
      await patchCommunicationThread(id, { is_archived: false, status: 'open' })
      return
    }
    if (action.type === 'priority_high') {
      await patchCommunicationThread(id, { priority: 'high' })
      return
    }
    if (action.type === 'priority_normal') {
      await patchCommunicationThread(id, { priority: 'normal' })
      return
    }
    if (action.type === 'tag_add' || action.type === 'tag_remove' || action.type === 'move_folder') {
      const current = threads.find((x) => x.id === id)
      const cleanTags = (current ? tagsOf(current) : []).filter((x) => !x.toLowerCase().startsWith(FOLDER_TAG_PREFIX))
      const tags = new Set(cleanTags)
      const value = String(action.value || '').trim()
      if (action.type === 'tag_add' && value) {
        tags.add(value)
        await patchCommunicationThread(id, { tags_json: Array.from(tags) })
        return
      }
      if (action.type === 'tag_remove' && value) {
        tags.delete(value)
        await patchCommunicationThread(id, { tags_json: Array.from(tags) })
        return
      }
      if (action.type === 'move_folder') {
        if (value && value !== 'inbox' && value !== 'archive' && value !== 'trash') {
          tags.add(`${FOLDER_TAG_PREFIX}${value}`)
          await patchCommunicationThread(id, { tags_json: Array.from(tags), is_archived: false, status: 'open' })
          return
        }
        if (value === 'archive') {
          await patchCommunicationThread(id, { tags_json: Array.from(tags), is_archived: true, status: 'archived' })
          return
        }
        if (value === 'trash') {
          await patchCommunicationThread(id, { tags_json: Array.from(tags), is_archived: true, status: 'deleted' })
          return
        }
        await patchCommunicationThread(id, { tags_json: Array.from(tags), is_archived: false, status: 'open' })
      }
    }
  }

  const runCommandTemplate = async () => {
    const cmd = commandTemplates.find((x) => x.id === commandId)
    if (!cmd || !selectedIds.length) return
    const runThreadIds = [...selectedIds]
    const startedAt = new Date().toISOString()
    await applyToSelected(async (id) => {
      for (const action of cmd.actions || []) {
        await applyActionToThread(id, action)
      }
    })
    try {
      await createCommunicationCommandAuditBatch({
        channel: 'email',
        thread_ids: runThreadIds,
        command_id: cmd.id,
        command_label: cmd.label,
        actions_json: (cmd.actions || []).map((a) => ({ type: a.type, value: a.value ?? null })),
        executed_at: startedAt,
      })
    } catch {
      // command actions already applied; audit failure should not block workspace
    }
  }

  const moveSelectedToFolder = async () => {
    if (!selectedIds.length) return
    const target = moveTarget
    await applyToSelected(async (id) => {
      const current = threads.find((x) => x.id === id)
      const tags = current ? tagsOf(current).filter((x) => !x.toLowerCase().startsWith(FOLDER_TAG_PREFIX)) : []
      if (target.startsWith('custom:')) {
        tags.push(`${FOLDER_TAG_PREFIX}${target.slice('custom:'.length)}`)
        await patchCommunicationThread(id, { tags_json: Array.from(new Set(tags)), is_archived: false, status: 'open' })
        return
      }
      if (target === 'archive') {
        await patchCommunicationThread(id, { tags_json: tags, is_archived: true, status: 'archived' })
        return
      }
      if (target === 'trash') {
        await patchCommunicationThread(id, { tags_json: tags, is_archived: true, status: 'deleted' })
        return
      }
      await patchCommunicationThread(id, { tags_json: tags, is_archived: false, status: 'open' })
    })
  }

  const mutateTag = async (mode: 'add' | 'remove') => {
    const tag = tagInput.trim()
    if (!tag || !selectedIds.length) return
    await applyToSelected(async (id) => {
      const current = threads.find((x) => x.id === id)
      const tags = new Set(current ? tagsOf(current) : [])
      if (mode === 'add') tags.add(tag)
      else tags.delete(tag)
      await patchCommunicationThread(id, { tags_json: Array.from(tags) })
    })
  }

  const createFolder = () => {
    const name = newFolderName.trim()
    if (!name) return
    if (!customFolders.includes(name)) setCustomFolders((prev) => [...prev, name])
    setNewFolderName('')
    setMoveTarget(`custom:${name}`)
  }

  const sendReplyOrForward = async (mode: 'reply' | 'forward') => {
    if (!selectedThread || !composeBody.trim()) return
    setBusy(true)
    setErrorText(null)
    try {
      const subject = composeSubject.trim() || `${mode === 'forward' ? 'Fwd:' : 'Re:'} ${selectedThread.subject || titleOf(selectedThread)}`
      const msg = await createCommunicationMessage(selectedThread.id, {
        direction: 'outbound',
        message_type: 'email',
        subject,
        body_text: composeBody.trim(),
        recipient_address: composeRecipient.trim() || undefined,
        delivery_status: 'queued',
      })
      await dispatchCommunicationMessage(msg.id, { mark_delivered: true })
      setComposeBody('')
      if (mode === 'forward') setComposeRecipient('')
      await load()
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to send message'))
    } finally {
      setBusy(false)
    }
  }

  const fetchInboundNow = async (opts?: { reason?: string; silent?: boolean }) => {
    if (pollInFlightRef.current) return
    pollInFlightRef.current = true
    setPollBusy(true)
    setPollNote(null)
    setPollDetails([])
    setErrorText(null)
    try {
      const res = await runCommunicationEmailPollWorker({ limit_per_account: 50 })
      if (!mountedRef.current) return
      setPollNote(
        `${t('app.communications.email.poll.summary', { defaultValue: 'Fetched' })}: ${Number(res.ingested_messages || 0)}, ${t(
          'app.communications.email.poll.new_threads',
          { defaultValue: 'new threads' },
        )}: ${Number(res.created_threads || 0)}, ${t('app.communications.email.poll.skipped', { defaultValue: 'skipped' })}: ${Number(
          res.skipped_messages || 0,
        )}${opts?.reason ? ` (${opts.reason})` : ''}`,
      )
      setPollDetails(Array.isArray(res.items) ? res.items : [])
      setLastPollAt(nowIso())
      await load(Boolean(opts?.silent))
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to fetch inbound email'))
    } finally {
      setPollBusy(false)
      pollInFlightRef.current = false
    }
  }

  // Auto-poll inbound email to reduce “missing inbound email” incidents (MOB-008/C2.1).
  useEffect(() => {
    if (loading) return
    if (pollBusy || busy) return
    if (commSetup.loading || !commSetup.isComplete) return
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    if (threads.length > 0) return
    if (!shouldAutoPoll(lastPollAt, 2)) return
    void fetchInboundNow({ reason: 'auto', silent: true })
  }, [busy, commSetup.isComplete, commSetup.loading, lastPollAt, loading, pollBusy, threads.length])

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (pollBusy || busy) return
      if (commSetup.loading || !commSetup.isComplete) return
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      if (!shouldAutoPoll(lastPollAt, 5)) return
      void fetchInboundNow({ reason: 'auto', silent: true })
    }, 60_000)
    return () => window.clearInterval(timer)
  }, [busy, commSetup.isComplete, commSetup.loading, lastPollAt, pollBusy])

  const openThread = (threadId: string) => {
    setSelectedThreadId(threadId)
    if (isMobile) setMobilePane('preview')
  }

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active="email" />
      {!commSetup.loading && !commSetup.isComplete && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="font-medium">
            {t('app.communications.setup.banner_incomplete', { defaultValue: 'Communications setup is not complete yet.' })}
          </div>
          <div className="mt-1 text-xs">
            {t('app.communications.setup.progress', { defaultValue: 'Setup progress' })}: {commSetup.doneCount}/5
          </div>
          <div className="mt-2">
            <Link to="/app/setup/communications" className="btn-secondary btn-xs">
              {t('app.nav.items.communications_setup', { defaultValue: 'Comms setup' })}
            </Link>
          </div>
        </div>
      )}

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.email_title', { defaultValue: 'Email Inbox' })}</h1>
          <p className="text-sm text-slate-500">Inbox workspace: folders, tags, commands, archive/delete, reply/forward.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="input"
            placeholder="Search subject, preview, tags, id..."
          />
          <button
            type="button"
            onClick={() => void load()}
            className="btn-secondary"
          >
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
          <button
            type="button"
            onClick={() => void fetchInboundNow()}
            disabled={pollBusy || busy}
            className="btn-secondary disabled:opacity-50"
          >
            {pollBusy
              ? t('app.communications.email.poll.loading', { defaultValue: 'Fetching…' })
              : t('app.communications.email.poll.cta', { defaultValue: 'Fetch incoming' })}
          </button>
          {!isMobile && (
            <>
              <button
                type="button"
                onClick={() => {
                  setFolder('all')
                  setQ('')
                  setSelectedIds([])
                }}
                className="btn-secondary"
              >
                Reset view
              </button>
              <Link to="/app/setup/communications" className="btn-secondary">
                {t('app.nav.items.communications_setup', { defaultValue: 'Comms setup' })}
              </Link>
            </>
          )}
        </div>
      </header>

      {(pollNote || lastPollAt) && (
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="space-y-0.5">
              {pollNote ? <div className="font-medium">{pollNote}</div> : null}
              <div className="text-xs text-slate-500">
                {t('app.communications.email.poll.last', { defaultValue: 'Last fetch' })}: {formatDateTime(lastPollAt)}
              </div>
            </div>
            <Link to="/app/setup/communications" className="btn-secondary btn-xs">
              {t('app.communications.email.poll.diagnostics', { defaultValue: 'Diagnostics' })}
            </Link>
          </div>
          {!!pollDetails.length && (
            <div className="mt-2 space-y-1 text-xs text-slate-600">
              {pollDetails.slice(0, 5).map((row, idx) => (
                <div key={`${row?.account_id || idx}`} className="flex flex-wrap items-center gap-2">
                  <span className="badge">{String(row?.provider || 'email')}</span>
                  <span className="font-medium">{String(row?.account_label || row?.account_id || 'account')}</span>
                  <span className={clsx('badge', String(row?.status || '').includes('error') ? 'badge-danger' : 'badge-secondary')}>
                    {String(row?.status || 'ok')}
                  </span>
                  {row?.error ? <span className="text-rose-700">{String(row.error)}</span> : null}
                </div>
              ))}
              {pollDetails.length > 5 ? (
                <div className="text-slate-500">{t('app.communications.email.poll.more_accounts', { defaultValue: 'More accounts…' })}</div>
              ) : null}
            </div>
          )}
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-3">
        <button
          type="button"
          onClick={() => setAdvancedOpen((prev) => !prev)}
          className="btn-secondary btn-sm"
        >
          {advancedOpen ? 'Hide filters & commands' : 'Show filters & commands'}
        </button>
        {advancedOpen && (
          <div className="mt-3 space-y-3">
            {isMobile && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500">Folder</span>
                <select value={folder} onChange={(e) => setFolder(e.target.value as FolderKey)} className="input">
                  {folderItems.map((item) => (
                    <option key={item.key} value={item.key}>{item.label} ({item.count})</option>
                  ))}
                </select>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase text-slate-500">Commands</span>
              <select
                value={bulkCommand}
                onChange={(e) => setBulkCommand(e.target.value as BulkCommand)}
                className="input"
              >
                <option value="mark_read">Mark read</option>
                <option value="archive">Archive</option>
                <option value="unarchive">Unarchive</option>
                <option value="delete">Delete</option>
                <option value="restore">Restore</option>
                <option value="priority_high">Priority high</option>
                <option value="priority_normal">Priority normal</option>
              </select>
              <button
                type="button"
                onClick={() => void runBulkCommand()}
                disabled={busy || selectedIds.length === 0}
                className="btn-secondary btn-sm disabled:opacity-50"
              >
                Run for selected ({selectedIds.length})
              </button>
              <select
                value={commandId}
                onChange={(e) => setCommandId(e.target.value)}
                className="input"
              >
                <option value="">Quick command…</option>
                {commandTemplates.map((cmd) => (
                  <option key={cmd.id} value={cmd.id}>{cmd.label}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void runCommandTemplate()}
                disabled={busy || !selectedIds.length || !commandId}
                className="btn-secondary btn-sm disabled:opacity-50"
              >
                Run template
              </button>
              <span className="ml-3 text-xs text-slate-500">Move to</span>
              <select
                value={moveTarget}
                onChange={(e) => setMoveTarget(e.target.value as FolderKey)}
                className="input"
              >
                <option value="inbox">Inbox</option>
                <option value="archive">Archive</option>
                <option value="trash">Deleted</option>
                {allCustomFolders.map((name) => (
                  <option key={name} value={`custom:${name}`}>{name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void moveSelectedToFolder()}
                disabled={busy || selectedIds.length === 0}
                className="btn-secondary btn-sm disabled:opacity-50"
              >
                Move
              </button>
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="tag"
                className="input ml-3"
              />
              <button type="button" onClick={() => void mutateTag('add')} disabled={busy || !selectedIds.length} className="btn-secondary btn-sm disabled:opacity-50">+Tag</button>
              <button type="button" onClick={() => void mutateTag('remove')} disabled={busy || !selectedIds.length} className="btn-secondary btn-sm disabled:opacity-50">-Tag</button>
            </div>
          </div>
        )}
      </section>

      {errorText && (
        <ErrorRecoveryBanner
          info={{
            title: errorText,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo="/app/settings/communications"
          secondaryLabel={t('admin.communications_sla.actions.all', { defaultValue: 'All communication settings' })}
          compact
        />
      )}
      <div className="grid gap-4 xl:grid-cols-[230px_minmax(420px,1fr)_minmax(360px,460px)]">
        <aside className={clsx('rounded-lg border border-slate-200 bg-white p-3', isMobile && 'hidden')}>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Folders</div>
          <div className="space-y-1">
            {folderItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setFolder(item.key)}
                className={clsx(
                  'btn-secondary w-full justify-between',
                  folder === item.key && 'border-brand-600 bg-brand-50 text-brand-800',
                )}
              >
                <span className="truncate">{item.label}</span>
                <span className="badge ml-2 bg-slate-100 text-slate-600">{item.count}</span>
              </button>
            ))}
          </div>
          <div className="mt-3 border-t border-slate-100 pt-3">
            <div className="mb-1 text-xs text-slate-500">New folder</div>
            <div className="flex gap-2">
              <input value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} className="input" />
              <button type="button" onClick={createFolder} className="btn-secondary btn-sm">Add</button>
            </div>
          </div>
        </aside>

        <section className={clsx('rounded-lg border border-slate-200 bg-white', isMobile && mobilePane === 'preview' && 'hidden')}>
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
            <span>Conversations</span>
            <label className="flex items-center gap-2 text-xs font-normal text-slate-500">
              <input
                type="checkbox"
                checked={filtered.length > 0 && selectedIds.length === filtered.length}
                onChange={(e) => setSelectedIds(e.target.checked ? filtered.map((x) => x.id) : [])}
              />
              Select all
            </label>
          </div>
          {loading && <div className="px-4 py-4 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
          {!loading && filtered.length === 0 && (
            <div className="px-4 py-6 text-sm text-slate-500">
              {threads.length > 0
                ? 'No items match current folder/search. Reset view to show all.'
                : t('app.communications.states.empty', { defaultValue: 'No activity yet' })}
            </div>
          )}
          {!loading && filtered.length > 0 && (
            <div className="max-h-[72vh] divide-y divide-slate-100 overflow-auto">
              {filtered.map((th) => (
                <div key={th.id} className={clsx('px-3 py-2', selectedThreadId === th.id && 'bg-brand-50')}>
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(th.id)}
                      onChange={(e) => setSelectedIds((prev) => e.target.checked ? [...new Set([...prev, th.id])] : prev.filter((x) => x !== th.id))}
                      className="mt-1"
                    />
                    <button type="button" onClick={() => openThread(th.id)} className="flex-1 text-left">
                      <div className="truncate text-sm font-medium text-slate-900">{titleOf(th)}</div>
                      <div className="mt-1 truncate text-xs text-slate-500">{th.last_message_preview || '—'}</div>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                        <span>Unread: {th.unread_count || 0}</span>
                        <span>Status: {th.status}</span>
                        <span>{formatDateTime(th.last_message_at || th.updated_at)}</span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {tagsOf(th).slice(0, 4).map((tag) => (
                          <span key={tag} className="badge bg-slate-100 text-slate-600">{tag}</span>
                        ))}
                      </div>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={clsx('rounded-lg border border-slate-200 bg-white', isMobile && mobilePane === 'list' && 'hidden')}>
          <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">
            <div className="flex items-center gap-2">
              {isMobile && (
                <button type="button" onClick={() => setMobilePane('list')} className="btn-secondary btn-xs">
                  Back
                </button>
              )}
              <span>Preview & Reply</span>
            </div>
          </div>
          {!selectedThread && (
            <div className="px-4 py-6 text-sm text-slate-500">Select a conversation to preview.</div>
          )}
          {selectedThread && (
            <div className="max-h-[72vh] space-y-3 overflow-auto px-4 py-4">
              <div>
                <div className="text-sm font-semibold text-slate-900">{titleOf(selectedThread)}</div>
                <div className="mt-1 text-xs text-slate-500">{selectedThread.last_message_preview || '—'}</div>
              </div>
              <div className="grid gap-2 text-xs text-slate-600">
                <div>Status: <strong>{selectedThread.status}</strong></div>
                <div>Assignee: <strong>{selectedThread.assignee_id || '—'}</strong></div>
                <div>Last activity: <strong>{formatDateTime(selectedThread.last_message_at || selectedThread.updated_at)}</strong></div>
                <div>Created: <strong>{formatDateTime(selectedThread.created_at)}</strong></div>
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <button type="button" onClick={() => void patchCommunicationThread(selectedThread.id, { is_archived: true, status: 'archived' }).then(load)} className="btn-secondary btn-xs">Archive</button>
                <button type="button" onClick={() => void patchCommunicationThread(selectedThread.id, { is_archived: true, status: 'deleted' }).then(load)} className="btn-danger btn-xs">Delete</button>
                <button type="button" onClick={() => void markCommunicationThreadRead(selectedThread.id, { mark_thread: true }).then(load)} className="btn-secondary btn-xs">Mark read</button>
                <Link
                  to={`/app/communications/threads/${selectedThread.id}`}
                  className="btn-primary btn-xs"
                >
                  {t('app.communications.actions.open_thread', { defaultValue: 'Open thread' })}
                </Link>
              </div>

              <div className="border-t border-slate-100 pt-3">
                <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Reply / Forward</div>
                <input
                  value={composeRecipient}
                  onChange={(e) => setComposeRecipient(e.target.value)}
                  className="input mb-2"
                  placeholder="Recipient email (optional if preconfigured)"
                />
                <input
                  value={composeSubject}
                  onChange={(e) => setComposeSubject(e.target.value)}
                  className="input mb-2"
                  placeholder="Subject"
                />
                <textarea
                  rows={6}
                  value={composeBody}
                  onChange={(e) => setComposeBody(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      e.preventDefault()
                      if (!busy && composeBody.trim()) {
                        void sendReplyOrForward('reply')
                      }
                    }
                  }}
                  className="textarea"
                  placeholder="Write your message"
                />
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={busy || !composeBody.trim()}
                    onClick={() => void sendReplyOrForward('reply')}
                    className="btn-primary btn-xs disabled:opacity-50"
                  >
                    Reply
                  </button>
                  <button
                    type="button"
                    disabled={busy || !composeBody.trim()}
                    onClick={() => void sendReplyOrForward('forward')}
                    className="btn-secondary btn-xs disabled:opacity-50"
                  >
                    Forward
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
