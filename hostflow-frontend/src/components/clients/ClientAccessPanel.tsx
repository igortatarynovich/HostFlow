import { useState } from 'react'
import { useI18n } from '../../i18n'
import { useMetaStages } from '../../store/useMeta'
import {
  createPortalLink,
  createTenantLink,
  getContactPolicy,
  revokePortalLink,
  updateTenantLink,
  type ContactPolicy,
  type TenantLink,
} from '../../api/tenantLinks'
import { ContactPolicyForm } from './ContactPolicyForm'

type ClientAccessPanelProps = {
  tenantId: string
  companyId: string
  link: TenantLink | null
  loading: boolean
  onLinkUpdated: (link: TenantLink | null) => void
  onNotify: (payload: { title: string; variant: 'success' | 'error' }) => void
}

export function ClientAccessPanel({
  tenantId,
  companyId,
  link,
  loading,
  onLinkUpdated,
  onNotify,
}: ClientAccessPanelProps) {
  const { t } = useI18n()
  const meta = useMetaStages()
  const stageOptions = meta?.order || meta?.codes || []
  const [saving, setSaving] = useState(false)
  const [portalBusy, setPortalBusy] = useState(false)
  const [creatingLink, setCreatingLink] = useState(false)
  const [policyExpanded, setPolicyExpanded] = useState(false)

  const handleCreateLink = async () => {
    setCreatingLink(true)
    try {
      const created = await createTenantLink(tenantId, {
        client_company_id: companyId,
        handoff_enabled: true,
      })
      onLinkUpdated(created)
      onNotify({
        title: t('app.clients.access_link_created', { defaultValue: 'Client access configured.' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onNotify({ title: typeof msg === 'string' ? msg : String(msg), variant: 'error' })
    } finally {
      setCreatingLink(false)
    }
  }

  const handleToggle = async (patch: {
    handoff_enabled?: boolean
    see_vacancies?: boolean
    see_reduced_profiles?: boolean
  }) => {
    if (!link) return
    setSaving(true)
    try {
      const updated = await updateTenantLink(tenantId, link.id, patch)
      onLinkUpdated(updated)
      onNotify({ title: t('common.saved'), variant: 'success' })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onNotify({ title: typeof msg === 'string' ? msg : String(msg), variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const handlePolicySave = async (policy: ContactPolicy) => {
    if (!link) return
    setSaving(true)
    try {
      const updated = await updateTenantLink(tenantId, link.id, { contact_policy: policy })
      onLinkUpdated(updated)
      setPolicyExpanded(false)
      onNotify({
        title: t('admin.tenant_links.policy_updated', { defaultValue: 'Contact policy updated.' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onNotify({ title: typeof msg === 'string' ? msg : String(msg), variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const handleCreatePortal = async () => {
    if (!link) return
    setPortalBusy(true)
    try {
      const out = await createPortalLink(tenantId, link.id)
      onLinkUpdated({ ...link, portal_token: out.token, portal_expires_at: out.expires_at })
      onNotify({
        title: t('app.clients.portal_created', { defaultValue: 'Portal link created.' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onNotify({ title: typeof msg === 'string' ? msg : String(msg), variant: 'error' })
    } finally {
      setPortalBusy(false)
    }
  }

  const handleRevokePortal = async () => {
    if (!link) return
    setPortalBusy(true)
    try {
      await revokePortalLink(tenantId, link.id)
      onLinkUpdated({ ...link, portal_token: null, portal_expires_at: null })
      onNotify({
        title: t('app.clients.portal_revoked', { defaultValue: 'Portal link revoked.' }),
        variant: 'success',
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onNotify({ title: typeof msg === 'string' ? msg : String(msg), variant: 'error' })
    } finally {
      setPortalBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }

  if (!link) {
    return (
      <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
        <p className="text-sm text-slate-700">
          {t('app.clients.access_not_configured', {
            defaultValue: 'Access settings are not linked yet. Configure them to enable handoff, portal, and contact attempts.',
          })}
        </p>
        <button type="button" className="btn-primary mt-3" disabled={creatingLink} onClick={() => void handleCreateLink()}>
          {creatingLink ? t('common.saving') : t('app.clients.configure_access', { defaultValue: 'Configure access' })}
        </button>
      </div>
    )
  }

  const policy = getContactPolicy(link)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-6">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(link.handoff_enabled)}
            disabled={saving}
            onChange={(e) => void handleToggle({ handoff_enabled: e.target.checked })}
          />
          <span className="text-sm">{t('app.clients.handoff_label')}</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(link.see_vacancies)}
            disabled={saving}
            onChange={(e) => void handleToggle({ see_vacancies: e.target.checked })}
          />
          <span className="text-sm">{t('app.clients.see_vacancies_label')}</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(link.see_reduced_profiles)}
            disabled={saving}
            onChange={(e) => void handleToggle({ see_reduced_profiles: e.target.checked })}
          />
          <span className="text-sm">{t('app.clients.see_reduced_label')}</span>
        </label>
      </div>

      <div className="border-t border-slate-100 pt-3">
        <p className="mb-2 text-sm font-medium text-slate-700">{t('app.clients.portal_access')}</p>
        {link.portal_token ? (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                const url = `${window.location.origin}/client-portal?token=${link.portal_token}`
                void navigator.clipboard.writeText(url)
              }}
            >
              {t('common.copy')}
            </button>
            <button type="button" className="btn-danger btn-sm" disabled={portalBusy} onClick={() => void handleRevokePortal()}>
              {t('app.clients.revoke_link')}
            </button>
          </div>
        ) : (
          <button type="button" className="btn-secondary btn-sm" disabled={portalBusy} onClick={() => void handleCreatePortal()}>
            {t('app.clients.create_portal_link')}
          </button>
        )}
      </div>

      <div className="border-t border-slate-100 pt-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-slate-700">
              {t('admin.tenant_links.contact_policy_title', { defaultValue: 'Contact attempts' })}
            </p>
            <p className="text-xs text-slate-500">
              {policy.enabled
                ? t('app.clients.contact_policy_active', {
                    defaultValue: 'Enabled · max {count} attempts',
                    values: { count: String(policy.max_attempts) },
                  })
                : t('app.clients.contact_policy_inactive', { defaultValue: 'Disabled for this client' })}
            </p>
          </div>
          <button type="button" className="btn-secondary btn-sm" onClick={() => setPolicyExpanded((v) => !v)}>
            {policyExpanded ? t('admin.tenant_links.hide_policy') : t('admin.tenant_links.edit_policy')}
          </button>
        </div>
        {policyExpanded && (
          <ContactPolicyForm
            policy={policy}
            stageOptions={stageOptions}
            saving={saving}
            onSave={(p) => void handlePolicySave(p)}
            compact
          />
        )}
      </div>
    </div>
  )
}
