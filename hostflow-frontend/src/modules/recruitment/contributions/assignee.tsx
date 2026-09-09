import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'

export function RecruitmentAssigneeContribution({
  application,
}: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const knownAssignee = String(application?.assignee_id || '').trim()

  if (!knownAssignee) {
    // Happy path does not ask for an assignee UUID. Known assignee is read-only.
    return null
  }

  return (
    <section className="space-y-1" data-capability-id="recruitment.assignee">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.recruitment.contributions.assignee')}
      </p>
      <p className="text-sm text-slate-800">{knownAssignee}</p>
    </section>
  )
}
