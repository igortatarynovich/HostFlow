import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { IconBell, IconRefresh } from '@tabler/icons-react'
import { getCommunicationsSettings, patchCommunicationsSettings, type CommunicationThread } from '../api/communications'
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
import { stashPendingGmailOAuthCode } from '../utils/oauthRedirectBridge'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

function isActiveThread(th: CommunicationThread): boolean {
  return !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted'
}

function canPatchCommunicationsSettings(role: string | undefined): boolean {
  const r = String(role || '').trim().toLowerCase()
  return r === 'administrator' || r === 'supervisor' || r === 'admin' || r === 'superadmin'
}

export default function CommunicationsInboxHubPage() {
  const { t } = useI18n()
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
      if (effectiveChannel === 'email' && hasEmail) {
        const cfg = await getCommunicationsSettings().catch(() => null)
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

  const { pollBusy, fetchInboundNow } = useEmailInboundSync({
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

  const showLoading = accessLoading || loading

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-auto">
        <h1 className="sr-only">{t('app.communications_inbox_hub.title')}</h1>

        {oauthRedirectNotice && (
          <div className="max-w-4xl rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
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

        {!commSetup.loading && !commSetup.isComplete && anyChannel && (
          <div className="max-w-4xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div className="font-medium">{t('app.communications.setup.banner_incomplete')}</div>
            <div className="mt-2">
              <Link to={CRM_APP_PATHS.settingsIntegrations} className="btn-secondary btn-xs">
                {t('app.nav.items.settings_integrations')}
              </Link>
            </div>
          </div>
        )}

        {!commSetup.loading && commSetup.isComplete && effectiveChannel === 'email' && serverIncomingEnabled === false && hasEmail && (
          <div className="max-w-4xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
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
          <div className="max-w-5xl flex flex-wrap gap-1">
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
        )}

        {showLoading && <p className="text-sm text-slate-500">{t('app.communications_inbox_hub.loading')}</p>}

        {!showLoading && error && (
          <div className="max-w-4xl rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-800">
            <p className="font-medium">{error.title}</p>
            {error.detail ? <p className="mt-1 text-xs text-rose-900/90">{error.detail}</p> : null}
            <p className="mt-2 text-xs text-rose-800/85">{error.hint}</p>
            <button type="button" className="btn-secondary btn-sm mt-3" onClick={() => void load()}>
              {t('app.communications_inbox_hub.retry')}
            </button>
          </div>
        )}

        {!showLoading && !error && anyChannel && (
          <div className={clsx('max-w-6xl', effectiveChannel === 'email' && hasEmail && 'flex flex-col gap-4 lg:flex-row lg:items-start')}>
            {effectiveChannel === 'email' && hasEmail && (
              <div className="w-full shrink-0 lg:w-64">
                <InboxEmailFolderRail threads={threads} activeFolder={listQuery.folder} onFolderChange={onEmailFolderChange} />
              </div>
            )}
            <div className="min-w-0 flex-1 space-y-3">
              {listQuery.candidateId ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-sky-200 bg-sky-50/90 px-3 py-2 text-sm text-sky-950">
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
                  className="input min-w-[12rem] flex-1 py-1.5 text-sm"
                  placeholder={t('app.communications_inbox_hub.search_placeholder')}
                />
                {effectiveChannel === 'email' && hasEmail && (
                  <button
                    type="button"
                    onClick={() => void fetchInboundNow()}
                    disabled={pollBusy}
                    className="inline-flex shrink-0 items-center justify-center rounded-md border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
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
              />
            </div>
          </div>
        )}

        {!showLoading && !error && !anyChannel && (
          <p className="mt-2 max-w-2xl text-sm text-slate-600">{t('app.communications_inbox_hub.unified_none_enabled')}</p>
        )}

        {!showLoading && !error && anyChannel && (
          <div className="max-w-5xl">
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
    </div>
  )
}
