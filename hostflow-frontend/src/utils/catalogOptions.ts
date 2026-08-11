import type { CatalogOptionDto } from '../api/catalogs'
import { detectStoredLocale, lookupScopedTranslation } from '../i18n'

function otherCountryLabel(locale?: string): string {
  const code = (locale || detectStoredLocale()) as 'en' | 'ru' | 'pl'
  return lookupScopedTranslation(code, 'app.catalog', 'other_country') || 'Other country'
}

export function catalogOptionLabel(option: CatalogOptionDto, locale?: string): string {
  const isRu = locale?.startsWith('ru')
  const meta = option.meta ?? {}
  if (isRu) return meta.label_ru ?? option.label
  return meta.label_en ?? option.label
}

export function catalogOptionDescription(option: CatalogOptionDto, locale?: string): string {
  const isRu = locale?.startsWith('ru')
  const meta = option.meta ?? {}
  if (isRu) return String(meta.description_ru ?? meta.subtitle_ru ?? '')
  return String(meta.description_en ?? meta.subtitle_en ?? '')
}

export function catalogCountryLabel(
  option: CatalogOptionDto,
  locale?: string,
  countryCode?: string,
): string {
  if (countryCode === 'OTHER') {
    return otherCountryLabel(locale)
  }
  return catalogOptionLabel(option, locale)
}

export function withOtherCountryOption(
  countries: CatalogOptionDto[],
  locale?: string,
): CatalogOptionDto[] {
  if (countries.some((row) => row.value === 'OTHER')) return countries
  const label = otherCountryLabel(locale)
  return [
    ...countries,
    {
      value: 'OTHER',
      label,
      meta: {
        label_ru: lookupScopedTranslation('ru', 'app.catalog', 'other_country') || 'Other country',
        label_en: lookupScopedTranslation('en', 'app.catalog', 'other_country') || 'Other country',
      },
    },
  ]
}
