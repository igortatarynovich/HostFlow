import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'

export type LeadNextActionPlaybookLead = Pick<
  Lead,
  'next_action_status' | 'next_action_title' | 'next_action_due_at' | 'stage_contract'
>

function playbookVisible(lead: LeadNextActionPlaybookLead): boolean {
  return Boolean(lead.next_action_status || lead.next_action_due_at || lead.stage_contract)
}

/**
 * Shared “stage contract + next action” summary for lead inbox and full-page lead (§2.3).
 */
export default function LeadNextActionPlaybook(props: {
  lead: LeadNextActionPlaybookLead
  formatDueAt: (iso: string | null | undefined) => string
  className?: string
}) {
  const { t } = useI18n()
  const { lead, formatDueAt, className } = props

  if (!playbookVisible(lead)) return null

  const statusLine =
    lead.next_action_status === 'no_next_action'
      ? t('app.leads.inbox.playbook.none')
      : lead.next_action_status === 'overdue'
        ? t('app.leads.inbox.playbook.overdue')
        : lead.next_action_status === 'scheduled'
          ? t('app.leads.inbox.playbook.scheduled')
          : lead.next_action_status
            ? String(lead.next_action_status)
            : t('app.leads.inbox.playbook.activity_unknown')

  return (
    <div
      className={[
        'rounded-lg border border-slate-200 bg-white p-3 space-y-2',
        className ?? '',
      ].join(' ')}
    >
      <div className="text-xs font-semibold text-slate-700">
        {t('app.leads.inbox.playbook.title')}
      </div>
      <div className="text-xs text-slate-600 space-y-1">
        <div>
          <span className="font-medium text-slate-800">
            {t('app.leads.inbox.playbook.activity')}:
          </span>{' '}
          {statusLine}
          {lead.next_action_title ? ` — ${lead.next_action_title}` : ''}
          {lead.next_action_due_at ? ` · ${formatDueAt(lead.next_action_due_at)}` : ''}
        </div>
        {lead.stage_contract?.owner_role ? (
          <div>
            <span className="font-medium text-slate-800">
              {t('app.leads.inbox.playbook.owner_role')}:
            </span>{' '}
            {lead.stage_contract.owner_role}
          </div>
        ) : null}
        {lead.stage_contract?.sla_hours != null ? (
          <div>
            <span className="font-medium text-slate-800">
              {t('app.leads.inbox.playbook.sla_hours')}:
            </span>{' '}
            {lead.stage_contract.sla_hours}h
          </div>
        ) : null}
        {lead.stage_contract?.required_actions && lead.stage_contract.required_actions.length > 0 ? (
          <div>
            <div className="font-medium text-slate-800 mb-0.5">
              {t('app.leads.inbox.playbook.required_actions')}
            </div>
            <ul className="list-disc pl-4 space-y-0.5">
              {lead.stage_contract.required_actions.map((a, i) => (
                <li key={`${i}-${a}`}>{a}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  )
}

