import { Link, useParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import CommunicationsThreadWorkArea from '../components/communications/CommunicationsThreadWorkArea'
import { useCommunicationsThread } from '../hooks/useCommunicationsThread'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../utils/friendlyError'

export default function CommunicationsThreadPage() {
  const { t } = useI18n()
  const { threadId = '' } = useParams()
  const model = useCommunicationsThread(threadId)
  const { thread, loading, load, threadError, threadListPath } = model

  if (loading) {
    return (
      <PageShell>
        <WorkspaceTopNav active={null} />
        <div className="flex min-h-0 flex-1 items-center justify-center px-4 pb-4 text-sm text-slate-500">
          {t('common.loading')}
        </div>
      </PageShell>
    )
  }

  if (!thread) {
    const missingThreadInfo: FriendlyErrorInfo =
      threadError ??
      ({
        title: t('app.communications.states.empty'),
        hint: t('app.common.retry_hint'),
      } satisfies FriendlyErrorInfo)
    return (
      <PageShell>
        <WorkspaceTopNav active={null} />
        <PageShellHeader>
          <PageHeader kind="browse" />
        </PageShellHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 pb-4">
          <div className="flex flex-wrap gap-2">
            <Link to={CRM_APP_PATHS.calendar} className="text-sm text-brand-700 hover:text-brand-900">
              {t('app.communications.actions.back_to_calendar')}
            </Link>
            <Link to={CRM_APP_PATHS.inboxMessagesScoped} className="text-sm text-slate-600 hover:text-slate-900">
              {t('app.nav.items.messages')}
            </Link>
          </div>
          <ErrorRecoveryBanner
            info={missingThreadInfo}
            onRetry={() => void load()}
            retryLabel={t('common.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              missingThreadInfo,
              threadListPath,
              t('app.communications.actions.back_to_hub'),
            )}
            compact
          />
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <WorkspaceTopNav active={null} />
      <PageShellHeader>
        <PageHeader kind="browse" breadcrumbCurrentLabel={thread.subject?.trim() || undefined} />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-4">
        <CommunicationsThreadWorkArea thread={thread} model={model} layout="page" />
      </div>
    </PageShell>
  )
}
