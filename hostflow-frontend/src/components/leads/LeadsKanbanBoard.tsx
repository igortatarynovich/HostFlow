import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconExternalLink } from '@tabler/icons-react'

import { listLeads } from '../../api/client'
import type { Lead, LeadStage, LeadStatus } from '../../api/types'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { leadsNextActionHref } from '../../api/nextActions'

const KANBAN_COLUMNS: Array<{
  key: string
  status: LeadStatus
  stage: LeadStage | ''
}> = [
  { key: 'inbox', status: 'new', stage: '' },
  { key: 'new', status: 'processed', stage: 'new' },
  { key: 'contacted', status: 'processed', stage: 'contacted' },
  { key: 'qualified', status: 'processed', stage: 'qualified' },
  { key: 'converted', status: 'processed', stage: 'converted' },
  { key: 'lost', status: 'processed', stage: 'lost' },
]

export type LeadsKanbanBaseFilters = {
  conversionRoot?: string
  lostReasonCode?: string
  lostFromCrmStage?: string
  pipelineError?: string
  customFieldKey?: string
  customFieldValue?: string
  q?: string
}

type Props = {
  base: LeadsKanbanBaseFilters
  stageLabels: Record<string, string>
  onOpenLead: (leadId: string) => void
  limitPerColumn?: number
}

export default function LeadsKanbanBoard({
  base,
  stageLabels,
  onOpenLead,
  limitPerColumn = 40,
}: Props) {
  const { t } = useI18n()
  const [byCol, setByCol] = useState<Record<string, Lead[]>>({})
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const next: Record<string, Lead[]> = {}
      for (const col of KANBAN_COLUMNS) {
        const payload = await listLeads({
          status: col.status,
          stage: col.stage || undefined,
          conversionRoot: base.conversionRoot || undefined,
          lostReasonCode: base.lostReasonCode || undefined,
          lostFromCrmStage: base.lostFromCrmStage || undefined,
          pipelineError: base.pipelineError || undefined,
          customFieldKey: base.customFieldKey?.trim() || undefined,
          customFieldValue: base.customFieldKey?.trim() ? base.customFieldValue : undefined,
          q: base.q && base.q.trim().length >= 2 ? base.q.trim() : undefined,
          limit: limitPerColumn,
          offset: 0,
        })
        const items = Array.isArray((payload as { items?: Lead[] })?.items)
          ? ((payload as { items: Lead[] }).items as Lead[])
          : []
        next[col.key] = items
      }
      setByCol(next)
    } catch (e: unknown) {
      setErr((e as { message?: string })?.message || 'Failed')
      setByCol({})
    } finally {
      setLoading(false)
    }
  }, [
    base.conversionRoot,
    base.customFieldKey,
    base.customFieldValue,
    base.lostFromCrmStage,
    base.lostReasonCode,
    base.pipelineError,
    base.q,
    limitPerColumn,
  ])

  useEffect(() => {
    void load()
  }, [load])

  const colTitle = (col: (typeof KANBAN_COLUMNS)[0]) => {
    if (col.key === 'inbox') return t('app.leads.kanban.col_inbox')
    if (col.stage) return stageLabels[col.stage] ?? col.stage
    return col.key
  }

  return (
    <div className="p-2">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
        <p className="text-xs text-slate-500">{t('app.leads.kanban.hint')}</p>
        <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={() => void load()}>
          {t('app.candidates.actions.refresh')}
        </button>
      </div>
      {err ? <div className="px-2 py-2 text-xs text-rose-700">{err}</div> : null}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {KANBAN_COLUMNS.map((col) => {
          const items = byCol[col.key] ?? []
          const href =
            col.key === 'inbox'
              ? leadsNextActionHref({ status: 'new' })
              : leadsNextActionHref({ status: 'processed', stage: col.stage || undefined })
          return (
            <div
              key={col.key}
              className="flex w-[min(280px,85vw)] shrink-0 flex-col rounded-lg border border-slate-200 bg-slate-50/80"
            >
              <div className="border-b border-slate-200 px-2 py-1.5">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                    {colTitle(col)}
                  </span>
                  <Link to={href} className="text-[10px] font-medium text-brand-700 hover:underline">
                    {t('app.leads.kanban.view_all')}
                  </Link>
                </div>
                <div className="text-[10px] text-slate-500 tabular-nums">
                  {loading ? '…' : items.length}
                  {items.length >= limitPerColumn ? '+' : ''}
                </div>
              </div>
              <ul className="max-h-[min(520px,55vh)] space-y-1 overflow-y-auto p-1.5">
                {loading && (
                  <li className="px-1 py-3 text-center text-xs text-slate-500">{t('common.loading')}</li>
                )}
                {!loading &&
                  items.map((lead) => {
                    const norm = lead.normalized || {}
                    const name =
                      (norm.full_name as string) ||
                      `${(norm.first_name as string) || ''} ${(norm.last_name as string) || ''}`.trim() ||
                      '—'
                    return (
                      <li key={lead.id}>
                        <button
                          type="button"
                          onClick={() => onOpenLead(lead.id)}
                          className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-left text-xs shadow-sm hover:border-brand-300"
                        >
                          <div className="flex items-start justify-between gap-1">
                            <span className="line-clamp-2 font-medium text-slate-900">{name}</span>
                            <Link
                              to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(lead.id)}`}
                              className="shrink-0 text-brand-600 hover:text-brand-800"
                              title={t('app.leads.table.full_page')}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <IconExternalLink size={14} />
                            </Link>
                          </div>
                          <div className="mt-0.5 line-clamp-1 text-[10px] text-slate-500">
                            {lead.company_name || (norm.email as string) || lead.source || ''}
                          </div>
                        </button>
                      </li>
                    )
                  })}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
