import { Link, useParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import CommunicationsThreadWorkArea from '../components/communications/CommunicationsThreadWorkArea'
import { useCommunicationsThread } from '../hooks/useCommunicationsThread'
import { useI18n } from '../i18n'

export default function CommunicationsThreadPage() {
  const { t } = useI18n()
  const { threadId = '' } = useParams()
  const model = useCommunicationsThread(threadId)
  const { thread, loading, load, errorText, threadListPath } = model

  if (loading) {
    return <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
  }

  if (!thread) {
    return (
      <div className="space-y-3">
        <WorkspaceTopNav active={null} />
        <div className="flex flex-wrap gap-2">
          <Link to="/app/calendar" className="text-sm text-brand-700 hover:text-brand-900">
            {t('app.communications.actions.back_to_calendar', { defaultValue: '← Back to calendar' })}
          </Link>
          <Link to="/app/inbox?channel=messages" className="text-sm text-slate-600 hover:text-slate-900">
            {t('app.nav.items.messages', { defaultValue: 'Messages' })}
          </Link>
        </div>
        <ErrorRecoveryBanner
          info={{
            title: errorText || t('app.communications.states.empty', { defaultValue: 'No activity yet' }),
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo={threadListPath}
          secondaryLabel={t('app.communications.actions.back_to_hub', { defaultValue: 'Back to inbox' })}
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
