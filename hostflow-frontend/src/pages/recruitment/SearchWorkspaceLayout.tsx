import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { api } from '../../api/client'
import {
  CRM_APP_PATHS,
  recruitmentSearchPath,
  recruitmentSearchAcquisitionPath,
} from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import {
  clearLastLaunchSearchId,
  loadLaunchSearch,
  persistLastLaunchSearchId,
  readLastLaunchSearchId,
} from '../../services/launchSearchSession'
import { SearchNextActionPanel } from '../../components/recruitment/SearchNextActionPanel'
import { useSearchWorkspacePulse } from '../../hooks/useSearchWorkspacePulse'
import { searchWorkspaceStatusLabel } from '../../utils/searchWorkspaceI18n'
import { SearchWorkspaceContext, type SearchWorkspaceContextValue } from './searchWorkspaceContext'

export type { SearchWorkspaceContextValue as SearchWorkspaceContext }
export { useSearchWorkspace } from './searchWorkspaceContext'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-lg px-3 py-2 text-sm font-medium transition',
    isActive ? 'bg-white text-brand-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:bg-white/80 hover:text-slate-900',
  )

export default function SearchWorkspaceLayout() {
  const { searchId = '' } = useParams<{ searchId: string }>()
  const { t } = useI18n()
  const location = useLocation()
  const cached = loadLaunchSearch(searchId)
  const [searchName, setSearchName] = useState(cached?.name ?? '')
  const [companyName, setCompanyName] = useState(cached?.companyName ?? '')
  const [publicUrl, setPublicUrl] = useState(cached?.publicUrl ?? '')
  const [vacancyStatus, setVacancyStatus] = useState('')
  const [vacancyArchived, setVacancyArchived] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const { pulse, loading: pulseLoading, refresh: refreshPulse } = useSearchWorkspacePulse(searchId, {
    enabled: !notFound,
  })

  const load = useCallback(async () => {
    if (!searchId) return
    try {
      const { data: vacancy } = await api.get(`/vacancies/${searchId}`)
      const row = vacancy as {
        title?: string
        status?: string | null
        is_archived?: boolean | null
        company?: { name?: string | null }
        extra?: unknown
      }
      setNotFound(false)
      setSearchName(String(row.title ?? cached?.name ?? t('app.search_home.default_title')))
      setCompanyName(String(row.company?.name ?? cached?.companyName ?? ''))
      setVacancyStatus(String(row.status ?? ''))
      setVacancyArchived(Boolean(row.is_archived))
      persistLastLaunchSearchId(searchId)
    } catch (err) {
      if ((err as { response?: { status?: number } })?.response?.status === 404) {
        setNotFound(true)
        if (readLastLaunchSearchId() === searchId) clearLastLaunchSearchId()
        return
      }
      if (cached?.name) setSearchName(cached.name)
    }
  }, [cached, searchId, t])

  useEffect(() => {
    void load()
  }, [load])

  const candidatesHref = `${CRM_APP_PATHS.candidates}?vacancy_id=${encodeURIComponent(searchId)}`
  const overviewPath = recruitmentSearchPath(searchId)
  const acquisitionPath = recruitmentSearchAcquisitionPath(searchId)

  const breadcrumbItems = useMemo(() => {
    const searchesLabel = t('app.searches_list.title')
    const items: { label: string; to?: string }[] = [
      { label: searchesLabel, to: CRM_APP_PATHS.recruitmentSearches },
    ]
    const path = location.pathname
    const acquisitionLabel = t('app.search_workspace.tab_acquisition')

    if (path.includes('/acquisition/meta')) {
      items.push({ label: searchName || '…', to: overviewPath })
      items.push({ label: acquisitionLabel, to: acquisitionPath })
      items.push({ label: t('app.search_meta.title') })
    } else if (path.includes('/acquisition/new')) {
      items.push({ label: searchName || '…', to: overviewPath })
      items.push({ label: acquisitionLabel, to: acquisitionPath })
      items.push({ label: t('app.acquisition.launch_title') })
    } else if (path.includes('/acquisition')) {
      items.push({ label: searchName || '…', to: overviewPath })
      items.push({ label: acquisitionLabel })
    } else {
      items.push({ label: searchName || '…' })
    }
    return items
  }, [acquisitionPath, location.pathname, overviewPath, searchName, t])

  const workspaceValue: SearchWorkspaceContextValue = {
    searchId,
    searchName,
    companyName: companyName || undefined,
    publicUrl: publicUrl || undefined,
    pulse,
    pulseLoading,
    reload: load,
    refreshPulse,
  }

  const status = pulse?.status
  const statusLabel = searchWorkspaceStatusLabel(t, vacancyStatus, vacancyArchived)

  if (notFound) {
    return (
      <Navigate
        to={CRM_APP_PATHS.recruitmentSearches}
        replace
        state={{ searchNotFound: true, searchId }}
      />
    )
  }

  return (
    <SearchWorkspaceContext.Provider value={workspaceValue}>
      <PageShell>
        <PageShellHeader>
          <PageHeader
            breadcrumbItems={breadcrumbItems}
            title={searchName || '…'}
            subtitle={companyName || undefined}
            kind="browse"
            secondaryActions={
              pulse ? (
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {statusLabel}
                </span>
              ) : undefined
            }
          />

          {status?.headcount_target ? (
            <p className="mt-2 text-sm text-slate-600">
              {t('app.search_workspace.status_line', {
                values: {
                  hired: status.hired ?? 0,
                  target: status.headcount_target,
                  active: status.active_candidates ?? 0,
                  awaiting: status.awaiting_call ?? 0,
                },
              })}
            </p>
          ) : null}

          <div className="mt-3">
            <SearchNextActionPanel
              pulse={pulse}
              searchId={searchId}
              searchName={searchName}
              loading={pulseLoading}
            />
          </div>

          <nav
            className="mt-3 flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-slate-50/90 p-1"
            aria-label={t('app.search_workspace.tabs_aria')}
          >
            <NavLink to={overviewPath} end className={tabClass}>
              {t('app.search_workspace.tab_overview')}
            </NavLink>
            <NavLink to={acquisitionPath} className={tabClass}>
              {t('app.search_workspace.tab_acquisition')}
            </NavLink>
            <Link
              to={candidatesHref}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-white/80 hover:text-slate-900"
            >
              {t('app.search_workspace.tab_candidates')}
            </Link>
          </nav>
        </PageShellHeader>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto pb-4">
          <div className="mx-auto w-full max-w-3xl" data-testid="m1-search-workspace">
            <Outlet />
          </div>
        </div>
      </PageShell>
    </SearchWorkspaceContext.Provider>
  )
}
