import { useMemo } from 'react'
import clsx from 'clsx'
import { useI18n, type LocaleCode } from '../../i18n'

const OPTIONS: { value: LocaleCode; label: string }[] = [
  { value: 'en', label: 'EN' },
  { value: 'ru', label: 'RU' },
  { value: 'pl', label: 'PL' },
]

type Props = {
  className?: string
}

export function PublicLocaleSwitcher({ className }: Props) {
  const { locale, setLocale } = useI18n()
  const value = useMemo<LocaleCode>(() => {
    if (locale === 'ru' || locale === 'pl') return locale
    return 'en'
  }, [locale])

  return (
    <label className={clsx('inline-flex items-center gap-2 text-xs font-medium text-slate-500', className)}>
      <span className="uppercase tracking-wide">Lang</span>
      <select
        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] uppercase tracking-wide text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none"
        value={value}
        onChange={(event) => setLocale(event.target.value as LocaleCode)}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
