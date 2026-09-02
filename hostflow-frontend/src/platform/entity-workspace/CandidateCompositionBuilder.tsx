import { useI18n } from '../../i18n'

/**
 * CL4 — D4 places two builder modes next to the Information zone.
 *
 * Card compile writes a layout_instance to the layout registry (D4 card).
 * Form compile writes a form_definition to the Forms platform — not this card.
 * Closed page-type catalog. Not Q&A. Not Flight.
 */

export const ENTITY_PROFILE_BUILDER_V1 = 'entity_profile_builder.v1'
export const BUILDER_MODE_CARD = 'card'
export const BUILDER_MODE_FORM = 'form'

export function CandidateCompositionBuilder() {
  const { t } = useI18n()
  return (
    <section
      data-host-region="composition-builder"
      data-builder-contract={ENTITY_PROFILE_BUILDER_V1}
      data-builder-modes="card,form"
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">{t('app.entity_workspace.composition_builder.title')}</p>
      <div
        data-builder-mode={BUILDER_MODE_CARD}
        data-page-type="candidate.card"
        data-artifact-kind="layout_instance"
        data-writes-to="layout_registry"
        data-places-on-d4="true"
        className="mt-2"
      >
        {t('app.entity_workspace.composition_builder.card')}
      </div>
      <div
        data-builder-mode={BUILDER_MODE_FORM}
        data-page-type="intake.form"
        data-artifact-kind="form_definition"
        data-writes-to="forms_platform"
        data-places-on-d4="false"
        className="mt-1"
      >
        {t('app.entity_workspace.composition_builder.form')}
      </div>
    </section>
  )
}
