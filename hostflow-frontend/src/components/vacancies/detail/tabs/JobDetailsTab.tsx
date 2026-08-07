import React from 'react'
import type { FieldErrors, UseFormRegister, UseFormWatch } from 'react-hook-form'
import { SectionCard } from '../../ui/SectionCard'
import { EMPLOYMENT_TYPES, type EmploymentType } from '../../../api/vacancies'
import type { CandidateProfile } from '../../../api/candidate_profiles'
import type { SalesOrderLine } from '../../../api/salesOrders'

export type JobDetailsFormFields = {
  title: string
  company_id: string
  description?: string
  location?: string
  employment_type: EmploymentType
  salary_from?: string | number
  salary_to?: string | number
  currency?: string
  headcount_target?: string
  order_line_id?: string
  candidate_profile_id?: string
}

type Props = {
  register: UseFormRegister<any>
  errors: FieldErrors<any>
  watch: UseFormWatch<any>
  companyOptions: { id: string; name: string }[]
  candidateProfiles: CandidateProfile[]
  orderLines: SalesOrderLine[]
  isCreate: boolean
  labels: {
    title: string
    company: string
    description: string
    location: string
    employment: string
    salaryFrom: string
    salaryTo: string
    currency: string
    headcount: string
    headcountHint: string
    orderLine: string
    orderLineNone: string
    profile: string
    profileNone: string
    section: string
  }
}

export function JobDetailsTab({
  register,
  errors,
  watch,
  companyOptions,
  candidateProfiles,
  orderLines,
  isCreate,
  labels,
}: Props) {
  return (
    <SectionCard title={labels.section}>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="block md:col-span-2">
          <div className="label">
            {labels.title} <span className="text-rose-600">*</span>
          </div>
          <input className="input" {...register('title')} />
          {errors.title && (
            <p className="mt-1 text-sm text-rose-600">{String(errors.title.message || '')}</p>
          )}
        </label>

        <label className="block">
          <div className="label">
            {labels.company} <span className="text-rose-600">*</span>
          </div>
          <select className="input" {...register('company_id')}>
            <option value="">—</option>
            {companyOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {errors.company_id && (
            <p className="mt-1 text-sm text-rose-600">{String(errors.company_id.message || '')}</p>
          )}
        </label>

        <label className="block">
          <div className="label">{labels.employment}</div>
          <select className="input" {...register('employment_type')}>
            {EMPLOYMENT_TYPES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <div className="label">{labels.location}</div>
          <input className="input" {...register('location')} />
        </label>

        <label className="block">
          <div className="label">{labels.headcount}</div>
          <input type="number" min={0} className="input" {...register('headcount_target')} />
          <p className="mt-1 text-xs text-slate-500">{labels.headcountHint}</p>
        </label>

        {isCreate ? (
          <label className="block">
            <div className="label">{labels.orderLine}</div>
            <select className="input" {...register('order_line_id')} data-testid="vacancy-order-line">
              <option value="">{labels.orderLineNone}</option>
              {orderLines.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.title} · qty {l.quantity_needed}
                  {l.location ? ` · ${l.location}` : ''}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label className="block">
          <div className="label">{labels.profile}</div>
          <select className="input" {...register('candidate_profile_id')}>
            <option value="">{labels.profileNone}</option>
            {candidateProfiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <div className="label">{labels.salaryFrom}</div>
          <input type="number" inputMode="decimal" className="input" {...register('salary_from')} />
        </label>
        <label className="block">
          <div className="label">{labels.salaryTo}</div>
          <input type="number" inputMode="decimal" className="input" {...register('salary_to')} />
        </label>
        <label className="block">
          <div className="label">{labels.currency}</div>
          <input className="input" {...register('currency')} placeholder="EUR / PLN" />
        </label>

        <label className="block md:col-span-2">
          <div className="label">{labels.description}</div>
          <textarea
            className="input min-h-[140px] w-full resize-y"
            {...register('description')}
            rows={Math.max(6, String(watch('description') || '').split('\n').length + 1)}
          />
        </label>
      </div>
    </SectionCard>
  )
}
