import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listVacancies } from '../../api/client'
import { rerouteMetaLead, retryLeads } from '../../api/metaLeads'
import type { Lead } from '../../api/types'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { isMetaProblemLead } from '../../utils/leadCrm'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { getLeadErrorSuggestion } from '../../utils/leadErrorSuggestion'

type Props = {
  lead: Lead
  /** Reload lead (and optionally timeline) after retry / reroute. */
  onRefreshed: () => void | Promise<void>
}

/**
 * Meta lead error troubleshooting (retry, reroute, integration links) — same flows as Leads inbox Fix tab.
 */
export default function LeadMetaProblemPanel({ lead, onRefreshed }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()

  const show = useMemo(() => isMetaProblemLead(lead), [lead])
  const suggestion = useMemo(
    () => (show ? getLeadErrorSuggestion(lead.error, t) : null),
    [lead.error, show, t],
  )

  const [vacanciesLoading, setVacanciesLoading] = useState(false)
  const [vacanciesError, setVacanciesError] = useState<string | null>(null)
  const [vacancyOptions, setVacancyOptions] = useState<Array<{ id: string; title: string }>>([])
  const [rerouteVacancyId, setRerouteVacancyId] = useState('')
  const [retrying, setRetrying] = useState(false)
  const [rerouting, setRerouting] = useState(false)

  const loadVacancies = useCallback(async () => {
    setVacanciesLoading(true)
    setVacanciesError(null)
    try {
      const res = await listVacancies({ limit: 200, offset: 0 })
      const items = Array.isArray((res as { items?: unknown })?.items)
        ? (res as { items: unknown[] }).items
        : Array.isArray(res)
          ? (res as unknown[])
          : []
      const normalized = items
        .map((v: unknown) => {
          const row = v as Record<string, unknown>
          return {
            id: String(row?.id ?? ''),
            title: String(row?.title ?? row?.vacancy_title ?? ''),
          }
        })
        .filter((v) => v.id && v.title)
      setVacancyOptions(normalized)
    } catch (err: unknown) {
      const msg = String(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          'Failed',
      )
      setVacanciesError(msg)
      notify({
        title: t('app.vacancies.list.errors.load_failed'),
        description: msg,
        variant: 'error',
      })
    } finally {
      setVacanciesLoading(false)
    }
  }, [notify, t])

  useEffect(() => {
    if (!show || suggestion?.tab !== 'field_mapping') return
    if (vacancyOptions.length > 0) return
    if (vacanciesLoading) return
    void loadVacancies()
  }, [loadVacancies, show, suggestion?.tab, vacanciesLoading, vacancyOptions.length])

  useEffect(() => {
    if (!show || suggestion?.tab !== 'field_mapping') return
    const pre = lead.vacancy_id ? String(lead.vacancy_id) : ''
    setRerouteVacancyId(pre)
  }, [lead.id, lead.vacancy_id, show, suggestion?.tab])

  const handleRetry = useCallback(async () => {
    setRetrying(true)
    try {
      const result = await retryLeads({ lead_ids: [String(lead.id)], refresh_graph: true })
      const item = result.items?.[0]
      if (item?.processed) {
        notify({ title: t('app.leads.messages.processed'), variant: 'success' })
      } else if (item?.message) {
        notify({
          title: t('app.leads.messages.process_failed'),
          description: item.message,
          variant: 'error',
        })
      } else {
        notify({
          title: t('app.leads.messages.process_failed'),
          variant: 'error',
        })
      }
      await onRefreshed()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (err as Error)?.message ?? 'Retry failed'
      notify({
        title: t('admin.meta_leads.errors.retry'),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setRetrying(false)
    }
  }, [lead.id, notify, onRefreshed, t])

  const handleReroute = useCallback(async () => {
    if (!rerouteVacancyId.trim()) return
    setRerouting(true)
    try {
      await rerouteMetaLead(lead.id, {
        vacancy_id: rerouteVacancyId.trim(),
        company_id: lead.company_id ?? undefined,
        force_process: true,
      })
      notify({
        title: t('admin.meta_leads.notices.lead_rerouted'),
        variant: 'success',
      })
      await onRefreshed()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (err as Error)?.message ?? 'Reroute failed'
      notify({
        title: t('admin.meta_leads.errors.reroute'),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setRerouting(false)
    }
  }, [lead.company_id, lead.id, notify, onRefreshed, rerouteVacancyId, t])

  if (!show) return null

  const openCredentialsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=credentials`
  const openMappingHref = CRM_APP_PATHS.marketingSources
  const openSettingsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=settings`

  return (
    <div className="mb-6 space-y-3">
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
        <div className="text-xs font-semibold text-rose-700">
          {t('app.leads.inbox.fix.title')}
        </div>
        <div className="mt-1 text-sm text-red-600">{(lead.error ?? '').trim() || '—'}</div>
        {suggestion?.hint ? <div className="mt-2 text-sm text-slate-800">{suggestion.hint}</div> : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn-primary rounded-lg px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-60"
          disabled={retrying}
          onClick={() => void handleRetry()}
        >
          {retrying ? t('common.loading') : t('admin.meta_leads.logs.actions.retry')}
        </button>
        <Link to={CRM_APP_PATHS.automations} className="text-xs text-slate-500 hover:text-brand-700 hover:underline">
          {t('admin.meta_leads.tabs.automation_rules')}
        </Link>
      </div>

      {suggestion?.tab === 'field_mapping' ? (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold text-slate-700">
            {t('admin.meta_leads.logs.actions.reroute')}
          </div>
          {vacanciesError ? <div className="text-xs text-rose-600">{vacanciesError}</div> : null}
          <label className="block text-xs font-medium text-slate-600">
            <div className="mb-1">{t('admin.meta_leads.logs.table.vacancy')}</div>
            <select
              className="input h-9 w-full max-w-md rounded-lg border-slate-300 bg-white px-2.5 text-sm"
              value={rerouteVacancyId}
              onChange={(e) => setRerouteVacancyId(e.target.value)}
              disabled={vacanciesLoading}
            >
              <option value="">
                {vacanciesLoading ? t('common.loading') : t('admin.meta_leads.prompts.reroute_vacancy')}
              </option>
              {vacancyOptions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.title}
                </option>
              ))}
            </select>
          </label>
          {vacancyOptions.length === 0 && !vacanciesLoading ? (
            <Link to={CRM_APP_PATHS.vacancies} className="text-xs text-slate-500 hover:text-brand-700 hover:underline">
              {t('app.vacancies.list.new_vacancy')}
            </Link>
          ) : null}
          <button
            type="button"
            className="btn-primary rounded-lg px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!rerouteVacancyId.trim() || rerouting || vacanciesLoading}
            onClick={() => void handleReroute()}
          >
            {rerouting ? t('common.loading') : t('admin.meta_leads.logs.actions.reroute')}
          </button>
        </div>
      ) : null}

      {suggestion ? (
        <div className="flex flex-wrap items-center gap-2">
          {suggestion.tab === 'advanced' ? (
            <Link to={openCredentialsHref} className="text-xs text-slate-500 hover:text-brand-700 hover:underline">
              {suggestion.actionLabel}
            </Link>
          ) : null}
          {suggestion.tab === 'field_mapping' ? (
            <Link to={openMappingHref} className="text-xs text-slate-500 hover:text-brand-700 hover:underline">
              {suggestion.actionLabel}
            </Link>
          ) : null}
          {suggestion.tab === 'processing' ? (
            <Link to={openSettingsHref} className="text-xs text-slate-500 hover:text-brand-700 hover:underline">
              {suggestion.actionLabel}
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
