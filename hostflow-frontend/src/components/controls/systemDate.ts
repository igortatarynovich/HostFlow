export const SYSTEM_DATE_FORMATS = ['DD.MM.YYYY', 'YYYY-MM-DD', 'MM/DD/YYYY'] as const

export type SystemDateFormat = (typeof SYSTEM_DATE_FORMATS)[number]

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

export function normalizeSystemDateFormat(value: string | null | undefined): SystemDateFormat {
  const text = String(value || '').trim().toUpperCase()
  if (text === 'YYYY-MM-DD' || text === 'MM/DD/YYYY' || text === 'DD.MM.YYYY') return text
  return 'DD.MM.YYYY'
}

function isRealDate(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1) return false
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

export function formatSystemDate(value: string | null | undefined, format: SystemDateFormat): string {
  const match = ISO_DATE.exec(String(value || '').slice(0, 10))
  if (!match) return ''
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  if (!isRealDate(year, month, day)) return ''
  const yyyy = match[1]
  const mm = match[2]
  const dd = match[3]
  if (format === 'YYYY-MM-DD') return `${yyyy}-${mm}-${dd}`
  if (format === 'MM/DD/YYYY') return `${mm}/${dd}/${yyyy}`
  return `${dd}.${mm}.${yyyy}`
}

export function parseSystemDate(text: string, format: SystemDateFormat): string | null {
  const source = text.trim()
  let year = ''
  let month = ''
  let day = ''
  if (format === 'YYYY-MM-DD') {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(source)
    if (!match) return null
    year = match[1]
    month = match[2]
    day = match[3]
  } else if (format === 'MM/DD/YYYY') {
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(source)
    if (!match) return null
    month = match[1]
    day = match[2]
    year = match[3]
  } else {
    const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(source)
    if (!match) return null
    day = match[1]
    month = match[2]
    year = match[3]
  }
  if (!isRealDate(Number(year), Number(month), Number(day))) return null
  return `${year}-${month}-${day}`
}

export function maskSystemDate(raw: string, format: SystemDateFormat): string {
  const digits = raw.replace(/\D/g, '').slice(0, 8)
  if (!digits) return ''
  if (format === 'YYYY-MM-DD') {
    return [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8)].filter(Boolean).join('-')
  }
  const separator = format === 'MM/DD/YYYY' ? '/' : '.'
  return [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)].filter(Boolean).join(separator)
}
