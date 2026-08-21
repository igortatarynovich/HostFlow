import { IconX } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import type { WorkspaceContributionDefinition } from './contribution'
import { groupContributionsByRegion, renderWorkspaceContribution } from './placement'
import type { WorkspaceCapabilityRenderContext } from './renderContext'

type Props = WorkspaceCapabilityRenderContext & {
  contributions: readonly WorkspaceContributionDefinition[]
}

/**
 * Application Workspace host placer. Places contributions into host regions.
 * Does not own Notes/Consent/Tasks/Documents semantics.
 */
export function ApplicationWorkspaceCapabilityHost({ contributions, ...ctx }: Props) {
  const { t } = useI18n()
  const renderCtx: WorkspaceCapabilityRenderContext = {
    ...ctx,
    host: ctx.host ?? 'application_workspace',
  }
  const byRegion = groupContributionsByRegion(contributions)

  return (
    <div
      className="flex h-full min-h-0 flex-col overflow-hidden bg-white"
      data-workspace-capability-host="application_workspace"
      data-proof-consumer="recruitment_application"
    >
      <header className="flex shrink-0 items-start justify-between gap-2 border-b border-slate-100 p-4" data-host-region="header">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {byRegion.header.map((row) => renderWorkspaceContribution(row, renderCtx))}
        </div>
        <button
          type="button"
          onClick={ctx.onClose}
          className="rounded-none p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label={t('common.close', { defaultValue: 'Закрыть' })}
        >
          <IconX size={18} stroke={2} />
        </button>
      </header>
      {byRegion.summary.length ? (
        <section className="shrink-0 border-b border-slate-100 p-4" data-host-region="summary">
          {byRegion.summary.map((row) => renderWorkspaceContribution(row, renderCtx))}
        </section>
      ) : null}
      <section className="shrink-0 border-b border-slate-100 p-4" data-host-region="decision">
        {byRegion.decision.map((row) => renderWorkspaceContribution(row, renderCtx))}
      </section>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {byRegion.overview.length ? (
          <div className="space-y-4 border-b border-slate-100 p-4" data-host-region="overview">
            {byRegion.overview.map((row) => renderWorkspaceContribution(row, renderCtx))}
          </div>
        ) : null}
        {byRegion.platform_slot.length ? (
          <div className="space-y-4 border-b border-slate-100 p-4" data-host-region="platform_slot">
            {byRegion.platform_slot.map((row) => renderWorkspaceContribution(row, renderCtx))}
          </div>
        ) : null}
        {byRegion.rail.length ? (
          <div className="space-y-4 p-4" data-host-region="rail">
            {byRegion.rail.map((row) => renderWorkspaceContribution(row, renderCtx))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
