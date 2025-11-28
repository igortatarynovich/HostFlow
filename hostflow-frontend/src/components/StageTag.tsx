// src/components/StageTag.tsx
import clsx from 'clsx'
import { useI18n } from '../i18n'
import { canonicalStageKey, translateStageLabel } from '../utils/stageLabels'

// Расширенная карта цветов: поддерживаем статусы вакансий и этапы кандидата
const COLORS: Record<string, string> = {
  // кандидаты
  new: 'bg-gray-200 text-gray-800',
  no_answer: 'bg-yellow-100 text-yellow-800',
  contacted: 'bg-blue-100 text-blue-800',
  interview: 'bg-cyan-100 text-cyan-800',
  questionnaire_submitted: 'bg-sky-100 text-sky-800',
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

  // вакансии
  open: 'bg-green-100 text-green-800',
  paused: 'bg-amber-100 text-amber-800',
  closed: 'bg-gray-200 text-gray-800',
}

const FALLBACK_LABELS: Record<string, string> = {
  new: 'Новый',
  no_answer: 'Не отвечает',
  contacted: 'Контакт установлен',
  questionnaire_submitted: 'Анкета заполнена',
  docs_wait: 'Ожидаем документы',
  docs_got: 'Документы получены',
  permit_ordered: 'Заказ разрешения на работу',
  permit_received: 'Разрешение на работу получено',
  visa: 'Виза',
  red_paper: 'Красная бумага заказана',
  red_paper_ordered: 'Красная бумага заказана',
  trip_plan: 'Планируем приезд',
  at_client: 'На базе клиента',
  on_trip: 'Выехал в рейс',
  interview: 'Контакт установлен',
  hiring: 'Документы получены',
  employed: 'Трудоустроен',
  probation: 'Испытательный срок',
  probation_ok: 'Испытательный срок',
  rejected: 'Отказ',
  declined: 'Отказался',
  // вакансии
  open: 'Открыта',
  paused: 'Пауза',
  closed: 'Закрыта',
}

export default function StageTag({ code }: { code?: string | null }) {
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
    <span className={clsx('badge inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', COLORS[c] || 'bg-gray-200 text-gray-800')}>
      {label}
    </span>
  )
}
