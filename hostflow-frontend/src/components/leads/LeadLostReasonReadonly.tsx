import { useMemo } from 'react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'

export function parseLeadLostReasonV1(
  normalized: Lead['normalized'],
): { code: string; note: string; at: string } | null {
  const n = normalized
  if (!n || typeof n !== 'object' || Array.isArray(n)) return null
  const raw = (n as Record<string, unknown>).lead_lost_reason_v1
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const code = typeof o.code === 'string' ? o.code.trim() : ''
  const note = typeof o.note === 'string' ? o.note : ''
  const at = typeof o.at === 'string' ? o.at : ''
  if (!code && !note && !at) return null
  return { code: code || 'unknown', note, at }
}

type Props = {
  lead: Lead
  formatAt: (iso: string) => string
  className?: string
}

/** Read-only block for normalized.lead_lost_reason_v1 when CRM stage is lost (inbox + detail). */
export default function LeadLostReasonReadonly({ lead, formatAt, className }: Props) {
  const { t } = useI18n()
  const v1 = useMemo(() => parseLeadLostReasonV1(lead?.normalized), [lead?.normalized])
  if (lead.stage !== 'lost' || !v1) return null
  return (
    <div
      className={
        className ??
        'mt-3 border-t border-slate-100 pt-3 text-sm text-slate-700'
      }
    >
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {t('app.leads.detail.lost_reason_title')}
      </div>
      <div className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="font-medium text-slate-900">{t(`app.leads.lost_reason.codes.${v1.code}`)}</span>
        {v1.at ? <span className="text-xs text-slate-500">{formatAt(v1.at)}</span> : null}
      </div>
      {v1.note ? <p className="mt-1 whitespace-pre-wrap text-xs text-slate-600">{v1.note}</p> : null}
    </div>
  )
}
