import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { IconRefresh } from '@tabler/icons-react'
import type { CommunicationThread } from '../api/communications'
import { useCommunicationsThread } from '../hooks/useCommunicationsThread'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { useEmailInboundSync } from '../hooks/useEmailInboundSync'
import InboxUnifiedThreadList, {
  inboxHubFilterToQueue,
  type InboxHubFilter,
} from '../components/communications/InboxUnifiedThreadList'
import InboxEmailFolderRail from '../components/communications/InboxEmailFolderRail'
import CommunicationsThreadWorkArea from '../components/communications/CommunicationsThreadWorkArea'
import CommunicationsInboxControlPanel from '../components/communications/CommunicationsInboxControlPanel'
import CommunicationsInboxWorkspaceGrid from '../components/communications/CommunicationsInboxWorkspaceGrid'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
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
import { PageShell, PageShellHeader } from '../components/layout'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

function isActiveThread(th: CommunicationThread): boolean {
  return !th.is_archived && String(th.status || '').toLowerCase() !== 'deleted'
}

export default function CommunicationsInboxCenterPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { me } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const listQuery = useMemo(() => readInboxListQuery(searchParams), [searchParams])
  const { threadId = '' } = useParams()
  const { canUseCommunicationsFeature, loading: accessLoading } = useCommunicationsAccess()
  const hasMessages = canUseCommunicationsFeature('messages')
  const hasEmail = canUseCommunicationsFeature('email')

  const effectiveChannel: InboxChannelScope = useMemo(() => {
    if (listQuery.channel === 'email' && !hasEmail && hasMessages) return 'messages'
    if (listQuery.channel === 'messages' && !hasMessages && hasEmail) return 'email'
    return listQuery.channel
  }, [hasEmail, hasMessages, listQuery.channel])

  const listQueryForLinks: InboxListQuery = useMemo(
    () => ({
      ...listQuery,
      channel: effectiveChannel,
    }),
    [effectiveChannel, listQuery],
  )

  const backToHubPath = useMemo(
    () => `${CRM_APP_PATHS.inbox}${inboxContextQueryString(listQueryForLinks)}`,
    [listQueryForLinks],
  )

  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<FriendlyErrorInfo | null>(null)
  const [hubFilter, setHubFilter] = useState<InboxHubFilter>('all')

  const loadList = useCallback(async () => {
    setListLoading(true)
    setListError(null)
    try {
      const items = await fetchInboxThreadPool({
        effectiveChannel,
        hasEmail,
        hasMessages,
        q: listQuery.q,
        queue: inboxHubFilterToQueue(hubFilter),
      })
      setThreads(items)
    } catch (err: unknown) {
      setThreads([])
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.communications_inbox_hub.error'))) {
        setListError(getFriendlyErrorInfo(err, t('app.communications_inbox_hub.error'), t))
      }
    } finally {
      setListLoading(false)
    }
  }, [effectiveChannel, hasEmail, hasMessages, hubFilter, listQuery.q, planLimitModal, t])

  useEffect(() => {
    void loadList()
  }, [loadList])

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

  const { pollBusy, fetchInboundNow } = useEmailInboundSync({
    enabled: effectiveChannel === 'email' && hasEmail && !accessLoading,
    listLoading,
    busy: false,
    onAfterPoll: loadList,
  })

  const writeInboxQuery = useCallback(
    (next: InboxListQuery) => {
      setSearchParams(inboxContextSearchParams(next), { replace: true })
    },
    [setSearchParams],
  )

  const onEmailFolderChange = (folder: EmailFolderKey) => {
    writeInboxQuery({ ...listQuery, channel: 'email', folder })
  }

  const model = useCommunicationsThread(threadId, { backListPathOverride: backToHubPath })
  const { thread, loading: threadLoading, load, threadError } = model

  const showListLoading = accessLoading || listLoading

  const threadMissingBannerInfo = useMemo<FriendlyErrorInfo | null>(() => {
    if (threadLoading || thread) return null
    return (
      threadError ?? {
        title: t('app.communications.states.empty'),
        hint: t('app.common.retry_hint'),
      }
    )
  }, [thread, threadLoading, threadError, t])

  return (
    <PageShell className="bg-slate-50">
      <Link
        to={backToHubPath}
        className="border-b border-slate-200 bg-white px-4 py-3 text-sm font-medium text-brand-700 hover:bg-slate-50 xl:hidden"
      >
        {t('app.communications_inbox_center.back_all_threads')}
      </Link>
      <PageShellHeader className="border-b border-slate-200 bg-slate-50/90 py-2">
        <PageHeader
          kind="browse"
          breadcrumbCurrentLabel={thread?.subject?.trim() || undefined}
          secondaryActions={
            effectiveChannel === 'email' && hasEmail ? (
              <button
                type="button"
                onClick={() => void fetchInboundNow()}
                disabled={pollBusy}
                className="btn-secondary btn-sm inline-flex items-center gap-1"
                title={t('app.communications.email.sync.title')}
              >
                <IconRefresh size={16} stroke={1.75} className={pollBusy ? 'animate-spin' : ''} />
                {t('app.communications.email.sync.title')}
              </button>
            ) : undefined
          }
        />
      </PageShellHeader>
      <CommunicationsInboxWorkspaceGrid variant="inbox_center" className="min-h-0 flex-1">
        <aside
          className={clsx(
            'hidden min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white xl:flex',
          )}
        >
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {effectiveChannel === 'email' && hasEmail && (
              <div className="flex items-center justify-end gap-2">
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
              </div>
            )}
            {effectiveChannel === 'email' && hasEmail && (
              <InboxEmailFolderRail threads={threads} activeFolder={listQuery.folder} onFolderChange={onEmailFolderChange} />
            )}
            {showListLoading && <p className="text-sm text-slate-500">{t('app.communications_inbox_hub.loading')}</p>}
            {!showListLoading && listError && (
              <ErrorRecoveryBanner
                info={listError}
                onRetry={() => void loadList()}
                retryLabel={t('app.communications_inbox_hub.retry')}
                {...friendlyErrorBannerSecondary(
                  listError,
                  backToHubPath,
                  t('app.communications.actions.back_to_hub'),
                )}
                compact
              />
            )}
            {!showListLoading && !listError && (hasMessages || hasEmail) && (
              <>
                {listQuery.candidateId ? (
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-blue-200 bg-blue-50/90 px-3 py-2 text-xs text-blue-950">
                    <span>{t('app.communications_inbox_hub.scoped_candidate_hint')}</span>
                    <button
                      type="button"
                      className="font-medium text-brand-700 hover:underline"
                      onClick={() => {
                        const tid = String(threadId || '').trim()
                        const qs = inboxContextQueryString({ ...listQueryForLinks, candidateId: '' })
                        navigate(
                          tid
                            ? `${CRM_APP_PATHS.inboxThreadsBase}/${encodeURIComponent(tid)}${qs}`
                            : `${CRM_APP_PATHS.inbox}${qs}`,
                          {
                            replace: true,
                          },
                        )
                      }}
                    >
                      {t('app.communications_inbox_hub.scoped_candidate_clear')}
                    </button>
                  </div>
                ) : null}
                <InboxUnifiedThreadList
                  threads={listForUi}
                  hubFilter={hubFilter}
                  onHubFilterChange={setHubFilter}
                  hasMessages={effectiveChannel === 'email' ? false : hasMessages}
                  hasEmail={effectiveChannel === 'messages' ? false : hasEmail}
                  threadLinkPrefix={CRM_APP_PATHS.inboxThreadsBase}
                  linkedCandidateId={listQuery.candidateId || undefined}
                  selectedThreadId={threadId}
                  hideSectionHeading
                  listQuery={listQueryForLinks}
                />
              </>
            )}
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-slate-50">
          {threadLoading && (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          )}
          {threadMissingBannerInfo && (
            <div className="space-y-3">
              <ErrorRecoveryBanner
                info={threadMissingBannerInfo}
                onRetry={() => void load()}
                retryLabel={t('common.actions.refresh')}
                {...friendlyErrorBannerSecondary(
                  threadMissingBannerInfo,
                  backToHubPath,
                  t('app.communications.actions.back_to_hub'),
                )}
                compact
              />
            </div>
          )}
          {!threadLoading && thread && (
            <div className="card flex min-h-0 flex-1 flex-col p-4">
              <CommunicationsThreadWorkArea thread={thread} model={model} layout="inboxCenter" />
            </div>
          )}
        </main>

        <aside
          className={clsx(
            'hidden min-h-0 min-w-0 flex-col overflow-y-auto rounded-lg border border-slate-200 bg-white xl:flex',
          )}
        >
          {thread ? (
            <CommunicationsInboxControlPanel
              thread={thread}
              model={model}
              compact
              onAfterArchiveOrDelete={() => {
                void loadList()
                navigate(backToHubPath)
              }}
            />
          ) : (
            <div className="p-4 text-sm text-slate-500">
              {t('app.communications_inbox_center.channel_rail_empty')}
            </div>
          )}
        </aside>
      </CommunicationsInboxWorkspaceGrid>
    </PageShell>
  )
}
