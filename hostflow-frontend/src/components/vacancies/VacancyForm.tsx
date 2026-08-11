// src/components/vacancies/VacancyForm.tsx
import { useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useI18n } from '../../i18n'

import { EMPLOYMENT_TYPES, VACANCY_STATUSES, normalizeVacancyStatus } from '../../api/vacancies'
import type { EmploymentType, VacancyStatus } from '../../api/vacancies'

type Company = { id: string; name?: string }

// Phase 2.6.D Stage C — single source of truth for status options.
// `VACANCY_STATUSES` mirrors the backend enum (`open|on_hold|closed|
// filled|cancelled`); see `docs/specs/vacancy-statuses.md` §6.
const STATUS_OPTIONS = VACANCY_STATUSES
const EMPLOYMENT_ENUM = [...EMPLOYMENT_TYPES] as [EmploymentType, ...EmploymentType[]]

type FormValues = {
  company_id: string
  title: string
  description?: string
  status: VacancyStatus
  is_open: boolean
  is_active: boolean
  is_archived: boolean
  salary_from?: string | number
  salary_to?: string | number
  currency?: string
  location?: string
  employment_type: EmploymentType
}

type Props = {
  open: boolean
  title: string
  companies: Company[]
  initial: Partial<FormValues>
  onClose: () => void
  onSubmit: (form: FormValues) => Promise<void>
}

export default function VacancyForm({ open, title, companies, initial, onClose, onSubmit }: Props) {
  const { t } = useI18n()

  const vacancySchema = useMemo(
    () =>
      z.object({
        company_id: z.string().min(1, t('app.vacancies.form.company_required', { defaultValue: 'Company is required' })),
        title: z.string().min(1, t('app.vacancies.form.title_required', { defaultValue: 'Title is required' })),
        description: z.string().optional().or(z.literal('')),
        status: z.enum([...STATUS_OPTIONS] as [VacancyStatus, ...VacancyStatus[]]).default('open'),
        is_open: z.boolean().default(true),
        is_active: z.boolean().default(true),
        is_archived: z.boolean().default(false),
        salary_from: z.union([z.string(), z.number()]).optional().transform((val) => (val === '' ? undefined : val)),
        salary_to: z.union([z.string(), z.number()]).optional().transform((val) => (val === '' ? undefined : val)),
        currency: z.string().optional().or(z.literal('')),
        location: z.string().optional().or(z.literal('')),
        employment_type: z.enum(EMPLOYMENT_ENUM),
      }),
    [t],
  )

  const defaultValues: FormValues = useMemo(
    () => ({
      company_id: initial.company_id ?? companies[0]?.id ?? '',
      title: initial.title ?? '',
      description: initial.description ?? '',
      status: normalizeVacancyStatus(initial.status),
      is_open: typeof initial.is_open === 'boolean' ? initial.is_open : (normalizeVacancyStatus(initial.status) === 'open'),
      is_active: typeof initial.is_active === 'boolean' ? initial.is_active : true,
      is_archived: !!initial.is_archived,
      salary_from: initial.salary_from ?? '',
      salary_to: initial.salary_to ?? '',
      currency: initial.currency ?? '',
      location: initial.location ?? '',
      employment_type: initial.employment_type ?? EMPLOYMENT_TYPES[0],
    }),
    [companies, initial]
  )

  const {
    control,
    handleSubmit,
    register,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(vacancySchema),
    defaultValues,
  })

  const status = watch('status')
  const isOpen = watch('is_open')

  useEffect(() => {
    reset(defaultValues)
  }, [defaultValues, reset])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const statusLower = (status ?? 'open').toLowerCase()
    const shouldBeOpen = statusLower === 'open'
    if (isOpen !== shouldBeOpen) {
      setValue('is_open', shouldBeOpen)
    }
  }, [status, isOpen, open, setValue])

  if (!open) return null

  const submitHandler = handleSubmit(async (values) => {
    await onSubmit(values)
  })

  const content = (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" role="dialog" aria-modal="true">
      <div className="w-full max-w-3xl rounded-xl bg-white shadow-xl overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">{title}</div>
          <button
            onClick={onClose}
            className="btn-secondary btn-sm"
            aria-label={t('app.vacancies.form.close_aria', { defaultValue: 'Close' })}
          >
            ✕
          </button>
        </div>

        <form onSubmit={submitHandler} className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label" htmlFor="vf-company">
              {t('app.vacancies.form.company', { defaultValue: 'Company' })}
            </label>
            <select id="vf-company" className="input" {...register('company_id')}>
              <option value="">
                {t('app.vacancies.form.company_placeholder', { defaultValue: '— select a company —' })}
              </option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name || c.id}</option>
              ))}
            </select>
            {errors.company_id && <p className="text-sm text-rose-600 mt-1">{errors.company_id.message}</p>}
          </div>

          <div className="col-span-2">
            <label className="label" htmlFor="vf-title">
              {t('app.vacancies.form.title', { defaultValue: 'Title' })}
            </label>
            <input id="vf-title" className="input" {...register('title')} />
            {errors.title && <p className="text-sm text-rose-600 mt-1">{errors.title.message}</p>}
          </div>

          <div>
            <label className="label" htmlFor="vf-status">
              {t('app.vacancies.form.status', { defaultValue: 'Status' })}
            </label>
            <select id="vf-status" className="input" {...register('status')}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {t(`app.vacancies.list.status.${s}`, { defaultValue: s })}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="vf-employment">
              {t('app.vacancies.form.employment_type', { defaultValue: 'Employment type' })}
            </label>
            <select id="vf-employment" className="input" {...register('employment_type')}>
              {EMPLOYMENT_TYPES.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
            {errors.employment_type && <p className="text-sm text-rose-600 mt-1">{errors.employment_type.message}</p>}
          </div>

          <div>
            <label className="label" htmlFor="vf-sfrom">
              {t('app.vacancies.form.salary_from', { defaultValue: 'From' })}
            </label>
            <input
              id="vf-sfrom"
              type="number"
              inputMode="decimal"
              className="input"
              {...register('salary_from')}
              placeholder={t('app.vacancies.form.salary_from_placeholder', { defaultValue: 'e.g. 9000' })}
            />
          </div>

          <div>
            <label className="label" htmlFor="vf-sto">
              {t('app.vacancies.form.salary_to', { defaultValue: 'To' })}
            </label>
            <input
              id="vf-sto"
              type="number"
              inputMode="decimal"
              className="input"
              {...register('salary_to')}
              placeholder={t('app.vacancies.form.salary_to_placeholder', { defaultValue: 'e.g. 12000' })}
            />
          </div>

          <div>
            <label className="label" htmlFor="vf-currency">
              {t('app.vacancies.form.currency', { defaultValue: 'Currency' })}
            </label>
            <input
              id="vf-currency"
              className="input"
              {...register('currency')}
              placeholder={t('app.vacancies.detail.placeholders.currency_codes', { defaultValue: 'PLN / EUR / USD' })}
            />
          </div>

          <div>
            <label className="label" htmlFor="vf-location">
              {t('app.vacancies.form.location', { defaultValue: 'Location' })}
            </label>
            <input id="vf-location" className="input" {...register('location')} />
          </div>

          <div className="col-span-2">
            <label className="label" htmlFor="vf-description">
              {t('app.vacancies.form.description', { defaultValue: 'Description' })}
            </label>
            <textarea id="vf-description" className="input min-h-[92px]" {...register('description')} />
          </div>

          <div className="col-span-2 flex items-center gap-6">
            <Controller
              control={control}
              name="is_active"
              render={({ field }) => (
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                  <span>{t('app.vacancies.form.is_active', { defaultValue: 'Active' })}</span>
                </label>
              )}
            />
            <Controller
              control={control}
              name="is_archived"
              render={({ field }) => (
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                  <span>{t('app.vacancies.form.is_archived', { defaultValue: 'Archived' })}</span>
                </label>
              )}
            />
            <Controller
              control={control}
              name="is_open"
              render={({ field }) => (
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />
                  <span>{t('app.vacancies.form.is_open', { defaultValue: 'Open' })}</span>
                </label>
              )}
            />
          </div>

          <div className="col-span-2 flex justify-end gap-2 pt-3 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">
              {t('app.vacancies.form.cancel', { defaultValue: 'Cancel' })}
            </button>
            <button type="submit" className="btn-primary disabled:opacity-60" disabled={isSubmitting}>
              {isSubmitting
                ? t('app.vacancies.form.saving', { defaultValue: 'Saving…' })
                : t('app.vacancies.form.save', { defaultValue: 'Save' })}
            </button>
          </div>
        </form>
      </div>
    </div>
  )

  return createPortal(content, document.body)
}
