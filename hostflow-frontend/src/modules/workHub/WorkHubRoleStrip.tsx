import { IconUserCog } from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import type { WorkHubProfile } from './profile'

/**
 * Small banner above the Work Hub explaining "what you'll see and why".
 *
 * Acceptance for G-6: every CRM role can answer the question
 * "is this page tuned for me?" in <1 second by reading this strip. The
 * strip is intentionally subdued (slate, no CTA) so it doesn't compete
 * with the hero card below it.
 */
export function WorkHubRoleStrip({ profile }: { profile: WorkHubProfile }) {
  const { t } = useI18n()
  const label = t(profile.labelKey, { defaultValue: profile.labelDefault })
  const lens = t(profile.lensKey, { defaultValue: profile.lensDefault })
  return (
    <div
      role="note"
      aria-label={t('app.work.profile.aria', {
        defaultValue: 'Active role view',
      })}
      className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm"
    >
      <span
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600"
        aria-hidden
      >
        <IconUserCog size={16} />
      </span>
      <div className="min-w-0">
        <p className="font-semibold text-slate-900">
          {t('app.work.profile.viewing_as', {
            defaultValue: 'Viewing as {role}',
            values: { role: label },
          })}
        </p>
        <p className="mt-0.5 text-slate-600">{lens}</p>
      </div>
    </div>
  )
}
