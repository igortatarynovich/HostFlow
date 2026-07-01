import type { FleetSeasonalityFromDataResponse } from '../../api/fleet'

function localeForIntl(locale: string): string {
  if (locale === 'pl') return 'pl-PL'
  if (locale === 'ru') return 'ru-RU'
  return 'en-US'
}

function monthShortLabel(month1to12: number, loc: string): string {
  return new Intl.DateTimeFormat(loc, { month: 'short' }).format(new Date(2024, month1to12 - 1, 1))
}

export default function FleetSeasonalityBars({
  data,
  locale,
}: {
  data: FleetSeasonalityFromDataResponse
  locale: string
}) {
  const loc = localeForIntl(locale)
  const vals = data.months_1_to_12
  const max = Math.max(...vals, 0.01)
  return (
    <div className="grid grid-cols-6 gap-3 sm:grid-cols-12">
      {vals.map((v, i) => {
        const m = i + 1
        const h = Math.round((v / max) * 100)
        return (
          <div key={m} className="flex flex-col items-center gap-1 text-center">
            <div className="flex h-24 w-full flex-col justify-end rounded-lg bg-slate-100 px-0.5 pb-0.5 pt-1">
              <div
                className="w-full rounded-md bg-blue-500"
                style={{ height: `${Math.max(h, 5)}%`, minHeight: 4 }}
                title={`${monthShortLabel(m, loc)}: ${v.toFixed(2)}`}
              />
            </div>
            <span className="text-[10px] font-semibold uppercase leading-tight text-slate-600">
              {monthShortLabel(m, loc)}
            </span>
            <span className="tabular-nums text-[11px] text-slate-700">{v.toFixed(2)}</span>
          </div>
        )
      })}
    </div>
  )
}
