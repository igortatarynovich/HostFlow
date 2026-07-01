import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCompanies } from '../../api/client'
import { listFleetOperatingLines, type FleetOperatingLine } from '../../api/fleet'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

const DIRECTORY_FETCH_LIMIT = 500
const PREVIEW_ROWS = 18

type CompanyRow = { id: string; name: string }

function normalizeCompanyList(raw: unknown): CompanyRow[] {
  const items: unknown[] = Array.isArray(raw)
    ? raw
    : raw && typeof raw === 'object' && Array.isArray((raw as { items?: unknown }).items)
      ? ((raw as { items: unknown[] }).items ?? [])
      : []
  const out: CompanyRow[] = []
  for (const item of items) {
    if (!item || typeof item !== 'object') continue
    const o = item as Record<string, unknown>
    const id = String(o.id ?? o.uuid ?? '').trim()
    if (!id) continue
    const name = String(o.name ?? o.title ?? '—').trim() || '—'
    out.push({ id, name })
  }
  return out
}

function companyIdsFromLines(lines: FleetOperatingLine[]): Set<string> {
  const s = new Set<string>()
  for (const ln of lines) {
    const oc = ln.operating_company_id?.trim()
    const cc = ln.client_company_id?.trim()
    if (oc) s.add(oc)
    if (cc) s.add(cc)
  }
  return s
}

export default function FleetCounterpartiesSection() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [companies, setCompanies] = useState<CompanyRow[]>([])
  const [lines, setLines] = useState<FleetOperatingLine[]>([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      listCompanies({ limit: DIRECTORY_FETCH_LIMIT, offset: 0 }),
      listFleetOperatingLines(),
    ])
      .then(([rawCompanies, linesRes]) => {
        if (cancelled) return
        setCompanies(normalizeCompanyList(rawCompanies))
        setLines(linesRes.items)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(getFriendlyErrorInfo(err))
          setCompanies([])
          setLines([])
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const companyById = useMemo(() => new Map(companies.map((c) => [c.id, c.name])), [companies])

  const lineCompanyIds = useMemo(() => companyIdsFromLines(lines), [lines])

  const linkedRows = useMemo(() => {
    const rows: CompanyRow[] = []
    for (const id of lineCompanyIds) {
      const resolved = companyById.get(id)
      rows.push({
        id,
        name:
          resolved ??
          t('app.fleet.counterparties.not_in_preview', {
            values: { id: id.slice(0, 8) },
            defaultValue: 'Company {id}… (not in preview batch)',
          }),
      })
    }
    rows.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
    return rows
  }, [lineCompanyIds, companyById, t])

  const previewRows = useMemo(() => {
    return [...companies]
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
      .slice(0, PREVIEW_ROWS)
  }, [companies])

  const directoryTruncated = companies.length >= DIRECTORY_FETCH_LIMIT

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.counterparties.title')}</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-600">{t('app.fleet.counterparties.body')}</p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link
            to={CRM_APP_PATHS.agencyClients}
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700"
          >
            {t('app.fleet.counterparties.open_clients')}
          </Link>
          <Link
            to={CRM_APP_PATHS.fleetOperatingLines}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50"
          >
            {t('app.fleet.counterparties.manage_operating_lines', { defaultValue: 'Operating lines' })}
          </Link>
        </div>
      </header>

      {error ? (
        <ErrorRecoveryBanner info={error} onRetry={() => window.location.reload()} />
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('app.fleet.counterparties.stats_in_directory', { defaultValue: 'In Clients directory' })}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{companies.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('app.fleet.counterparties.stats_on_lines', { defaultValue: 'On operating lines' })}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{lineCompanyIds.size}</p>
            </div>
          </div>

          {directoryTruncated ? (
            <p className="text-xs text-amber-800">
              {t('app.fleet.counterparties.list_truncated_note', {
                values: { max: DIRECTORY_FETCH_LIMIT },
                defaultValue: `Directory preview loads up to ${DIRECTORY_FETCH_LIMIT} records. Open Clients for the full list.`,
              })}
            </p>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.counterparties.preview_heading', { defaultValue: 'Directory preview' })}
              </h2>
              {companies.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">
                  {t('app.fleet.counterparties.no_companies', { defaultValue: 'No companies loaded.' })}
                </p>
              ) : (
                <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-sm">
                  {previewRows.map((row) => (
                    <li key={row.id}>
                      <Link
                        to={`${CRM_APP_PATHS.agencyClients}/${encodeURIComponent(row.id)}`}
                        className="block px-3 py-2 text-blue-700 hover:bg-slate-50 hover:underline"
                      >
                        {row.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.fleet.counterparties.companies_on_lines_heading', { defaultValue: 'Companies on lines' })}
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                {t('app.fleet.counterparties.companies_on_lines_hint', {
                  defaultValue: 'Carrier or client selected on at least one operating line.',
                })}
              </p>
              {linkedRows.length === 0 ? (
                <p className="mt-3 text-sm text-slate-600">
                  {t('app.fleet.counterparties.no_line_links', {
                    defaultValue: 'No carrier or client selected on operating lines yet.',
                  })}
                </p>
              ) : (
                <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-sm">
                  {linkedRows.map((row) => (
                    <li key={row.id}>
                      <Link
                        to={`${CRM_APP_PATHS.agencyClients}/${encodeURIComponent(row.id)}`}
                        className="block px-3 py-2 text-blue-700 hover:bg-slate-50 hover:underline"
                      >
                        {row.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  )
}
