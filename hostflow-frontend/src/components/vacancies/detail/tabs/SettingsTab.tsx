import React from 'react'
import { Controller, type Control, type UseFormRegister } from 'react-hook-form'
import { SectionCard } from '../../../ui/SectionCard'
import { formatDate } from '../../../../utils/vacancyUtils'

type Props = {
  control: Control<any>
  register: UseFormRegister<any>
  model: { id?: string; created_at?: string; updated_at?: string } | null
  onDelete?: () => void
  labels: {
    section: string
    id: string
    created: string
    updated: string
    active: string
    archived: string
    open: string
    status: string
    delete: string
    technicalHint: string
    statusOptions: { value: string; label: string }[]
  }
}

export function SettingsTab({ control, register, model, onDelete, labels }: Props) {
  return (
    <SectionCard title={labels.section}>
      <p className="mb-4 text-xs text-slate-500">{labels.technicalHint}</p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="block">
          <div className="label">{labels.id}</div>
          <input className="input font-mono text-xs" readOnly value={model?.id || '—'} />
        </label>
        <label className="block">
          <div className="label">{labels.status}</div>
          <select className="input" {...register('status')}>
            {labels.statusOptions.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <div className="label">{labels.created}</div>
          <input className="input" readOnly value={formatDate(model?.created_at) || '—'} />
        </label>
        <label className="block">
          <div className="label">{labels.updated}</div>
          <input className="input" readOnly value={formatDate(model?.updated_at) || '—'} />
        </label>
        <div className="md:col-span-2 flex flex-wrap items-center gap-6">
          <Controller
            control={control}
            name="is_active"
            render={({ field }) => (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={!!field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
                <span>{labels.active}</span>
              </label>
            )}
          />
          <Controller
            control={control}
            name="is_archived"
            render={({ field }) => (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={!!field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
                <span>{labels.archived}</span>
              </label>
            )}
          />
          <Controller
            control={control}
            name="is_open"
            render={({ field }) => (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={!!field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
                <span>{labels.open}</span>
              </label>
            )}
          />
        </div>
        {onDelete ? (
          <div className="md:col-span-2">
            <button type="button" className="btn-danger btn-sm" onClick={onDelete}>
              {labels.delete}
            </button>
          </div>
        ) : null}
      </div>
    </SectionCard>
  )
}
