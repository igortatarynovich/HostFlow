import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight, IconRefresh, IconUsers } from '@tabler/icons-react'
import { api } from '../../api/client'
import { listRecruitmentApplications } from '../../api/applications'
import { CRM_APP_PATHS, recruitmentSearchPath } from '../../app/crmAppPaths'
import { RECRUITMENT_INBOX_PATH } from '../../app/recruitmentInboxPaths'
import { useI18n } from '../../i18n'
import { getIntakeFormDetail, putIntakeFormPresentation } from '../../api/intakeForms'
import { loadLaunchSearch } from '../../services/launchSearchSession'
import {
  isLaunchSearchFormStale,
  launchSearchIntakeFields,
} from '../../utils/launchSearchIntakeFields'
import { launchSearchRoleDefaults, type SearchRole } from '../../utils/launchSearchRoleDefaults'
import { parseLaunchSearchVacancyExtra } from '../../utils/searchHomeContext'
import { useSearchWorkspace } from './searchWorkspaceContext'

type SearchCandidateRow = {
  id: string
  full_name?: string | null
  stage?: string | null
  created_at?: string | null
}

function normalizeRole(value: string | undefined): SearchRole {
  const role = String(value || '').trim()
  if (role === 'warehouse' || role === 'office' || role === 'other') return role
  return 'driver'
}

function stageLabel(stage: string | null | undefined): string {
  const s = String(stage || '').trim().toLowerCase()
  if (!s || s === 'new') return 'Новый'
  if (s === 'to_call' || s === 'to_contact' || s === 'no_answer') return 'Ждёт звонка'
  if (s === 'docs_wait') return 'Документы'
  return s
}

/** Process Workspace for a search — candidates in pipeline, not raw inbound applications. */
export default function SearchHomePage() {
  const { searchId, pulse, refreshPulse } = useSearchWorkspace()
  const { t } = useI18n()
  const cached = loadLaunchSearch(searchId)

  const [candidates, setCandidates] = useState<SearchCandidateRow[]>([])
  const [pendingApplications, setPendingApplications] = useState(0)
  const [loading, setLoading] = useState(true)
  const [formStale, setFormStale] = useState(false)
  const [updatingForm, setUpdatingForm] = useState(false)
  const [leadFormId, setLeadFormId] = useState('')
  const [searchRole, setSearchRole] = useState<SearchRole>('driver')

  const load = useCallback(async () => {
    if (!searchId) return
    setLoading(true)
    try {
      const [{ data: vacancy }, appsRes, { data: candidateRows }] = await Promise.all([
        api.get(`/vacancies/${searchId}`),
        listRecruitmentApplications({ vacancyId: searchId, limit: 50, scope: 'open' }),
        api.get('/candidates', { params: { vacancy_id: searchId, limit: 8, offset: 0, compact: true } }),
      ])

      const extra = parseLaunchSearchVacancyExtra((vacancy as { extra?: unknown }).extra)
      const role = normalizeRole(extra.search_role ?? cached?.searchRole)
      setSearchRole(role)
      const formId = extra.lead_form_id ?? cached?.leadFormId ?? ''
      setLeadFormId(formId)

      if (formId) {
        const detail = await getIntakeFormDetail(formId)
        setFormStale(isLaunchSearchFormStale(role, detail.presentation?.fields ?? []))
      } else {
        setFormStale(false)
      }

      setPendingApplications(appsRes.total)
      setCandidates((candidateRows as { items?: SearchCandidateRow[] })?.items ?? [])
    } catch {
      setCandidates([])
      setPendingApplications(0)
    } finally {
      setLoading(false)
    }
  }, [cached?.leadFormId, cached?.searchRole, searchId])

  useEffect(() => {
    void load()
  }, [load])

  const searchHomePath = recruitmentSearchPath(searchId)
  const candidateLinkState = useMemo(() => ({ originPath: searchHomePath }), [searchHomePath])
  const candidatesHref = `${CRM_APP_PATHS.candidates}?vacancy_id=${encodeURIComponent(searchId)}`
  const status = pulse?.status

  async function refreshIntakeForm() {
    if (!leadFormId) return
    setUpdatingForm(true)
    try {
      const roleSpec = launchSearchRoleDefaults(searchRole)
      const fields = await launchSearchIntakeFields(searchRole)
      await putIntakeFormPresentation(leadFormId, {
        entity_profile_code: roleSpec.entityProfileCode,
        fields,
      })
      setFormStale(false)
    } finally {
      setUpdatingForm(false)
    }
  }

  return (
    <div className="space-y-4" data-testid="m1-search-home">
      {formStale ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <p className="font-medium">{t('app.search_home.stale_warning_title', { defaultValue: 'Старая анкета' })}</p>
          <p className="mt-1">{t('app.search_home.stale_warning_body', { defaultValue: 'Обновите форму — кандидаты должны видеть полный опросник.' })}</p>
          <button
            type="button"
            disabled={updatingForm || !leadFormId}
            onClick={() => void refreshIntakeForm()}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
          >
            <IconRefresh size={14} />
            {updatingForm ? t('common.loading') : t('app.search_home.update_form', { defaultValue: 'Обновить форму' })}
          </button>
        </section>
      ) : null}

      {pendingApplications > 0 ? (
        <section className="rounded-xl border border-brand-200 bg-brand-50/50 p-4">
          <p className="text-sm font-semibold text-slate-900">
            {pendingApplications === 1
              ? '1 отклик ждёт обработки'
              : `${pendingApplications} откликов ждут обработки`}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Новые необработанные отклики обрабатываются в Application Workspace, не в подборе.
          </p>
          <Link
            to={RECRUITMENT_INBOX_PATH}
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
          >
            Открыть отклики
            <IconArrowRight size={16} />
          </Link>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <IconUsers size={18} className="text-brand-700" />
            <h3 className="text-sm font-semibold text-slate-900">
              {t('app.search_home.pipeline_title', { defaultValue: 'Кандидаты в подборе' })}
            </h3>
          </div>
          <Link to={candidatesHref} className="text-xs font-medium text-brand-700 hover:underline">
            {t('app.search_home.all_candidates', { defaultValue: 'Все кандидаты' })}
          </Link>
        </div>
        {status?.headcount_target ? (
          <p className="mt-2 text-xs text-slate-500">
            {status.hired ?? 0} нанято · {status.active_candidates ?? 0} в работе · {status.awaiting_call ?? 0} ждут
            звонка
          </p>
        ) : null}
        {loading ? (
          <p className="mt-3 text-sm text-slate-500">{t('common.loading')}</p>
        ) : candidates.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {candidates.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2 text-sm">
                <div>
                  <span className="font-medium text-slate-900">
                    {row.full_name?.trim() || t('app.candidates.unnamed', { defaultValue: 'Кандидат' })}
                  </span>
                  <p className="text-xs text-slate-500">
                    {stageLabel(row.stage)}
                    {row.created_at ? ` · ${new Date(row.created_at).toLocaleString()}` : ''}
                  </p>
                </div>
                <Link
                  to={`${CRM_APP_PATHS.candidates}/${row.id}`}
                  state={candidateLinkState}
                  className="text-brand-700 hover:underline"
                >
                  {t('app.search_home.open_candidate', { defaultValue: 'Открыть' })}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-600">
            {t('app.search_home.pipeline_empty', {
              defaultValue:
                'Пока нет кандидатов в этом подборе. После обработки отклика в «Откликах» кандидат появится здесь.',
            })}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-4 text-sm text-slate-600">
        <p>
          {t('app.search_home.process_hint', {
            defaultValue:
              'Подбор — Process Workspace: прогресс, кандидаты и реклама. Входящие отклики до решения — только в «Откликах».',
          })}
        </p>
        <button
          type="button"
          onClick={() => {
            void load()
            void refreshPulse()
          }}
          className="mt-2 text-xs font-medium text-brand-700 hover:underline"
        >
          {t('app.search_home.refresh', { defaultValue: 'Обновить' })}
        </button>
      </section>
    </div>
  )
}
