import { Link } from 'react-router-dom'
import { useMemo } from 'react'
import { useI18n } from '../../i18n'

export default function SettingsLandingPage() {
  const { t } = useI18n()
  const cards = useMemo(
    () => [
      {
        label: t('admin.settings.cards.users.label'),
        description: t('admin.settings.cards.users.description'),
        target: '/app/settings/users',
      },
      {
        label: t('admin.settings.cards.tenants.label'),
        description: t('admin.settings.cards.tenants.description'),
        target: '/app/settings/tenants',
      },
      {
        label: t('admin.settings.cards.documents.label'),
        description: t('admin.settings.cards.documents.description'),
        target: '/app/settings/docs',
      },
      {
        label: t('admin.settings.cards.ruleset.label'),
        description: t('admin.settings.cards.ruleset.description'),
        target: '/app/settings/ruleset',
      },
      {
        label: t('admin.settings.cards.integrations.label'),
        description: t('admin.settings.cards.integrations.description'),
        target: '/app/settings/integrations',
      },
      {
        label: t('admin.settings.cards.audit.label'),
        description: t('admin.settings.cards.audit.description'),
        target: '/app/settings/audit',
      },
    ],
    [t],
  )

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900">{t('admin.settings.title')}</h2>
          <p className="text-sm text-gray-500">{t('admin.settings.subtitle')}</p>
        </header>
        <ul className="grid gap-4 md:grid-cols-2">
          {cards.map((item) => (
            <li key={item.target} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <div className="text-sm font-semibold text-gray-900">{item.label}</div>
              <p className="mt-1 text-sm text-gray-500">{item.description}</p>
              <Link className="mt-3 inline-flex items-center text-sm font-medium text-brand-700 hover:underline" to={item.target}>
                {t('admin.settings.actions.open')}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
