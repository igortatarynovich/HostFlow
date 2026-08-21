import { IconX } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import type { WorkspaceContributionDefinition } from './contribution'
import { WORKSPACE_CAPABILITY_RENDERERS } from './renderers'
import type { WorkspaceCapabilityRenderContext } from './renderContext'

type Props = WorkspaceCapabilityRenderContext & {
  contributions: readonly WorkspaceContributionDefinition[]
}

function renderContribution(row: WorkspaceContributionDefinition, ctx: WorkspaceCapabilityRenderContext) {
  const Renderer = WORKSPACE_CAPABILITY_RENDERERS[row.component_id as keyof typeof WORKSPACE_CAPABILITY_RENDERERS]
  if (!Renderer) return null
  return <Renderer key={row.capability_id} {...ctx} />
}

/**
 * Application Workspace host placer. Places contributions into host regions.
 * Does not own Notes/Consent/Tasks/Documents semantics.
 */
export function ApplicationWorkspaceCapabilityHost({ contributions, ...ctx }: Props) {
  const { t } = useI18n()
  const ordered = [...contributions].sort((a, b) => a.ordering - b.ordering)
  const header = ordered.filter((row) => row.placement.region === 'header')
  const decision = ordered.filter((row) => row.placement.region === 'decision')
  const overview = ordered.filter((row) => row.placement.region === 'overview')
  const rail = ordered.filter((row) => row.placement.region === 'rail')

  return (
    <div
      className="flex h-full min-h-0 flex-col overflow-hidden bg-white"
      data-workspace-capability-host="application_workspace"
      data-proof-consumer="recruitment_application"
    >
      <header className="flex shrink-0 items-start justify-between gap-2 border-b border-slate-100 p-4" data-host-region="header">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {header.map((row) => renderContribution(row, ctx))}
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
      <section className="shrink-0 border-b border-slate-100 p-4" data-host-region="decision">
        {decision.map((row) => renderContribution(row, ctx))}
      </section>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {overview.length ? (
          <div className="space-y-4 border-b border-slate-100 p-4" data-host-region="overview">
            {overview.map((row) => renderContribution(row, ctx))}
          </div>
        ) : null}
        {rail.length ? (
          <div className="space-y-4 p-4" data-host-region="rail">
            {rail.map((row) => renderContribution(row, ctx))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
