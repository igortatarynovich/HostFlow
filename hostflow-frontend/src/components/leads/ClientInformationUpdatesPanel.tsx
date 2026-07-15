import { useMemo } from 'react'
import type { Lead } from '../../api/types'
import type { FieldOption } from '../../utils/serviceSalesFieldOptions'
import {
  buildAnswerRowsFromSubmission,
  listSubmissions,
} from '../../utils/salesQuestionnaireSubmissions'
import { diffAnswerRows, type AnswerFieldDiff } from '../../utils/clientInformationDiff'

type Props = {
  lead: Lead
  convertedClientId?: string | null
  optionsByCode: Record<string, FieldOption[]>
  onApply?: (diffs: AnswerFieldDiff[]) => void
  onDismiss?: () => void
}

export function ClientInformationUpdatesPanel({
  lead,
  convertedClientId,
  optionsByCode,
  onApply,
  onDismiss,
}: Props) {
  const pending = useMemo(() => {
    if (!convertedClientId) return null
    const submissions = listSubmissions(lead)
    if (submissions.length < 2) return null
    const previous = submissions[submissions.length - 2]
    const latest = submissions[submissions.length - 1]
    const prevRows = buildAnswerRowsFromSubmission(previous, optionsByCode)
    const nextRows = buildAnswerRowsFromSubmission(latest, optionsByCode)
    const diffs = diffAnswerRows(prevRows, nextRows)
    if (diffs.length === 0) return null
    return { diffs, latestAt: latest.submitted_at }
  }, [convertedClientId, lead, optionsByCode])

  if (!pending) return null

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4" data-testid="client-information-updates">
      <p className="text-sm font-semibold text-amber-950">Новые ответы требуют подтверждения</p>
      <p className="mt-1 text-xs text-amber-900">
        Клиент уже создан. Изменения не применятся к карточке автоматически.
      </p>
      <ul className="mt-3 space-y-2 text-sm">
        {pending.diffs.map((row) => (
          <li key={row.key} className="rounded-lg bg-white/80 px-3 py-2 ring-1 ring-amber-100">
            <p className="font-medium text-slate-900">{row.label}</p>
            <p className="text-xs text-slate-600">
              было: <span className="text-slate-800">{row.previous}</span>
            </p>
            <p className="text-xs text-slate-600">
              стало: <span className="font-medium text-slate-900">{row.next}</span>
            </p>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="btn-primary btn-sm" onClick={() => onApply?.(pending.diffs)}>
          Применить к карточке клиента
        </button>
        <button type="button" className="btn-secondary btn-sm" onClick={onDismiss}>
          Оставить без изменений
        </button>
      </div>
    </div>
  )
}
