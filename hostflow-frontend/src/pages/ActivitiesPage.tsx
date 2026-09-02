import { ActivitiesPanel } from '../components/activities/ActivitiesPanel'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'

export default function ActivitiesPage() {
  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader kind="browse" />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <ActivitiesPanel />
      </div>
    </PageShell>
  )
}
