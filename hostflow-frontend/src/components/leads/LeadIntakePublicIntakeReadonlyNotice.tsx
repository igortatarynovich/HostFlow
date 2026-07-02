import { useI18n } from '../../i18n'
import type { Lead } from '../../api/types'
import { leadPublicIntakeReadonlyVariant } from '../../utils/leadIntakeWorkspace'

type Props = {
  lead?: Lead | null
  /** Matches `LeadIntakeDecisionRail` layout naming. */
  layout?: 'panel' | 'embedded'
  className?: string
}

/** Read-only guidance for public intake leads (no POST intake-decision / process on backend). */
export default function LeadIntakePublicIntakeReadonlyNotice({ lead = null, layout = 'panel', className = '' }: Props) {
  const { t } = useI18n()
  const variant = leadPublicIntakeReadonlyVariant(lead)
  const embedded = layout === 'embedded'
  const titleKey =
    variant === 'draft'
      ? 'app.leads.intake_workspace.public_intake_readonly.draft_title'
      : variant === 'client_legacy'
        ? 'app.leads.intake_workspace.public_intake_readonly.client_title'
        : 'app.leads.intake_workspace.public_intake_readonly.title'
  const bodyKey =
    variant === 'draft'
      ? 'app.leads.intake_workspace.public_intake_readonly.draft_body'
      : variant === 'client_legacy'
        ? 'app.leads.intake_workspace.public_intake_readonly.client_body'
        : 'app.leads.intake_workspace.public_intake_readonly.body'
  return (
    <div
      role="status"
      className={
        embedded
          ? `space-y-2 text-sm leading-relaxed text-slate-700 ${className}`.trim()
          : `rounded-2xl bg-slate-50/90 px-4 py-4 text-sm leading-relaxed text-slate-800 ring-1 ring-slate-900/[0.06] ${className}`.trim()
      }
    >
      <p className="font-semibold text-slate-900">{t(titleKey)}</p>
      <p className="mt-1 text-slate-700">{t(bodyKey)}</p>
      <p className="mt-2 text-xs text-slate-600">{t('app.leads.intake_workspace.public_intake_readonly.payload_hint')}</p>
    </div>
  )
}
