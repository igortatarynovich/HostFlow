import clsx from 'clsx'
import { useI18n } from '../../i18n'
import type { WorkPanelRequirementRow } from '../../utils/workPanelRequirements'
import { requirementBlockerLabelKey } from '../../utils/requirementsPipelineBlockers'

type Props = {
  items: WorkPanelRequirementRow[]
  loading?: boolean
  className?: string
}

function requirementLabel(t: ReturnType<typeof useI18n>['t'], row: WorkPanelRequirementRow): string {
  const fromApi = String(row.public_name || '').trim()
  if (fromApi) return fromApi
  const code = row.requirement_code
  return t(requirementBlockerLabelKey(code), { defaultValue: code.replace(/_/g, ' ') })
}

function statusBadgeClass(row: WorkPanelRequirementRow): string {
  if (row.fulfilled) return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  const evidence = String(row.evidence_status || '').toLowerCase()
  if (evidence === 'rejected') return 'bg-rose-50 text-rose-800 border-rose-200'
  if (evidence === 'pending_review' || String(row.evaluation_status || '').toLowerCase() === 'pending_verification') {
    return 'bg-amber-50 text-amber-900 border-amber-200'
  }
  return 'bg-slate-50 text-slate-700 border-slate-200'
}

function statusLabel(t: ReturnType<typeof useI18n>['t'], row: WorkPanelRequirementRow): string {
  if (row.fulfilled) {
    return t('app.candidate_card.requirements_checklist.status.satisfied', { defaultValue: 'Confirmed' })
  }
  const evidence = String(row.evidence_status || '').toLowerCase()
  if (evidence === 'rejected') {
    return t('app.candidate_card.requirements_checklist.status.rejected', { defaultValue: 'Rejected' })
  }
  if (evidence === 'pending_review' || String(row.evaluation_status || '').toLowerCase() === 'pending_verification') {
    return t('app.candidate_card.requirements_checklist.status.pending_review', { defaultValue: 'Pending review' })
  }
  if (row.evidence_variant_code) {
    return t('app.candidate_card.requirements_checklist.status.pending_evidence', { defaultValue: 'Evidence selected' })
  }
  return t('app.candidate_card.requirements_checklist.status.missing', { defaultValue: 'Missing' })
}

export default function CandidateRequirementsWorkPanelPreview({ items, loading = false, className }: Props) {
  const { t } = useI18n()

  if (loading) {
    return (
      <div className={clsx('rounded-xl border border-slate-200 bg-white p-3 text-[11px] text-slate-500', className)}>
        {t('common.loading')}
      </div>
    )
  }

  if (!items.length) {
    return null
  }

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-3', className)}>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
        {t('app.candidates.preview.requirements_title', { defaultValue: 'Recruitment confirmations' })}
      </div>
      <div className="mt-2 overflow-x-auto">
        <table className="min-w-full text-left text-[11px]">
          <thead>
            <tr className="border-b border-slate-200 text-[10px] uppercase tracking-wide text-slate-500">
              <th className="py-1 pr-2 font-semibold">
                {t('app.candidates.preview.requirements_col_requirement', { defaultValue: 'Requirement' })}
              </th>
              <th className="py-1 pr-2 font-semibold">
                {t('app.candidates.preview.requirements_col_evidence', { defaultValue: 'Evidence' })}
              </th>
              <th className="py-1 pr-2 font-semibold">
                {t('app.candidates.preview.requirements_col_document', { defaultValue: 'Linked document' })}
              </th>
              <th className="py-1 font-semibold">
                {t('app.candidates.preview.requirements_col_status', { defaultValue: 'Status' })}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => {
              const linked = row.linked_document
              const linkedLabel = linked?.document_type_code
                ? linked.document_type_code.replace(/_/g, ' ')
                : '—'
              const evidenceLabel = row.evidence_variant_code
                ? t(`app.candidate_card.requirements_checklist.variants.${row.evidence_variant_code}`, {
                    defaultValue: row.evidence_variant_code.replace(/_/g, ' '),
                  })
                : '—'
              return (
                <tr key={row.requirement_code} className="border-b border-slate-100 last:border-0">
                  <td className="py-1.5 pr-2 align-top font-medium text-slate-900">
                    {requirementLabel(t, row)}
                  </td>
                  <td className="py-1.5 pr-2 align-top text-slate-700">{evidenceLabel}</td>
                  <td className="py-1.5 pr-2 align-top text-slate-600">{linkedLabel}</td>
                  <td className="py-1.5 align-top">
                    <span className={clsx('inline-flex rounded border px-1.5 py-0.5 font-medium', statusBadgeClass(row))}>
                      {statusLabel(t, row)}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
