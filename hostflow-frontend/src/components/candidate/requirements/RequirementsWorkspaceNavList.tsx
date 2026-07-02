import clsx from 'clsx'
import { useMemo, useState } from 'react'
import { useI18n } from '../../../i18n'
import type {
  OperationalRequirementRow,
  RequirementChecklistItem,
  WorkspaceFieldRequirement,
} from '../../../api/candidateRequirements'
import {
  evidenceStatusLabelKey,
  requirementStatusBadgeClass,
  resolveRequirementRowStatus,
} from '../requirementsChecklistPresentation'
import { requirementTitle } from './requirementRowLabels'

type FilterMode = 'all' | 'open'

type Props = {
  requirements: RequirementChecklistItem[]
  fieldRequirements: WorkspaceFieldRequirement[]
  operationalRequirements: OperationalRequirementRow[]
  selectedRequirementCode: string | null
  onSelectRequirement: (code: string) => void
  className?: string
}

function fieldLabel(t: ReturnType<typeof useI18n>['t'], row: WorkspaceFieldRequirement): string {
  const code = row.qualified_code
  return t(`app.candidate_card.fields.${code.split('.').pop() || code}`, {
    defaultValue: code.split('.').pop()?.replace(/_/g, ' ') || code,
  })
}

function isRequirementOpen(item: RequirementChecklistItem): boolean {
  if (item.evaluation?.status === 'not_applicable') return false
  return !item.fulfilled
}

function isOperationalOpen(item: OperationalRequirementRow): boolean {
  return item.status !== 'satisfied'
}

export default function RequirementsWorkspaceNavList({
  requirements,
  fieldRequirements,
  operationalRequirements,
  selectedRequirementCode,
  onSelectRequirement,
  className,
}: Props) {
  const { t } = useI18n()
  const [filter, setFilter] = useState<FilterMode>('open')

  const visibleRequirements = useMemo(() => {
    const rows = requirements || []
    if (filter === 'open') return rows.filter(isRequirementOpen)
    return rows
  }, [filter, requirements])

  const visibleFields = useMemo(() => {
    const rows = fieldRequirements || []
    if (filter === 'open') return rows.filter((row) => !row.satisfied)
    return rows
  }, [fieldRequirements, filter])

  const visibleOperational = useMemo(() => {
    const rows = operationalRequirements || []
    if (filter === 'open') return rows.filter(isOperationalOpen)
    return rows
  }, [filter, operationalRequirements])

  return (
    <section className={clsx('space-y-3', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.candidate_requirements.workspace.checklist_title', { defaultValue: 'Checklist' })}
        </h2>
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
          <button
            type="button"
            className={clsx(
              'rounded-md px-2.5 py-1 font-medium transition',
              filter === 'open' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600',
            )}
            onClick={() => setFilter('open')}
          >
            {t('app.candidate_requirements.workspace.filter_open', { defaultValue: 'Open only' })}
          </button>
          <button
            type="button"
            className={clsx(
              'rounded-md px-2.5 py-1 font-medium transition',
              filter === 'all' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600',
            )}
            onClick={() => setFilter('all')}
          >
            {t('app.candidate_requirements.workspace.filter_all', { defaultValue: 'All' })}
          </button>
        </div>
      </div>

      {visibleFields.length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_requirements.workspace.section_data', { defaultValue: 'Required data' })}
          </div>
          <ul className="mt-2 space-y-1.5">
            {visibleFields.map((row) => (
              <li
                key={row.qualified_code}
                className="flex items-center justify-between gap-2 text-xs"
              >
                <span className="font-medium text-slate-800">{fieldLabel(t, row)}</span>
                <span
                  className={clsx(
                    'rounded-full border px-2 py-0.5 text-[10px] font-medium',
                    row.satisfied
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                      : 'border-amber-200 bg-amber-50 text-amber-950',
                  )}
                >
                  {row.satisfied
                    ? t('app.candidate_requirements.workspace.data_ok', { defaultValue: 'Filled' })
                    : t('app.candidate_requirements.workspace.data_missing', { defaultValue: 'Missing' })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="border-b border-slate-100 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t('app.candidate_requirements.workspace.section_documents', {
            defaultValue: 'Documents & evidence',
          })}
        </div>
        {visibleRequirements.length === 0 ? (
          <div className="px-3 py-5 text-xs text-slate-500">
            {filter === 'open'
              ? t('app.candidate_requirements.workspace.no_open_requirements', {
                  defaultValue: 'No open document requirements.',
                })
              : t('app.candidate_card.requirements_checklist.empty', {
                  defaultValue: 'No requirements for this profile.',
                })}
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {visibleRequirements.map((item) => {
              const status = resolveRequirementRowStatus(item)
              const selected = selectedRequirementCode === item.requirement_code
              return (
                <li key={item.requirement_code}>
                  <button
                    type="button"
                    className={clsx(
                      'flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition',
                      selected ? 'bg-brand-50' : 'hover:bg-slate-50',
                    )}
                    onClick={() => onSelectRequirement(item.requirement_code)}
                  >
                    <span className="min-w-0 text-sm font-medium text-slate-900">
                      {requirementTitle(t, item)}
                    </span>
                    <span
                      className={clsx(
                        'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium',
                        requirementStatusBadgeClass(status),
                      )}
                    >
                      {t(evidenceStatusLabelKey(status), { defaultValue: status.replace(/_/g, ' ') })}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {visibleOperational.length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="border-b border-slate-100 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.candidate_requirements.workspace.section_operational', {
              defaultValue: 'Operational actions',
            })}
          </div>
          <ul className="divide-y divide-slate-100">
            {visibleOperational.map((item) => {
              const selected = selectedRequirementCode === item.requirement_code
              const open = isOperationalOpen(item)
              return (
                <li key={item.requirement_code}>
                  <button
                    type="button"
                    className={clsx(
                      'flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition',
                      selected ? 'bg-brand-50' : 'hover:bg-slate-50',
                    )}
                    onClick={() => onSelectRequirement(item.requirement_code)}
                  >
                    <span className="min-w-0 text-sm font-medium text-slate-900">
                      {t(`app.candidate_requirements.workspace.operational.${item.requirement_code}`, {
                        defaultValue: item.public_name || item.requirement_code.replace(/_/g, ' '),
                      })}
                    </span>
                    <span
                      className={clsx(
                        'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium',
                        open
                          ? 'border-amber-200 bg-amber-50 text-amber-950'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-900',
                      )}
                    >
                      {open
                        ? t('app.candidate_requirements.workspace.activity_open', { defaultValue: 'Open' })
                        : t('app.candidate_requirements.workspace.activity_satisfied', {
                            defaultValue: 'Completed',
                          })}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
