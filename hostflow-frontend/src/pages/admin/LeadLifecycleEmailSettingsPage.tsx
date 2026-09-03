import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listCompanies, listOwnCompanies } from '../../api/client'
import { getActiveLegalDocs } from '../../api/legalDocuments'
import {
  createLeadMessageTemplate,
  listLeadMessageTemplates,
  updateLeadMessageTemplate,
} from '../../api/metaLeads'
import {
  getLeadLifecycleEmailPolicy,
  getOwnCompanyLeadLifecycleEmailPolicy,
  putLeadLifecycleEmailPolicy,
  putOwnCompanyLeadLifecycleEmailPolicy,
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
import { Checkbox } from '../../components/ui/Checkbox'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useI18n } from '../../i18n'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  LeadLifecycleMessageModal,
  type LifecycleMessageDraft,
  type LifecycleMessagePurpose,
} from './LeadLifecycleMessageModal'

const PURPOSE_KEYS = [
  'gdpr_notice',
  'submission_acknowledgement',
  'intake_rejection_notice',
  'moving_forward_notice',
] as const

const OPS_KEYS = ['application_received', 'rejection', 'moving_forward'] as const

function emptyPolicy(): LeadLifecycleEmailPolicy {
  return {
    version: 1,
    rodo_send_mode: 'auto_on_lead_created',
    rodo_template_ref: null,
    ops_enabled: false,
    application_received: { enabled: false, template_ref: null },
    rejection: { enabled: false, template_ref: null },
    moving_forward: { enabled: false, template_ref: null },
    channels: ['email'],
  }
}

function withOpsMaster(policy: LeadLifecycleEmailPolicy): LeadLifecycleEmailPolicy {
  return {
    ...policy,
    ops_enabled: OPS_KEYS.some((key) => policy[key].enabled),
  }
}

function templateName(templates: LeadMessageTemplate[], id: string | null | undefined): string | null {
  if (!id) return null
  return templates.find((tpl) => tpl.id === id)?.name ?? null
}

export default function LeadLifecycleEmailSettingsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const P = CRM_APP_PATHS

  const purposeLabel = (key: string) => t(`admin.lead_lifecycle_email.purpose.${key}`)
  const opsLabel = (key: (typeof OPS_KEYS)[number]) => t(`admin.lead_lifecycle_email.ops.${key}`)
  const layerLabel = (layer: string) => {
    const key = `admin.lead_lifecycle_email.layers.${layer}`
    const value = t(key)
    return value === key ? layer : value
  }
  const blockLabel = (code: string | null) => {
    if (!code) return t('common.labels.not_available')
    const key = `admin.lead_lifecycle_email.block_codes.${code}`
    const value = t(key)
    return value === key ? code : value
  }
  const reasonLabel = (decision: LifecycleEmailPolicyDecision) => {
    const code = decision.block_code
    if (!code) return decision.reason || ''
    if (code === 'policy_template_missing' && decision.purpose !== 'gdpr_notice') {
      return t('admin.lead_lifecycle_email.reasons.ops_template_missing')
    }
    if (code === 'policy_template_missing' && decision.send_mode === 'manual') {
      return t('admin.lead_lifecycle_email.reasons.policy_template_missing_manual')
    }
    const key = `admin.lead_lifecycle_email.reasons.${code}`
    const value = t(key)
    return value === key ? decision.reason || code : value
  }

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [saveBusy, setSaveBusy] = useState(false)
  const [composerBusy, setComposerBusy] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showTechnical, setShowTechnical] = useState(false)

  const [companies, setCompanies] = useState<Array<{ id: string; name: string }>>([])
  const [companyId, setCompanyId] = useState('')
  const [ownCompanyId, setOwnCompanyId] = useState('')
  const [ownCompanies, setOwnCompanies] = useState<Array<{ id: string; name: string }>>([])
  const [policySource, setPolicySource] = useState('own_company')
  const [policy, setPolicy] = useState<LeadLifecycleEmailPolicy>(emptyPolicy)
  const [templates, setTemplates] = useState<LeadMessageTemplate[]>([])
  const [rodoDocument, setRodoDocument] = useState<{ versionId: string } | null>(null)
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [vacancyId, setVacancyId] = useState('')
  const [previewPurpose, setPreviewPurpose] = useState<string>('gdpr_notice')
  const [preview, setPreview] = useState<LifecycleEmailPolicyDecision | null>(null)
  const [overrideDraft, setOverrideDraft] = useState<Record<string, { enabled?: boolean; template_ref?: string | null }>>(
    {},
  )

  const [composerOpen, setComposerOpen] = useState(false)
  const [composerPurpose, setComposerPurpose] = useState<LifecycleMessagePurpose>('rodo')
  const [composerEditId, setComposerEditId] = useState<string | null>(null)
  const [composerDraft, setComposerDraft] = useState<LifecycleMessageDraft>({ name: '', subject: '', body: '' })

  const activeTemplates = useMemo(() => templates.filter((tpl) => tpl.is_active), [templates])
  const rodoActive = Boolean(policy.rodo_template_ref)
  const selectedRodoName = templateName(templates, policy.rodo_template_ref)
  const ownCompanyName = ownCompanies.find((c) => c.id === ownCompanyId)?.name || ''

  const defaultDraft = useCallback(
    (purpose: LifecycleMessagePurpose): LifecycleMessageDraft => {
      if (purpose === 'rodo') {
        return {
          name: t('admin.lead_lifecycle_email.default_rodo.name'),
          subject: t('admin.lead_lifecycle_email.default_rodo.subject'),
          body: t('admin.lead_lifecycle_email.default_rodo.body'),
        }
      }
      return {
        name: t(`admin.lead_lifecycle_email.default_ops.${purpose}.name`),
        subject: t(`admin.lead_lifecycle_email.default_ops.${purpose}.subject`),
        body: t(`admin.lead_lifecycle_email.default_ops.${purpose}.body`),
      }
    },
    [t],
  )

  const openComposer = useCallback(
    (purpose: LifecycleMessagePurpose, existingId?: string | null) => {
      const existing = existingId ? templates.find((tpl) => tpl.id === existingId) : undefined
      setComposerPurpose(purpose)
      setComposerEditId(existing?.id ?? null)
      setComposerDraft(
        existing
          ? { name: existing.name, subject: existing.subject, body: existing.body }
          : defaultDraft(purpose),
      )
      setComposerOpen(true)
    },
    [defaultDraft, templates],
  )

  const loadCompanies = useCallback(async () => {
    const [rows, ownRes] = await Promise.all([
      listCompanies({ limit: 200 }),
      listOwnCompanies().catch(() => ({ items: [] as Array<{ id: string; name?: string }>, active_own_company_id: null })),
    ])
    const list = (Array.isArray(rows) ? rows : (rows as { items?: unknown[] })?.items || []) as Array<{
      id: string
      name?: string
    }>
    setCompanies(list.map((c) => ({ id: String(c.id), name: String(c.name || c.id) })))
    const owns = Array.isArray(ownRes?.items) ? ownRes.items : []
    setOwnCompanies(owns.map((c) => ({ id: String(c.id), name: String(c.name || c.id) })))
    const active = String(ownRes?.active_own_company_id || owns[0]?.id || '').trim()
    if (active) setOwnCompanyId((prev) => prev || active)
  }, [])

  const refreshTemplates = useCallback(async () => {
    const tpls = await listLeadMessageTemplates()
    setTemplates(Array.isArray(tpls) ? tpls : [])
  }, [])

  const refreshLegal = useCallback(async () => {
    try {
      const docs = await getActiveLegalDocs()
      const clause = docs.rodo_clause
      setRodoDocument(clause?.is_active ? { versionId: clause.version_id } : null)
    } catch {
      setRodoDocument(null)
    }
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        await Promise.all([refreshTemplates(), loadCompanies(), refreshLegal()])
      } catch (err: unknown) {
        if (mounted) {
          if (
            !planLimitModal?.showPlanLimitIfNeeded(err, t('admin.lead_lifecycle_email.errors.load_failed'))
          ) {
            setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.load_failed'), t))
          }
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [loadCompanies, planLimitModal, refreshLegal, refreshTemplates, t])

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        void refreshTemplates().catch(() => undefined)
        void refreshLegal().catch(() => undefined)
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [refreshLegal, refreshTemplates])

  useEffect(() => {
    if (!ownCompanyId) return
    let mounted = true
    ;(async () => {
      setError(null)
      try {
        const out = await getOwnCompanyLeadLifecycleEmailPolicy(ownCompanyId)
        if (!mounted) return
        setPolicy({ ...emptyPolicy(), ...(out.policy || {}) })
        setPolicySource(out.source)
      } catch (err: unknown) {
        if (!mounted) return
        setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.load_company'), t))
      }
    })()
    return () => {
      mounted = false
    }
  }, [ownCompanyId, t])

  useEffect(() => {
    if (!companyId) {
      setVacancies([])
      setVacancyId('')
      setOverrideDraft({})
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const vacs = await listVacancies({ company_id: companyId, limit: 100 })
        if (!mounted) return
        setVacancies(
          (Array.isArray(vacs) ? vacs : []).map((v) => ({
            id: String(v.id),
            title: String((v as { title?: string }).title || v.id),
          })),
        )
        setVacancyId('')
        setOverrideDraft({})
      } catch {
        if (mounted) setVacancies([])
      }
    })()
    return () => {
      mounted = false
    }
  }, [companyId])

  const refreshPreview = useCallback(async () => {
    if (!ownCompanyId) return
    try {
      const d = await resolveLeadLifecycleEmailPreview({
        own_company_id: ownCompanyId,
        company_id: companyId || null,
        purpose: previewPurpose,
        vacancy_id: vacancyId || null,
      })
      setPreview(d)
    } catch {
      setPreview(null)
    }
  }, [ownCompanyId, companyId, previewPurpose, vacancyId])

  useEffect(() => {
    void refreshPreview()
  }, [refreshPreview])

  const persistFirmPolicy = useCallback(
    async (next: LeadLifecycleEmailPolicy, notice?: string) => {
      if (!ownCompanyId) return
      setSaveBusy(true)
      setSaveNotice(null)
      setError(null)
      try {
        const out = await putOwnCompanyLeadLifecycleEmailPolicy(ownCompanyId, withOpsMaster(next))
        setPolicy({ ...emptyPolicy(), ...(out.policy || {}) })
        setPolicySource(out.source)
        setSaveNotice(notice || t('common.saved'))
        await refreshPreview()
      } catch (err: unknown) {
        setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.save_failed'), t))
      } finally {
        setSaveBusy(false)
      }
    },
    [ownCompanyId, refreshPreview, t],
  )

  const applyMessageToPolicy = useCallback(
    (current: LeadLifecycleEmailPolicy, purpose: LifecycleMessagePurpose, templateId: string): LeadLifecycleEmailPolicy => {
      if (purpose === 'rodo') {
        return {
          ...current,
          rodo_template_ref: templateId,
          rodo_send_mode: 'auto_on_lead_created',
        }
      }
      return withOpsMaster({
        ...current,
        [purpose]: { enabled: true, template_ref: templateId },
      })
    },
    [],
  )

  const saveAndUseMessage = useCallback(async () => {
    const name = composerDraft.name.trim()
    const subject = composerDraft.subject.trim()
    const body = composerDraft.body.trim()
    if (!name || !subject || !body) return
    setComposerBusy(true)
    setError(null)
    try {
      const saved = composerEditId
        ? await updateLeadMessageTemplate(composerEditId, { name, subject, body, is_active: true })
        : await createLeadMessageTemplate({ name, subject, body, is_active: true })
      setTemplates((prev) => {
        const without = prev.filter((tpl) => tpl.id !== saved.id)
        return [...without, saved].sort((a, b) => a.name.localeCompare(b.name))
      })
      const next = applyMessageToPolicy(policy, composerPurpose, saved.id)
      setPolicy(next)
      setComposerOpen(false)
      await persistFirmPolicy(next, t('admin.lead_lifecycle_email.composer.applied'))
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.create_template'), t))
    } finally {
      setComposerBusy(false)
    }
  }, [applyMessageToPolicy, composerDraft, composerEditId, composerPurpose, persistFirmPolicy, policy, t])

  const selectRodoMessage = useCallback(
    (id: string | null) => {
      const next = { ...policy, rodo_template_ref: id }
      setPolicy(next)
      if (id) void persistFirmPolicy(next)
    },
    [persistFirmPolicy, policy],
  )

  const toggleOpsEvent = useCallback(
    (key: (typeof OPS_KEYS)[number], enabled: boolean) => {
      if (enabled && !policy[key].template_ref) {
        setPolicy((p) => withOpsMaster({ ...p, [key]: { ...p[key], enabled: true } }))
        openComposer(key)
        return
      }
      const next = withOpsMaster({
        ...policy,
        [key]: { ...policy[key], enabled },
      })
      setPolicy(next)
      void persistFirmPolicy(next)
    },
    [openComposer, persistFirmPolicy, policy],
  )

  const saveClientOverlay = async () => {
    if (!companyId) return
    setSaveBusy(true)
    setSaveNotice(null)
    setError(null)
    try {
      await putLeadLifecycleEmailPolicy(companyId, policy)
      setSaveNotice(t('admin.lead_lifecycle_email.client_overlay_saved'))
      await refreshPreview()
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.save_failed'), t))
    } finally {
      setSaveBusy(false)
    }
  }

  const loadClientOverlay = async () => {
    if (!companyId) return
    setError(null)
    try {
      const out = await getLeadLifecycleEmailPolicy(companyId)
      setPolicy({ ...emptyPolicy(), ...(out.policy || {}) })
      setPolicySource(out.source)
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.load_company'), t))
    }
  }

  const saveVacancyOverride = async () => {
    if (!vacancyId) return
    setSaveBusy(true)
    setError(null)
    try {
      await putVacancyLifecycleEmailOverride(vacancyId, overrideDraft)
      setSaveNotice(t('common.saved'))
      await refreshPreview()
    } catch (err: unknown) {
      setError(getFriendlyErrorInfo(err, t('admin.lead_lifecycle_email.errors.save_override'), t))
    } finally {
      setSaveBusy(false)
    }
  }

  if (loading) {
    return (
      <SettingsSubpageHeader
        backHref={P.settingsCommunications}
        backLabel={t('admin.communications_settings.page_title')}
        kicker={t('admin.lead_lifecycle_email.kicker')}
        title={t('admin.lead_lifecycle_email.page_title')}
        subtitle={t('admin.lead_lifecycle_email.loading')}
      >
        <p className="text-sm text-slate-600">…</p>
      </SettingsSubpageHeader>
    )
  }

  return (
    <SettingsSubpageHeader
      backHref={P.settingsCommunications}
      backLabel={t('admin.communications_settings.page_title')}
      kicker={t('admin.lead_lifecycle_email.kicker')}
      title={t('admin.lead_lifecycle_email.page_title')}
      subtitle={t('admin.lead_lifecycle_email.subtitle')}
    >
      {error ? <ErrorRecoveryBanner info={error} {...friendlyErrorBannerSecondary(error)} /> : null}
      {saveNotice ? <p className="mb-3 text-sm text-emerald-700">{saveNotice}</p> : null}

      {ownCompanies.length > 1 ? (
        <label className="mb-4 block text-sm font-medium text-slate-800">
          {t('admin.lead_lifecycle_email.own_company')}
          <select
            className="input mt-1 w-full max-w-lg"
            value={ownCompanyId}
            onChange={(e) => setOwnCompanyId(e.target.value)}
          >
            <option value="">{t('admin.lead_lifecycle_email.select_own_company')}</option>
            {ownCompanies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {!ownCompanyId ? (
        <p className="text-sm text-slate-600">{t('admin.lead_lifecycle_email.select_own_to_edit')}</p>
      ) : (
        <div className="space-y-4">
          <section
            className={
              rodoActive
                ? 'rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950'
                : 'rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950'
            }
          >
            <p className="font-semibold">
              {t('admin.lead_lifecycle_email.status.platform_required')}
            </p>
            <p className="mt-1 text-sm">
              {rodoActive
                ? t('admin.lead_lifecycle_email.status.active_detail', {
                    values: { name: selectedRodoName || t('admin.lead_lifecycle_email.rodo.message') },
                  })
                : t('admin.lead_lifecycle_email.status.platform_required_detail')}
            </p>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">
              {t('admin.lead_lifecycle_email.rodo.duty_title')}
            </h2>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-slate-600">{t('admin.lead_lifecycle_email.rodo.document')}</span>
              {rodoDocument ? (
                <span className="font-medium text-emerald-800">
                  {t('admin.lead_lifecycle_email.rodo.document_ok', {
                    values: { name: ownCompanyName || rodoDocument.versionId },
                  })}
                </span>
              ) : (
                <Link to={P.settingsLegal} className="font-medium text-brand-700 hover:underline">
                  {t('admin.lead_lifecycle_email.rodo.document_missing')}
                </Link>
              )}
            </div>

            <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
              <p className="text-sm font-medium text-slate-900">
                {t('admin.lead_lifecycle_email.rodo.obligation_status')}
              </p>
              <p className="mt-1 text-xs text-slate-600">
                {t('admin.lead_lifecycle_email.rodo.obligation_status_hint')}
              </p>
            </div>

            {activeTemplates.length === 0 ? (
              <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
                <p className="text-sm font-medium text-slate-900">
                  {t('admin.lead_lifecycle_email.rodo.empty_title')}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {t('admin.lead_lifecycle_email.rodo.empty_body')}
                </p>
                <button type="button" className="btn-primary mt-3" onClick={() => openComposer('rodo')}>
                  {t('admin.lead_lifecycle_email.rodo.create_message')}
                </button>
              </div>
            ) : (
              <div className="mt-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <label className="text-sm text-slate-700" htmlFor="rodo-email-template">
                    {t('admin.lead_lifecycle_email.rodo.message')}
                  </label>
                  <button
                    type="button"
                    className="text-xs font-medium text-brand-700 hover:underline"
                    onClick={() => openComposer('rodo', policy.rodo_template_ref)}
                  >
                    {t('admin.lead_lifecycle_email.rodo.edit_message')}
                  </button>
                </div>
                <div className="mt-1 flex flex-wrap gap-2">
                  <select
                    id="rodo-email-template"
                    className="input min-w-[16rem] flex-1"
                    value={policy.rodo_template_ref ?? ''}
                    onChange={(e) => selectRodoMessage(e.target.value || null)}
                  >
                    <option value="">{t('admin.lead_lifecycle_email.template.select')}</option>
                    {activeTemplates.map((tpl) => (
                      <option key={tpl.id} value={tpl.id}>
                        {tpl.name}
                      </option>
                    ))}
                  </select>
                  <button type="button" className="btn-secondary" onClick={() => openComposer('rodo')}>
                    {t('admin.lead_lifecycle_email.rodo.create_message')}
                  </button>
                </div>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold text-slate-900">
              {t('admin.lead_lifecycle_email.ops.section')}
            </h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[32rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3 font-medium">{t('admin.lead_lifecycle_email.ops.col_event')}</th>
                    <th className="py-2 pr-3 font-medium">{t('admin.lead_lifecycle_email.ops.col_send')}</th>
                    <th className="py-2 font-medium">{t('admin.lead_lifecycle_email.ops.col_message')}</th>
                  </tr>
                </thead>
                <tbody>
                  {OPS_KEYS.map((key) => {
                    const block = policy[key]
                    const name = templateName(templates, block.template_ref)
                    return (
                      <tr key={key} className="border-b border-slate-100">
                        <td className="py-3 pr-3 font-medium text-slate-800">{opsLabel(key)}</td>
                        <td className="py-3 pr-3">
                          <Checkbox
                            checked={Boolean(policy.ops_enabled && block.enabled)}
                            onChange={(checked) => toggleOpsEvent(key, checked)}
                            disabled={saveBusy}
                            label={
                              policy.ops_enabled && block.enabled
                                ? t('admin.lead_lifecycle_email.ops.on')
                                : t('admin.lead_lifecycle_email.ops.off')
                            }
                          />
                        </td>
                        <td className="py-3">
                          {name ? (
                            <button
                              type="button"
                              className="text-left font-medium text-brand-700 hover:underline"
                              onClick={() => openComposer(key, block.template_ref)}
                            >
                              {name}
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="text-brand-700 hover:underline"
                              onClick={() => openComposer(key)}
                            >
                              {t('admin.lead_lifecycle_email.ops.configure')}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <div>
            <button
              type="button"
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
              onClick={() => setShowAdvanced((v) => !v)}
            >
              {showAdvanced
                ? t('admin.lead_lifecycle_email.advanced.hide')
                : t('admin.lead_lifecycle_email.advanced.show')}
            </button>
          </div>

          {showAdvanced ? (
            <div className="space-y-4 rounded-lg border border-dashed border-slate-300 p-4">
              <label className="block text-sm font-medium text-slate-800">
                {t('admin.lead_lifecycle_email.client_overlay')}
                <select
                  className="input mt-1 w-full max-w-lg"
                  value={companyId}
                  onChange={(e) => setCompanyId(e.target.value)}
                >
                  <option value="">{t('admin.lead_lifecycle_email.none_firm_only')}</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              {companyId ? (
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary btn-sm" disabled={saveBusy} onClick={() => void loadClientOverlay()}>
                    {t('admin.lead_lifecycle_email.load_client_overlay')}
                  </button>
                  <button type="button" className="btn-secondary btn-sm" disabled={saveBusy} onClick={() => void saveClientOverlay()}>
                    {t('admin.lead_lifecycle_email.save_client_overlay')}
                  </button>
                </div>
              ) : null}

              <p className="text-sm text-slate-600">{t('admin.lead_lifecycle_email.advanced.platform_rodo_note')}</p>

              <div>
                <button
                  type="button"
                  className="text-sm font-medium text-slate-600 hover:text-slate-900"
                  onClick={() => setShowTechnical((v) => !v)}
                >
                  {showTechnical
                    ? t('admin.lead_lifecycle_email.advanced.hide_technical')
                    : t('admin.lead_lifecycle_email.advanced.show_technical')}
                </button>
              </div>

              {showTechnical ? (
                <section className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-900">
                      {t('admin.lead_lifecycle_email.section.preview')}
                    </h3>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => void refreshPreview()}>
                      {t('admin.lead_lifecycle_email.refresh')}
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{t('admin.lead_lifecycle_email.source_hint', { values: { source: layerLabel(policySource) } })}</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <label className="text-sm text-slate-700">
                      {t('admin.lead_lifecycle_email.preview.purpose')}
                      <select
                        className="input mt-1 w-full"
                        value={previewPurpose}
                        onChange={(e) => setPreviewPurpose(e.target.value)}
                      >
                        {PURPOSE_KEYS.map((key) => (
                          <option key={key} value={key}>
                            {purposeLabel(key)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm text-slate-700 md:col-span-2">
                      {t('admin.lead_lifecycle_email.vacancy_context')}
                      <select className="input mt-1 w-full" value={vacancyId} onChange={(e) => setVacancyId(e.target.value)}>
                        <option value="">{t('admin.lead_lifecycle_email.company_only')}</option>
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
                        <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.send')}</dt>
                        <dd>{preview.send ? t('common.yes') : t('common.no')}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.enabled')}</dt>
                        <dd>{preview.enabled ? t('common.yes') : t('common.no')}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.layer')}</dt>
                        <dd>{layerLabel(preview.source_layer)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.block_code')}</dt>
                        <dd>{blockLabel(preview.block_code)}</dd>
                      </div>
                      <div className="sm:col-span-2">
                        <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.template_ref')}</dt>
                        <dd className="font-mono text-xs">{preview.template_ref || t('common.labels.not_available')}</dd>
                      </div>
                      {preview.reason ? (
                        <div className="sm:col-span-2">
                          <dt className="text-xs uppercase tracking-wide text-slate-500">{t('admin.lead_lifecycle_email.preview.reason')}</dt>
                          <dd>{reasonLabel(preview)}</dd>
                        </div>
                      ) : null}
                    </dl>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">{t('admin.lead_lifecycle_email.preview.empty')}</p>
                  )}

                  <h3 className="mt-6 text-sm font-semibold text-slate-900">
                    {t('admin.lead_lifecycle_email.section.vacancy_override')}
                  </h3>
                  <p className="mt-1 text-xs text-slate-600">{t('admin.lead_lifecycle_email.vacancy_override_hint')}</p>
                  {!vacancyId ? (
                    <p className="mt-2 text-sm text-slate-500">{t('admin.lead_lifecycle_email.select_vacancy_for_override')}</p>
                  ) : (
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      {PURPOSE_KEYS.map((purposeKey) => {
                        const key = purposeKey === 'gdpr_notice' ? 'gdpr_notice' : purposeKey
                        const opsKey =
                          purposeKey === 'submission_acknowledgement'
                            ? 'application_received'
                            : purposeKey === 'intake_rejection_notice'
                              ? 'rejection'
                              : purposeKey === 'moving_forward_notice'
                                ? 'moving_forward'
                                : 'gdpr_notice'
                        const block = overrideDraft[opsKey] || overrideDraft[key] || {}
                        return (
                          <div key={purposeKey} className="rounded border border-slate-100 p-3">
                            <p className="text-sm font-medium text-slate-800">{purposeLabel(purposeKey)}</p>
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
                              {t('admin.lead_lifecycle_email.override_enabled')}
                            </label>
                            <select
                              className="input mt-2 w-full"
                              value={block.template_ref ?? ''}
                              onChange={(e) =>
                                setOverrideDraft((d) => ({
                                  ...d,
                                  [opsKey]: { ...block, template_ref: e.target.value || null },
                                }))
                              }
                            >
                              <option value="">{t('admin.lead_lifecycle_email.template.select')}</option>
                              {activeTemplates.map((tpl) => (
                                <option key={tpl.id} value={tpl.id}>
                                  {tpl.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        )
                      })}
                      <div className="md:col-span-2">
                        <button type="button" className="btn-secondary" disabled={saveBusy} onClick={() => void saveVacancyOverride()}>
                          {t('admin.lead_lifecycle_email.save_vacancy_override')}
                        </button>
                      </div>
                    </div>
                  )}
                </section>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      <LeadLifecycleMessageModal
        open={composerOpen}
        purpose={composerPurpose}
        draft={composerDraft}
        busy={composerBusy}
        onChange={setComposerDraft}
        onClose={() => setComposerOpen(false)}
        onSaveAndUse={() => void saveAndUseMessage()}
      />
    </SettingsSubpageHeader>
  )
}
