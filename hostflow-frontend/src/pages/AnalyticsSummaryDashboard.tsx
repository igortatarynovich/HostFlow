import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'

/**
 * System summary tab on the Analytics host.
 * Points operators to licensed module tabs — does not duplicate module drill-downs.
 */
export default function AnalyticsSummaryDashboard() {
  const { t } = useI18n()

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.summary.title')}
          subtitle={t('app.dashboard.summary.subtitle')}
          kind="browse"
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-700">{t('app.dashboard.summary.body')}</p>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-600">
            <li>{t('app.dashboard.summary.bullets.modules')}</li>
            <li>{t('app.dashboard.summary.bullets.filters')}</li>
            <li>{t('app.dashboard.summary.bullets.owned')}</li>
          </ul>
        </div>
      </div>
    </PageShell>
  )
}
