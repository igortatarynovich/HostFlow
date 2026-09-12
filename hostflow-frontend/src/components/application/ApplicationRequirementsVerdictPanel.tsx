import type { RequirementsVerdict } from '../../api/types/application'

type Props = {
  verdict: RequirementsVerdict | null | undefined
  t: (key: string, options?: Record<string, unknown>) => string
}

function statusLabel(
  status: string | undefined,
  t: Props['t'],
): string {
  if (status === 'fit') return t('app.recruitment.requirements.status.fit', { defaultValue: 'Подходит' })
  if (status === 'missing')
    return t('app.recruitment.requirements.status.missing', { defaultValue: 'Не хватает данных' })
  if (status === 'not_fit')
    return t('app.recruitment.requirements.status.not_fit', { defaultValue: 'Не подходит' })
  return status || '—'
}

/** Read-only Vacancy Requirements × canonical facts verdict on Application. */
export function ApplicationRequirementsVerdictPanel({ verdict, t }: Props) {
  if (!verdict || !verdict.status) return null
  const explanations = Array.isArray(verdict.explanation) ? verdict.explanation : []
  const tone =
    verdict.status === 'fit'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
      : verdict.status === 'not_fit'
        ? 'border-rose-200 bg-rose-50 text-rose-900'
        : 'border-amber-200 bg-amber-50 text-amber-950'

  return (
    <section
      data-testid="application-requirements-verdict"
      className={`mb-3 rounded-lg border px-3 py-2 text-sm ${tone}`}
    >
      <div className="font-semibold">
        {t('app.recruitment.requirements.title', { defaultValue: 'Требования вакансии' })}
        {': '}
        {statusLabel(String(verdict.status), t)}
      </div>
      {explanations.length > 0 ? (
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs opacity-90">
          {explanations.map((row, idx) => (
            <li key={`${row.code || 'row'}-${idx}`}>{row.message || row.requirement || row.code}</li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
