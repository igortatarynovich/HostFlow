import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import { IconArrowRight, IconPlus } from '@tabler/icons-react'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import { CRM_APP_PATHS, recruitmentSearchPath } from '../../app/crmAppPaths'
import { PageShell, PageShellHeader } from '../../components/layout'
import { PageHeader } from '../../components/nav/PageHeader'
import { useToast } from '../../components/Toast'
import { useI18n, type LocaleCode } from '../../i18n'
import { persistLastLaunchSearchId } from '../../services/launchSearchSession'
import { parseLaunchSearchVacancyExtra } from '../../utils/searchHomeContext'

function dateFnsLocale(code: LocaleCode) {
  if (code === 'pl') return plFns
  if (code === 'ru') return ruFns
  return enUS
}

function isLaunchSearch(row: Vacancy & { extra?: unknown }): boolean {
  return parseLaunchSearchVacancyExtra(row.extra).launch_search === true
}

export default function SearchesListPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const location = useLocation()
  const [rows, setRows] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const state = location.state as { searchNotFound?: boolean } | null
    if (!state?.searchNotFound) return
    notify({
      title: t('app.searches_list.not_found_title', { defaultValue: 'Подбор не найден' }),
      message: t('app.searches_list.not_found_body', {
        defaultValue: 'Этот подбор удалён или недоступен. Выберите другой или создайте новый.',
      }),
      variant: 'warning',
    })
    window.history.replaceState({}, document.title)
  }, [location.state, notify, t])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const vacancies = await listVacancies({
        limit: 100,
        order_by: 'updated_at',
        desc: true,
        is_archived: false,
      })
      const launchOnly = vacancies.filter((row) =>
        isLaunchSearch(row as Vacancy & { extra?: unknown }),
      )
      setRows(launchOnly.length > 0 ? launchOnly : vacancies)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const dfLocale = useMemo(() => dateFnsLocale(locale), [locale])

  const handleOpen = (searchId: string) => {
    persistLastLaunchSearchId(searchId)
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          breadcrumbItems={[
            { label: t('app.nav.items.launchpad', { defaultValue: 'Launchpad' }), to: CRM_APP_PATHS.launchpad },
            { label: t('app.searches_list.title', { defaultValue: 'Подборы' }) },
          ]}
          title={t('app.searches_list.title', { defaultValue: 'Подборы' })}
          subtitle={t('app.searches_list.subtitle', {
            defaultValue: 'Откройте подбор — ссылка, отклики и следующие шаги в одном месте.',
          })}
          kind="action"
          primaryAction={
            <Link
              to={CRM_APP_PATHS.recruitmentSearchesNew}
              className="btn-primary btn-sm inline-flex items-center gap-1.5"
              data-testid="m1-searches-list-create"
            >
              <IconPlus size={16} stroke={1.9} />
              {t('app.searches_list.create', { defaultValue: 'Создать подбор' })}
            </Link>
          }
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {loading ? t('common.loading', { defaultValue: 'Загрузка…' }) : t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-4">
      <div className="mx-auto w-full max-w-3xl space-y-5" data-testid="m1-searches-list">
      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
      ) : rows.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('app.searches_list.empty_title', { defaultValue: 'Пока нет подборов' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.searches_list.empty_body', {
              defaultValue: 'Создайте первый подбор — получите ссылку для кандидатов и начните принимать отклики.',
            })}
          </p>
          <Link
            to={CRM_APP_PATHS.recruitmentSearchesNew}
            className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            <IconPlus size={16} stroke={1.9} />
            {t('app.searches_list.create', { defaultValue: 'Создать подбор' })}
          </Link>
        </section>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => {
            const updatedLabel =
              row.updated_at || row.created_at
                ? formatDistanceToNow(new Date(String(row.updated_at || row.created_at)), {
                    addSuffix: true,
                    locale: dfLocale,
                  })
                : null
            const candidateCount = Number(row.candidate_count ?? 0)
            return (
              <li key={row.id}>
                <Link
                  to={recruitmentSearchPath(row.id)}
                  onClick={() => handleOpen(row.id)}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-200 hover:shadow-md"
                  data-testid={`m1-searches-list-row-${row.id}`}
                >
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold text-slate-900">{row.title}</p>
                    {row.company_name ? (
                      <p className="mt-0.5 truncate text-sm text-slate-600">{row.company_name}</p>
                    ) : null}
                    <p className="mt-2 text-xs text-slate-500">
                      {candidateCount > 0
                        ? t('app.searches_list.candidates_count', {
                            defaultValue: '{count} кандидатов',
                            values: { count: candidateCount },
                          })
                        : t('app.searches_list.no_candidates', { defaultValue: 'Пока нет откликов' })}
                      {updatedLabel ? ` · ${updatedLabel}` : ''}
                    </p>
                  </div>
                  <span className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-brand-700">
                    {t('app.searches_list.open', { defaultValue: 'Открыть' })}
                    <IconArrowRight size={14} stroke={1.9} />
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      </div>
      </div>
    </PageShell>
  )
}
