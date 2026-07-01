import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getTransferPolicySettings, type TransferPolicySettings } from '../../api/tenants'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

const layerLinks: Record<string, string> = {
  hiring_pipeline_gates: CRM_APP_PATHS.settingsHiringPipelineGates,
  legacy_ruleset: CRM_APP_PATHS.settingsRuleset,
  candidate_profile: CRM_APP_PATHS.settingsCandidateProfiles,
  tenant_link_routing: CRM_APP_PATHS.settingsTenantLinks,
}

export default function TransferPolicySettingsPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [policy, setPolicy] = useState<TransferPolicySettings | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getTransferPolicySettings()
      setPolicy(data)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setPolicy(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const layerEntries = useMemo(() => Object.entries(policy?.layers || {}), [policy?.layers])
  const governanceEntries = useMemo(() => Object.entries(policy?.governance || {}), [policy?.governance])

  return (
    <div className="settings-page-shell-narrow">
      <SettingsSubpageHeader
        className="max-w-4xl"
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('admin.settings.sections.crm_setup.label', { defaultValue: 'CRM Setup' })}
        title={t('admin.transfer_policy.title', { defaultValue: 'Transfer Policy' })}
        subtitle={t('admin.transfer_policy.blurb', {
          defaultValue:
            'Single view of handoff rules. Underlying settings stay in their storage layers; this page aggregates and links them.',
        })}
      />

      {error ? (
        <ErrorRecoveryBanner
          title={t('admin.transfer_policy.load_error', { defaultValue: 'Failed to load transfer policy' })}
          description={error}
          onRetry={() => void load()}
        />
      ) : null}

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : policy ? (
        <div className="space-y-6">
          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.transfer_policy.layers_title', { defaultValue: 'Policy layers' })}
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.transfer_policy.layers_hint', {
                defaultValue: 'TransferPolicyResolver aggregates these layers into one readiness decision.',
              })}
            </p>
            <ul className="mt-4 space-y-4">
              {layerEntries.map(([key, layer]) => (
                <li key={key} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{key}</p>
                      {'storage' in layer && layer.storage ? (
                        <p className="mt-1 text-xs text-slate-500">{String(layer.storage)}</p>
                      ) : null}
                      {'note' in layer && layer.note ? (
                        <p className="mt-1 text-xs text-amber-800">{String(layer.note)}</p>
                      ) : null}
                    </div>
                    {layerLinks[key] ? (
                      <Link className="btn-secondary btn-xs" to={layerLinks[key]}>
                        {t('admin.transfer_policy.open_settings', { defaultValue: 'Open settings' })}
                      </Link>
                    ) : null}
                  </div>
                  <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                    {JSON.stringify(layer, null, 2)}
                  </pre>
                </li>
              ))}
            </ul>
          </section>

          <section className="settings-panel">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.transfer_policy.governance_title', { defaultValue: 'Who can change what' })}
            </h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              {governanceEntries.map(([action, roles]) => (
                <li key={action} className="flex flex-wrap gap-2">
                  <span className="font-medium">{action}:</span>
                  <span>{Array.isArray(roles) ? roles.join(', ') : String(roles)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </div>
  )
}
