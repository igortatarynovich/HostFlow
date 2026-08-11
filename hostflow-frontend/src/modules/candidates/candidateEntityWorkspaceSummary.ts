import type { EntityPassport } from '../../platform/entity-model'
import type { EntityWorkspaceSummaryModel } from '../../platform/entity-workspace'
import { projectEntityWorkspaceSummary } from '../../platform/entity-workspace/projectEntityWorkspaceView'

/** Candidate summary strip — semantic cards aligned with product mockup. */
export function buildCandidateEntityWorkspaceSummary(
  passport: EntityPassport,
  docsPercentReady?: number | null,
  t?: (key: string, opts?: { defaultValue?: string }) => string,
): EntityWorkspaceSummaryModel {
  const projected = projectEntityWorkspaceSummary(passport, t)
  const cards = projected.cards.filter((card) => card.id !== 'owner')

  if (typeof docsPercentReady === 'number' && !Number.isNaN(docsPercentReady)) {
    const pct = Math.max(0, Math.min(100, Math.round(docsPercentReady)))
    cards.push({
      id: 'match-progress',
      label: t
        ? t('app.entity_workspace.summary.match_progress', { defaultValue: 'Match progress' })
        : 'Match progress',
      value: `${pct}%`,
      progressPercent: pct,
      tone: pct >= 80 ? 'success' : 'default',
    })
  }

  return {
    ...projected,
    cards: cards.slice(0, 5),
  }
}
