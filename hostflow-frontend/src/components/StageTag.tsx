// src/components/StageTag.tsx
import clsx from 'clsx'
import { useI18n } from '../i18n'
import { canonicalStageKey, translateStageLabel } from '../utils/stageLabels'

// Расширенная карта цветов: поддерживаем статусы вакансий и этапы кандидата
const COLORS: Record<string, string> = {
  // кандидаты
  new: 'bg-slate-200 text-slate-800',
  no_answer: 'bg-yellow-100 text-yellow-800',
  contacted: 'bg-brand-100 text-brand-800',
  interview: 'bg-brand-100 text-brand-800',
  questionnaire_submitted: 'bg-brand-50 text-brand-700',
  docs_wait: 'bg-indigo-100 text-indigo-800',
  docs_got: 'bg-green-100 text-green-800',
  permit_ordered: 'bg-orange-100 text-orange-800',
  permit_received: 'bg-emerald-100 text-emerald-800',
  visa: 'bg-purple-100 text-purple-800',
  red_paper: 'bg-rose-100 text-rose-800',
  trip_plan: 'bg-teal-100 text-teal-800',
  at_client: 'bg-slate-200 text-slate-800',
  on_trip: 'bg-emerald-100 text-emerald-800',
  hiring: 'bg-amber-100 text-amber-800',
  employed: 'bg-green-100 text-green-800',
  probation: 'bg-violet-100 text-violet-800',
  probation_ok: 'bg-violet-200 text-violet-900',
  rejected: 'bg-red-100 text-red-800',
  declined: 'bg-red-200 text-red-900',
  ready_for_handoff: 'bg-teal-100 text-teal-800',
  processing_by_client: 'bg-indigo-100 text-indigo-800',
  docs_submitted_permit: 'bg-amber-100 text-amber-800',
  handoff_returned: 'bg-orange-200 text-orange-900',

  // вакансии
  open: 'bg-green-100 text-green-800',
  paused: 'bg-amber-100 text-amber-800',
  closed: 'bg-slate-200 text-slate-800',
}

const FALLBACK_LABELS: Record<string, string> = {
  new: 'New',
  no_answer: 'No answer',
  contacted: 'Contact established',
  questionnaire_submitted: 'Questionnaire submitted',
  docs_wait: 'Waiting for documents',
  docs_got: 'Documents received',
  permit_ordered: 'Work permit ordered',
  permit_received: 'Work permit received',
  visa: 'Visa',
  red_paper: 'Red paper ordered',
  red_paper_ordered: 'Red paper ordered',
  trip_plan: 'Trip planned',
  at_client: 'At client base',
  on_trip: 'On trip',
  interview: 'Contact established',
  hiring: 'Hiring',
  employed: 'Employed',
  probation: 'Probation',
  probation_ok: 'Probation passed',
  rejected: 'Rejected',
  declined: 'Declined',
  ready_for_handoff: 'Ready for handoff',
  processing_by_client: 'Processed by client',
  docs_submitted_permit: 'Documents submitted for permit',
  handoff_returned: 'Returned',
  // вакансии
  open: 'Open',
  paused: 'Paused',
  closed: 'Closed',
}

export default function StageTag({
  code,
  size = 'md',
}: {
  code?: string | null
  /** `sm` — компактный бейдж рядом с select в таблице кандидатов */
  size?: 'sm' | 'md'
}) {
  const { t } = useI18n()
  const raw = code || 'new'
  const canonical = canonicalStageKey(raw, raw)
  const c = canonical || String(raw).toLowerCase().trim()
  const label =
    translateStageLabel(t, raw, raw) ||
    FALLBACK_LABELS[c] ||
    String(raw) ||
    '—'
  return (
    <span
      className={clsx(
        'badge inline-flex max-w-full items-center truncate font-medium',
        size === 'sm' ? 'px-1.5 py-0 text-[10px]' : 'px-2 py-0.5 text-xs',
        COLORS[c] || 'bg-slate-200 text-slate-800',
      )}
      title={label}
    >
      {label}
    </span>
  )
}
