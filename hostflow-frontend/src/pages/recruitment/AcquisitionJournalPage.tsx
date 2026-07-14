import { format, isToday, isYesterday } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import type { AcquisitionJournalEntry } from '../../api/searchAcquisition'
import { useI18n, type LocaleCode } from '../../i18n'
import { useAcquisitionOutlet } from './useAcquisitionOutlet'

function dateFnsLocale(code: LocaleCode) {
  if (code === 'pl') return plFns
  if (code === 'ru') return ruFns
  return enUS
}

function groupLabel(date: Date, locale: LocaleCode, t: ReturnType<typeof useI18n>['t']): string {
  if (isToday(date)) return t('app.acquisition.journal_today', { defaultValue: 'Сегодня' })
  if (isYesterday(date)) return t('app.acquisition.journal_yesterday', { defaultValue: 'Вчера' })
  return format(date, 'd MMMM', { locale: dateFnsLocale(locale) })
}

function groupEntries(entries: AcquisitionJournalEntry[]) {
  const groups: { label: string; sortKey: string; rows: AcquisitionJournalEntry[] }[] = []
  const map = new Map<string, AcquisitionJournalEntry[]>()
  for (const entry of entries) {
    const at = entry.at ? new Date(entry.at) : new Date()
    const dayKey = format(at, 'yyyy-MM-dd')
    const bucket = map.get(dayKey) ?? []
    bucket.push(entry)
    map.set(dayKey, bucket)
  }
  for (const [dayKey, rows] of map.entries()) {
    groups.push({ label: dayKey, sortKey: dayKey, rows })
  }
  groups.sort((a, b) => b.sortKey.localeCompare(a.sortKey))
  return groups
}

export default function AcquisitionJournalPage() {
  const { t, locale } = useI18n()
  const { snapshot, loading } = useAcquisitionOutlet()
  const entries = snapshot?.journal ?? []

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
  }

  if (entries.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
        <p className="text-sm text-slate-600">
          {t('app.acquisition.journal_empty', {
            defaultValue: 'Журнал пока пуст. Здесь будут синхронизации, новые активности и изменения метрик.',
          })}
        </p>
      </section>
    )
  }

  const groups = groupEntries(entries)

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" data-testid="m1-acquisition-journal">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('app.acquisition.journal_title', { defaultValue: 'Журнал изменений' })}
      </h3>
      <div className="mt-4 space-y-6">
        {groups.map((group) => {
          const sampleDate = group.rows[0]?.at ? new Date(group.rows[0].at) : new Date()
          return (
            <div key={group.sortKey}>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {groupLabel(sampleDate, locale, t)}
              </h4>
              <ul className="mt-2 space-y-2">
                {group.rows.map((entry) => {
                  const at = entry.at ? new Date(entry.at) : new Date()
                  return (
                    <li key={entry.id} className="flex gap-3 text-sm text-slate-700">
                      <span className="w-12 shrink-0 tabular-nums text-slate-400">{format(at, 'HH:mm')}</span>
                      <span>{entry.title}</span>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
