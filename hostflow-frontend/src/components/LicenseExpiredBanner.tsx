import { useI18n } from '../i18n'

type Props = {
  visible: boolean
  validUntil: string | null
}

export function LicenseExpiredBanner({ visible, validUntil }: Props) {
  const { t } = useI18n()
  if (!visible) return null
  return (
    <div
      className="bg-amber-600 text-white px-4 py-2 text-center text-sm font-medium"
      role="alert"
    >
      {t('app.license.expired_banner', {
        defaultValue: 'Licencja wygasła. Skontaktuj się z administratorem, aby odnowić dostęp.',
        values: { date: validUntil ? new Date(validUntil).toLocaleDateString() : '' },
      })}
    </div>
  )
}
