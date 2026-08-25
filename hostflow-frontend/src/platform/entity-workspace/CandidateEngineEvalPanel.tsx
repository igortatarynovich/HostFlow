/**
 * CL7 — D4 places Requirement Engine evaluation next to Flight-map.
 *
 * Host region `engine-eval` (distinct from information / qa / flight-map).
 * Status is ready | not_ready + blockers. Not a boolean. Not Hub asks.
 * Not Engine v2. Not Vacancy overlay SoT.
 */

export const ENTITY_PROFILE_ENGINE_EVAL_V1 = 'entity_profile_engine_eval.v1'

export function CandidateEngineEvalPanel() {
  return (
    <section
      data-host-region="engine-eval"
      data-engine-eval-contract={ENTITY_PROFILE_ENGINE_EVAL_V1}
      data-status-shape="ready|not_ready"
      data-boolean="false"
      data-hub-asks="false"
      data-engine-v2="false"
      data-vacancy-overlay-sot="false"
      data-layout-widget="false"
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">Requirement Engine</p>
      <p>
        Ready or not ready, with blockers. Not a boolean. Not Hub asks.
        Profile may only ref.
      </p>
    </section>
  )
}
