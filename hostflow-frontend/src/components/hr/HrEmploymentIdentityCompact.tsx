import type { HrReviewPanel } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  panel: HrReviewPanel
}

function consumerReady(identity: NonNullable<HrReviewPanel['employment_identity']>, codes: string[]): boolean {
  const missing = new Set(identity.missing_required ?? [])
  const pending = new Set(identity.pending_attributes ?? [])
  return codes.every((c) => !missing.has(c) && !pending.has(c))
}

export default function HrEmploymentIdentityCompact({ panel }: Props) {
  const { t } = useI18n()
  const identity = panel.employment_identity
  const dv = panel.data_verification_summary
  if (!identity && !dv) return null

  const labels = identity?.attribute_labels ?? {}
  const missing = (identity?.missing_required ?? []).map((c) => labels[c] ?? c.replace(/_/g, ' '))
  const ready = identity?.ready_for_downstream ?? dv?.identity_status === 'complete'

  const contractsOk = identity
    ? consumerReady(identity, ['legal_name', 'citizenship', 'permit_type', 'passport_number'])
    : ready
  const zusOk = identity
    ? consumerReady(identity, ['pesel', 'citizenship', 'legal_name'])
    : ready
  const payrollOk = identity ? consumerReady(identity, ['legal_name', 'pesel']) : ready

  const pill = (ok: boolean, label: string) => (
    <span
      className={
        ok
          ? 'inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-800 ring-1 ring-emerald-200'
          : 'inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 ring-1 ring-slate-200'
      }
    >
      <span aria-hidden>{ok ? '✓' : '○'}</span>
      {label}
    </span>
  )

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-700">
      <span className="font-medium text-slate-600">
        {t('app.hr.identity.compact_title', { defaultValue: 'Downstream readiness' })}
      </span>
      {pill(contractsOk, t('app.hr.identity.contracts', { defaultValue: 'Contracts' }))}
      {pill(zusOk, t('app.hr.identity.zus', { defaultValue: 'ZUS' }))}
      {pill(payrollOk, t('app.hr.identity.payroll', { defaultValue: 'Payroll' }))}
      {missing.length > 0 ? (
        <span className="text-amber-800">
          {t('app.hr.identity.missing', { defaultValue: 'Missing' })}: {missing.slice(0, 3).join(', ')}
          {missing.length > 3 ? ` +${missing.length - 3}` : ''}
        </span>
      ) : ready ? (
        <span className="font-medium text-emerald-700">
          {t('app.hr.identity.ready', { defaultValue: 'Employment identity ready' })}
        </span>
      ) : null}
    </div>
  )
}
