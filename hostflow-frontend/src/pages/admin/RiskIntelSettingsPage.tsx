import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { recordPerfMeasurement } from '../../api/analytics'
import { getRiskModelV1Settings, patchRiskModelV1Settings } from '../../api/tenants'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

const RISK_BANDS = ['low', 'medium', 'high', 'critical'] as const
type RiskBand = (typeof RISK_BANDS)[number]

function asObj(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}

function parseBand(v: unknown, fallback: RiskBand): RiskBand {
  const s = String(v || '').toLowerCase().trim()
  return (RISK_BANDS as readonly string[]).includes(s) ? (s as RiskBand) : fallback
}

function splitList(text: string): string[] {
  return text
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

export default function RiskIntelSettingsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const { role } = usePermissions()
  const isAdmin = String(role || '').toLowerCase() === 'administrator'

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [overridesJson, setOverridesJson] = useState<string>('{}')

  const [hourlyJobEnabled, setHourlyJobEnabled] = useState(true)

  const [sgEnabled, setSgEnabled] = useState(false)
  const [sgMinBand, setSgMinBand] = useState<RiskBand>('critical')
  const [sgBlock, setSgBlock] = useState(true)

  const [digestEnabled, setDigestEnabled] = useState(false)
  const [digestMinBand, setDigestMinBand] = useState<RiskBand>('high')
  const [digestMaxRows, setDigestMaxRows] = useState(25)
  const [digestSkipEmpty, setDigestSkipEmpty] = useState(true)
  const [digestToRaw, setDigestToRaw] = useState('')
  const [digestRolesRaw, setDigestRolesRaw] = useState('')

  const [autoEnabled, setAutoEnabled] = useState(false)
  const [autoMinBand, setAutoMinBand] = useState<RiskBand>('high')
  const [autoDedupeHours, setAutoDedupeHours] = useState(24)

  const applyEffective = useCallback((effective: Record<string, unknown>) => {
    setHourlyJobEnabled(effective.hourly_job_enabled !== false)
    const sg = asObj(effective.stage_gate)
    setSgEnabled(Boolean(sg.enabled))
    setSgMinBand(parseBand(sg.min_band, 'critical'))
    setSgBlock(sg.block_forward_without_next_action !== false)
    const de = asObj(effective.digest_email)
    setDigestEnabled(Boolean(de.enabled))
    setDigestMinBand(parseBand(de.min_band, 'high'))
    setDigestMaxRows(Math.max(1, Math.min(500, Number(de.max_rows) || 25)))
    setDigestSkipEmpty(de.skip_if_empty !== false)
    const to = de.to
    setDigestToRaw(Array.isArray(to) ? to.map(String).join(', ') : '')
    const tr = de.to_roles
    setDigestRolesRaw(Array.isArray(tr) ? tr.map(String).join(', ') : '')
    const au = asObj(effective.automations)
    setAutoEnabled(au.enabled === true)
    setAutoMinBand(parseBand(au.min_band, 'high'))
    setAutoDedupeHours(Math.max(1, Math.min(168, Number(au.dedupe_hours) || 24)))
  }, [])

  const load = useCallback(async () => {
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    setLoading(true)
    let loadOk = false
    try {
      const res = await getRiskModelV1Settings()
      applyEffective((res.effective || {}) as Record<string, unknown>)
      setOverridesJson(JSON.stringify(res.overrides ?? {}, null, 2))
      loadOk = true
    } catch (e: any) {
      notify({
        title: t('admin.risk_intel.settings.load_error', { defaultValue: 'Failed to load risk intelligence settings' }),
        description: e?.response?.data?.detail ?? e?.message,
        variant: 'error',
      })
      setOverridesJson('{}')
    } finally {
      const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
      void recordPerfMeasurement({
        metricKey: 'settings.risk_intel.page.load',
        durationMs,
        route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
        meta: { ok: loadOk },
      }).catch(() => {})
      setLoading(false)
    }
  }, [applyEffective, notify, t])

  useEffect(() => {
    void load()
  }, [load])

  const handleSave = async () => {
    if (!isAdmin) return
    setSaving(true)
    try {
      const patch = {
        hourly_job_enabled: hourlyJobEnabled,
        stage_gate: {
          enabled: sgEnabled,
          min_band: sgMinBand,
          block_forward_without_next_action: sgBlock,
        },
        digest_email: {
          enabled: digestEnabled,
          min_band: digestMinBand,
          max_rows: digestMaxRows,
          skip_if_empty: digestSkipEmpty,
          to: splitList(digestToRaw),
          to_roles: splitList(digestRolesRaw).map((s) => s.toLowerCase()),
        },
        automations: {
          enabled: autoEnabled,
          min_band: autoMinBand,
          dedupe_hours: autoDedupeHours,
        },
      }
      const res = await patchRiskModelV1Settings(patch)
      applyEffective((res.effective || {}) as Record<string, unknown>)
      setOverridesJson(JSON.stringify(res.overrides ?? {}, null, 2))
      notify({
        title: t('admin.risk_intel.settings.saved', { defaultValue: 'Risk intelligence settings saved' }),
        variant: 'success',
      })
    } catch (e: any) {
      notify({
        title: t('admin.risk_intel.settings.save_error', { defaultValue: 'Save failed' }),
        description: e?.response?.data?.detail ?? e?.message,
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const bandSelect = (value: RiskBand, onChange: (b: RiskBand) => void, disabled: boolean) => (
    <select
      className="mt-1 w-full max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 disabled:opacity-60"
      value={value}
      onChange={(e) => onChange(e.target.value as RiskBand)}
      disabled={disabled}
    >
      {RISK_BANDS.map((b) => (
        <option key={b} value={b}>
          {b}
        </option>
      ))}
    </select>
  )

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <SettingsSubpageHeader
        className="max-w-4xl"
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('admin.settings.subpage.kicker_workspace_setup')}
        title={t('admin.risk_intel.settings.title', { defaultValue: 'Risk intelligence (v1)' })}
        subtitle={t('admin.risk_intel.settings.blurb', {
          defaultValue:
            'Tenant overrides for risk_model_v1: hourly job, stage gate, digest email, and risk-band automations. Effective values merge with product defaults.',
        })}
      />

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              {t('admin.risk_intel.settings.overrides_title', { defaultValue: 'Stored tenant overrides (read-only)' })}
            </div>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.risk_intel.settings.overrides_hint', {
                defaultValue: 'Raw JSON fragment under settings.risk_model_v1 after save.',
              })}
            </p>
            <pre className="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-100 bg-slate-50 p-3 font-mono text-[11px] text-slate-800">
              {overridesJson}
            </pre>
          </div>

          <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <input
              type="checkbox"
              checked={hourlyJobEnabled}
              onChange={(e) => setHourlyJobEnabled(e.target.checked)}
              disabled={!isAdmin}
              className="rounded border-slate-300"
            />
            <div>
              <div className="text-sm font-semibold text-slate-800">
                {t('admin.risk_intel.settings.hourly_job', { defaultValue: 'Hourly risk job enabled' })}
              </div>
              <p className="text-xs text-slate-600">
                {t('admin.risk_intel.settings.hourly_job_hint', {
                  defaultValue: 'When off, the scheduled hourly persistence job skips this workspace.',
                })}
              </p>
            </div>
          </label>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              {t('admin.risk_intel.settings.stage_gate', { defaultValue: 'Stage gate' })}
            </div>
            <label className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                checked={sgEnabled}
                onChange={(e) => setSgEnabled(e.target.checked)}
                disabled={!isAdmin}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-800">
                {t('admin.risk_intel.settings.stage_gate_enabled', { defaultValue: 'Enforce gate on forward' })}
              </span>
            </label>
            <div className="mt-3">
              <div className="text-xs font-medium text-slate-600">
                {t('admin.risk_intel.settings.min_band', { defaultValue: 'Minimum band' })}
              </div>
              {bandSelect(sgMinBand, setSgMinBand, !isAdmin)}
            </div>
            <label className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                checked={sgBlock}
                onChange={(e) => setSgBlock(e.target.checked)}
                disabled={!isAdmin}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-800">
                {t('admin.risk_intel.settings.block_without_next_action', {
                  defaultValue: 'Block forward without next action (when gate applies)',
                })}
              </span>
            </label>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              {t('admin.risk_intel.settings.digest', { defaultValue: 'Shadow digest email' })}
            </div>
            <label className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                checked={digestEnabled}
                onChange={(e) => setDigestEnabled(e.target.checked)}
                disabled={!isAdmin}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-800">
                {t('admin.risk_intel.settings.digest_enabled', { defaultValue: 'Send digest when criteria match' })}
              </span>
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <div className="text-xs font-medium text-slate-600">
                  {t('admin.risk_intel.settings.min_band', { defaultValue: 'Minimum band' })}
                </div>
                {bandSelect(digestMinBand, setDigestMinBand, !isAdmin)}
              </div>
              <div>
                <div className="text-xs font-medium text-slate-600">
                  {t('admin.risk_intel.settings.max_rows', { defaultValue: 'Max rows' })}
                </div>
                <input
                  type="number"
                  min={1}
                  max={500}
                  className="mt-1 w-full max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
                  value={digestMaxRows}
                  onChange={(e) => setDigestMaxRows(Number(e.target.value) || 1)}
                  disabled={!isAdmin}
                />
              </div>
            </div>
            <label className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                checked={digestSkipEmpty}
                onChange={(e) => setDigestSkipEmpty(e.target.checked)}
                disabled={!isAdmin}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-800">
                {t('admin.risk_intel.settings.skip_if_empty', { defaultValue: 'Skip send when digest is empty' })}
              </span>
            </label>
            <label className="mt-3 block">
              <div className="text-xs font-medium text-slate-600">
                {t('admin.risk_intel.settings.digest_to', { defaultValue: 'Direct emails (comma-separated)' })}
              </div>
              <input
                type="text"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm disabled:opacity-60"
                value={digestToRaw}
                onChange={(e) => setDigestToRaw(e.target.value)}
                disabled={!isAdmin}
                placeholder="ops@example.com"
              />
            </label>
            <label className="mt-3 block">
              <div className="text-xs font-medium text-slate-600">
                {t('admin.risk_intel.settings.digest_roles', { defaultValue: 'Role inboxes (comma-separated)' })}
              </div>
              <input
                type="text"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm disabled:opacity-60"
                value={digestRolesRaw}
                onChange={(e) => setDigestRolesRaw(e.target.value)}
                disabled={!isAdmin}
                placeholder="administrator, supervisor"
              />
            </label>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              {t('admin.risk_intel.settings.automations', { defaultValue: 'Risk-band automations' })}
            </div>
            <p className="mt-1 text-xs text-slate-600">
              {t('admin.risk_intel.settings.automations_hint', {
                defaultValue: 'Runs after hourly scoring when shadow rows exist; uses automation rules for candidate risk bands.',
              })}
            </p>
            <label className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoEnabled}
                onChange={(e) => setAutoEnabled(e.target.checked)}
                disabled={!isAdmin}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-800">
                {t('admin.risk_intel.settings.auto_enabled', { defaultValue: 'Enable automations' })}
              </span>
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <div className="text-xs font-medium text-slate-600">
                  {t('admin.risk_intel.settings.min_band', { defaultValue: 'Minimum band' })}
                </div>
                {bandSelect(autoMinBand, setAutoMinBand, !isAdmin)}
              </div>
              <div>
                <div className="text-xs font-medium text-slate-600">
                  {t('admin.risk_intel.settings.dedupe_hours', { defaultValue: 'Dedupe window (hours)' })}
                </div>
                <input
                  type="number"
                  min={1}
                  max={168}
                  className="mt-1 w-full max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
                  value={autoDedupeHours}
                  onChange={(e) => setAutoDedupeHours(Number(e.target.value) || 1)}
                  disabled={!isAdmin}
                />
              </div>
            </div>
          </div>

          {isAdmin ? (
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={saving}>
                {t('common.reload', { defaultValue: 'Reload' })}
              </button>
              <button type="button" className="btn-primary btn-sm" onClick={() => void handleSave()} disabled={saving}>
                {saving ? t('common.saving', { defaultValue: 'Saving…' }) : t('common.save', { defaultValue: 'Save' })}
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              {t('admin.risk_intel.settings.read_only', {
                defaultValue: 'Only workspace administrators can edit these settings.',
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
