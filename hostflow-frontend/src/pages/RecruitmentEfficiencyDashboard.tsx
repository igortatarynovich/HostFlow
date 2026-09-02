import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import api, { withTenant } from '../api/client'
import {
  getContactAttemptStats,
  getDocumentStats,
  type ContactAttemptStatsResponse,
  type DocumentStatsResponse,
} from '../api/analytics'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import type { CandidateSlicesResponse, QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'
import { RecruitmentEfficiencyFiltersBar } from '../modules/dashboard/components/RecruitmentEfficiencyFiltersBar'
import { RecruitmentEfficiencyPanel } from '../modules/dashboard/components/RecruitmentEfficiencyPanel'

type ListResp<T> = { items: T[]; total?: number } | T[]

export default function RecruitmentEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const scopeTid = currentTenantId ?? (me as { tenant_id?: string })?.tenant_id
  const loadSeq = useRef(0)

  const initialRange = calcRange('all')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('all')
  const [companyFilter, setCompanyFilter] = useState('')
  const [vacancyFilter, setVacancyFilter] = useState('')
  const [companyOptions, setCompanyOptions] = useState<{ id: string; label: string }[]>([])
  const [vacancyOptions, setVacancyOptions] = useState<{ id: string; label: string }[]>([])
  const [allVacancies, setAllVacancies] = useState<
    { id: string; label: string; companyId: string | null }[]
  >([])

  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [slices, setSlices] = useState<CandidateSlicesResponse | null>(null)
  const [documentStats, setDocumentStats] = useState<DocumentStatsResponse | null>(null)
  const [contactStats, setContactStats] = useState<ContactAttemptStatsResponse | null>(null)
  const [periodTotal, setPeriodTotal] = useState(0)

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'),
    [locale],
  )
  const formatNumber = useCallback(
    (value?: number) => numberFormatter.format(value ?? 0),
    [numberFormatter],
  )

  const quickRangeOptions = useMemo(
    () =>
      QUICK_RANGE_OPTIONS.map((value) => ({
        value,
        label: t(`app.dashboard.ranges.${value}`),
      })),
    [t],
  )

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)

  const load = useCallback(
    async (overrides?: {
      from?: string
      to?: string
      companyId?: string
      vacancyId?: string
    }) => {
      const from = overrides?.from ?? dateFrom
      const to = overrides?.to ?? dateTo
      const companyId = overrides?.companyId ?? companyFilter
      const vacancyId = overrides?.vacancyId ?? vacancyFilter

      if (from && to && from > to) {
        setErrText(t('app.dashboard.errors.range_invalid'))
        return
      }

      const seq = ++loadSeq.current
      setLoading(true)
      setErrText(null)
      try {
        const params: Record<string, string | number> = { limit: 100, by: 'created' }
        if (from) params.from = from
        if (to) params.to = to
        if (companyId) params.company_id = companyId
        if (vacancyId) params.vacancy_id = vacancyId
        if (scopeTid) params.scope_tenant_id = scopeTid

        const candidatesClient = scopeTid ? withTenant(scopeTid) : api
        const filterParams = {
          from: from || undefined,
          to: to || undefined,
          companyId: companyId || undefined,
          vacancyId: vacancyId || undefined,
        }
        const [sliceResp, docResp, contactResp] = await Promise.all([
          candidatesClient.get<CandidateSlicesResponse>('/analytics/candidate-slices', { params }),
          getDocumentStats(filterParams).catch(() => null),
          getContactAttemptStats(filterParams).catch(() => null),
        ])

        if (seq !== loadSeq.current) return

        const slicesData = sliceResp.data
        setSlices(slicesData)
        setPeriodTotal(slicesData?.total ?? 0)
        setDocumentStats(docResp)
        setContactStats(contactResp)
      } catch (e: unknown) {
        if (seq !== loadSeq.current) return
        // Keep previous slices/docs so charts stay mounted and layout does not collapse to -1.
        setErrText(formatAnalyticsLoadError(e, t))
      } finally {
        if (seq === loadSeq.current) setLoading(false)
      }
    },
    [dateFrom, dateTo, companyFilter, vacancyFilter, scopeTid, t],
  )

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get<ListResp<{ id?: string; name?: string; label?: string }>>(
          '/companies/',
          { params: { limit: 200, offset: 0 } },
        )
        const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
        setCompanyOptions(
          list
            .map((item) => {
              const id = item?.id
              if (!id) return null
              return { id, label: item?.name || item?.label || id }
            })
            .filter(Boolean) as { id: string; label: string }[],
        )
      } catch {
        setCompanyOptions([])
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get<
          ListResp<{
            id?: string
            title?: string
            vacancy_title?: string
            company_id?: string
            company_name?: string
            company?: { name?: string; id?: string }
          }>
        >('/vacancies/', { params: { limit: 200, offset: 0 } })
        const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
        const untitled = t('app.dashboard.labels.untitled', { defaultValue: '—' })
        const mapped = list
          .map((item) => {
            const id = item?.id
            if (!id) return null
            const title = item?.title || item?.vacancy_title || untitled
            const companyName = item?.company_name || item?.company?.name || ''
            const companyId = item?.company_id || item?.company?.id || null
            const label = companyName ? `${title} • ${companyName}` : title
            return { id, label, companyId: companyId ? String(companyId) : null }
          })
          .filter(Boolean) as { id: string; label: string; companyId: string | null }[]
        setAllVacancies(mapped)
      } catch {
        setAllVacancies([])
      }
    })()
  }, [t])

  useEffect(() => {
    const filtered = companyFilter
      ? allVacancies.filter((v) => v.companyId === companyFilter)
      : allVacancies
    setVacancyOptions(filtered.map(({ id, label }) => ({ id, label })))
    if (vacancyFilter && !filtered.some((v) => v.id === vacancyFilter)) {
      setVacancyFilter('')
    }
  }, [allVacancies, companyFilter, vacancyFilter])

  const applyQuickRange = (range: QuickRange) => {
    const next = calcRange(range)
    setActiveRange(range)
    setDateFrom(next.from)
    setDateTo(next.to)
  }

  const onCompanyChange = (value: string) => {
    setCompanyFilter(value)
    if (vacancyFilter) {
      const stillValid = allVacancies.some(
        (v) => v.id === vacancyFilter && (!value || v.companyId === value),
      )
      if (!stillValid) setVacancyFilter('')
    }
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void load()}
              disabled={loading || rangeInvalid}
            >
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
        <RecruitmentEfficiencyFiltersBar
          t={t}
          quickRangeOptions={quickRangeOptions}
          activeRange={activeRange}
          applyQuickRange={applyQuickRange}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          setActiveRange={setActiveRange}
          companyFilter={companyFilter}
          companyOptions={companyOptions}
          onCompanyChange={onCompanyChange}
          vacancyFilter={vacancyFilter}
          vacancyOptions={vacancyOptions}
          onVacancyChange={setVacancyFilter}
          loading={loading}
          periodTotal={periodTotal}
          formatNumber={formatNumber}
        />

        {errText ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errText}
          </div>
        ) : null}

        <RecruitmentEfficiencyPanel
          t={t}
          formatNumber={formatNumber}
          slices={slices}
          documentStats={documentStats}
          contactStats={contactStats}
          loading={loading}
        />
      </div>
    </PageShell>
  )
}
