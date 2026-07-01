import type { ComboboxOption } from '../components/ui/comboboxShared'

export type Option = ComboboxOption

const COUNTRY_CODES: string[] = [
  'AE','AF','AL','AM','AO','AR','AT','AU','AZ','BA','BD','BE','BF','BG','BH','BI','BJ','BO','BR','BT','BW','BY',
  'CA','CD','CF','CG','CH','CI','CL','CM','CN','CO','CV','CY','CZ',
  'DE','DJ','DK','DZ',
  'EC','EE','EG','EH','ER','ES','ET',
  'FI','FR',
  'GA','GB','GE','GH','GM','GN','GQ','GR','GW','GY',
  'HR','HU',
  'ID','IE','IL','IN','IQ','IR','IS','IT',
  'JO','JP',
  'KE','KG','KM','KR','KZ','KW',
  'LK','LR','LS','LT','LU','LV','LY',
  'MA','MD','ME','MG','MK','ML','MR','MT','MU','MV','MW','MX','MZ',
  'NA','NE','NG','NL','NO','NP','NZ',
  'OM',
  'PE','PH','PK','PL','PT','PY','QA',
  'RO','RS','RU','RW',
  'SA','SC','SD','SE','SI','SK','SL','SN','SO','SR','SS','ST','SZ',
  'TD','TG','TH','TJ','TM','TN','TR','TZ',
  'UA','UG','US','UY','UZ',
  'VE','VN',
  'XK','YE',
  'ZA','ZM','ZW',
]

function createDisplayNames(locale?: string): Intl.DisplayNames | null {
  if (typeof Intl === 'undefined' || typeof Intl.DisplayNames === 'undefined') {
    return null
  }
  const locales: string[] = []
  if (locale) locales.push(locale)
  locales.push('en')
  try {
    return new Intl.DisplayNames(locales, { type: 'region' })
  } catch (err) {
    try {
      return new Intl.DisplayNames(['en'], { type: 'region' })
    } catch {
      return null
    }
  }
}

export function buildCountryOptions(locale?: string): Option[] {
  const display = createDisplayNames(locale)
  const options = COUNTRY_CODES.map((code) => {
    const label = display?.of(code) || code
    return { value: code, label: `${label} (${code})` }
  })
  return options.sort((a, b) => a.label.localeCompare(b.label))
}

export { COUNTRY_CODES }
