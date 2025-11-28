import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { normalizeVacancy, formatDate, buildVacancyPayload, hydrateSavedWithForm } from '../../utils/vacancyUtils'
import StageTag from '../StageTag'
import { api } from '../../api/client'
import { useParams, Link } from 'react-router-dom'
import { EMPLOYMENT_TYPES, createVacancy, getVacancy, updateVacancy } from '../../api/vacancies'
import type { EmploymentType } from '../../api/vacancies'

const primaryBtn = 'btn-primary'
const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-300 text-gray-800 bg-white hover:bg-gray-100 active:bg-gray-200 transition-colors cursor-pointer";

const STATUS_OPTIONS = ['open', 'paused', 'closed'] as const
const EMPLOYMENT_ENUM = [...EMPLOYMENT_TYPES] as [EmploymentType, ...EmploymentType[]]

const vacancyFormSchema = z.object({
  title: z.string().min(1, 'Название обязательно'),
  status: z.enum(STATUS_OPTIONS).default('open'),
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
    'created_at', 'updated_at', 'tenant_id', 'company_name'
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
  const rawStatus = (source?.status ?? source?.state ?? source?.stage ?? 'open') as string
  const normalizedStatus = (STATUS_OPTIONS.includes(rawStatus as typeof STATUS_OPTIONS[number])
    ? (rawStatus as typeof STATUS_OPTIONS[number])
    : 'open')

  const employment = source?.employment_type
  const normalizedEmployment = EMPLOYMENT_TYPES.includes(employment as EmploymentType)
    ? (employment as EmploymentType)
    : EMPLOYMENT_TYPES[0]

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
  }
}

type TabKey = 'info' | 'candidates' | 'notes'

function StatPill({ label, value }:{ label: React.ReactNode; value: React.ReactNode }){
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border bg-white">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium">{value}</span>
    </span>
  )
}

function MiniTable({ rows }:{ rows: React.ReactNode }){
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="py-2 pr-3">Кандидат</th>
            <th className="py-2 pr-3">Email</th>
            <th className="py-2 pr-3">Этап</th>
          </tr>
        </thead>
        <tbody className="align-top divide-y">{rows}</tbody>
      </table>
    </div>
  )
}

export default function VacancyDetail({ item, companiesMap = {}, onBack, onRemove }: Props) {
  const { id: routeId } = useParams<{ id: string }>()

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
  const [candLoading, setCandLoading] = useState(false)
  const [candItems, setCandItems] = useState<any[]>([])
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [loading, setLoading] = useState<boolean>(!item)
  const [pipeCounts, setPipeCounts] = useState<Record<string, number>>({})
  const [pipeLoading, setPipeLoading] = useState(false)

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
    const shouldBeOpen = (watchStatus ?? 'open') === 'open'
    if (watchIsOpen !== shouldBeOpen) {
      setValue('is_open', shouldBeOpen)
    }
  }, [watchStatus, watchIsOpen, setValue])
  useEffect(() => {
    async function loadCandidates(){
      if (!model?.id) return
      setCandLoading(true)
      try{
        let candData: any
        try{
          const r = await api.get('/candidates?limit=200&offset=0')
          candData = r.data
        } catch {
          const r = await api.get('/candidates/')
          candData = r.data
        }
        const list: any[] = Array.isArray(candData) ? candData : (candData?.items || [])
        const filtered = list.filter((c:any) => String((c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id) ?? '') === String(model.id))
        setCandItems(filtered)
      } finally {
        setCandLoading(false)
      }
    }
    if (tab === 'candidates') loadCandidates()
  }, [tab, model?.id])

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
          company_id: '',
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

        const response = mode === 'update'
          ? await updateVacancy(model!.id, payload)
          : await createVacancy(payload)

        const latest = mode === 'update' ? await getVacancy(model!.id) : response
        const hydrated = hydrateSavedWithForm(latest, values, payload)
        const ensured = ensurePersistedFields(hydrated, latest)

        setModel(ensured)
        resetForm(toFormDefaults(ensured))
        setSavedOk(true); setTimeout(() => setSavedOk(false), 2000)
      } catch (err: any) {
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
    [model, resetForm]
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
    <div className="h-full min-h-0 w-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-start justify-between">
          <div className="min-w-0">
            <div className="text-xs text-gray-500 mb-1">
              <button type="button" onClick={onBack} className="hover:underline">← Вакансии</button>
            </div>
            <h1 className="text-2xl font-semibold break-words">{watchTitle || model?.title || 'Вакансия'}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2">
              {statusText && <StageTag code={String(statusText)} />}
              {companyName && <span className="text-slate-600">{companyName}</span>}
              {/* lightweight pipeline counters */}
              {Object.keys(pipeCounts).length > 0 && (
                <div className="flex flex-wrap gap-2 ml-2">
                  {Object.entries(pipeCounts).map(([k, v]) => (
                    <StatPill key={k} label={<StageTag code={k} />} value={v} />
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {handleRemove && (
              <button onClick={handleRemove} className="btn-ghost text-rose-700">Удалить</button>
            )}
            <button className={secondaryBtn} onClick={refresh}>Обновить</button>
            <button className={secondaryBtn} onClick={exportCSV}>Экспорт</button>
            <Link className={secondaryBtn} to="/app/candidates?view=kanban">Пайплайн</Link>
            <button className={secondaryBtn} onClick={onBack}>Отмена</button>
            <button type="button" className={primaryBtn} disabled={saving} onClick={save}>
              {saving ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </div>
        {pipeLoading && <div className="text-xs text-slate-500">Загружаю счётчики…</div>}
      </div>

      <div className="flex items-center gap-2 border-b">
        {(['info','candidates','notes'] as TabKey[]).map(key => (
          <button
            key={key}
            className={[
              'px-3 py-2 text-sm -mb-[1px] border-b-2',
              tab === key ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'
            ].join(' ')}
            onClick={()=>setTab(key)}
          >
            {key === 'info' ? 'Инфо' : key === 'candidates' ? `Кандидаты${candItems.length ? ` (${candItems.length})` : ''}` : 'Заметки'}
          </button>
        ))}
      </div>

      {savedOk ? (
        <div className="p-3 rounded-lg bg-green-50 text-green-800 border border-green-200">Сохранено</div>
      ) : null}

      {tab === 'info' && (
        <form className="card p-3" onSubmit={handleSubmit(submitVacancy)}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <div className="label">Название</div>
              <input className="input" {...register('title')} />
              {errors.title && <p className="text-sm text-rose-600 mt-1">{errors.title.message}</p>}
            </label>

            <label className="block">
              <div className="label">Статус</div>
              <select className="input" {...register('status')}>
                {statusOptions.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>

            <label className="block">
              <div className="label">Тип занятости</div>
              <select className="input" {...register('employment_type')}>
                {EMPLOYMENT_TYPES.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
              {errors.employment_type && <p className="text-sm text-rose-600 mt-1">{errors.employment_type.message}</p>}
            </label>

            <label className="block">
              <div className="label">Компания</div>
              <select className="input" {...register('company_id')}>
                <option value="">— выберите компанию —</option>
                {companyOptions.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              {errors.company_id && <p className="text-sm text-rose-600 mt-1">{errors.company_id.message}</p>}
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
              <input className="input" {...register('currency')} placeholder="PLN / EUR / USD" />
            </label>

            <label className="block">
              <div className="label">Локация</div>
              <input className="input" {...register('location')} />
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
            <Input label="ID" value={model?.id || '—'} mono readOnly />

            <div className="md:col-span-2">
              <label className="block">
                <div className="label">Описание</div>
                <textarea
                  className="input w-full bg-muted/60 resize-none overflow-hidden min-h-[140px] max-h-none"
                  {...register('description')}
                  rows={Math.max(6, ((watch('description') || '') as string).split('\n').length + 1)}
                  onInput={(e) => {
                    const t = e.currentTarget
                    t.style.height = 'auto'
                    t.style.height = `${t.scrollHeight}px`
                  }}
                  style={{ height: 'auto' }}
                />
              </label>
            </div>
          </div>
        </form>
      )}

      {tab === 'candidates' && (
        <div className="card p-3">
          {candLoading ? (
            <div className="text-slate-500">Загрузка кандидатов…</div>
          ) : candItems.length === 0 ? (
            <div className="text-slate-500">Кандидатов для этой вакансии пока нет.</div>
          ) : (
            <MiniTable
              rows={(
                candItems.map((c:any) => (
                  <tr key={c.id}>
                    <td className="py-2 pr-3">
                      <a className="hover:underline" href={`/app/candidates/${c.id}`}>{c.name || [c.first_name, c.last_name].filter(Boolean).join(' ') || 'Без имени'}</a>
                    </td>
                    <td className="py-2 pr-3 text-slate-600">{c.email || '—'}</td>
                    <td className="py-2 pr-3"><StageTag code={String(c.stage ?? c.status ?? 'new')} /></td>
                  </tr>
                ))
              )}
            />
          )}
        </div>
      )}

      {tab === 'notes' && (
        <div className="card p-3 text-slate-500">Заметки: скоро здесь будет блок заметок.</div>
      )}
    </div>
  )
}
