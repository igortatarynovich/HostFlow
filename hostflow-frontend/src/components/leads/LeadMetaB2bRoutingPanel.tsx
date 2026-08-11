import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listAdditionalServices } from '../../api/additionalServices'
import { getUnmappedLeads, putMetaFormRoute, retryLeads } from '../../api/metaLeads'
import type { Lead } from '../../api/types'
import type { LeadTargetType } from '../../api/types/lead'
import type { AdditionalService } from '../../api/types/service'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import {
  inquiryMetaAttribution,
  isMetaAdNotMappedLead,
  isMetaB2bCandidateLead,
  metaIntakeRouteSettingsHref,
  metaLeadFormId,
  metaLeadNormalized,
  metaLeadOwnCompanyId,
  metaLeadPageId,
} from '../../utils/metaLeadB2b'

type Props = {
  lead: Lead
  retrying?: boolean
  onRetry: () => void | Promise<void>
  /** Reload lead (and timeline) after the route is applied. */
  onRefreshed?: () => void | Promise<void>
}

type RouteChoice = Extract<LeadTargetType, 'candidate' | 'client_lead' | 'service_order_lead'>

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

/**
 * Inline "Needs Routing" control. A Meta lead landed here because its form has no
 * route (or fell into recruitment without a vacancy). The operator picks the
 * destination once — candidates / companies / service — and (by default) the
 * decision is remembered for the whole form so future leads never fall in again.
 */
export default function LeadMetaB2bRoutingPanel({ lead, retrying = false, onRetry, onRefreshed }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()

  const [choice, setChoice] = useState<RouteChoice | null>(null)
  const [serviceCode, setServiceCode] = useState('')
  const [applyToForm, setApplyToForm] = useState(true)
  const [services, setServices] = useState<AdditionalService[]>([])
  const [servicesLoading, setServicesLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const formId = metaLeadFormId(lead)
  const pageId = metaLeadPageId(lead)
  const ownCompanyId = metaLeadOwnCompanyId(lead)
  const adId = lead.ad_id ?? (metaLeadNormalized(lead).ad_id as number | undefined) ?? null
  const formName = inquiryMetaAttribution(lead)?.formLabel ?? null
  const settingsHref = metaIntakeRouteSettingsHref(formId, pageId)

  const loadServices = useCallback(async () => {
    if (services.length > 0 || servicesLoading) return
    setServicesLoading(true)
    try {
      const list = await listAdditionalServices(false, false)
      setServices(Array.isArray(list) ? list.filter((s) => s.is_active) : [])
    } catch {
      setServices([])
    } finally {
      setServicesLoading(false)
    }
  }, [services.length, servicesLoading])

  useEffect(() => {
    if (choice === 'service_order_lead') void loadServices()
  }, [choice, loadServices])

  const handleApply = useCallback(async () => {
    if (!choice || !formId) return
    if (!ownCompanyId) {
      notify({
        title: t('app.leads.needs_routing.errors.no_own_company', { defaultValue: 'Could not resolve own company. Configure the route in Meta integration.',
        }),
        variant: 'error',
      })
      return
    }
    if (choice === 'service_order_lead' && !serviceCode) {
      notify({
        title: t('app.leads.needs_routing.errors.no_service', { defaultValue: 'Select a service from the catalog' }),
        variant: 'error',
      })
      return
    }

    setSaving(true)
    try {
      await putMetaFormRoute(formId, {
        own_company_id: ownCompanyId,
        lead_target_type: choice,
        service_code: choice === 'service_order_lead' ? serviceCode : null,
        page_id: pageId ?? undefined,
        source: 'meta',
        is_active: true,
      })

      const leadIds = new Set<string>([String(lead.id)])
      if (applyToForm) {
        try {
          const res = await getUnmappedLeads({ status: 'needs_routing', limit_per_ad: 200 })
          for (const group of res.groups ?? []) {
            for (const sibling of group.leads ?? []) {
              const sForm = String(record(sibling.normalized).form_id ?? '').trim()
              if (sForm && sForm === formId && sibling.id) leadIds.add(String(sibling.id))
            }
          }
        } catch {
          // Non-fatal: still reprocess at least the current lead.
        }
      }

      const result = await retryLeads({ lead_ids: Array.from(leadIds), refresh_graph: true })
      notify({
        title: t('app.leads.needs_routing.applied', { defaultValue: 'Route saved · reprocessed: {count}',
          values: { count: String(result.processed ?? 0) },
        }),
        variant: 'success',
      })
      if (onRefreshed) await onRefreshed()
      else await onRetry()
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        'Failed'
      notify({
        title: t('app.leads.needs_routing.errors.apply', { defaultValue: 'Could not apply route' }),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }, [applyToForm, choice, formId, lead.id, notify, onRefreshed, onRetry, ownCompanyId, pageId, serviceCode, t])

  if (isMetaB2bCandidateLead(lead)) return null
  if (!isMetaAdNotMappedLead(lead)) return null

  const busy = saving || retrying
  const routeBtn = (key: RouteChoice, label: string) => (
    <button
      type="button"
      className={
        'inline-flex rounded-lg border px-3 py-2 text-sm font-medium transition ' +
        (choice === key
          ? 'border-blue-600 bg-blue-600 text-white'
          : 'border-blue-300 bg-white text-blue-900 hover:bg-blue-50')
      }
      aria-pressed={choice === key}
      disabled={busy}
      onClick={() => setChoice(key)}
    >
      {label}
    </button>
  )

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/80 p-4">
      <p className="text-sm font-semibold text-blue-950">
        {t('app.leads.needs_routing.title', { defaultValue: 'Where should this inquiry go?' })}
      </p>
      <p className="mt-1 text-sm text-blue-900">
        {t('app.leads.needs_routing.body', { defaultValue: 'This Meta form arrived without a route. Choose a stream once — you can apply it to the whole form so similar inquiries no longer land in recruitment without a vacancy.',
        })}
      </p>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-blue-800/90 sm:grid-cols-3">
        {formId ? (
          <div>
            <dt className="text-blue-700/70">Form ID</dt>
            <dd className="font-medium">{formId}</dd>
          </div>
        ) : null}
        {adId != null && String(adId).trim() ? (
          <div>
            <dt className="text-blue-700/70">Ad ID</dt>
            <dd className="font-medium">{String(adId)}</dd>
          </div>
        ) : null}
        {formName ? (
          <div>
            <dt className="text-blue-700/70">{t('app.leads.needs_routing.form_name', { defaultValue: 'Form' })}</dt>
            <dd className="font-medium">{formName}</dd>
          </div>
        ) : null}
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {routeBtn('candidate', t('app.leads.needs_routing.route.candidates', { defaultValue: 'These are candidates' }))}
        {routeBtn('client_lead', t('app.leads.needs_routing.route.companies', { defaultValue: 'These are companies' }))}
        {routeBtn('service_order_lead', t('app.leads.needs_routing.route.service', { defaultValue: 'This is a service' }))}
      </div>

      {choice === 'service_order_lead' ? (
        <label className="mt-3 block max-w-md text-xs font-medium text-blue-900">
          <div className="mb-1">{t('app.leads.needs_routing.pick_service', { defaultValue: 'Service from catalog' })}</div>
          <select
            className="input h-9 w-full rounded-lg border-blue-300 bg-white px-3 text-sm"
            value={serviceCode}
            onChange={(e) => setServiceCode(e.target.value)}
            disabled={servicesLoading || busy}
          >
            <option value="">
              {servicesLoading ? t('common.loading') : t('app.leads.needs_routing.pick_service_placeholder', { defaultValue: 'Select a service…' })}
            </option>
            {services.map((s) => (
              <option key={s.id} value={s.code}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <label className="mt-3 flex items-center gap-2 text-sm text-blue-900">
        <input
          type="checkbox"
          className="h-4 w-4 rounded border-blue-300"
          checked={applyToForm}
          onChange={(e) => setApplyToForm(e.target.checked)}
          disabled={busy}
        />
        {t('app.leads.needs_routing.apply_to_form', { defaultValue: 'Apply to all inquiries from this form' })}
      </label>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="inline-flex rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          disabled={busy || !choice || !formId || (choice === 'service_order_lead' && !serviceCode)}
          onClick={() => void handleApply()}
        >
          {saving
            ? t('common.loading')
            : t('app.leads.needs_routing.apply', { defaultValue: 'Apply route and reprocess' })}
        </button>
        <Link to={settingsHref} className="text-xs text-blue-700 hover:text-blue-900 hover:underline">
          {t('app.leads.needs_routing.open_settings', { defaultValue: 'Open route settings' })}
        </Link>
      </div>

      {!ownCompanyId ? (
        <p className="mt-2 text-xs text-rose-700">
          {t('app.leads.needs_routing.no_own_company_hint', { defaultValue: 'Own company is not resolved — configure the form route in Meta integration.',
          })}
        </p>
      ) : null}
    </div>
  )
}
