import { useMemo } from 'react'
import Select from './Select'
import type { Option } from './Select'

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
  // Строим список опций из справочников БЕЗ JSX — чистые строки, чтобы ничего не превращалось в [object Object]
  const options: Option[] = useMemo(() => {
    const opts = countries.map((c) => {
      const code = c.code
      const dial = dialCodes?.[code] ?? ''
      // Метка — обычная строка "Poland (+48)" или "Poland" если кода нет
      const label = dial ? `${c.name} (${dial})` : c.name
      return { value: code, label }
    })
    // сортируем по названию страны
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
          onChange={setCountry}             // Select ожидает (value: string) => void
          placeholder="Поиск страны/кода…"
        />
      </div>
      <div className="w-10 grid place-items-center text-gray-400">—</div>
      <input
        className="input flex-1"
        placeholder="номер"
        value={value.number}
        onChange={(e) => onChange({ country: value.country, number: e.target.value })}
      />
    </div>
  )
}