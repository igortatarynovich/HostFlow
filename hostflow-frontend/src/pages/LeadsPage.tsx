import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listLeads } from '../api/client'
import type { Lead, LeadListResponse, LeadStatus } from '../api/types'
import { useI18n } from '../i18n'

const STATUS_FILTERS: Array<'' | LeadStatus> = ['', 'new', 'processed', 'duplicated', 'needs_routing', 'failed']
const DATE_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
}

const LOCALE_TO_DATE = {
  en: 'en-US',
  ru: 'ru-RU',
  pl: 'pl-PL',
} as const

export default function LeadsPage() {
  const { t, locale } = useI18n()
  const [status, setStatus] = useState<'' | LeadStatus>('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<LeadListResponse>({ items: [], total: 0, limit: 20, offset: 0 })

  const limit = 20
  const offset = (page - 1) * limit

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listLeads({ status: status || undefined, limit, offset })
      .then((payload: LeadListResponse) => {
        if (!cancelled) {
          setData(payload)
        }
      })
      .catch((err: any) => {
        if (!cancelled) {
          setError(err?.message || t('app.leads.messages.load_failed'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [status, page, t])

  const totalPages = useMemo(() => {
    if (!data.limit) return 1
    return Math.max(1, Math.ceil((data.total || 0) / data.limit))
  }, [data.total, data.limit])

  const canPrev = page > 1
  const canNext = page < totalPages

  const items: Lead[] = useMemo(() => (Array.isArray(data.items) ? data.items : []), [data.items])
  const statusOptions = useMemo<Array<{ value: '' | LeadStatus; label: string }>>(
    () =>
      STATUS_FILTERS.map((value) => ({
        value,
        label: value ? t(`app.leads.statuses.${value}`) : t('app.leads.filters.status_all'),
      })),
    [t]
  )
  const statusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    STATUS_FILTERS.forEach((value) => {
      if (!value) return
      map[value] = t(`app.leads.statuses.${value}`)
    })
    return map
  }, [t])
  const dateFormatter = useMemo(() => {
    const localeCode = LOCALE_TO_DATE[locale as keyof typeof LOCALE_TO_DATE] || 'en-US'
    try {
      return new Intl.DateTimeFormat(localeCode, DATE_FORMAT_OPTIONS)
    } catch (err) {
      return new Intl.DateTimeFormat('en-US', DATE_FORMAT_OPTIONS)
    }
  }, [locale])
  const formatDateValue = (value?: string) => {
    if (!value) return '—'
    try {
      return dateFormatter.format(new Date(value))
    } catch (err) {
      return value
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t('app.leads.title')}</h1>
          <p className="text-sm text-gray-500">{t('app.leads.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">
            {t('app.leads.filters.status')}
            <select
              className="ml-2 rounded border border-gray-300 px-2 py-1 text-sm"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as '' | LeadStatus)
                setPage(1)
              }}
            >
              {statusOptions.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.created')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.status')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.company')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.vacancy')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.contact')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.source')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.candidate')}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">{t('app.leads.table.error')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading && (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                    {t('common.loading')}
                  </td>
                </tr>
              )}
              {error && !loading && (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-red-500">
                    {error}
                  </td>
                </tr>
              )}
              {!loading && !error && items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                    {t('app.leads.states.empty')}
                  </td>
                </tr>
              )}
              {!loading && !error && items.map((lead) => {
                const normalized = lead.normalized || {}
                const contactName = normalized.full_name || `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
                const contactEmail = normalized.email
                const contactPhone = normalized.phone
                const contact = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ')

                return (
                  <tr key={lead.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-600">{formatDateValue(lead.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                        {statusLabels[lead.status] ?? lead.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-800">{lead.company_name || lead.company_id}</td>
                    <td className="px-4 py-3 text-gray-800">{lead.vacancy_title || lead.vacancy_id || '—'}</td>
                    <td className="px-4 py-3 text-gray-700">
                      {contact || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{lead.source}</td>
                    <td className="px-4 py-3 text-blue-600">
                      {lead.candidate_id ? (
                        <Link to={`/app/candidates/${lead.candidate_id}`}>{lead.candidate_name || lead.candidate_id}</Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-red-500">{lead.error || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <footer className="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
          <div>
            {t('app.leads.pagination.shown', { values: { count: items.length, total: data.total } })}
          </div>
          <div className="space-x-2">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => canPrev && setPage((prev) => prev - 1)}
              className="rounded border border-gray-300 px-3 py-1 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('app.leads.pagination.prev')}
            </button>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => canNext && setPage((prev) => prev + 1)}
              className="rounded border border-gray-300 px-3 py-1 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('app.leads.pagination.next')}
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
