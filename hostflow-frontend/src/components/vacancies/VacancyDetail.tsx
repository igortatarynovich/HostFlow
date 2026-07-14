import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { normalizeVacancy, formatDate, buildVacancyPayload, hydrateSavedWithForm } from '../../utils/vacancyUtils'
import StageTag from '../StageTag'
import { api } from '../../api/client'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { SectionCard } from '../ui/SectionCard'
import { useI18n } from '../../i18n'
import type { LocaleCode } from '../../i18n'
import { EMPLOYMENT_TYPES, VACANCY_STATUSES, createVacancy, getVacancy, normalizeVacancyStatus, updateVacancy } from '../../api/vacancies'
import type { EmploymentType, VacancyStatus } from '../../api/vacancies'
import { listCandidateProfiles, type CandidateProfile } from '../../api/candidate_profiles'
import { listVacancyRequirementsPresets, type VacancyRequirementsPreset } from '../../api/tenants'
import { usePermissions } from '../../hooks/usePermissions'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageHeader } from '../nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../layout'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { servicesWorkspacePath } from '../../modules/services/utils'
import { NextActionBadge } from '../candidate/NextActionBadge'
import { useVacancyNextAction } from '../vacancy/useVacancyNextAction'
import { useEffectiveVacancyLayout } from '../../hooks/useEffectiveVacancyLayout'
import {
  getVacancyFieldsRenderOrder,
  vacancyFieldLabel,
  vacancyFieldRequired,
  vacancyFieldVisible,
  type VacancyRegistryFieldKey,
} from '../../utils/vacancyLayoutUtils'

const primaryBtn = 'btn-primary'
const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-slate-300 text-slate-800 bg-white hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer";

// Phase 2.6.D Stage C — single source of truth for status options;
// see `docs/specs/vacancy-statuses.md`. Backend `VacancyOut` already
// normalizes legacy `paused` rows to `on_hold` before they reach us.
const STATUS_OPTIONS = VACANCY_STATUSES
const EMPLOYMENT_ENUM = [...EMPLOYMENT_TYPES] as [EmploymentType, ...EmploymentType[]]

const vacancyFormSchema = z.object({
  title: z.string().min(1, 'Название обязательно'),
  status: z.enum([...STATUS_OPTIONS] as [VacancyStatus, ...VacancyStatus[]]).default('open'),
  company_id: z.string().min(1, 'Компания обязательна'),
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
  // Lead qualification criteria (stored in vacancy.extra.lead_criteria_v1)
  criteria_min_experience_eu_years: z
    .union([z.string(), z.number()])
    .optional()
    .transform((v) => (v === '' || v == null ? undefined : v)),
  criteria_requires_documents: z.string().optional().or(z.literal('')),
  criteria_requires_candidate_documents_v1: z.string().optional().or(z.literal('')),
  criteria_candidate_documents_allow_statuses: z.string().optional().or(z.literal('')),
  /** §2.5: ISO2 lists vs normalized.geo_country / location_country / current_country */
  criteria_allowed_geo_countries: z.string().optional().or(z.literal('')),
  criteria_blocked_geo_countries: z.string().optional().or(z.literal('')),
  /** §2.4: vacancy.extra.leads_auto_convert_on_fit_v1 = false */
  vacancy_disable_auto_convert_on_fit: z.boolean().optional().default(false),
  /** Vacancy.extra.lead_fit_evaluation_enabled_v1 — apply lead_criteria_v1 vs incoming leads */
  lead_fit_evaluation_enabled: z.boolean().optional().default(false),
  headcount_target: z.string().optional().or(z.literal('')),
})

type VacancyFormValues = z.infer<typeof vacancyFormSchema>

type Props = {
  item: any | null | undefined
  companiesMap?: Record<string, string>
  onBack: () => void
  onEdit?: () => void // kept for backward-compat; unused now
  onRemove?: () => Promise<void>
}

/* --------------------------------- ui atoms -------------------------------- */
const Input = (
  {
    label,
    mono,
    className,
    ...rest
  }: React.InputHTMLAttributes<HTMLInputElement> & { label?: string; mono?: boolean }
) => {
  return (
    <label className="block">
      {label && <div className="label">{label}</div>}
      <input {...rest} className={["input", mono ? 'font-mono' : '', className || ''].filter(Boolean).join(' ')} />
    </label>
  )
}

/* --------------------------------- helpers -------------------------------- */

function ensurePersistedFields(normalized: any, source: any) {
  // Keep edited scalar fields even if normalizeVacancy drops/renames them
  const keepKeys = [
    'status', 'state', 'stage',
    'salary_from', 'salary_to', 'currency',
    'is_open', 'is_active', 'is_archived',
    'employment_type', 'location', 'company_id',
    'created_at', 'updated_at', 'tenant_id', 'company_name', 'headcount_target', 'candidate_count'
  ] as const

  const ensured: any = { ...normalized }
  for (const k of keepKeys) {
    if (typeof (normalized as any)[k] === 'undefined' && typeof (source as any)[k] !== 'undefined') {
      ensured[k] = (source as any)[k]
    }
  }
  // Also make sure status mirrors state/stage if only they are present
  if (!ensured.status && (ensured.state || ensured.stage)) {
    ensured.status = ensured.state || ensured.stage
  }
  // Keep is_open consistent with status
  if (typeof ensured.is_open === 'undefined' && typeof source?.is_open !== 'undefined') {
    ensured.is_open = source.is_open
  }
  if (typeof ensured.is_open === 'undefined' && ensured.status) {
    ensured.is_open = String(ensured.status).toLowerCase() === 'open'
  }
  return ensured
}

function toFormDefaults(source: any | null): VacancyFormValues {
  // Phase 2.6.D Stage C — funnel every status entry point (status /
  // state / stage) through `normalizeVacancyStatus` so legacy `paused`
  // is rewritten to `on_hold` before the form schema validates it.
  const rawStatus = source?.status ?? source?.state ?? source?.stage ?? 'open'
  const normalizedStatus = normalizeVacancyStatus(rawStatus)

  const employment = source?.employment_type
  const normalizedEmployment = EMPLOYMENT_TYPES.includes(employment as EmploymentType)
    ? (employment as EmploymentType)
    : EMPLOYMENT_TYPES[0]

  let extra: any = {}
  const rawExtra = source?.extra
  if (typeof rawExtra === 'string') {
    try {
      const p = JSON.parse(rawExtra)
      if (p && typeof p === 'object' && !Array.isArray(p)) extra = p
    } catch {
      extra = {}
    }
  } else if (rawExtra && typeof rawExtra === 'object') {
    extra = rawExtra
  }
  const crit = (extra?.lead_criteria_v1 && typeof extra.lead_criteria_v1 === 'object' ? extra.lead_criteria_v1 : {}) as any
  const explicitFit = extra?.lead_fit_evaluation_enabled_v1
  let leadFitEvaluationEnabled = false
  if (explicitFit === true) {
    leadFitEvaluationEnabled = true
  } else if (explicitFit === false) {
    leadFitEvaluationEnabled = false
  } else {
    leadFitEvaluationEnabled = !!(crit && typeof crit === 'object' && !Array.isArray(crit) && Object.keys(crit).length > 0)
  }

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
    criteria_min_experience_eu_years: crit?.min_experience_eu_years ?? '',
    criteria_requires_documents: Array.isArray(crit?.requires_documents) ? crit.requires_documents.join(', ') : '',
    criteria_requires_candidate_documents_v1: Array.isArray(crit?.requires_candidate_documents_v1)
      ? crit.requires_candidate_documents_v1.join(', ')
      : '',
    criteria_candidate_documents_allow_statuses: Array.isArray(crit?.candidate_documents_allow_statuses)
      ? crit.candidate_documents_allow_statuses.join(', ')
      : '',
    criteria_allowed_geo_countries: Array.isArray(crit?.allowed_geo_countries)
      ? crit.allowed_geo_countries.join(', ')
      : '',
    criteria_blocked_geo_countries: Array.isArray(crit?.blocked_geo_countries)
      ? crit.blocked_geo_countries.join(', ')
      : '',
    vacancy_disable_auto_convert_on_fit: extra?.leads_auto_convert_on_fit_v1 === false,
    lead_fit_evaluation_enabled: leadFitEvaluationEnabled,
    headcount_target:
      source?.headcount_target != null && Number(source.headcount_target) > 0
        ? String(source.headcount_target)
        : '',
  }
}

type TabKey = 'info' | 'candidates' | 'notes'

const DATE_FNS_LOCALES: Record<LocaleCode, typeof enUS> = {
  en: enUS,
  pl: plFns,
  ru: ruFns,
}

function StatPill({ stageCode, value }:{ stageCode: string; value: React.ReactNode }){
  return (
    <span className="inline-flex items-center gap-1.5">
      <StageTag code={stageCode} />
      <span className="inline-flex min-w-[22px] items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] font-semibold text-slate-700">
        {value}
      </span>
    </span>
  )
}

function MiniTable({
  rows,
  labels,
}:{
  rows: React.ReactNode
  labels: {
    candidate: string
    email: string
    stage: string
  }
}){
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>{labels.candidate}</th>
            <th>{labels.email}</th>
            <th>{labels.stage}</th>
          </tr>
        </thead>
        <tbody className="align-top">{rows}</tbody>
      </table>
    </div>
  )
}

export default function VacancyDetail({ item, companiesMap = {}, onBack, onRemove }: Props) {
  const { t, locale } = useI18n()
  const dateFnsLocale = DATE_FNS_LOCALES[locale] ?? enUS
  const { can } = usePermissions()
  const planLimitModal = usePlanLimitModal()
  const leadFieldExperience = 'experience_eu_years'
  const leadFieldDocuments = 'documents[]'
  const leadFieldGeo = 'geo_country | location_country | current_country'
  const { id: routeId, tab: tabFromRoute } = useParams<{ id: string; tab?: string }>()
  const [searchParams] = useSearchParams()
  const companyFromUrl = searchParams.get('company') || ''

  function toModel(raw: any) {
    let base = raw || {}
    try { base = normalizeVacancy(base) } catch {}
    const st = (base.status ?? base.state ?? base.stage ?? 'open') as any
    return {
      ...base,
      status: st,
      is_open: typeof base.is_open === 'boolean' ? base.is_open : String(st).toLowerCase() === 'open',
      salary_from: typeof base.salary_from !== 'undefined' ? base.salary_from : null,
      salary_to:   typeof base.salary_to   !== 'undefined' ? base.salary_to   : null,
      currency:    typeof base.currency    !== 'undefined' ? base.currency    : null,
    }
  }

  const [model, setModel] = useState<any | null>(item ? toModel(item) : null)
  const [tab, setTab] = useState<TabKey>('info')

  // G-8 stage 2.1: per-vacancy primary next-action badge.
  // `routeId` is available from the URL before `model` arrives; we prefer
  // it so the badge can fetch as soon as the page mounts. Once `model`
  // hydrates we still pass the same id (route + model agree by definition).
  const vacancyIdForBadge = (routeId || model?.id || '') as string
  const [nextActionTick, setNextActionTick] = useState(0)
  const bumpNextActionTick = useCallback(() => setNextActionTick((n) => n + 1), [])
  const {
    data: vacancyNextAction,
    loading: vacancyNextActionLoading,
    error: vacancyNextActionError,
  } = useVacancyNextAction(vacancyIdForBadge || null, nextActionTick)

  useEffect(() => {
    if (tabFromRoute === 'candidates' || tabFromRoute === 'notes' || tabFromRoute === 'info') {
      setTab(tabFromRoute)
    }
  }, [tabFromRoute])
  const [candLoading, setCandLoading] = useState(false)
  const [candItems, setCandItems] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [loading, setLoading] = useState<boolean>(!item)
  const [pipeCounts, setPipeCounts] = useState<Record<string, number>>({})
  const [pipeLoading, setPipeLoading] = useState(false)
  const [candidateProfiles, setCandidateProfiles] = useState<CandidateProfile[]>([])
  const [requirementsPresets, setRequirementsPresets] = useState<VacancyRequirementsPreset[]>([])
  const [selectedPresetId, setSelectedPresetId] = useState<string>('')

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

  useEffect(() => {
    resetForm(toFormDefaults(model))
  }, [model, resetForm])

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
    if (watchIsOpen !== shouldBeOpen) {
      setValue('is_open', shouldBeOpen)
    }
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
      const list: any[] = Array.isArray(candData) ? candData : (candData?.items || [])
      const filtered = list.filter((c: any) => String((c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id) ?? '') === String(model.id))
      setCandItems(filtered)
    } finally {
      setCandLoading(false)
    }
  }, [model?.id])

  useEffect(() => {
    if (tab === 'candidates') loadCandidates()
  }, [tab, loadCandidates])

  useEffect(() => {
    async function loadPipe(){
      if (!model?.id) return
      setPipeLoading(true)
      try{
        const response = await api.get(
          `/vacancies/${model.id}/pipeline`,
          { validateStatus: status => status === 200 || status === 404 }
        )
        if (response.status === 404) {
          setPipeCounts({})
          return
        }
        const { data } = response
        const cols = (data?.columns || data?.columns_by_status || {}) as Record<string, any>
        const res: Record<string, number> = {}
        Object.keys(cols || {}).forEach(k => {
          const val: any = (cols as any)[k]
          const arr = Array.isArray(val) ? val : (Array.isArray(val?.items) ? val.items : [])
          res[k] = arr.length
        })
        setPipeCounts(res)
      } catch (err) {
        setPipeCounts({})
      } finally {
        setPipeLoading(false)
      }
    }
    loadPipe()
  }, [model?.id])

  const pipelineBottleneck = useMemo(() => {
    const entries = Object.entries(pipeCounts).filter(([, n]) => Number(n) > 0)
    if (!entries.length) return null
    return entries.reduce((a, b) => (Number(b[1]) > Number(a[1]) ? b : a))
  }, [pipeCounts])

  const lastCandidateActivityLabel = useMemo(() => {
    const raw = model?.last_candidate_activity_at
    if (!raw) return null
    try {
      return formatDistanceToNow(new Date(raw), { addSuffix: true, locale: dateFnsLocale })
    } catch {
      return null
    }
  }, [model?.last_candidate_activity_at, dateFnsLocale])

  const loadCandidateProfiles = useCallback(async () => {
    try {
      // Профили привязаны к вакансиям, а не к клиентам
      const profiles = await listCandidateProfiles({ is_active: true })
      setCandidateProfiles(profiles)
    } catch (err) {
      console.error('[VacancyDetail] failed to load candidate profiles', err)
    }
  }, [])

  useEffect(() => {
    const companyId = watch('company_id')
    if (companyId) {
      loadCandidateProfiles()
    } else {
      loadCandidateProfiles()
    }
  }, [watch('company_id'), loadCandidateProfiles])

  useEffect(() => {
    if (item) {
      setModel(toModel(item))
      setLoading(false)
      return
    }

    // Creating a new vacancy: do NOT fetch `/vacancies/new`
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
        })
      )
      setLoading(false)
      return
    }

    if (!item && routeId) {
      setLoading(true)
      getVacancy(routeId)
        .then((data) => setModel(toModel(data)))
        .catch((err: any) => {
          console.error('[vacancy/load] failed', err)
          setModel(null)
        })
        .finally(() => setLoading(false))
    }
  }, [item, routeId])

  const submitVacancy = useCallback(
    async (values: VacancyFormValues) => {
      setSaving(true)
      try {
        const mode: 'create' | 'update' = model?.id ? 'update' : 'create'

        const payload = buildVacancyPayload(values, model, mode)
        // Inject lead criteria into extra — merge with existing lead_criteria_v1 from extra (API / legacy keys).
        const minRaw: any = (values as any).criteria_min_experience_eu_years
        let minYears: number | undefined = undefined
        if (minRaw !== undefined && minRaw !== null && String(minRaw).trim() !== '') {
          const parsed = Number(minRaw)
          if (Number.isFinite(parsed) && parsed > 0) minYears = Math.floor(parsed)
        }
        const docs = String((values as any).criteria_requires_documents || '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
        const modDocs = String((values as any).criteria_requires_candidate_documents_v1 || '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
        const allowSts = String((values as any).criteria_candidate_documents_allow_statuses || '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
        const allowedGeo = String((values as any).criteria_allowed_geo_countries || '')
          .split(',')
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean)
        const blockedGeo = String((values as any).criteria_blocked_geo_countries || '')
          .split(',')
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean)
        const criteria: Record<string, unknown> = {}
        const prevExtra = payload?.extra && typeof payload.extra === 'object' && !Array.isArray(payload.extra) ? payload.extra : {}
        const prevCrit = (prevExtra as any).lead_criteria_v1
        if (prevCrit && typeof prevCrit === 'object' && !Array.isArray(prevCrit)) {
          Object.assign(criteria, prevCrit)
        }
        if (typeof minYears !== 'undefined') criteria.min_experience_eu_years = minYears
        else delete criteria.min_experience_eu_years
        if (docs.length > 0) criteria.requires_documents = docs
        else delete criteria.requires_documents
        if (modDocs.length > 0) criteria.requires_candidate_documents_v1 = modDocs
        else delete criteria.requires_candidate_documents_v1
        if (allowSts.length > 0) criteria.candidate_documents_allow_statuses = allowSts
        else delete criteria.candidate_documents_allow_statuses
        if (allowedGeo.length > 0) criteria.allowed_geo_countries = allowedGeo
        else delete criteria.allowed_geo_countries
        if (blockedGeo.length > 0) criteria.blocked_geo_countries = blockedGeo
        else delete criteria.blocked_geo_countries
        if (payload?.extra && typeof payload.extra === 'object') {
          ;(payload.extra as any).lead_criteria_v1 = criteria
          ;(payload.extra as any).lead_fit_evaluation_enabled_v1 = Boolean((values as any).lead_fit_evaluation_enabled)
          if ((values as any).vacancy_disable_auto_convert_on_fit) {
            ;(payload.extra as any).leads_auto_convert_on_fit_v1 = false
          } else {
            delete (payload.extra as any).leads_auto_convert_on_fit_v1
          }
        }

        const response = mode === 'update'
          ? await updateVacancy(model!.id, payload)
          : await createVacancy(payload)

        const latest = mode === 'update' ? await getVacancy(model!.id) : response
        const hydrated = hydrateSavedWithForm(latest, values, payload)
        const ensured = ensurePersistedFields(hydrated, latest)

        setModel(ensured)
        resetForm(toFormDefaults(ensured))
        bumpNextActionTick()
        setSavedOk(true); setTimeout(() => setSavedOk(false), 2000)
      } catch (err: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(
            err,
            t('app.vacancies.form.save_failed'),
          )
        ) {
          return
        }
        const r = err?.response?.data
        const detail = (typeof r?.detail === 'string')
          ? r.detail
          : (Array.isArray(r?.detail) ? JSON.stringify(r.detail) : (r ? JSON.stringify(r) : err?.message || 'Unknown error'))
        alert(`Сохранение не удалось: ${detail}`)
        throw err
      } finally {
        setSaving(false)
      }
    },
    [model, planLimitModal, resetForm, t, bumpNextActionTick]
  )

  const save = useCallback(async () => {
    await handleSubmit(submitVacancy)()
  }, [handleSubmit, submitVacancy])

  const companyName = useMemo(() => {
    const candidateId = watchCompanyId || model?.company_id
    const fromMap = candidateId ? companiesMap[candidateId] : undefined
    return fromMap ?? model?.company_name ?? candidateId ?? ''
  }, [companiesMap, model?.company_id, model?.company_name, watchCompanyId])

  const statusText = watchStatus ?? model?.status ?? model?.state ?? model?.stage ?? ''

  const statusOptions = STATUS_OPTIONS

  const companyOptions = useMemo(() => {
    return Object.entries(companiesMap).map(([id, name]) => ({ id, name: name || id }))
  }, [companiesMap])

  const { effectiveLayout } = useEffectiveVacancyLayout(Boolean(model || routeId))
  const vacancyFieldOrder = useMemo(
    () => getVacancyFieldsRenderOrder(effectiveLayout),
    [effectiveLayout],
  )

  const renderVacancyRegistryField = useCallback(
    (key: VacancyRegistryFieldKey) => {
      if (!vacancyFieldVisible(key, effectiveLayout)) return null
      const requiredMark = vacancyFieldRequired(key, effectiveLayout)
      switch (key) {
        case 'title':
          return (
            <label key="title" className="block">
              <div className="label">
                {vacancyFieldLabel('title', 'Название', effectiveLayout)}
                {requiredMark ? <span className="text-red-600"> *</span> : null}
              </div>
              <input className="input" {...register('title')} />
              {errors.title && <p className="text-sm text-rose-600 mt-1">{errors.title.message}</p>}
            </label>
          )
        case 'employment_type':
          return (
            <label key="employment_type" className="block">
              <div className="label">
                {vacancyFieldLabel('employment_type', 'Тип занятости', effectiveLayout)}
                {requiredMark ? <span className="text-red-600"> *</span> : null}
              </div>
              <select className="input" {...register('employment_type')}>
                {EMPLOYMENT_TYPES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {errors.employment_type && (
                <p className="text-sm text-rose-600 mt-1">{errors.employment_type.message}</p>
              )}
            </label>
          )
        case 'company_id':
          return (
            <label key="company_id" className="block">
              <div className="label">
                {vacancyFieldLabel('company_id', 'Компания', effectiveLayout)}
                {requiredMark ? <span className="text-red-600"> *</span> : null}
              </div>
              <select className="input" {...register('company_id')}>
                <option value="">— выберите компанию —</option>
                {companyOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              {errors.company_id && (
                <p className="text-sm text-rose-600 mt-1">{errors.company_id.message}</p>
              )}
            </label>
          )
        case 'headcount_target':
          return (
            <label key="headcount_target" className="block">
              <div className="label">
                {vacancyFieldLabel('headcount_target', t('app.vacancies.detail.fields.headcount_target'), effectiveLayout)}
                {requiredMark ? <span className="text-red-600"> *</span> : null}
              </div>
              <input
                type="number"
                inputMode="numeric"
                min={0}
                max={9999}
                className="input"
                {...register('headcount_target')}
                placeholder="—"
              />
              <p className="mt-1 text-xs text-slate-500">{t('app.vacancies.detail.fields.headcount_hint')}</p>
            </label>
          )
        case 'location':
          return (
            <label key="location" className="block">
              <div className="label">
                {vacancyFieldLabel('location', 'Локация', effectiveLayout)}
                {requiredMark ? <span className="text-red-600"> *</span> : null}
              </div>
              <input className="input" {...register('location')} />
            </label>
          )
        case 'description':
          return (
            <div key="description" className="md:col-span-2">
              <label className="block">
                <div className="label">
                  {vacancyFieldLabel('description', 'Описание', effectiveLayout)}
                  {requiredMark ? <span className="text-red-600"> *</span> : null}
                </div>
                <textarea
                  className="input w-full bg-muted/60 resize-none overflow-hidden min-h-[140px] max-h-none"
                  {...register('description')}
                  rows={Math.max(6, ((watch('description') || '') as string).split('\n').length + 1)}
                  onInput={(e) => {
                    const el = e.currentTarget
                    el.style.height = 'auto'
                    el.style.height = `${el.scrollHeight}px`
                  }}
                  style={{ height: 'auto' }}
                />
              </label>
            </div>
          )
        default:
          return null
      }
    },
    [effectiveLayout, register, errors, companyOptions, watch, t],
  )

  if (loading) {
    return <div className="text-slate-500">Загрузка карточки вакансии…</div>
  }
  if (!model) {
    return (
      <div className="p-3 rounded-lg bg-amber-50 text-amber-800 border border-amber-200">
        Вакансия не найдена или недоступна. 
        <button type="button" onClick={onBack} className="ml-2 underline">Вернуться к списку</button>
      </div>
    )
  }

  async function refresh(){
    if (!model?.id) return
    setLoading(true)
    try{
      const data = await getVacancy(model.id)
      setModel(toModel(data))
      try {
        const p = await api.get(`/vacancies/${model.id}/pipeline`)
        const cols = (p.data?.columns || p.data?.columns_by_status || {}) as Record<string, any>
        const res: Record<string, number> = {}
        Object.keys(cols || {}).forEach(k => {
          const val: any = (cols as any)[k]
          const arr = Array.isArray(val) ? val : (Array.isArray(val?.items) ? val.items : [])
          res[k] = arr.length
        })
        setPipeCounts(res)
      } catch {}
      bumpNextActionTick()
    } finally {
      setLoading(false)
    }
  }

  async function exportCSV(){
    if (!model?.id) return
    // Fetch candidates scoped to this vacancy; fall back to generic list
    let candData: any
    try{
      const r = await api.get('/candidates?limit=1000&offset=0')
      candData = r.data
    } catch {
      const r = await api.get('/candidates/')
      candData = r.data
    }
    const list: any[] = Array.isArray(candData) ? candData : (candData?.items || [])
    const filtered = list.filter((c:any) => String((c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id) ?? '') === String(model.id))

    const rows = [
      ['id','name','email','stage','phone','created_at'] as const,
      ...filtered.map((c:any) => [
        c.id,
        c.name || [c.first_name, c.last_name].filter(Boolean).join(' '),
        c.email || '',
        String(c.stage ?? c.status ?? ''),
        c.phone || '',
        c.created_at || ''
      ])
    ]
    const csv = rows.map(r => r.map(x => {
      const s = (x ?? '').toString().replace(/"/g, '""')
      return `"${s}` + `"`
    }).join(',')).join('\n')
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
        if (!confirm('Удалить вакансию? Это действие нельзя отменить.')) return
        await onRemove()
      }
    : undefined

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          breadcrumbCurrentLabel={watchTitle || model?.title || t('app.vacancies.detail.untitled')}
          subtitle={
            <div className="flex flex-wrap items-center gap-2">
              {companyName ? <span>{companyName}</span> : null}
              {statusText ? <StageTag code={String(statusText)} /> : null}
              {vacancyIdForBadge ? (
                <NextActionBadge
                  dto={vacancyNextAction}
                  loading={vacancyNextActionLoading}
                  error={vacancyNextActionError}
                />
              ) : null}
              {Object.keys(pipeCounts).length > 0
                ? Object.entries(pipeCounts).map(([k, v]) => <StatPill key={k} stageCode={k} value={v} />)
                : null}
            </div>
          }
          secondaryActions={
            <>
              {handleRemove ? (
                <button type="button" className="btn-danger btn-sm" onClick={handleRemove}>
                  {t('common.actions.delete')}
                </button>
              ) : null}
              <button type="button" className="btn-secondary btn-sm" onClick={refresh}>
                {t('common.actions.refresh')}
              </button>
              <Link
                className="btn-secondary btn-sm"
                to={
                  model?.id
                    ? `${CRM_APP_PATHS.candidates}?view=kanban&vacancy=${model.id}`
                    : `${CRM_APP_PATHS.candidates}?view=kanban`
                }
              >
                {t('app.candidates.pipeline.title')}
              </Link>
              {can('services.view') && model?.id ? (
                <Link
                  className="btn-secondary btn-sm"
                  to={servicesWorkspacePath('orders', {
                    vacancyId: String(model.id),
                    ...(model.company_id ? { companyId: String(model.company_id) } : {}),
                  })}
                >
                  {t('app.nav.items.services')}
                </Link>
              ) : null}
              <button type="button" className="btn-secondary btn-sm" onClick={onBack}>
                {t('common.actions.cancel')}
              </button>
            </>
          }
          primaryAction={
            <button type="button" className="btn-primary btn-sm" disabled={saving} onClick={save}>
              {saving ? t('common.saving') : t('common.actions.save')}
            </button>
          }
        />
        {pipeLoading ? <div className="mt-2 text-xs text-slate-500">{t('common.loading')}</div> : null}
        {savedOk ? (
          <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {t('common.messages.saved')}
          </div>
        ) : null}
        {model?.id && routeId !== 'new' ? (
          <div className="mt-2 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <span className="font-medium">
              {t('app.vacancies.detail.ops.candidates_linked', {
                values: { count: model.candidate_count ?? 0 },
              })}
            </span>
            {model.headcount_target != null && model.headcount_target > 0 ? (
              <span>
                {t('app.vacancies.detail.ops.headcount_target', {
                  values: {
                    current: model.candidate_count ?? 0,
                    target: model.headcount_target,
                  },
                })}
              </span>
            ) : null}
            {lastCandidateActivityLabel ? (
              <span className="text-slate-500">
                {t('app.vacancies.detail.ops.last_candidate_activity', {
                  values: { when: lastCandidateActivityLabel },
                })}
              </span>
            ) : null}
            {pipelineBottleneck ? (
              <span className="text-slate-600">
                {t('app.vacancies.detail.ops.bottleneck', {
                  values: { stage: pipelineBottleneck[0], count: pipelineBottleneck[1] },
                })}
              </span>
            ) : null}
            <div className="ml-auto flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setTab('candidates')}
              >
                {t('app.vacancies.detail.ops.open_candidate_queue')}
              </button>
            </div>
          </div>
        ) : null}
      </PageShellHeader>

      <Toolbar>
        <div className="flex flex-wrap gap-2">
          {(['info', 'candidates', 'notes'] as TabKey[]).map((key) => (
            <button
              key={key}
              type="button"
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                tab === key
                  ? 'bg-slate-900 text-white'
                  : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
              onClick={() => setTab(key)}
            >
              {key === 'info'
                ? t('app.vacancies.detail.tabs.info')
                : key === 'candidates'
                  ? `${t('app.vacancies.detail.tabs.candidates')}${candItems.length ? ` (${candItems.length})` : ''}`
                  : t('app.vacancies.detail.tabs.notes')}
            </button>
          ))}
        </div>
      </Toolbar>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
      {tab === 'info' && (
        <div className="space-y-4">
          <SectionCard title={t('app.vacancies.detail.sections.info')}>
            <form className="space-y-4" onSubmit={handleSubmit(submitVacancy)}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {vacancyFieldOrder.map((key) => renderVacancyRegistryField(key))}

            <label className="block">
              <div className="label">Статус</div>
              <select className="input" {...register('status')}>
                {statusOptions.map((s) => (
                  <option key={s} value={s}>
                    {t(`app.vacancies.list.status.${s}`, { defaultValue: s })}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <div className="label">Профиль кандидата</div>
              <select className="input" {...register('candidate_profile_id')}>
                <option value="">— не выбран —</option>
                {candidateProfiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>{profile.name}</option>
                ))}
              </select>
            </label>

            <label className="block">
              <div className="label">От (зарплата)</div>
              <input type="number" inputMode="decimal" className="input" {...register('salary_from')} placeholder="напр., 9000" />
            </label>

            <label className="block">
              <div className="label">До (зарплата)</div>
              <input type="number" inputMode="decimal" className="input" {...register('salary_to')} placeholder="напр., 12000" />
            </label>

            <label className="block">
              <div className="label">Валюта</div>
              <input
                className="input"
                {...register('currency')}
                placeholder={t('app.vacancies.detail.placeholders.currency_codes')}
              />
            </label>

            <div className="md:col-span-2 flex items-center gap-6">
              <Controller
                control={control}
                name="is_active"
                render={({ field }) => (
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                    <span>Активна</span>
                  </label>
                )}
              />
              <Controller
                control={control}
                name="is_archived"
                render={({ field }) => (
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                    <span>В архиве</span>
                  </label>
                )}
              />
              <Controller
                control={control}
                name="is_open"
                render={({ field }) => (
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                    <span>Открыта</span>
                  </label>
                )}
              />
            </div>

            <Input label="Создана" value={formatDate(model?.created_at)} readOnly />
            <Input label="Изменена" value={formatDate(model?.updated_at)} readOnly />
            <Input label={t('app.vacancies.detail.fields.id')} value={model?.id || '—'} mono readOnly />

            <div className="md:col-span-2">
              <div className="mb-2 text-sm font-semibold text-slate-800">
                {t('app.vacancies.detail.criteria.title')}
              </div>
              <Controller
                control={control}
                name="lead_fit_evaluation_enabled"
                render={({ field }) => (
                  <label className="mb-3 flex cursor-pointer items-start gap-2 text-sm text-slate-800">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={!!field.value}
                      onChange={(e) => field.onChange(e.target.checked)}
                    />
                    <span>
                      <span className="font-medium">{t('app.vacancies.detail.criteria.enable_fit_evaluation')}</span>
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">
                        {t('app.vacancies.detail.criteria.enable_fit_evaluation_hint')}
                      </span>
                    </span>
                  </label>
                )}
              />
              {requirementsPresets.length > 0 && (
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <select
                    className="input h-9 rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                    value={selectedPresetId}
                    onChange={(e) => setSelectedPresetId(e.target.value)}
                  >
                    <option value="">— пресет требований —</option>
                    {requirementsPresets.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className={secondaryBtn}
                    disabled={!selectedPresetId}
                    onClick={() => {
                      const preset = requirementsPresets.find((p) => p.id === selectedPresetId)
                      const crit: any = preset?.criteria || {}
                      const min = crit?.min_experience_eu_years
                      const docs = Array.isArray(crit?.requires_documents) ? crit.requires_documents.join(', ') : ''
                      const ag = Array.isArray(crit?.allowed_geo_countries) ? crit.allowed_geo_countries.join(', ') : ''
                      const bg = Array.isArray(crit?.blocked_geo_countries) ? crit.blocked_geo_countries.join(', ') : ''
                      setValue('criteria_min_experience_eu_years' as any, (typeof min !== 'undefined' ? String(min) : '') as any)
                      setValue('criteria_requires_documents' as any, docs as any)
                      setValue('criteria_allowed_geo_countries' as any, ag as any)
                      setValue('criteria_blocked_geo_countries' as any, bg as any)
                    }}
                  >
                    Применить пресет
                  </button>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="block">
                  <div className="label">Мин. опыт по ЕС (лет)</div>
                  <input
                    type="number"
                    inputMode="numeric"
                    className="input"
                    {...register('criteria_min_experience_eu_years')}
                    placeholder="например, 1"
                  />
                </label>
                <label className="block">
                  <div className="label">Требуемые документы (коды, через запятую)</div>
                  <input
                    className="input"
                    {...register('criteria_requires_documents')}
                    placeholder={t('app.vacancies.detail.criteria.documents_placeholder')}
                  />
                </label>
                <label className="block md:col-span-2">
                  <div className="label">
                    {t('app.vacancies.detail.criteria.candidate_docs_module')}
                  </div>
                  <input
                    className="input font-mono text-xs"
                    {...register('criteria_requires_candidate_documents_v1')}
                    placeholder={t('app.vacancies.detail.criteria.candidate_docs_placeholder')}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    {t('app.vacancies.detail.criteria.candidate_docs_hint')}
                  </p>
                </label>
                <label className="block md:col-span-2">
                  <div className="label">
                    {t('app.vacancies.detail.criteria.allow_statuses')}
                  </div>
                  <input
                    className="input font-mono text-xs"
                    {...register('criteria_candidate_documents_allow_statuses')}
                    placeholder="approved, completed, verified, received, delivered, issued, active, registered"
                  />
                </label>
                <label className="block md:col-span-2">
                  <div className="label">{t('app.vacancies.detail.criteria.allowed_geo_countries')}</div>
                  <input
                    className="input font-mono text-xs"
                    {...register('criteria_allowed_geo_countries')}
                    placeholder={t('app.vacancies.detail.criteria.geo_countries_placeholder')}
                  />
                  <p className="mt-1 text-xs text-slate-500">{t('app.vacancies.detail.criteria.allowed_geo_hint')}</p>
                </label>
                <label className="block md:col-span-2">
                  <div className="label">{t('app.vacancies.detail.criteria.blocked_geo_countries')}</div>
                  <input
                    className="input font-mono text-xs"
                    {...register('criteria_blocked_geo_countries')}
                    placeholder={t('app.vacancies.detail.criteria.geo_countries_placeholder')}
                  />
                  <p className="mt-1 text-xs text-slate-500">{t('app.vacancies.detail.criteria.blocked_geo_hint')}</p>
                </label>
              </div>
              <div className="mt-2 text-xs text-slate-500">
                {t('app.vacancies.detail.criteria.lead_fields')}{' '}
                <span className="font-mono">{leadFieldExperience}</span> {t('common.and')}{' '}
                <span className="font-mono">{leadFieldDocuments}</span> ({t('common.words.if_available')}
                ); {t('app.vacancies.detail.criteria.lead_fields_geo')}{' '}
                <span className="font-mono">{leadFieldGeo}</span>.
              </div>
              <Controller
                control={control}
                name="vacancy_disable_auto_convert_on_fit"
                render={({ field }) => (
                  <label className="mt-3 flex cursor-pointer items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={!!field.value}
                      onChange={(e) => field.onChange(e.target.checked)}
                    />
                    <span>
                      <span className="font-medium">{t('app.vacancies.detail.criteria.disable_auto_convert')}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {t('app.vacancies.detail.criteria.disable_auto_convert_hint')}
                      </span>
                    </span>
                  </label>
                )}
              />
            </div>
              </div>
            </form>
          </SectionCard>

          <SectionCard title={t('app.vacancies.detail.sections.documents')}>
            <div className="space-y-2 text-sm text-slate-700">
              <p className="text-slate-600">
                {t('app.vacancies.detail.documents.hint')}
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Link to={CRM_APP_PATHS.documents} className="btn-secondary btn-xs">
                  {t('app.nav.items.documents')}
                </Link>
                <Link to={CRM_APP_PATHS.settingsCandidateProfiles} className="btn-secondary btn-xs">
                  {t('admin.settings.cards.candidate_profiles.label')}
                </Link>
              </div>
            </div>
          </SectionCard>
        </div>
      )}

      {tab === 'candidates' && (
        <SectionCard title={t('app.vacancies.detail.tabs.candidates')}>
          {candLoading ? (
            <div className="text-slate-500">Загрузка кандидатов…</div>
          ) : candItems.length === 0 ? (
            <div className="text-slate-500">Кандидатов для этой вакансии пока нет.</div>
          ) : (
            <MiniTable
              labels={{
                candidate: t('app.vacancies.detail.table.candidate'),
                email: t('app.vacancies.detail.table.email'),
                stage: t('app.vacancies.detail.table.stage'),
              }}
              rows={(
                candItems.map((c:any) => (
                  <tr key={c.id}>
                    <td className="py-2 pr-3">
                      <a className="hover:underline" href={`${CRM_APP_PATHS.candidates}/${c.id}`}>{c.name || [c.first_name, c.last_name].filter(Boolean).join(' ') || 'Без имени'}</a>
                    </td>
                    <td className="py-2 pr-3 text-slate-600">{c.email || '—'}</td>
                    <td className="py-2 pr-3"><StageTag code={String(c.stage ?? c.status ?? 'new')} /></td>
                  </tr>
                ))
              )}
            />
          )}
        </SectionCard>
      )}

      {tab === 'notes' && (
        <SectionCard title={t('app.vacancies.detail.tabs.notes')}>
          <p className="text-sm text-slate-500">{t('app.vacancies.detail.notes_coming')}</p>
        </SectionCard>
      )}

      </div>
    </PageShell>
  )
}
