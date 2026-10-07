import type { ComboboxOption } from '../components/ui/comboboxShared'

export type Option = ComboboxOption

const COUNTRY_CODES: string[] = [
  'AD','AE','AF','AG','AI','AL','AM','AO','AQ','AR','AS','AT','AU','AW','AX','AZ','BA','BB','BD','BE','BF','BG',
  'BH','BI','BJ','BL','BM','BN','BO','BQ','BR','BS','BT','BV','BW','BY','BZ','CA','CC','CD','CF','CG','CH','CI',
  'CK','CL','CM','CN','CO','CR','CU','CV','CW','CX','CY','CZ','DE','DJ','DK','DM','DO','DZ','EC','EE','EG','EH',
  'ER','ES','ET','FI','FJ','FK','FM','FO','FR','GA','GB','GD','GE','GF','GG','GH','GI','GL','GM','GN','GP','GQ',
  'GR','GS','GT','GU','GW','GY','HK','HM','HN','HR','HT','HU','ID','IE','IL','IM','IN','IO','IQ','IR','IS','IT',
  'JE','JM','JO','JP','KE','KG','KH','KI','KM','KN','KP','KR','KW','KY','KZ','LA','LB','LC','LI','LK','LR','LS',
  'LT','LU','LV','LY','MA','MC','MD','ME','MF','MG','MH','MK','ML','MM','MN','MO','MP','MQ','MR','MS','MT','MU',
  'MV','MW','MX','MY','MZ','NA','NC','NE','NF','NG','NI','NL','NO','NP','NR','NU','NZ','OM','PA','PE','PF','PG',
  'PH','PK','PL','PM','PN','PR','PS','PT','PW','PY','QA','RE','RO','RS','RU','RW','SA','SB','SC','SD','SE','SG',
  'SH','SI','SJ','SK','SL','SM','SN','SO','SR','SS','ST','SV','SX','SY','SZ','TC','TD','TF','TG','TH','TJ','TK',
  'TL','TM','TN','TO','TR','TT','TV','TW','TZ','UA','UG','UM','US','UY','UZ','VA','VC','VE','VG','VI','VN','VU',
  'WF','WS','YE','YT','ZA','ZM','ZW',
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

/** Registry countries the operator works with, in the order they should appear. */
export const WORKING_COUNTRY_CODES = ['PL', 'BY', 'UA', 'MD', 'GE', 'KZ', 'UZ'] as const

export function compareCountryOptions(
  a: { value: string; label: string },
  b: { value: string; label: string },
  locale?: string,
): number {
  const rank = (code: string) => {
    const index = WORKING_COUNTRY_CODES.indexOf(code.toUpperCase() as (typeof WORKING_COUNTRY_CODES)[number])
    return index === -1 ? WORKING_COUNTRY_CODES.length : index
  }
  const byRank = rank(a.value) - rank(b.value)
  if (byRank !== 0) return byRank
  return a.label.localeCompare(b.label, locale)
}

export function buildCountryOptions(locale?: string): Option[] {
  const display = createDisplayNames(locale)
  const options = COUNTRY_CODES.map((code) => {
    const label = display?.of(code) || code
    return { value: code, label: `${label} (${code})` }
  })
  return options.sort((a, b) => compareCountryOptions(a, b, locale))
}

export { COUNTRY_CODES }
