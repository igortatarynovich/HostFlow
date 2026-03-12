// src/components/vacancies/VacancyForm.tsx
import { useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

import { EMPLOYMENT_TYPES } from '../../api/vacancies'
import type { EmploymentType } from '../../api/vacancies'

type Company = { id: string; name?: string }

const STATUS_OPTIONS = ['open', 'paused', 'closed'] as const
const EMPLOYMENT_ENUM = [...EMPLOYMENT_TYPES] as [EmploymentType, ...EmploymentType[]]

const vacancySchema = z.object({
  company_id: z.string().min(1, 'Компания обязательна'),
  title: z.string().min(1, 'Название обязательно'),
  description: z.string().optional().or(z.literal('')),
  status: z.enum(STATUS_OPTIONS).default('open'),
  is_open: z.boolean().default(true),
  is_active: z.boolean().default(true),
  is_archived: z.boolean().default(false),
  salary_from: z.union([z.string(), z.number()]).optional().transform((val) => (val === '' ? undefined : val)),
  salary_to: z.union([z.string(), z.number()]).optional().transform((val) => (val === '' ? undefined : val)),
  currency: z.string().optional().or(z.literal('')),
  location: z.string().optional().or(z.literal('')),
  employment_type: z.enum(EMPLOYMENT_ENUM),
})

type FormValues = z.infer<typeof vacancySchema>

type Props = {
  open: boolean
  title: string
  companies: Company[]
  initial: Partial<FormValues>
  onClose: () => void
  onSubmit: (form: FormValues) => Promise<void>
}

export default function VacancyForm({ open, title, companies, initial, onClose, onSubmit }: Props) {
  const defaultValues: FormValues = useMemo(
    () => ({
      company_id: initial.company_id ?? companies[0]?.id ?? '',
      title: initial.title ?? '',
      description: initial.description ?? '',
      status: (initial.status as FormValues['status']) ?? 'open',
      is_open: typeof initial.is_open === 'boolean' ? initial.is_open : ((initial.status ?? 'open') === 'open'),
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
          <button onClick={onClose} className="btn-secondary btn-sm" aria-label="Закрыть">
            ✕
          </button>
        </div>

        <form onSubmit={submitHandler} className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="label" htmlFor="vf-company">Компания</label>
            <select id="vf-company" className="input" {...register('company_id')}>
              <option value="">— выберите компанию —</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name || c.id}</option>
              ))}
            </select>
            {errors.company_id && <p className="text-sm text-rose-600 mt-1">{errors.company_id.message}</p>}
          </div>

          <div className="col-span-2">
            <label className="label" htmlFor="vf-title">Название</label>
            <input id="vf-title" className="input" {...register('title')} />
            {errors.title && <p className="text-sm text-rose-600 mt-1">{errors.title.message}</p>}
          </div>

          <div>
            <label className="label" htmlFor="vf-status">Статус</label>
            <select id="vf-status" className="input" {...register('status')}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="vf-employment">Тип занятости</label>
            <select id="vf-employment" className="input" {...register('employment_type')}>
              {EMPLOYMENT_TYPES.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
            {errors.employment_type && <p className="text-sm text-rose-600 mt-1">{errors.employment_type.message}</p>}
          </div>

          <div>
            <label className="label" htmlFor="vf-sfrom">От</label>
            <input id="vf-sfrom" type="number" inputMode="decimal" className="input" {...register('salary_from')} placeholder="напр., 9000" />
          </div>

          <div>
            <label className="label" htmlFor="vf-sto">До</label>
            <input id="vf-sto" type="number" inputMode="decimal" className="input" {...register('salary_to')} placeholder="напр., 12000" />
          </div>

          <div>
            <label className="label" htmlFor="vf-currency">Валюта</label>
            <input id="vf-currency" className="input" {...register('currency')} placeholder="PLN / EUR / USD" />
          </div>

          <div>
            <label className="label" htmlFor="vf-location">Локация</label>
            <input id="vf-location" className="input" {...register('location')} />
          </div>

          <div className="col-span-2">
            <label className="label" htmlFor="vf-description">Описание</label>
            <textarea id="vf-description" className="input min-h-[92px]" {...register('description')} />
          </div>

          <div className="col-span-2 flex items-center gap-6">
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

          <div className="col-span-2 flex justify-end gap-2 pt-3 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">
              Отмена
            </button>
            <button type="submit" className="btn-primary disabled:opacity-60" disabled={isSubmitting}>
              {isSubmitting ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )

  return createPortal(content, document.body)
}
