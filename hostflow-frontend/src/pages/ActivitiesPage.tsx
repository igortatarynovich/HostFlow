import { useI18n } from '../i18n'
import { ActivitiesPanel } from '../components/activities/ActivitiesPanel'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'

export default function ActivitiesPage() {
  const { t } = useI18n()

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.activities.title', { defaultValue: 'Activities' })}
          subtitle={t('app.activities.subtitle', { defaultValue: 'Planned work for you' })}
          kind="browse"
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <ActivitiesPanel />
      </div>
    </PageShell>
  )
}
