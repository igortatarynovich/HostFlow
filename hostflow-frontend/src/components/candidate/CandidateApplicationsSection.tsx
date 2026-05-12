import { memo, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCandidateRecruitmentApplications, type RecruitmentApplicationOut } from '../../api/candidates'
import { getVacancy } from '../../api/vacancies'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

interface CandidateApplicationsSectionProps {
  candidateId: string
  locale: string
  /** Bump to refetch after lead→candidate flows (optional). */
  refreshTrigger?: number
  /**
   * When API returns no `RecruitmentApplication` rows but the dossier still has
   * `candidate.vacancy_id` (pre-intent-layer data), show one legacy row so the
   * section is not empty.
   */
  legacyVacancyId?: string | null
}

function CandidateApplicationsSection({
  candidateId,
  locale,
  refreshTrigger = 0,
  legacyVacancyId = null,
}: CandidateApplicationsSectionProps) {
  const { t } = useI18n()
  const [items, setItems] = useState<RecruitmentApplicationOut[]>([])
  const [vacancyTitles, setVacancyTitles] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    if (!candidateId) return
    try {
      setLoading(true)
      setError(false)
      const rows = await listCandidateRecruitmentApplications(candidateId)
      setItems(rows)
    } catch {
      setItems([])
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void load()
  }, [load, refreshTrigger])

  const legacyVacancyTrimmed =
    typeof legacyVacancyId === 'string' && legacyVacancyId.trim() ? legacyVacancyId.trim() : ''

  useEffect(() => {
    const fromRows = items.map((r) => r.vacancy_id).filter(Boolean) as string[]
    const ids = [...new Set(fromRows)]
    if (legacyVacancyTrimmed && items.length === 0) {
      ids.push(legacyVacancyTrimmed)
    }
    if (ids.length === 0) {
      setVacancyTitles({})
      return
    }
    let cancelled = false
    void (async () => {
      const next: Record<string, string> = {}
      await Promise.all(
        ids.map(async (id) => {
          try {
            const v = await getVacancy(id)
            const title = typeof (v as { title?: string })?.title === 'string' ? (v as { title: string }).title : ''
            if (title) next[id] = title
          } catch {
            /* keep id fallback */
          }
        }),
      )
      if (!cancelled) setVacancyTitles(next)
    })()
    return () => {
      cancelled = true
    }
  }, [items, legacyVacancyTrimmed])

  return (
    <section
      id="section-applications"
      className="group app-surface scroll-mt-24 p-4 transition-shadow hover:shadow-xl"
    >
      <div className="flex flex-col gap-0.5">
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.candidate_card.applications.title')}
        </h2>
        <p className="text-sm text-slate-500">{t('app.candidate_card.applications.subtitle')}</p>
      </div>

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">{t('common.loading')}</p>
      ) : error ? (
        <p className="mt-4 text-sm text-amber-800">{t('app.candidate_card.applications.load_error')}</p>
      ) : items.length === 0 && !legacyVacancyTrimmed ? (
        <p className="mt-4 text-sm text-slate-500">{t('app.candidate_card.applications.empty')}</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          {items.length === 0 && legacyVacancyTrimmed ? (
            <p className="mb-3 text-sm text-slate-600">{t('app.candidate_card.applications.legacy_note')}</p>
          ) : null}
          <table className="w-full min-w-[520px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">{t('app.candidate_card.applications.columns.source')}</th>
                <th className="py-2 pr-3">{t('app.candidate_card.applications.columns.vacancy')}</th>
                <th className="py-2 pr-3">{t('app.candidate_card.applications.columns.status')}</th>
                <th className="py-2 pr-3">{t('app.candidate_card.applications.columns.applied_at')}</th>
                <th className="py-2">{t('app.candidate_card.applications.columns.lead')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-2.5 pr-3 align-top text-slate-800">
                    <span className="font-medium">{row.source || '—'}</span>
                  </td>
                  <td className="py-2.5 pr-3 align-top text-slate-700">
                    {row.vacancy_id ? (
                      <Link
                        to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(row.vacancy_id)}`}
                        className="btn text-sm font-medium text-brand-700 hover:underline"
                      >
                        {vacancyTitles[row.vacancy_id] || row.vacancy_id.slice(0, 8) + '…'}
                      </Link>
                    ) : (
                      <span className="text-slate-500">{t('app.candidate_card.applications.vacancy_pool')}</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3 align-top text-slate-700">{row.status}</td>
                  <td className="py-2.5 pr-3 align-top text-slate-600 whitespace-nowrap">
                    {formatDateTime(row.applied_at, locale)}
                  </td>
                  <td className="py-2.5 align-top text-slate-600">
                    {row.lead_id ? (
                      <Link
                        to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
                        className="btn text-sm font-medium text-brand-700 hover:underline"
                      >
                        {t('app.candidate_card.applications.lead_link')}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
              {items.length === 0 && legacyVacancyTrimmed ? (
                <tr className="border-b border-slate-100 last:border-0">
                  <td className="py-2.5 pr-3 align-top text-slate-800">
                    <span className="font-medium text-slate-600">
                      {t('app.candidate_card.applications.legacy_source_label')}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 align-top text-slate-700">
                    <Link
                      to={`${CRM_APP_PATHS.vacancies}/${encodeURIComponent(legacyVacancyTrimmed)}`}
                      className="btn text-sm font-medium text-brand-700 hover:underline"
                    >
                      {vacancyTitles[legacyVacancyTrimmed] || legacyVacancyTrimmed.slice(0, 8) + '…'}
                    </Link>
                  </td>
                  <td className="py-2.5 pr-3 align-top text-slate-500">—</td>
                  <td className="py-2.5 pr-3 align-top text-slate-500">—</td>
                  <td className="py-2.5 align-top text-slate-500">—</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default memo(CandidateApplicationsSection)
