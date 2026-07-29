import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listCompanies } from '../../api/client'
import { listLeadMessageTemplates } from '../../api/metaLeads'
import {
  getLeadLifecycleEmailPolicy,
  putLeadLifecycleEmailPolicy,
  putVacancyLifecycleEmailOverride,
  resolveLeadLifecycleEmailPreview,
  type LeadLifecycleEmailPolicy,
  type LifecycleEmailPolicyDecision,
} from '../../api/leadLifecycleEmail'
import type { LeadMessageTemplate } from '../../api/types'
import { listVacancies } from '../../api/vacancies'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useI18n } from '../../i18n'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

const PURPOSES = [
  { key: 'gdpr_notice', label: 'RODO / art.14' },
  { key: 'submission_acknowledgement', label: 'Application received' },
  { key: 'intake_rejection_notice', label: 'Intake rejection' },
  { key: 'moving_forward_notice', label: 'Moving forward' },
] as const

function emptyPolicy(): LeadLifecycleEmailPolicy {
  return {
    version: 1,
    rodo_send_mode: 'manual',
    rodo_template_ref: null,
    ops_enabled: false,
    application_received: { enabled: false, template_ref: null },
    rejection: { enabled: false, template_ref: null },
    moving_forward: { enabled: false, template_ref: null },
    channels: ['email'],
  }
}

function TemplateSelect({
  value,
  templates,
  onChange,
}: {
  value: string | null | undefined
  templates: LeadMessageTemplate[]
  onChange: (id: string | null) => void
}) {
  return (
    <select
      className="input mt-1 w-full"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value ? e.target.value : null)}
    >
      <option value="">— select template —</option>
      {templates
        .filter((t) => t.is_active)
        .map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
    </select>
  )
}

export default function LeadLifecycleEmailSettingsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const P = CRM_APP_PATHS

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [saveBusy, setSaveBusy] = useState(false)

  const [companies, setCompanies] = useState<Array<{ id: string; name: string }>>([])
  const [companyId, setCompanyId] = useState('')
  const [policySource, setPolicySource] = useState('company')
  const [policy, setPolicy] = useState<LeadLifecycleEmailPolicy>(emptyPolicy)
  const [templates, setTemplates] = useState<LeadMessageTemplate[]>([])
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [vacancyId, setVacancyId] = useState('')
  const [previewPurpose, setPreviewPurpose] = useState<string>('gdpr_notice')
  const [preview, setPreview] = useState<LifecycleEmailPolicyDecision | null>(null)
  const [overrideDraft, setOverrideDraft] = useState<Record<string, { enabled?: boolean; template_ref?: string | null }>>(
    {},
  )

  const misconfigured = useMemo(() => {
    const issues: string[] = []
    if (policy.rodo_send_mode !== 'manual' && !policy.rodo_template_ref) {
      issues.push('RODO auto mode without template')
    }
    if (policy.ops_enabled) {
      for (const [key, label] of [
        ['application_received', 'Application received'],
        ['rejection', 'Rejection'],
        ['moving_forward', 'Moving forward'],
      ] as const) {
        const block = policy[key]
        if (block.enabled && !block.template_ref) issues.push(`${label}: enabled without template`)
      }
    }
    return issues
  }, [policy])

  const loadCompanies = useCallback(async () => {
    const rows = await listCompanies({ limit: 200 })
    const list = (Array.isArray(rows) ? rows : (rows as { items?: unknown[] })?.items || []) as Array<{
      id: string
      name?: string
    }>
    setCompanies(list.map((c) => ({ id: String(c.id), name: String(c.name || c.id) })))
    if (!companyId && list[0]?.id) setCompanyId(String(list[0].id))
  }, [companyId])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const [tpls] = await Promise.all([listLeadMessageTemplates(), loadCompanies()])
        if (mounted) setTemplates(Array.isArray(tpls) ? tpls : [])
      } catch (err: unknown) {
        if (mounted) {
          if (
            !planLimitModal?.showPlanLimitIfNeeded(
              err,
              t('admin.lead_lifecycle_email.errors.load_failed', { defaultValue: 'Failed to load Control Center' }),
            )
          ) {
            setError(
              getFriendlyErrorInfo(
                err,
                t('admin.lead_lifecycle_email.errors.load_failed', { defaultValue: 'Failed to load Control Center' }),
                t,
              ),
            )
          }
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [loadCompanies, planLimitModal, t])

  useEffect(() => {
    if (!companyId) return
    let mounted = true
    ;(async () => {
      setError(null)
      try {
        const [out, vacs] = await Promise.all([
          getLeadLifecycleEmailPolicy(companyId),
          listVacancies({ company_id: companyId, limit: 100 }),
        ])
        if (!mounted) return
        setPolicy({ ...emptyPolicy(), ...(out.policy || {}) })
        setPolicySource(out.source)
        setVacancies(
          (Array.isArray(vacs) ? vacs : []).map((v) => ({
            id: String(v.id),
            title: String((v as { title?: string }).title || v.id),
          })),
        )
        setVacancyId('')
        setOverrideDraft({})
      } catch (err: unknown) {
        if (!mounted) return
        setError(
          getFriendlyErrorInfo(
            err,
            t('admin.lead_lifecycle_email.errors.load_company', { defaultValue: 'Failed to load company policy' }),
            t,
          ),
        )
      }
    })()
    return () => {
      mounted = false
    }
  }, [companyId, t])

  const refreshPreview = useCallback(async () => {
    if (!companyId) return
    try {
      const d = await resolveLeadLifecycleEmailPreview({
        company_id: companyId,
        purpose: previewPurpose,
        vacancy_id: vacancyId || null,
      })
      setPreview(d)
    } catch {
      setPreview(null)
    }
  }, [companyId, previewPurpose, vacancyId])

  useEffect(() => {
    void refreshPreview()
  }, [refreshPreview])

  const saveCompany = async () => {
    if (!companyId) return
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      const out = await putLeadLifecycleEmailPolicy(companyId, policy)
      setPolicy({ ...emptyPolicy(), ...(out.policy || {}) })
      setPolicySource(out.source)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
      await refreshPreview()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.lead_lifecycle_email.errors.save_failed', { defaultValue: 'Failed to save policy' }),
          t,
        ),
      )
    } finally {
      setSaveBusy(false)
    }
  }

  const saveVacancyOverride = async () => {
    if (!vacancyId) return
    setSaveBusy(true)
    setError(null)
    try {
      await putVacancyLifecycleEmailOverride(vacancyId, overrideDraft)
      setSaveNotice(t('common.saved', { defaultValue: 'Saved' }))
      await refreshPreview()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.lead_lifecycle_email.errors.save_override', { defaultValue: 'Failed to save vacancy override' }),
          t,
        ),
      )
    } finally {
      setSaveBusy(false)
    }
  }

  if (loading) {
    return (
      <SettingsSubpageHeader
        backHref={P.settingsCommunications}
        backLabel={t('admin.communications_settings.page_title', { defaultValue: 'Communications' })}
        kicker="Communications"
        title="Lead lifecycle email"
        subtitle="Loading…"
      >
        <p className="text-sm text-slate-600">…</p>
      </SettingsSubpageHeader>
    )
  }

  return (
    <SettingsSubpageHeader
      backHref={P.settingsCommunications}
      backLabel={t('admin.communications_settings.page_title', { defaultValue: 'Communications' })}
      kicker="Communications"
      title={t('admin.lead_lifecycle_email.page_title', { defaultValue: 'Lead lifecycle email' })}
      subtitle={t('admin.lead_lifecycle_email.subtitle', {
        defaultValue: 'Per-company RODO and ops email policy. Vacancy overrides are optional.',
      })}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link to={P.settingsEmail} className="btn-secondary btn-sm">
            SMTP
          </Link>
          <Link to={P.settingsMessageTemplates} className="btn-secondary btn-sm">
            Templates
          </Link>
          <Link to={P.settingsIntegrationsMeta} className="btn-secondary btn-sm">
            Meta (deep-link)
          </Link>
        </div>
      }
    >
      {error ? (
        <ErrorRecoveryBanner
          title={error.title}
          message={error.message}
          secondary={friendlyErrorBannerSecondary(error)}
          onDismiss={() => setError(null)}
        />
      ) : null}
      {saveNotice ? <p className="mb-3 text-sm text-emerald-700">{saveNotice}</p> : null}

      {misconfigured.length > 0 ? (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="font-semibold">Misconfiguration</p>
          <ul className="mt-1 list-disc pl-5">
            {misconfigured.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mb-4">
        <label className="text-sm font-medium text-slate-800">
          Company
          <select className="input mt-1 w-full max-w-lg" value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
            <option value="">Select company…</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        {companyId ? (
          <p className="mt-1 text-xs text-slate-500">Source: {policySource}</p>
        ) : null}
      </div>

      {!companyId ? (
        <p className="text-sm text-slate-600">Select a company to edit lifecycle email policy.</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">RODO / art.14</h2>
            <label className="mt-3 block text-sm text-slate-700">
              Send mode
              <select
                className="input mt-1 w-full"
                value={policy.rodo_send_mode}
                onChange={(e) =>
                  setPolicy((p) => ({
                    ...p,
                    rodo_send_mode: e.target.value as LeadLifecycleEmailPolicy['rodo_send_mode'],
                  }))
                }
              >
                <option value="manual">Manual</option>
                <option value="auto_on_lead_created">Auto on lead created</option>
                <option value="auto_on_first_action">Auto on first gated action</option>
              </select>
            </label>
            <label className="mt-3 block text-sm text-slate-700">
              Template
              <TemplateSelect
                value={policy.rodo_template_ref}
                templates={templates}
                onChange={(id) => setPolicy((p) => ({ ...p, rodo_template_ref: id }))}
              />
            </label>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">Operational emails</h2>
            <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={policy.ops_enabled}
                onChange={(e) => setPolicy((p) => ({ ...p, ops_enabled: e.target.checked }))}
              />
              Master enabled
            </label>
            {(
              [
                ['application_received', 'Application received'],
                ['rejection', 'Rejection'],
                ['moving_forward', 'Moving forward'],
              ] as const
            ).map(([key, label]) => (
              <div key={key} className="mt-3 border-t border-slate-100 pt-3">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    disabled={!policy.ops_enabled}
                    checked={policy.ops_enabled ? policy[key].enabled : false}
                    onChange={(e) =>
                      setPolicy((p) => ({
                        ...p,
                        [key]: { ...p[key], enabled: e.target.checked },
                      }))
                    }
                  />
                  {label}
                </label>
                <TemplateSelect
                  value={policy[key].template_ref}
                  templates={templates}
                  onChange={(id) =>
                    setPolicy((p) => ({
                      ...p,
                      [key]: { ...p[key], template_ref: id },
                    }))
                  }
                />
              </div>
            ))}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">Effective policy (resolve-preview)</h2>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void refreshPreview()}>
                Refresh
              </button>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <label className="text-sm text-slate-700">
                Purpose
                <select
                  className="input mt-1 w-full"
                  value={previewPurpose}
                  onChange={(e) => setPreviewPurpose(e.target.value)}
                >
                  {PURPOSES.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-slate-700 md:col-span-2">
                Vacancy (optional override context)
                <select className="input mt-1 w-full" value={vacancyId} onChange={(e) => setVacancyId(e.target.value)}>
                  <option value="">Company only</option>
                  {vacancies.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {preview ? (
              <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">send</dt>
                  <dd>{String(preview.send)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">enabled</dt>
                  <dd>{String(preview.enabled)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">layer</dt>
                  <dd>{preview.source_layer}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">block_code</dt>
                  <dd>{preview.block_code || '—'}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">template_ref</dt>
                  <dd className="font-mono text-xs">{preview.template_ref || '—'}</dd>
                </div>
                {preview.reason ? (
                  <div className="sm:col-span-2">
                    <dt className="text-xs uppercase tracking-wide text-slate-500">reason</dt>
                    <dd>{preview.reason}</dd>
                  </div>
                ) : null}
              </dl>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No preview yet.</p>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 lg:col-span-2">
            <h2 className="text-base font-semibold text-slate-900">Vacancy sparse override</h2>
            <p className="mt-1 text-xs text-slate-600">
              Only set keys you want to override. Missing keys inherit company policy.
            </p>
            {!vacancyId ? (
              <p className="mt-2 text-sm text-slate-500">Select a vacancy in the preview panel to edit overrides.</p>
            ) : (
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {PURPOSES.map((p) => {
                  const key = p.key === 'gdpr_notice' ? 'gdpr_notice' : p.key
                  const opsKey =
                    p.key === 'submission_acknowledgement'
                      ? 'application_received'
                      : p.key === 'intake_rejection_notice'
                        ? 'rejection'
                        : p.key === 'moving_forward_notice'
                          ? 'moving_forward'
                          : 'gdpr_notice'
                  const block = overrideDraft[opsKey] || overrideDraft[key] || {}
                  return (
                    <div key={p.key} className="rounded border border-slate-100 p-3">
                      <p className="text-sm font-medium text-slate-800">{p.label}</p>
                      <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                        <input
                          type="checkbox"
                          checked={Boolean(block.enabled)}
                          onChange={(e) =>
                            setOverrideDraft((d) => ({
                              ...d,
                              [opsKey]: { ...block, enabled: e.target.checked },
                            }))
                          }
                        />
                        Override enabled
                      </label>
                      <TemplateSelect
                        value={block.template_ref}
                        templates={templates}
                        onChange={(id) =>
                          setOverrideDraft((d) => ({
                            ...d,
                            [opsKey]: { ...block, template_ref: id },
                          }))
                        }
                      />
                    </div>
                  )
                })}
                <div className="md:col-span-2">
                  <button type="button" className="btn-secondary" disabled={saveBusy} onClick={() => void saveVacancyOverride()}>
                    Save vacancy override
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      <div className="mt-6 flex gap-2">
        <button type="button" className="btn-primary" disabled={!companyId || saveBusy} onClick={() => void saveCompany()}>
          {saveBusy ? 'Saving…' : 'Save company policy'}
        </button>
      </div>
    </SettingsSubpageHeader>
  )
}
