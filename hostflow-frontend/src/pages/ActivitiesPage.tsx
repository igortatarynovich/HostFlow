import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import { ActivitiesPanel } from '../components/activities/ActivitiesPanel'

export default function ActivitiesPage() {
  const { t } = useI18n()

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <WorkspaceTopNav active="tasks" />

      <header className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.activities.title', { defaultValue: 'Activities' })}
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900">
              {t('app.activities.subtitle', { defaultValue: 'Planned work for you' })}
            </h1>
          </div>
        </div>
      </header>

      <ActivitiesPanel />
    </div>
  )
}
