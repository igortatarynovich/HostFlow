import { useI18n } from '../../i18n'

/**
 * CL6 — D4 places Flight map Binding snapshot next to Q&A.
 *
 * Host region `flight-map` (distinct from information / qa).
 * Snapshot lives on Binding. Dest = Profile member fields.
 * Not Zapier UX. Not Flight entity dest. Not extra. Not a CL3 widget.
 */

export const ENTITY_PROFILE_FLIGHT_MAP_V1 = 'entity_profile_flight_map.v1'

export function CandidateFlightMapPanel() {
  const { t } = useI18n()
  return (
    <section
      data-host-region="flight-map"
      data-flight-map-contract={ENTITY_PROFILE_FLIGHT_MAP_V1}
      data-snapshot-on="binding"
      data-dest="profile"
      data-layout-widget="false"
      data-writes-to-extra="false"
      data-zapier-ux="false"
      data-meta-admin-sot="false"
      data-flight-entity-dest="false"
      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
    >
      <p className="font-medium text-slate-800">{t('app.entity_workspace.flight_map.title')}</p>
      <p>{t('app.entity_workspace.flight_map.body')}</p>
    </section>
  )
}
