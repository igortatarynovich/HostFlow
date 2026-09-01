import { IconPhone } from '@tabler/icons-react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { leadShowsDuplicateMark } from '../../utils/leadDuplicateReview'
import { StatusBadge } from '../ui/StatusBadge'

type Props = {
  lead: Lead
  displayName: string
  formatDate: (iso: string | null | undefined) => string
  createLabel: string
  rejectLabel: string
  poolLabel: string
  createDisabled?: boolean
  rejectDisabled?: boolean
  poolDisabled?: boolean
  createBusy?: boolean
  onCreate: () => void
  onReject: () => void
  onPool: () => void
}

function digitsPhone(raw: unknown): string {
  return String(raw || '').replace(/\s/g, '')
}

function hasCallablePhone(raw: unknown): boolean {
  return digitsPhone(raw).replace(/\D/g, '').length > 0
}

export default function LeadIntakeIdentityBar({
  lead,
  displayName,
  formatDate,
  createLabel,
  rejectLabel,
  poolLabel,
  createDisabled,
  rejectDisabled,
  poolDisabled,
  createBusy,
  onCreate,
  onReject,
  onPool,
}: Props) {
  const { t } = useI18n()
  const n = lead.normalized && typeof lead.normalized === 'object' && !Array.isArray(lead.normalized)
    ? (lead.normalized as Record<string, unknown>)
    : {}
  const phone = n.phone
  const canTel = hasCallablePhone(phone)
  const formTitle = String(n.form_name || n.form_title || lead.vacancy_title || '').trim()
  const sourceBits = [lead.source || 'Meta', formTitle ? `${t('app.leads.intake_workspace.identity.form', { defaultValue: 'form' })} «${formTitle}»` : '', formatDate(lead.created_at)]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="space-y-3">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-xl font-semibold tracking-tight text-slate-900">{displayName}</h2>
          {leadShowsDuplicateMark(lead) ? (
            <StatusBadge
              label={t('app.leads.duplicate_review.badge_duplicate', { defaultValue: 'Duplicate' })}
              semantic="warning"
              size="sm"
            />
          ) : null}
        </div>
        {canTel ? (
          <p className="mt-0.5 text-base font-medium tabular-nums text-slate-800">{String(phone)}</p>
        ) : null}
        <p className="mt-1 text-xs text-slate-500">{sourceBits}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {canTel ? (
          <a
            href={`tel:${digitsPhone(phone)}`}
            className="btn-primary inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold"
          >
            <IconPhone size={16} stroke={1.75} aria-hidden />
            {t('app.leads.inbox.action_call', { defaultValue: 'Call' })}
          </a>
        ) : (
          <span className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-400">
            <IconPhone size={16} stroke={1.75} aria-hidden />
            {t('app.leads.inbox.action_call', { defaultValue: 'Call' })}
          </span>
        )}
        <button
          type="button"
          className="inline-flex items-center rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          disabled={createDisabled || createBusy}
          onClick={onCreate}
        >
          {createBusy ? t('common.loading') : createLabel}
        </button>
        <button
          type="button"
          className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          disabled={poolDisabled}
          onClick={onPool}
        >
          {poolLabel}
        </button>
        <button
          type="button"
          className="inline-flex items-center rounded-xl px-3 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
          disabled={rejectDisabled}
          onClick={onReject}
        >
          {rejectLabel}
        </button>
      </div>
    </div>
  )
}
