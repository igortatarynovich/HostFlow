/**
 * CL3 — D4 Information zone places Entity Profile card layout.
 *
 * Page type `candidate.card` only. Not a form template.
 * CL4 builder compiles card into this zone; form is a separate artifact.
 * Membership (CL2) owns which fields exist; this zone places presentation.
 */

export const ENTITY_PROFILE_LAYOUT_V1 = 'entity_profile_layout.v1'
export const PAGE_TYPE_CANDIDATE_CARD = 'candidate.card'

export function CandidateInformationLayout() {
  return (
    <section
      data-host-region="information"
      data-layout-contract={ENTITY_PROFILE_LAYOUT_V1}
      data-page-type={PAGE_TYPE_CANDIDATE_CARD}
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">Information</p>
      <p>
        Card layout from Entity Profile membership. Not an intake form. CL4
        builder compiles card here.
      </p>
    </section>
  )
}
