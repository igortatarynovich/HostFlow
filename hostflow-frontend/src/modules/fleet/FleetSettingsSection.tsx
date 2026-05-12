import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

export default function FleetSettingsSection() {
  const { t } = useI18n()

  const workspaceLinks = useMemo(
    () =>
      [
        { to: CRM_APP_PATHS.settingsUsers, labelKey: 'app.fleet.module_settings.link_users' as const },
        { to: CRM_APP_PATHS.settingsTeam, labelKey: 'app.fleet.module_settings.link_team' as const },
        { to: CRM_APP_PATHS.settingsIntegrations, labelKey: 'app.fleet.module_settings.link_integrations' as const },
        { to: CRM_APP_PATHS.settingsBilling, labelKey: 'app.fleet.module_settings.link_billing' as const },
      ] as const,
    [],
  )

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.module_settings.title')}</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">{t('app.fleet.module_settings.body')}</p>
        <div className="pt-1">
          <Link
            to={CRM_APP_PATHS.settings}
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700"
          >
            {t('app.fleet.module_settings.open_settings')}
          </Link>
        </div>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.fleet.module_settings.workspace_links_title', { defaultValue: 'Workspace shortcuts' })}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {t('app.fleet.module_settings.workspace_links_hint', {
            defaultValue: 'Fleet shares tenant-wide access, billing, and integrations with the rest of the workspace.',
          })}
        </p>
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {workspaceLinks.map(({ to, labelKey }) => (
            <li key={to}>
              <Link to={to} className="font-medium text-blue-700 hover:underline">
                {t(labelKey)}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
