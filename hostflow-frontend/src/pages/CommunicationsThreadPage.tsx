import { Link, useParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
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
    return <div className="text-sm text-slate-500">{t('common.loading')}</div>
  }

  if (!thread) {
    const missingThreadInfo: FriendlyErrorInfo =
      threadError ??
      ({
        title: t('app.communications.states.empty'),
        hint: t('app.common.retry_hint'),
      } satisfies FriendlyErrorInfo)
    return (
      <div className="space-y-3">
        <WorkspaceTopNav active={null} />
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
    )
  }

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active={null} />
      <CommunicationsThreadWorkArea thread={thread} model={model} layout="page" />
    </div>
  )
}
