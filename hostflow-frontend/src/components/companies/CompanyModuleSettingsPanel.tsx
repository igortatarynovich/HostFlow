import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  type CompanyModuleKey,
  getCompanyModuleSettings,
  patchCompanyModuleSettings,
} from '../../api/companyModuleSettings'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import FunnelSelector from '../profile/FunnelSelector'

const MODULE_TABS: CompanyModuleKey[] = ['hr', 'recruitment', 'fleet', 'services', 'finance']

type Props = {
  companyId: string
  /** Administrator / supervisor — can PATCH */
  canEdit: boolean
}

export function CompanyModuleSettingsPanel({ companyId, canEdit }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [tab, setTab] = useState<CompanyModuleKey>('hr')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [rowId, setRowId] = useState<string | null>(null)
  const [isEnabled, setIsEnabled] = useState(false)
  const [jsonDraft, setJsonDraft] = useState('{}')
  const [configuredAt, setConfiguredAt] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!companyId) return
    setLoading(true)
    try {
      const data = await getCompanyModuleSettings(companyId, tab)
      setRowId(data.id || null)
      setIsEnabled(Boolean(data.is_enabled))
      setConfiguredAt(data.configured_at)
      setJsonDraft(JSON.stringify(data.settings_json ?? {}, null, 2))
    } catch (e: unknown) {
      const st = Number((e as { response?: { status?: number } })?.response?.status || 0)
      if (st === 403) {
        notify({
          variant: 'error',
          title: t('app.companies.detail.sections.module_settings.forbidden', {
            defaultValue: 'You cannot view these settings for this company.',
          }),
        })
      } else {
        notify({
          variant: 'error',
          title: t('app.companies.detail.sections.module_settings.load_error', {
            defaultValue: 'Could not load module settings',
          }),
        })
      }
    } finally {
      setLoading(false)
    }
  }, [companyId, tab, notify, t])

  useEffect(() => {
    void load()
  }, [load])

  const recruitmentDefaultFunnelId = useMemo(() => {
    if (tab !== 'recruitment') return null
    try {
      const parsed = JSON.parse(jsonDraft) as { default_candidate_funnel_id?: string | null }
      const raw = parsed?.default_candidate_funnel_id
      return typeof raw === 'string' && raw.trim() ? raw.trim() : null
    } catch {
      return null
    }
  }, [tab, jsonDraft])

  const handleRecruitmentDefaultFunnelChange = (funnelId: string | null) => {
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(jsonDraft) as Record<string, unknown>
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('not_object')
      }
    } catch {
      parsed = {}
    }
    parsed.version = 1
    if (funnelId) {
      parsed.default_candidate_funnel_id = funnelId
    } else {
      delete parsed.default_candidate_funnel_id
    }
    setJsonDraft(JSON.stringify(parsed, null, 2))
  }

  const handleSave = async () => {
    if (!canEdit || !companyId) return
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(jsonDraft) as Record<string, unknown>
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('not_object')
      }
    } catch {
      notify({
        variant: 'error',
        title: t('app.companies.detail.sections.module_settings.json_invalid', {
          defaultValue: 'Settings must be a JSON object.',
        }),
      })
      return
    }
    setSaving(true)
    try {
      const data = await patchCompanyModuleSettings(companyId, tab, {
        settings_json: parsed,
        is_enabled: isEnabled,
      })
      setRowId(data.id || null)
      setConfiguredAt(data.configured_at)
      setJsonDraft(JSON.stringify(data.settings_json ?? {}, null, 2))
      notify({
        variant: 'success',
        title: t('app.companies.detail.sections.module_settings.saved', { defaultValue: 'Saved' }),
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      notify({
        variant: 'error',
        title: t('app.companies.detail.sections.module_settings.save_error', {
          defaultValue: 'Could not save',
        }),
        description: typeof detail === 'string' ? detail : JSON.stringify(detail ?? ''),
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="card p-4">
      <header className="flex flex-col gap-1 pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">
            {t('app.companies.detail.sections.module_settings.title', { defaultValue: 'Module settings' })}
          </h2>
          <p className="text-sm text-slate-500">
            {t('app.companies.detail.sections.module_settings.subtitle', {
              defaultValue: 'Per-module configuration for this company (tenant allows the module).',
            })}
          </p>
        </div>
      </header>

      <div className="mb-3 flex flex-wrap gap-1 border-b border-slate-200 pb-2">
        {MODULE_TABS.map((key) => (
          <button
            key={key}
            type="button"
            className={`btn rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              tab === key
                ? 'bg-brand-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
            onClick={() => setTab(key)}
          >
            {t(`app.companies.detail.sections.module_settings.tabs.${key}`, { defaultValue: key })}
          </button>
        ))}
      </div>

      {!canEdit && (
        <p className="mb-3 text-xs text-amber-800">
          {t('app.companies.detail.sections.module_settings.read_only', {
            defaultValue: 'View only. Ask an administrator or supervisor to edit.',
          })}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isEnabled}
              disabled={!canEdit}
              onChange={(ev) => setIsEnabled(ev.target.checked)}
            />
            {t('app.companies.detail.sections.module_settings.enabled', {
              defaultValue: 'Configuration enabled for this module',
            })}
          </label>
          {configuredAt && rowId ? (
            <p className="text-xs text-slate-500">
              {t('app.companies.detail.sections.module_settings.configured_at', {
                defaultValue: 'Last configured: {at}',
                values: { at: configuredAt },
              })}
            </p>
          ) : null}
          {tab === 'recruitment' && (
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">
                {t('app.companies.detail.sections.module_settings.recruitment.default_funnel_title', {
                  defaultValue: 'Default candidate pipeline',
                })}
              </h3>
              <p className="mb-3 text-xs text-slate-500">
                {t('app.companies.detail.sections.module_settings.recruitment.default_funnel_hint', {
                  defaultValue:
                    'Used by the recruitment resolver when no explicit funnel is set on a candidate or profile.',
                })}
              </p>
              <FunnelSelector
                companyId={companyId}
                value={recruitmentDefaultFunnelId}
                onChange={handleRecruitmentDefaultFunnelChange}
                disabled={!canEdit}
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.companies.detail.sections.module_settings.json_label', { defaultValue: 'Settings (JSON)' })}
            </label>
            <p className="mb-1 text-xs text-slate-500">
              {t('app.companies.detail.sections.module_settings.json_hint', {
                defaultValue: 'Must match the server schema for this module (e.g. version: 1).',
              })}
            </p>
            <textarea
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900 disabled:bg-slate-50"
              rows={14}
              value={jsonDraft}
              disabled={!canEdit}
              onChange={(ev) => setJsonDraft(ev.target.value)}
              spellCheck={false}
            />
          </div>
          {canEdit && (
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary btn-sm" disabled={saving} onClick={() => void handleSave()}>
                {t('app.companies.detail.sections.module_settings.save', { defaultValue: 'Save' })}
              </button>
              <button type="button" className="btn-secondary btn-sm" disabled={saving} onClick={() => void load()}>
                {t('common.actions.refresh', { defaultValue: 'Refresh' })}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
