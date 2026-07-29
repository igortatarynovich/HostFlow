import { useI18n } from '../i18n'

type Props = {
  visible: boolean
}

/** SSOT §6 / Phase 5 — explicit elevated / impersonation indication. */
export function ImpersonationBanner({ visible }: Props) {
  const { t } = useI18n()
  if (!visible) return null
  return (
    <div
      className="bg-rose-700 px-4 py-2 text-center text-sm font-semibold tracking-wide text-white"
      role="status"
      data-testid="impersonation-banner"
    >
      {t('app.topbar.impersonation_banner', {
        defaultValue: 'SUPERADMIN ACCESS ACTIVE — impersonating customer tenant',
      })}
    </div>
  )
}
