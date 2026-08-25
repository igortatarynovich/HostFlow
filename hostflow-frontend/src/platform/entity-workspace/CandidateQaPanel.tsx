/**
 * CL5 — D4 places Recruiter Q&A next to Information / Composition builder.
 *
 * Host region `qa`. Source = Lead / Application, never candidate.extra.
 * Survives convert. Not a CL3 layout widget. Not card fields. Map is CL6.
 */

export const ENTITY_PROFILE_QA_V1 = 'entity_profile_qa.v1'

export function CandidateQaPanel() {
  return (
    <section
      data-host-region="qa"
      data-qa-contract={ENTITY_PROFILE_QA_V1}
      data-source="lead_application"
      data-survives-convert="true"
      data-dispositions="map,qa_only,ignore"
      data-layout-widget="false"
      data-writes-to-extra="false"
      data-executes-map="false"
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">Recruiter Q&A</p>
      <p>
        Lead / Application answers. Visible after convert. Not extra. Not
        card fields. Map is CL6 Flight — not executed here.
      </p>
    </section>
  )
}
