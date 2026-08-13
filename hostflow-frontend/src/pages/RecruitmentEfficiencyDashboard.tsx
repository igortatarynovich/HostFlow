import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
import { useTenantInfo } from '../contexts/TenantInfo'
import { PageShell, PageShellHeader } from '../components/layout'
import { Button } from '../components/ui/Button'
import {
  AnalyticsReportHeader,
  isAnalyticsPresentation,
  readAnalyticsView,
  writeAnalyticsView,
} from '../components/analytics'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import type { CandidateSlicesResponse, QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { RecruitmentEfficiencyFiltersBar } from '../modules/dashboard/components/RecruitmentEfficiencyFiltersBar'
import { RecruitmentEfficiencyPanel } from '../modules/dashboard/components/RecruitmentEfficiencyPanel'

type ListResp<T> = { items: T[]; total?: number } | T[]

export default function RecruitmentEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const tenant = useTenantInfo()
  const currentTenantId = useCurrentTenantId()
  const scopeTid = currentTenantId ?? (me as { tenant_id?: string })?.tenant_id
  const loadSeq = useRef(0)
  const [searchParams, setSearchParams] = useSearchParams()
  const present = isAnalyticsPresentation(searchParams)
  const boot = useRef(readAnalyticsView(searchParams)).current
  const bootRange: QuickRange = (QUICK_RANGE_OPTIONS as readonly string[]).includes(boot.range)
    ? (boot.range as QuickRange)
    : 'all'
  const bootCalc = boot.from && boot.to ? { from: boot.from, to: boot.to } : calcRange(bootRange)

  const [dateFrom, setDateFrom] = useState(bootCalc.from)
  const [dateTo, setDateTo] = useState(bootCalc.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>(
    boot.from && boot.to && !boot.range ? 'custom' : bootRange,
  )
  const [companyFilter, setCompanyFilter] = useState(boot.companyId)
  const [vacancyFilter, setVacancyFilter] = useState(boot.vacancyId)
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

  const buildCandidatesHref = useCallback(
    (opts: { stages?: string }) => {
      const q = new URLSearchParams()
      if (opts.stages) q.set('stages', opts.stages)
      if (vacancyFilter) q.set('vacancy_id', vacancyFilter)
      const qs = q.toString()
      return qs ? `${CRM_APP_PATHS.candidates}?${qs}` : CRM_APP_PATHS.candidates
    },
    [vacancyFilter],
  )

  const onCompanyChange = (value: string) => {
    setCompanyFilter(value)
    if (vacancyFilter) {
      const stillValid = allVacancies.some(
        (v) => v.id === vacancyFilter && (!value || v.companyId === value),
      )
      if (!stillValid) setVacancyFilter('')
    }
  }

  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle')

  useEffect(() => {
    setSearchParams(
      (prev) =>
        writeAnalyticsView(prev, {
          range: activeRange,
          from: dateFrom,
          to: dateTo,
          companyId: companyFilter,
          vacancyId: vacancyFilter,
        }),
      { replace: true },
    )
  }, [activeRange, dateFrom, dateTo, companyFilter, vacancyFilter, setSearchParams])

  const periodLabel =
    dateFrom && dateTo
      ? `${dateFrom} — ${dateTo}`
      : t('app.dashboard.share.period_all', { defaultValue: 'All time' })

  const onTogglePresent = useCallback(() => {
    setSearchParams((prev) => writeAnalyticsView(prev, { present: !present }))
  }, [present, setSearchParams])

  useEffect(() => {
    if (!present) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onTogglePresent()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [present, onTogglePresent])

  const onCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopyState('copied')
      window.setTimeout(() => setCopyState('idle'), 2000)
    } catch {
      setCopyState('failed')
      window.setTimeout(() => setCopyState('idle'), 2000)
    }
  }

  return (
    <PageShell>
      <PageShellHeader>
        <AnalyticsReportHeader
          brand={t('app.dashboard.share.brand', { defaultValue: 'HostFlow' })}
          company={tenant?.name}
          title={t('app.dashboard.efficiency.title')}
          periodLabel={periodLabel}
          present={present}
          onTogglePresent={onTogglePresent}
          onCopyLink={() => void onCopyLink()}
          copyState={copyState}
          presentLabel={t('app.dashboard.share.present', { defaultValue: 'Presentation' })}
          workingLabel={t('app.dashboard.share.working', { defaultValue: 'Working view' })}
          copyLabel={t('app.dashboard.share.copy_link', { defaultValue: 'Copy link' })}
          copiedLabel={t('app.dashboard.share.copied', { defaultValue: 'Link copied' })}
          copyFailedLabel={t('app.dashboard.share.copy_failed', { defaultValue: 'Could not copy' })}
          exitLabel={t('app.dashboard.share.exit', { defaultValue: 'Exit presentation' })}
          extra={
            present ? null : (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void load()}
                disabled={loading || rangeInvalid}
              >
                {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
              </Button>
            )
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-4 pb-6">
        {present ? null : (
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
        )}

        {errText && !present ? (
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
          buildCandidatesHref={present ? undefined : buildCandidatesHref}
          present={present}
        />
      </div>
    </PageShell>
  )
}
