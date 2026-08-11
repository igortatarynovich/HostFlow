import { useMemo } from 'react'
import Select from './Select'
import type { Option } from './Select'
import { useI18n } from '../../i18n'

type Country = { code: string; name: string }
type DialCodes = Record<string, string>

export default function PhoneInput({
  countries,
  dialCodes,
  value,
  onChange,
}: {
  countries: Country[]
  dialCodes: DialCodes
  value: { country: string; number: string }
  onChange: (v: { country: string; number: string }) => void
}) {
  const { t } = useI18n()
  const options: Option[] = useMemo(() => {
    const opts = countries.map((c) => {
      const code = c.code
      const dial = dialCodes?.[code] ?? ''
      const label = dial ? `${c.name} (${dial})` : c.name
      return { value: code, label }
    })
    return opts.sort((a, b) => a.label.localeCompare(b.label))
  }, [countries, dialCodes])

  function setCountry(code: string) {
    onChange({ country: code, number: value.number })
  }

  return (
    <div className="flex gap-2">
      <div className="min-w-[240px]">
        <Select
          options={options}
          value={value.country || ''}
          onChange={setCountry}
          placeholder={t('app.controls.country_search', { defaultValue: 'Search country/code…' })}
        />
      </div>
      <div className="w-10 grid place-items-center text-slate-400">—</div>
      <input
        className="input flex-1"
        placeholder={t('app.controls.phone_number', { defaultValue: 'number' })}
        value={value.number}
        onChange={(e) => onChange({ country: value.country, number: e.target.value })}
      />
    </div>
  )
}
