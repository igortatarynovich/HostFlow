import type { HrEmploymentIdentityProjection, HrReviewPanel } from '../../api/workforce'

type Props = {
  panel: HrReviewPanel
}

const STATUS_LABEL: Record<string, string> = {
  complete: 'Complete',
  incomplete: 'Incomplete',
  conflicted: 'Conflicted',
  stale: 'Stale (expiry)',
}

function statusClass(status: string): string {
  switch (status) {
    case 'complete':
      return 'bg-emerald-50 text-emerald-800 ring-emerald-200'
    case 'conflicted':
      return 'bg-amber-50 text-amber-900 ring-amber-200'
    case 'stale':
      return 'bg-orange-50 text-orange-900 ring-orange-200'
    default:
      return 'bg-slate-50 text-slate-700 ring-slate-200'
  }
}

const DISPLAY_ORDER = [
  'legal_name',
  'birth_date',
  'citizenship',
  'pesel',
  'passport_number',
  'residence_basis',
  'permit_type',
  'permit_expiry',
  'driver_license_categories',
  'code95_expiry',
  'medical_expiry',
  'psychotests_expiry',
] as const

export default function HrEmploymentIdentitySummary({ panel }: Props) {
  const identity: HrEmploymentIdentityProjection | null | undefined = panel.employment_identity
  if (!identity) return null

  const labels = identity.attribute_labels ?? {}
  const attrs = identity.attributes ?? {}
  const meta = identity.attribute_meta ?? {}

  const rows = DISPLAY_ORDER.filter((code) => code in attrs)

  return (
    <section id="hr-employment-identity" className="scroll-mt-24 space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Employment identity</h2>
          <p className="mt-1 text-sm text-slate-600">
            Derived from verified fields only — source for contracts, ZUS, and payroll prep.
          </p>
        </div>
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusClass(identity.status)}`}
        >
          {STATUS_LABEL[identity.status] ?? identity.status}
          {identity.filled_count != null && identity.total_count != null
            ? ` · ${identity.filled_count}/${identity.total_count}`
            : null}
        </span>
      </div>

      {identity.missing_required?.length ? (
        <p className="text-xs text-amber-800">
          Missing required: {identity.missing_required.map((c) => labels[c] ?? c).join(', ')}
        </p>
      ) : null}
      {identity.conflicts?.length ? (
        <p className="text-xs text-amber-800">
          Conflicts: {identity.conflicts.map((c) => labels[c] ?? c).join(', ')}
        </p>
      ) : null}

      <div className="grid gap-2 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2">
        {rows.map((code) => {
          const value = attrs[code]
          const prov = meta[code]
          const label = labels[code] ?? code
          return (
            <div key={code} className="min-w-0">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{value || <span className="text-slate-400">—</span>}</dd>
              {prov?.source_document_key ? (
                <p className="mt-0.5 text-xs text-slate-500">
                  From {prov.source_document_key}
                  {prov.verified_at ? ` · ${prov.verified_at.slice(0, 10)}` : ''}
                </p>
              ) : null}
            </div>
          )
        })}
      </div>
    </section>
  )
}
