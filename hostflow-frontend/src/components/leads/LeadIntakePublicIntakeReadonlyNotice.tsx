import { useI18n } from '../../i18n'

type Props = {
  /** Matches `LeadIntakeDecisionRail` layout naming. */
  layout?: 'panel' | 'embedded'
  className?: string
}

/** Read-only guidance for public-intake recruitment leads (no POST intake-decision / process on backend). */
export default function LeadIntakePublicIntakeReadonlyNotice({ layout = 'panel', className = '' }: Props) {
  const { t } = useI18n()
  const embedded = layout === 'embedded'
  return (
    <div
      role="status"
      className={
        embedded
          ? `space-y-2 text-sm leading-relaxed text-slate-700 ${className}`.trim()
          : `rounded-2xl bg-slate-50/90 px-4 py-4 text-sm leading-relaxed text-slate-800 ring-1 ring-slate-900/[0.06] ${className}`.trim()
      }
    >
      <p className="font-semibold text-slate-900">{t('app.leads.intake_workspace.public_intake_readonly.title')}</p>
      <p className="mt-1 text-slate-700">{t('app.leads.intake_workspace.public_intake_readonly.body')}</p>
      <p className="mt-2 text-xs text-slate-600">{t('app.leads.intake_workspace.public_intake_readonly.payload_hint')}</p>
    </div>
  )
}
