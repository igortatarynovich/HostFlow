export const formatDateTime = (value?: string | null, locale?: string): string => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const resolved =
    locale === 'ru'
      ? 'ru-RU'
      : locale === 'pl'
      ? 'pl-PL'
      : locale
  return date.toLocaleString(resolved)
}

