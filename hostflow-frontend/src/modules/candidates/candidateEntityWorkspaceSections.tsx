import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EntityPassport } from '../../platform/entity-model'
import type { EntityWorkspaceSectionId, EntityWorkspaceSectionRenderer } from '../../platform/entity-workspace'
import CandidateDocsWorkspacePanel from '../../components/candidate/CandidateDocsWorkspacePanel'
import type { AugmentedCandidate } from './types'
import {
  CandidateContactsContent,
  CandidateOverviewContent,
  CandidateRelationsContent,
  CandidateTasksContent,
  CandidateTimelineContent,
} from './candidateEntityWorkspaceContent'

export type CandidateEntityWorkspaceSectionContext = {
  passport: EntityPassport
  candidate: AugmentedCandidate
  candidateId: string
  locale: string
  candidateProfile: CandidateProfile | null
  effectiveLayout?: EffectiveCardLayout | null
}

/** Candidate section renderers — mockup-aligned content, no passport JSON dump. */
export function buildCandidateEntityWorkspaceSectionRenderers(
  ctx: CandidateEntityWorkspaceSectionContext,
): Partial<Record<EntityWorkspaceSectionId, EntityWorkspaceSectionRenderer>> {
  const { passport, candidate, candidateId, locale, candidateProfile, effectiveLayout } = ctx

  return {
    overview: () => (
      <CandidateOverviewContent
        passport={passport}
        candidate={candidate}
        locale={locale}
        candidateProfile={candidateProfile}
        effectiveLayout={effectiveLayout}
      />
    ),
    contacts: () => <CandidateContactsContent passport={passport} candidate={candidate} />,
    documents: () => (
      <CandidateDocsWorkspacePanel candidateId={candidateId} isNew={false} candidateProfile={candidateProfile} />
    ),
    timeline: () => <CandidateTimelineContent passport={passport} />,
    relations: () => <CandidateRelationsContent passport={passport} />,
    tasks: () => <CandidateTasksContent passport={passport} />,
    outcome: () => {
      const outcome = passport.sections.outcome
      if (!outcome) {
        return <p className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-500">Процесс активен</p>
      }
      return (
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-lg font-bold text-slate-900">{outcome.title}</p>
          {outcome.body ? <p className="text-sm text-slate-600">{outcome.body}</p> : null}
          {outcome.why ? <p className="border-l-2 border-slate-300 pl-3 text-sm text-slate-700">{outcome.why}</p> : null}
        </div>
      )
    },
  }
}
