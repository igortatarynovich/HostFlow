import { useI18n } from '../../i18n'

/**
 * CL5 — D4 places Recruiter Q&A next to Information / Composition builder.
 *
 * Host region `qa`. Source = Lead / Application, never candidate.extra.
 * Survives convert. Not a CL3 layout widget. Not card fields. Map is CL6.
 */

export const ENTITY_PROFILE_QA_V1 = 'entity_profile_qa.v1'

export function CandidateQaPanel() {
  const { t } = useI18n()
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
      <p className="font-medium text-slate-800">{t('app.entity_workspace.qa.title')}</p>
      <p>{t('app.entity_workspace.qa.body')}</p>
    </section>
  )
}
