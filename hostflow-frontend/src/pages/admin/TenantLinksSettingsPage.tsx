import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import { useMetaStages } from '../../store/useMeta'
import {
  listTenantLinks,
  updateTenantLink,
  createTenantLink,
  getContactPolicy,
  type TenantLink,
  type ContactPolicy,
} from '../../api/tenantLinks'
import { useToast } from '../../components/Toast'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { ContactPolicyForm } from '../../components/clients/ContactPolicyForm'

export default function TenantLinksSettingsPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const { notify } = useToast()
  const meta = useMetaStages()
  const stageOptions = meta?.order || meta?.codes || []

  const tenantId = (currentTenantId ?? (me as { tenant_id?: string })?.tenant_id)?.trim()
  const [links, setLinks] = useState<TenantLink[]>([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [addOrgOpen, setAddOrgOpen] = useState(false)
  const [addOrgTenantId, setAddOrgTenantId] = useState('')
  const [addOrgHandoff, setAddOrgHandoff] = useState(true)
  const [addOrgSaving, setAddOrgSaving] = useState(false)

  const load = useCallback(async () => {
    if (!tenantId) return
    try {
      setLoading(true)
      const data = await listTenantLinks(tenantId)
      setLinks(data)
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
      setLinks([])
    } finally {
      setLoading(false)
    }
  }, [tenantId, notify])

  useEffect(() => {
    void load()
  }, [load])

  const handleHandoffToggle = async (link: TenantLink, enabled: boolean) => {
    if (!tenantId) return
    setSavingId(link.id)
    try {
      const updated = await updateTenantLink(tenantId, link.id, { handoff_enabled: enabled })
      setLinks((prev) => prev.map((l) => (l.id === link.id ? updated : l)))
      notify({
        title: t('admin.tenant_links.handoff_updated'),
        variant: 'success',
      })
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSavingId(null)
    }
  }

  const handleAddOrgLink = async () => {
    if (!tenantId || !addOrgTenantId.trim()) return
    const tid = addOrgTenantId.trim().replace(/\s/g, '')
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(tid)) {
      notify({ title: t('admin.tenant_links.invalid_uuid'), variant: 'error' })
      return
    }
    setAddOrgSaving(true)
    try {
      const created = await createTenantLink(tenantId, {
        client_tenant_id: tid,
        handoff_enabled: addOrgHandoff,
      })
      setLinks((prev) => [...prev, created])
      setAddOrgTenantId('')
      setAddOrgOpen(false)
      notify({
        title: t('admin.tenant_links.link_created'),
        variant: 'success',
      })
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setAddOrgSaving(false)
    }
  }

  const handleContactPolicySave = async (link: TenantLink, policy: ContactPolicy) => {
    if (!tenantId) return
    setSavingId(link.id)
    try {
      const updated = await updateTenantLink(tenantId, link.id, { contact_policy: policy })
      setLinks((prev) => prev.map((l) => (l.id === link.id ? updated : l)))
      setExpandedId(null)
      notify({
        title: t('admin.tenant_links.policy_updated'),
        variant: 'success',
      })
    } catch (e: unknown) {
      notify({
        title: (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSavingId(null)
    }
  }

  if (!tenantId) {
    return (
      <div className="settings-panel">
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <section className="settings-panel">
        <div className="mb-4">
          <SettingsSubpageHeader
            backLabel={t('admin.settings.subpage.back_all')}
            kicker={t('admin.tenant_links.header_kicker')}
            title={t('admin.tenant_links.title')}
            subtitle={t('admin.tenant_links.subtitle')}
          />
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : (
          <>
            <div className="settings-toolbar mb-4">
              <button
                type="button"
                onClick={() => setAddOrgOpen((o) => !o)}
                className="btn-secondary btn-sm"
              >
                {addOrgOpen
                  ? t('admin.tenant_links.cancel_add')
                  : t('admin.tenant_links.add_org_link')}
              </button>
              {addOrgOpen && (
                <div className="mt-3 rounded-xl border border-brand-100 bg-white p-4">
                  <p className="mb-2 text-sm text-slate-600">
                    {t('admin.tenant_links.add_org_hint')}
                  </p>
                  <div className="flex flex-wrap items-end gap-3">
                    <div className="min-w-[280px] flex-1">
                      <label className="label">
                        {t('admin.tenant_links.tenant_uuid')}
                      </label>
                      <input
                        type="text"
                        value={addOrgTenantId}
                        onChange={(e) => setAddOrgTenantId(e.target.value)}
                        placeholder={t('admin.tenant_links.placeholders.tenant_uuid', {
                          defaultValue: '517319d0-b53e-493d-9ac8-40f23091a35d',
                        })}
                        className="input mt-1 font-mono text-sm"
                      />
                    </div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={addOrgHandoff}
                        onChange={(e) => setAddOrgHandoff(e.target.checked)}
                      />
                      <span className="text-sm">
                        {t('admin.tenant_links.handoff_label')}
                      </span>
                    </label>
                    <button
                      type="button"
                      onClick={handleAddOrgLink}
                      disabled={addOrgSaving || !addOrgTenantId.trim()}
                      className="btn-primary"
                    >
                      {addOrgSaving
                        ? t('common.saving')
                        : t('common.actions.add')}
                    </button>
                  </div>
                </div>
              )}
            </div>
            {links.length === 0 && !addOrgOpen ? (
              <p className="text-sm text-slate-500">
                {t('admin.tenant_links.no_links')}
              </p>
            ) : (
          <ul className="space-y-3">
            {links.map((link) => (
              <LinkRow
                key={link.id}
                link={link}
                stageOptions={stageOptions}
                saving={savingId === link.id}
                expanded={expandedId === link.id}
                onToggleExpand={() => setExpandedId((id) => (id === link.id ? null : link.id))}
                onHandoffToggle={(enabled) => handleHandoffToggle(link, enabled)}
                onContactPolicySave={(policy) => handleContactPolicySave(link, policy)}
              />
            ))}
          </ul>
            )}
          </>
        )}
      </section>
    </div>
  )
}

function LinkRow({
  link,
  stageOptions,
  saving,
  expanded,
  onToggleExpand,
  onHandoffToggle,
  onContactPolicySave,
}: {
  link: TenantLink
  stageOptions: string[]
  saving: boolean
  expanded: boolean
  onToggleExpand: () => void
  onHandoffToggle: (enabled: boolean) => void
  onContactPolicySave: (policy: ContactPolicy) => void
}) {
  const { t } = useI18n()
  const policy = getContactPolicy(link)
  const companyLabel = link.company_name || link.client_company_id || '—'

  return (
    <li className="card border-slate-200 bg-brand-50/30 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-medium text-slate-900">{companyLabel}</div>
          {link.client_company_id && (
            <span className="badge mt-1 bg-slate-100 text-slate-600">{t('admin.tenant_links.type_company')}</span>
          )}
          {link.client_tenant_id && (
            <span className="badge mt-1 bg-brand-100 text-brand-700">{t('admin.tenant_links.type_org')}</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!link.handoff_enabled}
              disabled={saving}
              onChange={(e) => onHandoffToggle(e.target.checked)}
            />
            <span className="text-sm">{t('admin.tenant_links.handoff_label')}</span>
          </label>
          <button
            type="button"
            onClick={onToggleExpand}
            className="btn-secondary btn-sm"
          >
            {expanded
              ? t('admin.tenant_links.hide_policy')
              : t('admin.tenant_links.edit_policy')}
          </button>
        </div>
      </div>
      {expanded && (
        <ContactPolicyForm
          policy={policy}
          stageOptions={stageOptions}
          saving={saving}
          onSave={onContactPolicySave}
        />
      )}
    </li>
  )
}
