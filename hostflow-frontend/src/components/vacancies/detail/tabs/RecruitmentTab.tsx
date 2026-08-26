import React from 'react'
import { Controller, type Control, type UseFormRegister, type UseFormWatch } from 'react-hook-form'
import { SectionCard } from '../../../ui/SectionCard'
import FunnelSelector from '../../../profile/FunnelSelector'
import type { ManagerOption } from '../../../../api/types'

type PoolDraft = Record<string, { selected: boolean; weight: number }>

type Props = {
  control: Control<any>
  register: UseFormRegister<any>
  watch: UseFormWatch<any>
  companyId: string
  managerOptions: ManagerOption[]
  recruiterOptions: ManagerOption[]
  poolDraft: PoolDraft
  setPoolDraft: React.Dispatch<React.SetStateAction<PoolDraft>>
  stageCodes: string[]
  labels: {
    section: string
    pipeline: string
    pipelineHint: string
    pipelineRequired: string
    assignment: string
    assignmentHint: string
    manager: string
    managerNone: string
    recruiters: string
    noRecruiters: string
    weight: string
    rotationHint: string
    autoAssign: string
    autoAssignHint: string
    sla: string
    slaReserved: string
    transitions: string
    transitionsReserved: string
    systemStages: string
    systemStagesEmpty: string
  }
}

export function RecruitmentTab({
  control,
  register,
  watch,
  companyId,
  managerOptions,
  recruiterOptions,
  poolDraft,
  setPoolDraft,
  stageCodes,
  labels,
}: Props) {
  return (
    <div className="space-y-4">
      <SectionCard title={labels.section}>
        <div className="space-y-4">
          <div>
            <div className="label">{labels.pipeline}</div>
            <p className="mb-2 text-xs text-slate-500">{labels.pipelineHint}</p>
            <Controller
              name="funnel_id"
              control={control}
              render={({ field }) => (
                <FunnelSelector
                  companyId={companyId || null}
                  value={field.value || null}
                  onChange={(id) => field.onChange(id || '')}
                  funnelType="candidate"
                  moduleKey="recruitment"
                />
              )}
            />
            {!watch('funnel_id') ? (
              <p className="mt-2 text-xs text-amber-700">{labels.pipelineRequired}</p>
            ) : null}
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <div className="label">{labels.assignment}</div>
            <p className="mb-3 text-xs text-slate-500">{labels.assignmentHint}</p>
            <label className="mb-3 block max-w-xl">
              <div className="label">{labels.manager}</div>
              <select className="input" {...register('manager')}>
                <option value="">{labels.managerNone}</option>
                {managerOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label || opt.full_name || opt.email || opt.id}
                  </option>
                ))}
              </select>
            </label>

            <div className="label">{labels.autoAssign}</div>
            <p className="mb-2 text-xs text-slate-500">{labels.autoAssignHint}</p>
            <div className="label">{labels.recruiters}</div>
            {recruiterOptions.length === 0 ? (
              <p className="text-xs text-amber-700">{labels.noRecruiters}</p>
            ) : (
              <ul className="mt-1 space-y-2">
                {recruiterOptions.map((opt) => {
                  const row = poolDraft[opt.id] || { selected: false, weight: 1 }
                  return (
                    <li
                      key={opt.id}
                      className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
                    >
                      <label className="flex min-w-[12rem] flex-1 items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={row.selected}
                          onChange={(e) => {
                            const checked = e.target.checked
                            setPoolDraft((prev) => ({
                              ...prev,
                              [opt.id]: {
                                selected: checked,
                                weight: prev[opt.id]?.weight ?? 1,
                              },
                            }))
                          }}
                        />
                        <span>{opt.label || opt.full_name || opt.email || opt.id}</span>
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-600">
                        <span>{labels.weight}</span>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          className="input w-20"
                          disabled={!row.selected}
                          value={row.weight}
                          onChange={(e) => {
                            const n = Math.max(1, Math.min(100, Number(e.target.value) || 1))
                            setPoolDraft((prev) => ({
                              ...prev,
                              [opt.id]: {
                                selected: prev[opt.id]?.selected ?? false,
                                weight: n,
                              },
                            }))
                          }}
                        />
                      </label>
                    </li>
                  )
                })}
              </ul>
            )}
            <p className="mt-2 text-xs text-slate-500">{labels.rotationHint}</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard title={labels.sla}>
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
          {labels.slaReserved}
        </p>
      </SectionCard>

      <SectionCard title={labels.transitions}>
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
          {labels.transitionsReserved}
        </p>
      </SectionCard>

      <SectionCard title={labels.systemStages}>
        {stageCodes.length === 0 ? (
          <p className="text-sm text-slate-500">{labels.systemStagesEmpty}</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {stageCodes.map((code) => (
              <li
                key={code}
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 font-mono text-xs text-slate-700"
              >
                {code}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  )
}
