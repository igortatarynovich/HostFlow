/**
 * CL7 — D4 places Requirement Engine evaluation next to Flight-map.
 *
 * Host region `engine-eval` (distinct from information / qa / flight-map).
 * Status is ready | not_ready + blockers. Overlay is a defined input
 * (`entity_profile_vacancy_overlay.v1`); this zone does not mint overlay SoT
 * and is not vacancy UI.
 */

export const ENTITY_PROFILE_ENGINE_EVAL_V1 = 'entity_profile_engine_eval.v1'
export const ENTITY_PROFILE_VACANCY_OVERLAY_V1 = 'entity_profile_vacancy_overlay.v1'

export function CandidateEngineEvalPanel() {
  return (
    <section
      data-host-region="engine-eval"
      data-engine-eval-contract={ENTITY_PROFILE_ENGINE_EVAL_V1}
      data-overlay-contract={ENTITY_PROFILE_VACANCY_OVERLAY_V1}
      data-overlay-input="defined"
      data-status-shape="ready|not_ready"
      data-boolean="false"
      data-hub-asks="false"
      data-engine-v2="false"
      data-vacancy-overlay-sot="false"
      data-vacancy-ui="false"
      data-layout-widget="false"
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">Requirement Engine</p>
      <p>
        Ready or not ready, with blockers. Overlay is a defined input.
        Not a boolean. Not Hub asks. Not vacancy UI. Profile may only ref.
      </p>
    </section>
  )
}
