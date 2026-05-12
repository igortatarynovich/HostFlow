import { useMemo, useState } from 'react'
import { useI18n } from '../../i18n'

function parseNum(raw: string): number {
  const n = Number.parseFloat(String(raw).replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}

export default function FleetCalculatorSection() {
  const { t } = useI18n()
  const [distanceKm, setDistanceKm] = useState('120')
  const [ratePerKm, setRatePerKm] = useState('2.5')
  const [hours, setHours] = useState('8')
  const [ratePerHour, setRatePerHour] = useState('25')

  const distanceCharge = useMemo(() => parseNum(distanceKm) * parseNum(ratePerKm), [distanceKm, ratePerKm])
  const timeCharge = useMemo(() => parseNum(hours) * parseNum(ratePerHour), [hours, ratePerHour])
  const total = distanceCharge + timeCharge

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    unit?: string,
  ) => (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="text"
          inputMode="decimal"
          className="input w-full max-w-xs"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {unit ? <span className="text-xs text-slate-500">{unit}</span> : null}
      </div>
    </label>
  )

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.fleet.calculator.title', { defaultValue: 'Trip calculator' })}</h1>
        <p className="text-slate-600">{t('app.fleet.calculator.subtitle', { defaultValue: 'Rough estimate: distance × km rate plus hours × hourly rate. Does not persist or replace payroll.' })}</p>
      </header>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {field(t('app.fleet.calculator.distance_km', { defaultValue: 'Distance' }), distanceKm, setDistanceKm, 'km')}
        {field(t('app.fleet.calculator.rate_per_km', { defaultValue: 'Rate per km' }), ratePerKm, setRatePerKm)}
        {field(t('app.fleet.calculator.hours', { defaultValue: 'Hours on duty' }), hours, setHours, 'h')}
        {field(t('app.fleet.calculator.rate_per_hour', { defaultValue: 'Rate per hour' }), ratePerHour, setRatePerHour)}
      </div>

      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4 text-white shadow-md">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-300">{t('app.fleet.calculator.estimate', { defaultValue: 'Estimated accrual' })}</p>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">{t('app.fleet.calculator.part_distance', { defaultValue: 'Distance component' })}</dt>
            <dd className="tabular-nums font-semibold">{distanceCharge.toFixed(2)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-400">{t('app.fleet.calculator.part_time', { defaultValue: 'Time component' })}</dt>
            <dd className="tabular-nums font-semibold">{timeCharge.toFixed(2)}</dd>
          </div>
          <div className="flex justify-between gap-4 border-t border-slate-700 pt-2 text-base">
            <dt className="font-medium text-white">{t('app.fleet.calculator.total', { defaultValue: 'Total' })}</dt>
            <dd className="tabular-nums font-bold">{total.toFixed(2)}</dd>
          </div>
        </dl>
      </section>
    </div>
  )
}
