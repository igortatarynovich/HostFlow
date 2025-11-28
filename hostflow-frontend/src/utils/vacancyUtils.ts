// src/utils/vacancyUtils.ts
import { format } from 'date-fns'
import { EMPLOYMENT_TYPES } from '../api/vacancies'
import type { EmploymentType, VacancyPayload } from '../api/vacancies'

/** Базовый тип вакансии (гибкий, чтобы не мешать текущему API) */
export interface VacancyLike {
  id?: string
  company_id?: string
  title?: string
  description?: string
  status?: string
  state?: string
  stage?: string
  is_open?: boolean
  is_active?: boolean
  is_archived?: boolean
  salary_from?: number | string
  salary_to?: number | string
  currency?: string
  location?: string
  employment_type?: EmploymentType
  extra?: any
  [key: string]: any
}

// ===== in-memory cache =====
const VACANCY_CACHE: Record<string, VacancyLike> = {}

export function cacheVacancy(v: VacancyLike | VacancyLike[] | any) {
  if (!v) return
  if (Array.isArray(v)) {
    v.forEach(x => {
      if (x?.id) {
        VACANCY_CACHE[x.id] = { ...(VACANCY_CACHE[x.id] || {}), ...x }
      }
    })
  } else if (v.id) {
    VACANCY_CACHE[v.id] = { ...(VACANCY_CACHE[v.id] || {}), ...v }
  }
}

export function mergeFromCache<T extends { id?: string }>(input: T | T[]): T | T[] {
  if (Array.isArray(input)) {
    return input.map((v: any) => (v?.id ? { ...(VACANCY_CACHE[v.id] || {}), ...v } : v)) as T[]
  }
  const v: any = input
  if (!v || !v.id) return input
  return { ...(VACANCY_CACHE[v.id] || {}), ...v }
}

// ===== formatting =====
export function formatDate(value?: string | Date): string {
  if (!value) return ''
  const date = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(date.getTime?.())) return ''
  return format(date, 'dd.MM.yyyy, HH:mm:ss')
}

// ===== normalization =====
export function normalizeVacancy(raw: any): VacancyLike {
  if (!raw || typeof raw !== 'object') return raw

  let ex: any = raw.extra ?? {}
  if (typeof ex === 'string') {
    try { ex = JSON.parse(ex) } catch { ex = {} }
  }

  const out: VacancyLike = { ...raw }
  const exSalary = ex?.salary || {}

  const salary_from = out.salary_from ?? exSalary.from ?? ex?.salary_from
  const salary_to   = out.salary_to   ?? exSalary.to   ?? ex?.salary_to
  const currency    = out.currency    ?? exSalary.currency ?? ex?.currency

  if (salary_from !== undefined) out.salary_from = salary_from
  if (salary_to   !== undefined) out.salary_to   = salary_to
  if (currency    !== undefined) out.currency    = currency

  if (out.location == null && ex?.location != null) out.location = ex.location
  const normalizedEmployment = (value: any): EmploymentType | undefined => {
    if (typeof value !== 'string') return undefined
    return EMPLOYMENT_TYPES.includes(value as EmploymentType)
      ? (value as EmploymentType)
      : undefined
  }

  if (out.employment_type == null) {
    const fromExtra = normalizedEmployment(ex?.employment_type)
    if (fromExtra) out.employment_type = fromExtra
  } else {
    const normalized = normalizedEmployment(out.employment_type)
    if (normalized) {
      out.employment_type = normalized
    } else {
      delete out.employment_type
    }
  }

  if (typeof out.is_active === 'undefined' && typeof ex?.is_active !== 'undefined') out.is_active = !!ex.is_active
  if (typeof out.is_archived === 'undefined' && typeof ex?.is_archived !== 'undefined') out.is_archived = !!ex.is_archived

  const status = out.status ?? ex?.status ?? ex?.state ?? ex?.stage ?? out.state ?? out.stage
  if (typeof status !== 'undefined') {
    const s = String(status)
    out.status = s
    out.state = s
    out.stage = s
    if (typeof out.is_open === 'undefined') out.is_open = s.toLowerCase() === 'open'
  }

  if (!out.employment_type) {
    out.employment_type = EMPLOYMENT_TYPES[0]
  }

  return out
}

// ===== UI helpers =====

// Допускаем 1–3 аргумента, чтобы не ломать существующие вызовы
export function hydrateSavedWithForm(saved: any, form: any = null, payload: any = null): VacancyLike {
  const out: VacancyLike = { ...saved }

  // если бек выкинул extra из ответа — восстанавливаем то, что отправляли
  if (payload?.extra && typeof out.extra === 'undefined') out.extra = payload.extra

  const status = form?.status
  if (typeof out.status === 'undefined' && status) out.status = String(status)
  if (typeof out.state  === 'undefined' && status) out.state  = String(status)
  if (typeof out.stage  === 'undefined' && status) out.stage  = String(status)
  if (typeof out.is_open === 'undefined' && status) out.is_open = String(status).toLowerCase() === 'open'

  const sf = form?.salary_from
  const st = form?.salary_to
  const cur = form?.currency
  if (typeof out.salary_from === 'undefined' && sf !== '') out.salary_from = Number.isFinite(Number(sf)) ? Number(sf) : sf
  if (typeof out.salary_to   === 'undefined' && st !== '') out.salary_to   = Number.isFinite(Number(st)) ? Number(st) : st
  if (typeof out.currency    === 'undefined' && cur !== '') out.currency    = cur
  const formEmployment = form?.employment_type
  if (typeof out.employment_type === 'undefined' && typeof formEmployment === 'string') {
    if (EMPLOYMENT_TYPES.includes(formEmployment as EmploymentType)) {
      out.employment_type = formEmployment as EmploymentType
    }
  }

  return normalizeVacancy(out)
}

// Аналогично: принимаем (form, base?, mode?) — чтобы вызов из страницы не падал
export function buildVacancyPayload(
  form: Record<string, any>,
  _base: any = null,
  _mode: 'create' | 'update' = 'update'
): (VacancyPayload & Record<string, any>) {
  const employmentType = typeof form.employment_type === 'string' && EMPLOYMENT_TYPES.includes(form.employment_type as EmploymentType)
    ? (form.employment_type as EmploymentType)
    : EMPLOYMENT_TYPES[0]

  const payload: VacancyPayload & Record<string, any> = {
    company_id: form.company_id,
    title: form.title,
    employment_type: employmentType,
  }

  if (form.status) {
    const s = String(form.status)
    payload.status = s
    payload.state = s
    payload.stage = s
    payload.is_open = s.toLowerCase() === 'open'
  }

  if (typeof form.is_open !== 'undefined') {
    payload.is_open = !!form.is_open
  }

  if (typeof form.description !== 'undefined') {
    if (typeof form.description === 'string') {
      const trimmed = form.description.trim()
      payload.description = trimmed === '' ? null : form.description
    } else {
      payload.description = form.description ?? null
    }
  }

  const hasFrom = form.salary_from !== '' && form.salary_from != null
  const hasTo   = form.salary_to   !== '' && form.salary_to   != null
  const hasCur  = form.currency    !== '' && form.currency    != null

  const numFrom = hasFrom ? Number(form.salary_from) : undefined
  const numTo   = hasTo   ? Number(form.salary_to)   : undefined

  if (hasFrom) payload.salary_from = Number.isFinite(numFrom!) ? numFrom : form.salary_from
  else if (form.salary_from === '' || form.salary_from == null) payload.salary_from = null

  if (hasTo)   payload.salary_to   = Number.isFinite(numTo!)   ? numTo   : form.salary_to
  else if (form.salary_to === '' || form.salary_to == null)     payload.salary_to = null

  if (hasCur)  payload.currency    = form.currency
  else if (form.currency === '') payload.currency = null

  if (typeof form.location !== 'undefined') {
    if (typeof form.location === 'string') {
      const trimmed = form.location.trim()
      payload.location = trimmed === '' ? null : form.location
    } else {
      payload.location = form.location ?? null
    }
  }
  if (typeof form.is_active   !== 'undefined') payload.is_active   = !!form.is_active
  if (typeof form.is_archived !== 'undefined') payload.is_archived = !!form.is_archived

  const extraObject: Record<string, any> = {
    salary: {
      from: hasFrom ? (Number.isFinite(numFrom!) ? numFrom : form.salary_from) : undefined,
      to:   hasTo   ? (Number.isFinite(numTo!)   ? numTo   : form.salary_to)   : undefined,
      currency: hasCur ? form.currency : undefined,
    },
    salary_from: hasFrom ? (Number.isFinite(numFrom!) ? numFrom : form.salary_from) : undefined,
    salary_to:   hasTo   ? (Number.isFinite(numTo!)   ? numTo   : form.salary_to)   : undefined,
    currency:    hasCur  ? form.currency : undefined,

    location: form.location || undefined,
    employment_type: employmentType,
    is_active:   typeof form.is_active   !== 'undefined' ? !!form.is_active   : undefined,
    is_archived: typeof form.is_archived !== 'undefined' ? !!form.is_archived : undefined,
    status: form.status || undefined,
    state:  form.status || undefined,
    stage:  form.status || undefined,
  }

  payload.extra = extraObject

  return payload
}

// Унифицированный распаковщик списков: поддерживает массивы и популярные структуры ответов API
export function unwrapVacancyList(input: any): VacancyLike[] {
  if (!input) return []
  if (Array.isArray(input)) return input
  if (typeof input === 'object') {
    const obj: any = input
    if (Array.isArray(obj.items)) return obj.items
    if (Array.isArray(obj.results)) return obj.results
    if (Array.isArray(obj.data?.items)) return obj.data.items
    if (Array.isArray(obj.data)) return obj.data
  }
  return []
}

// Согласовано с использованием на странице: (list, base?) -> Promise<list>
export async function enrichVacancyList(list: any, _base?: any): Promise<VacancyLike[]> {
  const arr = unwrapVacancyList(list)
  const normalized = arr.map(normalizeVacancy)
  cacheVacancy(normalized)
  return normalized
}
