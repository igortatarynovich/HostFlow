import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  normalizeVacancy,
  buildVacancyPayload,
  hydrateSavedWithForm,
} from '../../utils/vacancyUtils'
import { api } from '../../api/client'
import { useI18n } from '../../i18n'
import {
  EMPLOYMENT_TYPES,
  VACANCY_STATUSES,
  createVacancy,
  getVacancy,
  getVacancyRecruiters,
  normalizeVacancyStatus,
  putVacancyRecruiters,
  updateVacancy,
} from '../../api/vacancies'
import type { EmploymentType, VacancyRecruiterPoolItem, VacancyStatus } from '../../api/vacancies'
import { listSalesOrderLines, type SalesOrderLine } from '../../api/salesOrders'
import { listCandidateProfiles, type CandidateProfile } from '../../api/candidate_profiles'
import { listTenantManagers } from '../../api/users'
import type { ManagerOption } from '../../api/types'
import { listVacancyRequirementsPresets, type VacancyRequirementsPreset } from '../../api/tenants'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageShell } from '../layout'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { NextActionBadge } from '../candidate/NextActionBadge'
import { useVacancyNextAction } from '../vacancy/useVacancyNextAction'
import { StatusBadge } from '../ui/StatusBadge'
import { criteriaDefaultsFromSource, applyCriteriaToPayload } from './detail/criteriaForm'
import { computePipelineMetrics, stageCountsFromPipelineColumns } from './detail/pipelineMetrics'
import { StageMetricCards } from './detail/StageMetricCards'
import { WorkspaceTab } from './detail/tabs/WorkspaceTab'
import { JobDetailsTab } from './detail/tabs/JobDetailsTab'
import { RecruitmentTab } from './detail/tabs/RecruitmentTab'
import { CandidateRequirementsTab } from './detail/tabs/CandidateRequirementsTab'
import { AutomationTab } from './detail/tabs/AutomationTab'
import { AnalyticsTab } from './detail/tabs/AnalyticsTab'
import { SettingsTab } from './detail/tabs/SettingsTab'
import { CandidatesTab } from './detail/tabs/CandidatesTab'

const STATUS_OPTIONS = VACANCY_STATUSES
const EMPLOYMENT_ENUM = [...EMPLOYMENT_TYPES] as [EmploymentType, ...EmploymentType[]]

const stringArray = z.array(z.string()).default([])

const vacancyFormSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  status: z.enum([...STATUS_OPTIONS] as [VacancyStatus, ...VacancyStatus[]]).default('open'),
  company_id: z.string().min(1, 'Company is required'),
  description: z.string().optional().or(z.literal('')),
  location: z.string().optional().or(z.literal('')),
  salary_from: z.union([z.string(), z.number()]).optional().transform((v) => (v === '' ? undefined : v)),
  salary_to: z.union([z.string(), z.number()]).optional().transform((v) => (v === '' ? undefined : v)),
  currency: z.string().optional().or(z.literal('')),
  is_open: z.boolean().default(true),
  is_active: z.boolean().default(true),
  is_archived: z.boolean().default(false),
  employment_type: z.enum(EMPLOYMENT_ENUM),
  candidate_profile_id: z.string().optional().or(z.literal('')),
  funnel_id: z.string().optional().or(z.literal('')),
  manager: z.string().optional().or(z.literal('')),
  criteria_min_experience_eu_years: z
    .union([z.string(), z.number()])
    .optional()
    .transform((v) => (v === '' || v == null ? undefined : v)),
  criteria_requires_documents: stringArray,
  criteria_requires_candidate_documents_v1: stringArray,
  criteria_candidate_documents_allow_statuses: stringArray,
  criteria_allowed_geo_countries: stringArray,
  criteria_blocked_geo_countries: stringArray,
  criteria_preferred_documents: stringArray,
  criteria_preferred_languages: stringArray,
  vacancy_disable_auto_convert_on_fit: z.boolean().optional().default(false),
  lead_fit_evaluation_enabled: z.boolean().optional().default(false),
  headcount_target: z.string().optional().or(z.literal('')),
  order_line_id: z.string().optional().or(z.literal('')),
})

type VacancyFormValues = z.infer<typeof vacancyFormSchema>

export type WorkspaceTabKey =
  | 'workspace'
  | 'job_details'
  | 'recruitment'
  | 'requirements'
  | 'automation'
  | 'analytics'
  | 'settings'
  | 'candidates'

const PRIMARY_TABS: WorkspaceTabKey[] = [
  'workspace',
  'job_details',
  'recruitment',
  'requirements',
  'automation',
  'analytics',
  'settings',
]

function normalizeTab(raw?: string | null): WorkspaceTabKey {
  const t = String(raw || '').toLowerCase()
  if (t === 'info' || t === 'overview' || t === 'notes' || !t) return 'workspace'
  if ((PRIMARY_TABS as string[]).includes(t) || t === 'candidates') return t as WorkspaceTabKey
  return 'workspace'
}

function ensurePersistedFields(normalized: any, source: any) {
  const keepKeys = [
    'id',
    'company_id',
    'manager',
    'manager_name',
    'manager_short',
    'funnel_id',
    'candidate_profile_id',
    'order_line_id',
    'extra',
    'created_at',
    'updated_at',
    'tenant_id',
    'company_name',
    'headcount_target',
    'candidate_count',
  ] as const
  const ensured: any = { ...normalized }
  for (const k of keepKeys) {
    if (typeof ensured[k] === 'undefined' && typeof source?.[k] !== 'undefined') {
      ensured[k] = source[k]
    }
  }
  if (!ensured.status && (ensured.state || ensured.stage)) {
    ensured.status = ensured.state || ensured.stage
  }
  if (typeof ensured.is_open === 'undefined' && typeof source?.is_open !== 'undefined') {
    ensured.is_open = source.is_open
  }
  if (typeof ensured.is_open === 'undefined' && ensured.status) {
    ensured.is_open = String(ensured.status).toLowerCase() === 'open'
  }
  return ensured
}

function toFormDefaults(source: any | null): VacancyFormValues {
  const rawStatus = source?.status ?? source?.state ?? source?.stage ?? 'open'
  const normalizedStatus = normalizeVacancyStatus(rawStatus)
  const employment = source?.employment_type
  const normalizedEmployment = EMPLOYMENT_TYPES.includes(employment as EmploymentType)
    ? (employment as EmploymentType)
    : EMPLOYMENT_TYPES[0]
  const crit = criteriaDefaultsFromSource(source)

  return {
    title: source?.title ?? '',
    status: normalizedStatus,
    company_id: source?.company_id ?? '',
    description: source?.description ?? '',
    location: source?.location ?? '',
    salary_from: source?.salary_from ?? '',
    salary_to: source?.salary_to ?? '',
    currency: source?.currency ?? '',
    is_active: typeof source?.is_active === 'boolean' ? source.is_active : true,
    is_archived: !!source?.is_archived,
    is_open: typeof source?.is_open === 'boolean' ? source.is_open : normalizedStatus === 'open',
    employment_type: normalizedEmployment,
    candidate_profile_id: source?.candidate_profile_id ?? '',
    funnel_id: source?.funnel_id ?? '',
    manager: source?.manager ?? '',
    criteria_min_experience_eu_years: crit.criteria_min_experience_eu_years ?? '',
    criteria_requires_documents: crit.criteria_requires_documents,
    criteria_requires_candidate_documents_v1: crit.criteria_requires_candidate_documents_v1,
    criteria_candidate_documents_allow_statuses: crit.criteria_candidate_documents_allow_statuses,
    criteria_allowed_geo_countries: crit.criteria_allowed_geo_countries,
    criteria_blocked_geo_countries: crit.criteria_blocked_geo_countries,
    criteria_preferred_documents: crit.criteria_preferred_documents,
    criteria_preferred_languages: crit.criteria_preferred_languages,
    vacancy_disable_auto_convert_on_fit: crit.vacancy_disable_auto_convert_on_fit,
    lead_fit_evaluation_enabled: crit.lead_fit_evaluation_enabled,
    headcount_target:
      source?.headcount_target != null && Number(source.headcount_target) > 0
        ? String(source.headcount_target)
        : '',
    order_line_id: source?.order_line_id ? String(source.order_line_id) : '',
  }
}

function statusSemantic(status: string): 'success' | 'warning' | 'neutral' | 'danger' | 'info' {
  const s = status.toLowerCase()
  if (s === 'open') return 'success'
  if (s === 'on_hold') return 'warning'
  if (s === 'filled') return 'info'
  if (s === 'cancelled' || s === 'closed') return 'neutral'
  return 'neutral'
}

type Props = {
  item: any | null | undefined
  companiesMap?: Record<string, string>
  onBack: () => void
  onEdit?: () => void
  onRemove?: () => Promise<void>
}

export default function VacancyDetail({ item, companiesMap = {}, onBack, onRemove }: Props) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const planLimitModal = usePlanLimitModal()
  const { id: routeId, tab: tabFromRoute } = useParams<{ id: string; tab?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const companyFromUrl = searchParams.get('company') || ''
  const stageFromUrl = searchParams.get('stage')

  function toModel(raw: any) {
    let base = raw || {}
    try {
      base = normalizeVacancy(base)
    } catch {
      /* ignore */
    }
    const st = (base.status ?? base.state ?? base.stage ?? 'open') as any
    return {
      ...base,
      status: st,
      is_open: typeof base.is_open === 'boolean' ? base.is_open : String(st).toLowerCase() === 'open',
      salary_from: typeof base.salary_from !== 'undefined' ? base.salary_from : null,
      salary_to: typeof base.salary_to !== 'undefined' ? base.salary_to : null,
      currency: typeof base.currency !== 'undefined' ? base.currency : null,
    }
  }

  const [model, setModel] = useState<any | null>(item ? toModel(item) : null)
  const [tab, setTab] = useState<WorkspaceTabKey>(normalizeTab(tabFromRoute))
  const [menuOpen, setMenuOpen] = useState(false)
  const [stageFilter, setStageFilter] = useState<string | null>(stageFromUrl)

  const vacancyIdForBadge = (routeId || model?.id || '') as string
  const [nextActionTick, setNextActionTick] = useState(0)
  const bumpNextActionTick = useCallback(() => setNextActionTick((n) => n + 1), [])
  const {
    data: vacancyNextAction,
    loading: vacancyNextActionLoading,
    error: vacancyNextActionError,
  } = useVacancyNextAction(vacancyIdForBadge || null, nextActionTick)

  useEffect(() => {
    setTab(normalizeTab(tabFromRoute))
  }, [tabFromRoute])

  useEffect(() => {
    setStageFilter(stageFromUrl)
  }, [stageFromUrl])

  const [candLoading, setCandLoading] = useState(false)
  const [candItems, setCandItems] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [loading, setLoading] = useState<boolean>(!item)
  const [pipeCounts, setPipeCounts] = useState<Record<string, number>>({})
  const [pipeLoading, setPipeLoading] = useState(false)
  const [candidateProfiles, setCandidateProfiles] = useState<CandidateProfile[]>([])
  const [requirementsPresets, setRequirementsPresets] = useState<VacancyRequirementsPreset[]>([])
  const [orderLines, setOrderLines] = useState<SalesOrderLine[]>([])
  const [linkedOrderLine, setLinkedOrderLine] = useState<SalesOrderLine | null>(null)
  const [managerOptions, setManagerOptions] = useState<ManagerOption[]>([])
  const [recruiterOptions, setRecruiterOptions] = useState<ManagerOption[]>([])
  const [poolDraft, setPoolDraft] = useState<Record<string, { selected: boolean; weight: number }>>({})
  const isCreate = !item && routeId === 'new'

  const {
    control,
    handleSubmit,
    register,
    reset: resetForm,
    setValue,
    watch,
    formState: { errors },
  } = useForm<VacancyFormValues>({
    resolver: zodResolver(vacancyFormSchema),
    defaultValues: toFormDefaults(item ? toModel(item) : null),
  })

  const watchStatus = watch('status')
  const watchIsOpen = watch('is_open')
  const watchCompanyId = watch('company_id')
  const watchTitle = watch('title')
  const watchOrderLineId = watch('order_line_id')
  const watchManager = watch('manager')
  const watchCriteria = {
    criteria_min_experience_eu_years: watch('criteria_min_experience_eu_years'),
    criteria_requires_documents: watch('criteria_requires_documents') || [],
    criteria_requires_candidate_documents_v1: watch('criteria_requires_candidate_documents_v1') || [],
    criteria_candidate_documents_allow_statuses:
      watch('criteria_candidate_documents_allow_statuses') || [],
    criteria_allowed_geo_countries: watch('criteria_allowed_geo_countries') || [],
    criteria_blocked_geo_countries: watch('criteria_blocked_geo_countries') || [],
    criteria_preferred_documents: watch('criteria_preferred_documents') || [],
    criteria_preferred_languages: watch('criteria_preferred_languages') || [],
    vacancy_disable_auto_convert_on_fit: !!watch('vacancy_disable_auto_convert_on_fit'),
    lead_fit_evaluation_enabled: !!watch('lead_fit_evaluation_enabled'),
  }

  const goTab = useCallback(
    (next: WorkspaceTabKey, stage?: string | null) => {
      setTab(next)
      if (!model?.id && routeId !== 'new') return
      const id = model?.id || routeId
      if (!id || id === 'new') {
        setTab(next)
        return
      }
      const base = `${CRM_APP_PATHS.vacancies}/${id}/${next}`
      if (stage) {
        navigate(`${base}?stage=${encodeURIComponent(stage)}`)
        setStageFilter(stage)
      } else {
        navigate(base)
        if (next !== 'candidates') setStageFilter(null)
      }
    },
    [model?.id, navigate, routeId],
  )

  const openStageCandidates = useCallback(
    (stageCode: string) => {
      goTab('candidates', stageCode)
    },
    [goTab],
  )

  useEffect(() => {
    if (!isCreate || !watchCompanyId) {
      setOrderLines([])
      return
    }
    let cancelled = false
    void listSalesOrderLines({
      company_id: watchCompanyId,
      unlinked: true,
      status: 'open',
      limit: 100,
    })
      .then((rows) => {
        if (!cancelled) setOrderLines(rows)
      })
      .catch(() => {
        if (!cancelled) setOrderLines([])
      })
    return () => {
      cancelled = true
    }
  }, [isCreate, watchCompanyId])

  useEffect(() => {
    if (!isCreate || !watchOrderLineId) return
    const line = orderLines.find((l) => l.id === watchOrderLineId)
    if (!line) return
    setValue('headcount_target', String(line.quantity_needed))
    if (!watchTitle) setValue('title', line.title)
    if (line.location) setValue('location', line.location)
  }, [isCreate, watchOrderLineId, orderLines, setValue, watchTitle])

  useEffect(() => {
    const orderLineId = model?.order_line_id || watchOrderLineId
    if (!orderLineId || isCreate) {
      setLinkedOrderLine(null)
      return
    }
    let cancelled = false
    void listSalesOrderLines({ limit: 200 })
      .then((rows) => {
        if (cancelled) return
        const found = rows.find((l) => l.id === orderLineId) || null
        setLinkedOrderLine(found)
      })
      .catch(() => {
        if (!cancelled) setLinkedOrderLine(null)
      })
    return () => {
      cancelled = true
    }
  }, [model?.order_line_id, watchOrderLineId, isCreate])

  useEffect(() => {
    resetForm(toFormDefaults(model))
  }, [model, resetForm])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [managers, recruiters] = await Promise.all([
          listTenantManagers(),
          listTenantManagers({ roles: ['recruiter'] }),
        ])
        if (!cancelled) {
          setManagerOptions(managers)
          setRecruiterOptions(recruiters)
        }
      } catch {
        if (!cancelled) {
          setManagerOptions([])
          setRecruiterOptions([])
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const syncPoolDraftFromItems = useCallback(
    (items: VacancyRecruiterPoolItem[], recruiters: ManagerOption[]) => {
      const next: Record<string, { selected: boolean; weight: number }> = {}
      for (const opt of recruiters) {
        next[opt.id] = { selected: false, weight: 1 }
      }
      for (const row of items) {
        next[row.user_id] = {
          selected: true,
          weight: Math.max(1, Number(row.weight) || 1),
        }
      }
      setPoolDraft(next)
    },
    [],
  )

  useEffect(() => {
    if (!model?.id || isCreate) {
      syncPoolDraftFromItems([], recruiterOptions)
      return
    }
    let cancelled = false
    getVacancyRecruiters(String(model.id))
      .then((data) => {
        if (!cancelled) syncPoolDraftFromItems(data.items, recruiterOptions)
      })
      .catch(() => {
        if (!cancelled) syncPoolDraftFromItems([], recruiterOptions)
      })
    return () => {
      cancelled = true
    }
  }, [model?.id, isCreate, recruiterOptions, syncPoolDraftFromItems])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const items = await listVacancyRequirementsPresets()
        if (!cancelled) setRequirementsPresets(items)
      } catch {
        if (!cancelled) setRequirementsPresets([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const shouldBeOpen = (watchStatus ?? 'open') === 'open'
    if (watchIsOpen !== shouldBeOpen) setValue('is_open', shouldBeOpen)
  }, [watchStatus, watchIsOpen, setValue])

  const loadCandidates = useCallback(async () => {
    if (!model?.id) return
    setCandLoading(true)
    try {
      let candData: any
      try {
        const r = await api.get('/candidates?limit=200&offset=0')
        candData = r.data
      } catch {
        const r = await api.get('/candidates/')
        candData = r.data
      }
      const list: any[] = Array.isArray(candData) ? candData : candData?.items || []
      setCandItems(
        list.filter(
          (c: any) =>
            String(c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id ?? '') === String(model.id),
        ),
      )
    } finally {
      setCandLoading(false)
    }
  }, [model?.id])

  useEffect(() => {
    if (tab === 'candidates') loadCandidates()
  }, [tab, loadCandidates])

  const loadPipe = useCallback(async () => {
    if (!model?.id) return
    setPipeLoading(true)
    try {
      const response = await api.get(`/vacancies/${model.id}/pipeline`, {
        validateStatus: (status) => status === 200 || status === 404,
      })
      if (response.status === 404) {
        setPipeCounts({})
        return
      }
      const cols = (response.data?.columns || response.data?.columns_by_status || {}) as Record<
        string,
        unknown
      >
      // Count by candidate.stage (not kanban column key) so Vacancy Progress
      // treats employed/hired/probation_ok as success even when they land in
      // aggregated columns like client_process / internal_hr.
      setPipeCounts(stageCountsFromPipelineColumns(cols))
    } catch {
      setPipeCounts({})
    } finally {
      setPipeLoading(false)
    }
  }, [model?.id])

  useEffect(() => {
    void loadPipe()
  }, [loadPipe])

  useEffect(() => {
    void listCandidateProfiles({ is_active: true })
      .then(setCandidateProfiles)
      .catch(() => setCandidateProfiles([]))
  }, [])

  useEffect(() => {
    if (item) {
      setModel(toModel(item))
      setLoading(false)
      return
    }
    if (!item && routeId === 'new') {
      setModel(
        toModel({
          title: '',
          description: '',
          status: 'open',
          is_open: true,
          is_active: true,
          is_archived: false,
          location: '',
          employment_type: EMPLOYMENT_TYPES[0],
          company_id: companyFromUrl || '',
          salary_from: null,
          salary_to: null,
          currency: null,
        }),
      )
      setLoading(false)
      return
    }
    if (!item && routeId) {
      setLoading(true)
      getVacancy(routeId)
        .then((data) => setModel(toModel(data)))
        .catch(() => setModel(null))
        .finally(() => setLoading(false))
    }
  }, [item, routeId, companyFromUrl])

  const submitVacancy = useCallback(
    async (values: VacancyFormValues) => {
      setSaving(true)
      try {
        const mode: 'create' | 'update' = model?.id ? 'update' : 'create'
        const payload = buildVacancyPayload(values, model, mode)
        applyCriteriaToPayload(payload as any, {
          criteria_min_experience_eu_years: values.criteria_min_experience_eu_years,
          criteria_requires_documents: values.criteria_requires_documents || [],
          criteria_requires_candidate_documents_v1:
            values.criteria_requires_candidate_documents_v1 || [],
          criteria_candidate_documents_allow_statuses:
            values.criteria_candidate_documents_allow_statuses || [],
          criteria_allowed_geo_countries: values.criteria_allowed_geo_countries || [],
          criteria_blocked_geo_countries: values.criteria_blocked_geo_countries || [],
          criteria_preferred_documents: values.criteria_preferred_documents || [],
          criteria_preferred_languages: values.criteria_preferred_languages || [],
          vacancy_disable_auto_convert_on_fit: !!values.vacancy_disable_auto_convert_on_fit,
          lead_fit_evaluation_enabled: !!values.lead_fit_evaluation_enabled,
        })

        const response =
          mode === 'update' ? await updateVacancy(model!.id, payload) : await createVacancy(payload)

        const vacancyId = String(
          mode === 'update' ? model!.id : response?.id || response?.vacancy_id || '',
        )
        if (vacancyId) {
          const poolItems = Object.entries(poolDraft)
            .filter(([, row]) => row.selected)
            .map(([userId, row]) => ({
              user_id: userId,
              weight: Math.max(1, Math.min(100, Number(row.weight) || 1)),
              is_active: true,
            }))
          await putVacancyRecruiters(vacancyId, poolItems)
        }

        const latest =
          mode === 'update'
            ? await getVacancy(model!.id)
            : vacancyId
              ? await getVacancy(vacancyId)
              : response
        const hydrated = hydrateSavedWithForm(latest, values, payload)
        const ensured = ensurePersistedFields(hydrated, latest)
        setModel(ensured)
        resetForm(toFormDefaults(ensured))
        bumpNextActionTick()
        setSavedOk(true)
        setTimeout(() => setSavedOk(false), 2000)
        if (mode === 'create' && vacancyId) {
          navigate(`${CRM_APP_PATHS.vacancies}/${vacancyId}/workspace`)
        }
      } catch (err: any) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.vacancies.form.save_failed'))) {
          return
        }
        const r = err?.response?.data
        const detail =
          typeof r?.detail === 'string'
            ? r.detail
            : Array.isArray(r?.detail)
              ? JSON.stringify(r.detail)
              : r
                ? JSON.stringify(r)
                : err?.message || 'Unknown error'
        alert(t('app.vacancies.detail.save_failed_alert', { defaultValue: 'Save failed: {detail}', values: { detail } }))
        throw err
      } finally {
        setSaving(false)
      }
    },
    [model, planLimitModal, poolDraft, resetForm, t, bumpNextActionTick, navigate],
  )

  const save = useCallback(async () => {
    await handleSubmit(submitVacancy)()
  }, [handleSubmit, submitVacancy])

  const companyName = useMemo(() => {
    const candidateId = watchCompanyId || model?.company_id
    const fromMap = candidateId ? companiesMap[candidateId] : undefined
    return fromMap ?? model?.company_name ?? candidateId ?? ''
  }, [companiesMap, model?.company_id, model?.company_name, watchCompanyId])

  const statusText = String(watchStatus ?? model?.status ?? 'open')
  const metrics = useMemo(
    () =>
      computePipelineMetrics(
        pipeCounts,
        model?.headcount_target ??
          (watch('headcount_target') ? Number(watch('headcount_target')) : null),
      ),
    [pipeCounts, model?.headcount_target, watch],
  )

  const companyOptions = useMemo(
    () => Object.entries(companiesMap).map(([id, name]) => ({ id, name: name || id })),
    [companiesMap],
  )

  const poolSelectedCount = useMemo(
    () => Object.values(poolDraft).filter((r) => r.selected).length,
    [poolDraft],
  )

  const managerLabel = useMemo(() => {
    const id = watchManager || model?.manager
    const opt = managerOptions.find((m) => m.id === id)
    return (
      model?.manager_name ||
      model?.manager_short ||
      opt?.label ||
      opt?.full_name ||
      opt?.email ||
      id ||
      '—'
    )
  }, [watchManager, model, managerOptions])

  async function refresh() {
    if (!model?.id) return
    setLoading(true)
    try {
      const data = await getVacancy(model.id)
      setModel(toModel(data))
      await loadPipe()
      bumpNextActionTick()
    } finally {
      setLoading(false)
    }
  }

  async function exportCSV() {
    if (!model?.id) return
    let candData: any
    try {
      const r = await api.get('/candidates?limit=1000&offset=0')
      candData = r.data
    } catch {
      const r = await api.get('/candidates/')
      candData = r.data
    }
    const list: any[] = Array.isArray(candData) ? candData : candData?.items || []
    const filtered = list.filter(
      (c: any) => String(c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id ?? '') === String(model.id),
    )
    const rows = [
      ['id', 'name', 'email', 'stage', 'phone', 'created_at'] as const,
      ...filtered.map((c: any) => [
        c.id,
        c.name || [c.first_name, c.last_name].filter(Boolean).join(' '),
        c.email || '',
        String(c.stage ?? c.status ?? ''),
        c.phone || '',
        c.created_at || '',
      ]),
    ]
    const csv = rows
      .map((r) =>
        r
          .map((x) => {
            const s = (x ?? '').toString().replace(/"/g, '""')
            return `"${s}"`
          })
          .join(','),
      )
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vacancy_${model.id}_candidates.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleRemove = onRemove
    ? async () => {
        if (!confirm(t('app.vacancies.detail.delete_confirm', { defaultValue: 'Delete this vacancy? This cannot be undone.' }))) return
        await onRemove()
      }
    : undefined

  const pauseVacancy = async () => {
    setValue('status', 'on_hold')
    await save()
  }

  if (loading) {
    return <div className="text-slate-500">{t('common.loading')}</div>
  }
  if (!model) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-800">
        {t('app.vacancies.detail.not_found', {
          defaultValue: 'Vacancy not found or unavailable.',
        })}
        <button type="button" onClick={onBack} className="ml-2 underline">
          {t('common.actions.back', { defaultValue: 'Back' })}
        </button>
      </div>
    )
  }

  const statusLabel = t(`app.vacancies.list.status.${statusText}`, { defaultValue: statusText })
  const tw = 'app.vacancies.workspace'

  return (
    <PageShell>
      <div className="sticky top-0 z-20 -mx-1 border-b border-slate-200 bg-white/95 px-1 pb-3 pt-1 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-xl font-semibold text-slate-900">
                {watchTitle || model?.title || t('app.vacancies.detail.untitled')}
              </h1>
              <StatusBadge label={statusLabel} semantic={statusSemantic(statusText)} size="sm" />
              {vacancyIdForBadge ? (
                <NextActionBadge
                  dto={vacancyNextAction}
                  loading={vacancyNextActionLoading}
                  error={vacancyNextActionError}
                />
              ) : null}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
              {companyName ? (
                <span>
                  {t(`${tw}.meta.client`, { defaultValue: 'Client' })}: {companyName}
                </span>
              ) : null}
              {linkedOrderLine ? (
                <span>
                  {t(`${tw}.meta.order`, { defaultValue: 'Order' })}: {linkedOrderLine.title}
                </span>
              ) : null}
              {watch('funnel_id') ? (
                <span>
                  {t(`${tw}.meta.funnel`, { defaultValue: 'Funnel' })}:{' '}
                  <span className="font-mono">{String(watch('funnel_id')).slice(0, 8)}…</span>
                </span>
              ) : null}
              <span>
                {t(`${tw}.meta.recruiter`, { defaultValue: 'Recruiter' })}: {managerLabel}
              </span>
            </div>
            <div className="flex flex-wrap gap-3 text-xs font-medium text-slate-700">
              <span>
                {t(`${tw}.kpi.headcount`, { defaultValue: 'Headcount' })}: {metrics.plan ?? '—'}
              </span>
              <span>
                {t(`${tw}.kpi.hired`, { defaultValue: 'Hired' })}: {metrics.hired}
              </span>
              <span>
                {t(`${tw}.kpi.remaining`, { defaultValue: 'Remaining' })}:{' '}
                {metrics.remaining ?? '—'}
              </span>
              <span>
                {t(`${tw}.kpi.completion`, { defaultValue: 'Completion' })}:{' '}
                {metrics.completionPct != null ? `${metrics.completionPct}%` : '—'}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn-secondary btn-sm" onClick={onBack}>
              {t('common.actions.back', { defaultValue: 'Back' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={refresh}>
              {t('common.actions.refresh')}
            </button>
            {statusText === 'open' ? (
              <button type="button" className="btn-secondary btn-sm" onClick={pauseVacancy}>
                {t(`${tw}.actions.pause`, { defaultValue: 'Pause' })}
              </button>
            ) : null}
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={() => goTab('job_details')}
            >
              {t(`${tw}.actions.edit`, { defaultValue: 'Edit' })}
            </button>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={saving}
              onClick={save}
            >
              {saving ? t('common.saving') : t('common.actions.save')}
            </button>
            <div className="relative">
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setMenuOpen((o) => !o)}
                aria-label="More"
              >
                ⋮
              </button>
              {menuOpen ? (
                <div className="absolute right-0 z-30 mt-1 w-48 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                  <Link
                    className="block px-3 py-2 text-sm hover:bg-slate-50"
                    to={
                      model?.id
                        ? `${CRM_APP_PATHS.candidates}?view=kanban&vacancy=${model.id}`
                        : `${CRM_APP_PATHS.candidates}?view=kanban`
                    }
                    onClick={() => setMenuOpen(false)}
                  >
                    {t('app.candidates.pipeline.title')}
                  </Link>
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                    onClick={() => {
                      setMenuOpen(false)
                      void exportCSV()
                    }}
                  >
                    {t(`${tw}.actions.export`, { defaultValue: 'Export report' })}
                  </button>
                  {handleRemove ? (
                    <button
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm text-rose-700 hover:bg-rose-50"
                      onClick={() => {
                        setMenuOpen(false)
                        void handleRemove()
                      }}
                    >
                      {t('common.actions.delete')}
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {savedOk ? (
          <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {t('common.messages.saved')}
          </div>
        ) : null}

        {model?.id && routeId !== 'new' ? (
          <div className="mt-3">
            <StageMetricCards
              stages={metrics.stages}
              loading={pipeLoading}
              viewListLabel={t(`${tw}.stage_cards.view_list`, { defaultValue: 'View list' })}
              onSelect={openStageCandidates}
            />
          </div>
        ) : null}

        <div className="mt-3 flex flex-wrap gap-1">
          {[...PRIMARY_TABS, 'candidates' as WorkspaceTabKey].map((key) => (
            <button
              key={key}
              type="button"
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                tab === key
                  ? 'bg-slate-900 text-white'
                  : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
              onClick={() => goTab(key)}
            >
              {t(`${tw}.tabs.${key}`, {
                defaultValue:
                  key === 'workspace'
                    ? 'Workspace'
                    : key === 'job_details'
                      ? 'Job Details'
                      : key === 'recruitment'
                        ? 'Recruitment'
                        : key === 'requirements'
                          ? 'Candidate Requirements'
                          : key === 'automation'
                            ? 'Automation'
                            : key === 'analytics'
                              ? 'Analytics'
                              : key === 'settings'
                                ? 'Settings'
                                : 'Candidates',
              })}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pt-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
        >
          {tab === 'workspace' ? (
            <WorkspaceTab
              metrics={metrics}
              orderLine={
                linkedOrderLine
                  ? {
                      quantity_needed: linkedOrderLine.quantity_needed,
                      title: linkedOrderLine.title,
                    }
                  : null
              }
              mainInfoRows={[
                {
                  label: t(`${tw}.main.location`, { defaultValue: 'Location' }),
                  value: watch('location') || model?.location,
                },
                {
                  label: t(`${tw}.main.employment`, { defaultValue: 'Employment' }),
                  value: watch('employment_type'),
                },
                {
                  label: t(`${tw}.main.salary`, { defaultValue: 'Salary' }),
                  value: [watch('salary_from'), watch('salary_to')]
                    .filter((v) => v !== '' && v != null)
                    .join(' – '),
                },
                {
                  label: t(`${tw}.main.currency`, { defaultValue: 'Currency' }),
                  value: watch('currency'),
                },
                {
                  label: t(`${tw}.kpi.headcount`, { defaultValue: 'Headcount' }),
                  value: metrics.plan ?? '—',
                },
                {
                  label: t(`${tw}.kpi.hired`, { defaultValue: 'Hired' }),
                  value: metrics.hired,
                },
              ]}
              mandatoryCards={[
                {
                  title: t(`${tw}.req.documents`, { defaultValue: 'Documents' }),
                  items: [
                    ...(watchCriteria.criteria_requires_candidate_documents_v1 || []),
                    ...(watchCriteria.criteria_requires_documents || []),
                  ],
                },
                {
                  title: t(`${tw}.req.experience`, { defaultValue: 'Experience' }),
                  items: watchCriteria.criteria_min_experience_eu_years
                    ? [
                        `${watchCriteria.criteria_min_experience_eu_years}+ ${t(`${tw}.req.years`, { defaultValue: 'years' })}`,
                      ]
                    : [],
                },
                {
                  title: t(`${tw}.req.countries_allowed`, { defaultValue: 'Allowed countries' }),
                  items: watchCriteria.criteria_allowed_geo_countries || [],
                },
                {
                  title: t(`${tw}.req.countries_blocked`, { defaultValue: 'Blocked countries' }),
                  items: watchCriteria.criteria_blocked_geo_countries || [],
                },
              ]}
              preferredCards={[
                {
                  title: t(`${tw}.req.preferred_docs`, { defaultValue: 'Preferred documents' }),
                  items: watchCriteria.criteria_preferred_documents || [],
                },
                {
                  title: t(`${tw}.req.languages`, { defaultValue: 'Languages' }),
                  items: watchCriteria.criteria_preferred_languages || [],
                },
              ]}
              preferredEmptyNote={t(`${tw}.req.preferred_empty`, {
                defaultValue: 'Preferred requirements will appear when configured.',
              })}
              onEditRequirements={() => goTab('requirements')}
              onStageClick={openStageCandidates}
              hasManager={!!(watchManager || model?.manager)}
              poolSelectedCount={poolSelectedCount}
              ownerName={String(managerLabel)}
              quickActions={[
                {
                  id: 'add-candidate',
                  label: t(`${tw}.quick.add_candidate`, { defaultValue: 'Add candidate' }),
                  href: model?.id
                    ? `${CRM_APP_PATHS.candidateNew}?vacancy=${model.id}`
                    : CRM_APP_PATHS.candidateNew,
                },
                {
                  id: 'assign-recruiter',
                  label: t(`${tw}.quick.assign_recruiter`, { defaultValue: 'Assign recruiter' }),
                  onClick: () => goTab('recruitment'),
                },
                {
                  id: 'create-doc',
                  label: t(`${tw}.quick.create_document`, { defaultValue: 'Create document' }),
                  href: CRM_APP_PATHS.documents,
                },
                {
                  id: 'message',
                  label: t(`${tw}.quick.message`, { defaultValue: 'Message candidate' }),
                  disabled: true,
                  title: t(`${tw}.quick.soon`, { defaultValue: 'Coming soon' }),
                },
                {
                  id: 'export',
                  label: t(`${tw}.quick.export`, { defaultValue: 'Export report' }),
                  onClick: () => void exportCSV(),
                },
              ]}
              relatedLinks={[
                {
                  id: 'company',
                  label: t(`${tw}.related.company`, { defaultValue: 'Company' }),
                  href: model?.company_id
                    ? `${CRM_APP_PATHS.companiesLegacy}/${model.company_id}`
                    : undefined,
                  value: companyName || undefined,
                  disabled: !model?.company_id,
                },
                {
                  id: 'order',
                  label: t(`${tw}.related.order`, { defaultValue: 'Order' }),
                  href: linkedOrderLine
                    ? `${CRM_APP_PATHS.salesOrders}/${linkedOrderLine.sales_order_id}`
                    : undefined,
                  value: linkedOrderLine?.title,
                  disabled: !linkedOrderLine,
                },
                {
                  id: 'funnel',
                  label: t(`${tw}.related.funnel`, { defaultValue: 'Funnel' }),
                  href: CRM_APP_PATHS.settingsFunnels || CRM_APP_PATHS.settings,
                  value: watch('funnel_id') ? String(watch('funnel_id')).slice(0, 8) : undefined,
                  disabled: !watch('funnel_id'),
                },
                {
                  id: 'profile',
                  label: t(`${tw}.related.profile`, { defaultValue: 'Candidate profile' }),
                  href: CRM_APP_PATHS.settingsCandidateProfiles,
                  value: candidateProfiles.find((p) => p.id === watch('candidate_profile_id'))
                    ?.name,
                  disabled: !watch('candidate_profile_id'),
                },
                {
                  id: 'documents',
                  label: t(`${tw}.related.documents`, { defaultValue: 'Documents' }),
                  href: CRM_APP_PATHS.documents,
                  value: t(`${tw}.related.open`, { defaultValue: 'Open' }),
                },
                {
                  id: 'recruiter',
                  label: t(`${tw}.related.recruiter`, { defaultValue: 'Recruiter' }),
                  value: String(managerLabel),
                  disabled: true,
                },
                {
                  id: 'team',
                  label: t(`${tw}.related.team`, { defaultValue: 'Team' }),
                  value: String(poolSelectedCount),
                  disabled: true,
                },
                {
                  id: 'meta',
                  label: t(`${tw}.related.meta`, { defaultValue: 'Meta campaigns' }),
                  value: t(`${tw}.related.soon`, { defaultValue: 'Soon' }),
                  disabled: true,
                },
                {
                  id: 'forms',
                  label: t(`${tw}.related.forms`, { defaultValue: 'Forms' }),
                  value: t(`${tw}.related.soon`, { defaultValue: 'Soon' }),
                  disabled: true,
                },
              ]}
              labels={{
                orderProgress: t(`${tw}.order_progress`, { defaultValue: 'Order Progress' }),
                orderHint: t(`${tw}.order_hint`, {
                  defaultValue:
                    'Order fulfillment uses vacancy hired count until order-level fulfillment API is available.',
                }),
                vacancyProgress: t(`${tw}.vacancy_progress`, { defaultValue: 'Vacancy Progress' }),
                headcount: t(`${tw}.kpi.headcount`, { defaultValue: 'Headcount' }),
                hired: t(`${tw}.kpi.hired`, { defaultValue: 'Hired' }),
                remaining: t(`${tw}.kpi.remaining`, { defaultValue: 'Remaining' }),
                completion: t(`${tw}.kpi.completion`, { defaultValue: 'Completion' }),
                mainInfo: t(`${tw}.main.title`, { defaultValue: 'Main information' }),
                requirements: t(`${tw}.req.title`, { defaultValue: 'Candidate requirements' }),
                mandatory: t(`${tw}.req.mandatory`, { defaultValue: 'Mandatory' }),
                preferred: t(`${tw}.req.preferred`, { defaultValue: 'Preferred' }),
                edit: t(`${tw}.actions.edit`, { defaultValue: 'Edit' }),
                funnel: t(`${tw}.funnel`, { defaultValue: 'Recruitment funnel' }),
                funnelEmpty: t(`${tw}.funnel_empty`, { defaultValue: 'No pipeline data yet.' }),
                activity: t(`${tw}.activity.title`, { defaultValue: 'Recent activity' }),
                activityMessage: t(`${tw}.activity.message`, {
                  defaultValue:
                    'Vacancy activity history will appear after Activity Feed is connected.',
                }),
                attention: t(`${tw}.attention.title`, { defaultValue: 'Needs attention' }),
                noRecruiter: t(`${tw}.attention.no_recruiter`, {
                  defaultValue: 'No manager or recruiter assigned',
                }),
                waitingDocs: t(`${tw}.attention.waiting_docs`, {
                  defaultValue: '{count} candidates waiting for documents ({stage})',
                }),
                permit: t(`${tw}.attention.permit`, {
                  defaultValue: '{count} in work permit ({stage})',
                }),
                attentionEmpty: t(`${tw}.attention.empty`, {
                  defaultValue: 'Nothing urgent right now.',
                }),
                quickActions: t(`${tw}.quick.title`, { defaultValue: 'Quick actions' }),
                owner: t(`${tw}.owner`, { defaultValue: 'Owner' }),
                related: t(`${tw}.related.title`, { defaultValue: 'Related' }),
              }}
            />
          ) : null}

          {tab === 'job_details' ? (
            <JobDetailsTab
              register={register}
              errors={errors}
              watch={watch}
              companyOptions={companyOptions}
              candidateProfiles={candidateProfiles}
              orderLines={orderLines}
              isCreate={isCreate}
              labels={{
                section: t(`${tw}.tabs.job_details`, { defaultValue: 'Job Details' }),
                title: t('app.vacancies.detail.fields.title', { defaultValue: 'Title' }),
                company: t('app.vacancies.detail.fields.company', { defaultValue: 'Company' }),
                description: t('app.vacancies.detail.fields.description', {
                  defaultValue: 'Description',
                }),
                location: t(`${tw}.main.location`, { defaultValue: 'Location' }),
                employment: t(`${tw}.main.employment`, { defaultValue: 'Employment' }),
                salaryFrom: t('app.vacancies.detail.fields.salary_from', {
                  defaultValue: 'Salary from',
                }),
                salaryTo: t('app.vacancies.detail.fields.salary_to', {
                  defaultValue: 'Salary to',
                }),
                currency: t(`${tw}.main.currency`, { defaultValue: 'Currency' }),
                headcount: t('app.vacancies.detail.fields.headcount_target'),
                headcountHint: t('app.vacancies.detail.fields.headcount_hint'),
                orderLine: t(`${tw}.related.order`, { defaultValue: 'Order line' }),
                orderLineNone: t(`${tw}.order_none`, {
                  defaultValue: '— free vacancy (no order) —',
                }),
                profile: t(`${tw}.related.profile`, { defaultValue: 'Candidate profile' }),
                profileNone: t(`${tw}.profile_none`, { defaultValue: '— not selected —' }),
              }}
            />
          ) : null}

          {tab === 'recruitment' ? (
            <RecruitmentTab
              control={control}
              register={register}
              watch={watch}
              companyId={watchCompanyId || ''}
              managerOptions={managerOptions}
              recruiterOptions={recruiterOptions}
              poolDraft={poolDraft}
              setPoolDraft={setPoolDraft}
              stageCodes={metrics.stages.map((s) => s.code)}
              labels={{
                section: t(`${tw}.tabs.recruitment`, { defaultValue: 'Recruitment' }),
                pipeline: t('app.vacancies.detail.recruitment_pipeline', {
                  defaultValue: 'Recruitment Pipeline',
                }),
                pipelineHint: t('app.vacancies.detail.recruitment_pipeline_hint', {
                  defaultValue: 'Assigned to this vacancy.',
                }),
                pipelineRequired: t('app.vacancies.detail.recruitment_pipeline_required', {
                  defaultValue: 'Without a pipeline, search launch should not proceed.',
                }),
                assignment: t('app.vacancies.detail.assignment.title', {
                  defaultValue: 'Assignment',
                }),
                assignmentHint: t('app.vacancies.detail.assignment.hint', {
                  defaultValue: 'Manager is the primary owner.',
                }),
                manager: t('app.vacancies.detail.assignment.manager', {
                  defaultValue: 'Vacancy manager',
                }),
                managerNone: t('app.vacancies.detail.assignment.manager_none', {
                  defaultValue: '— not set —',
                }),
                recruiters: t('app.vacancies.detail.assignment.recruiters', {
                  defaultValue: 'Recruiters',
                }),
                noRecruiters: t('app.vacancies.detail.assignment.no_recruiters', {
                  defaultValue: 'No recruiters.',
                }),
                weight: t('app.vacancies.detail.assignment.weight', { defaultValue: 'Weight' }),
                rotationHint: t('app.vacancies.detail.assignment.rotation_hint', {
                  defaultValue: 'Higher weight receives more candidates.',
                }),
                autoAssign: t(`${tw}.recruitment.auto_assign`, {
                  defaultValue: 'Auto assignment',
                }),
                autoAssignHint: t(`${tw}.recruitment.auto_assign_hint`, {
                  defaultValue: 'Pool weights drive least-load rotation.',
                }),
                sla: t(`${tw}.recruitment.sla`, { defaultValue: 'SLA' }),
                slaReserved: t(`${tw}.recruitment.sla_reserved`, {
                  defaultValue: 'SLA configuration will appear here.',
                }),
                transitions: t(`${tw}.recruitment.transitions`, {
                  defaultValue: 'Transition rules',
                }),
                transitionsReserved: t(`${tw}.recruitment.transitions_reserved`, {
                  defaultValue: 'Transition rules will appear here.',
                }),
                systemStages: t(`${tw}.recruitment.system_stages`, {
                  defaultValue: 'System stages',
                }),
                systemStagesEmpty: t(`${tw}.recruitment.system_stages_empty`, {
                  defaultValue: 'No stages loaded yet.',
                }),
              }}
            />
          ) : null}

          {tab === 'requirements' ? (
            <CandidateRequirementsTab
              control={control}
              setValue={setValue}
              locale={locale}
              requirementsPresets={requirementsPresets}
              labels={{
                section: t(`${tw}.tabs.requirements`, {
                  defaultValue: 'Candidate Requirements',
                }),
                mandatory: t(`${tw}.req.mandatory`, { defaultValue: 'Mandatory' }),
                preferred: t(`${tw}.req.preferred`, { defaultValue: 'Preferred' }),
                preferredNote: t(`${tw}.req.preferred_note`, {
                  defaultValue:
                    'Preferred criteria are soft signals. Full preferred schema may expand later.',
                }),
                experience: t(`${tw}.req.experience`, { defaultValue: 'Min. EU experience (years)' }),
                documents: t(`${tw}.req.documents`, { defaultValue: 'Required documents' }),
                candidateDocs: t('app.vacancies.detail.criteria.candidate_docs_module'),
                allowStatuses: t(`${tw}.req.allow_statuses`, {
                  defaultValue: 'Allowed document statuses',
                }),
                allowedGeo: t(`${tw}.req.countries_allowed`, {
                  defaultValue: 'Allowed countries',
                }),
                blockedGeo: t(`${tw}.req.countries_blocked`, {
                  defaultValue: 'Blocked countries',
                }),
                preferredDocs: t(`${tw}.req.preferred_docs`, {
                  defaultValue: 'Preferred documents',
                }),
                preferredLang: t(`${tw}.req.languages`, { defaultValue: 'Languages' }),
                preferredLangHint: t(`${tw}.req.languages_hint`, {
                  defaultValue: 'Comma-separated language codes (e.g. pl, en).',
                }),
                enableFit: t('app.vacancies.detail.criteria.enable_fit_evaluation'),
                enableFitHint: t('app.vacancies.detail.criteria.enable_fit_evaluation_hint'),
                disableConvert: t('app.vacancies.detail.criteria.disable_auto_convert'),
                disableConvertHint: t('app.vacancies.detail.criteria.disable_auto_convert_hint'),
                preset: t(`${tw}.req.preset`, { defaultValue: '— requirements preset —' }),
                applyPreset: t(`${tw}.req.apply_preset`, { defaultValue: 'Apply preset' }),
              }}
            />
          ) : null}

          {tab === 'automation' ? (
            <AutomationTab
              values={watchCriteria}
              title={t(`${tw}.tabs.automation`, { defaultValue: 'Automation' })}
              empty={t(`${tw}.automation.empty`, {
                defaultValue: 'No automation rules derived from current requirements.',
              })}
              ifLabel={t(`${tw}.automation.if`, { defaultValue: 'If' })}
              thenLabel={t(`${tw}.automation.then`, { defaultValue: 'Then' })}
            />
          ) : null}

          {tab === 'analytics' ? (
            <AnalyticsTab
              metrics={metrics}
              onStageClick={openStageCandidates}
              labels={{
                title: t(`${tw}.tabs.analytics`, { defaultValue: 'Analytics' }),
                funnel: t(`${tw}.funnel`, { defaultValue: 'Recruitment funnel' }),
                funnelEmpty: t(`${tw}.funnel_empty`, { defaultValue: 'No pipeline data yet.' }),
                reserved: t(`${tw}.analytics.reserved`, { defaultValue: 'No data yet' }),
                applications: t(`${tw}.analytics.applications`, { defaultValue: 'Applications' }),
                conversion: t(`${tw}.analytics.conversion`, { defaultValue: 'Conversion' }),
                sources: t(`${tw}.analytics.sources`, { defaultValue: 'Sources' }),
                cost: t(`${tw}.analytics.cost`, { defaultValue: 'Cost' }),
                timeToHire: t(`${tw}.analytics.time_to_hire`, { defaultValue: 'Time to Hire' }),
                hireRate: t(`${tw}.analytics.hire_rate`, { defaultValue: 'Hire Rate' }),
              }}
            />
          ) : null}

          {tab === 'settings' ? (
            <SettingsTab
              control={control}
              register={register}
              model={model}
              onDelete={handleRemove}
              labels={{
                section: t(`${tw}.tabs.settings`, { defaultValue: 'Settings' }),
                id: t('app.vacancies.detail.fields.id'),
                created: t(`${tw}.settings.created`, { defaultValue: 'Created' }),
                updated: t(`${tw}.settings.updated`, { defaultValue: 'Updated' }),
                active: t(`${tw}.settings.active`, { defaultValue: 'Active' }),
                archived: t(`${tw}.settings.archived`, { defaultValue: 'Archived' }),
                open: t(`${tw}.settings.open`, { defaultValue: 'Open' }),
                status: t(`${tw}.settings.status`, { defaultValue: 'Status' }),
                delete: t('common.actions.delete'),
                technicalHint: t(`${tw}.settings.hint`, {
                  defaultValue: 'Technical parameters only. Business fields live on other tabs.',
                }),
                statusOptions: STATUS_OPTIONS.map((s) => ({
                  value: s,
                  label: t(`app.vacancies.list.status.${s}`, { defaultValue: s }),
                })),
              }}
            />
          ) : null}

          {tab === 'candidates' ? (
            <CandidatesTab
              loading={candLoading}
              items={candItems}
              stageFilter={stageFilter}
              onClearFilter={() => {
                setStageFilter(null)
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev)
                  next.delete('stage')
                  return next
                })
              }}
              labels={{
                title: t(`${tw}.tabs.candidates`, { defaultValue: 'Candidates' }),
                loading: t('common.loading'),
                empty: t(`${tw}.candidates.empty`, {
                  defaultValue: 'No candidates for this vacancy yet.',
                }),
                filterActive: t(`${tw}.candidates.filter`, { defaultValue: 'Filter' }),
                clearFilter: t(`${tw}.candidates.clear_filter`, { defaultValue: 'Clear filter' }),
                candidate: t('app.vacancies.detail.table.candidate'),
                email: t('app.vacancies.detail.table.email'),
                stage: t('app.vacancies.detail.table.stage'),
              }}
            />
          ) : null}
        </form>
      </div>
    </PageShell>
  )
}
