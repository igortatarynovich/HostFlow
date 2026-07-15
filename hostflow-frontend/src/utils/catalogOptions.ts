import type { CatalogOptionDto } from '../api/catalogs'

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
    return locale?.startsWith('ru') ? 'Другая страна' : 'Other country'
  }
  return catalogOptionLabel(option, locale)
}

export function withOtherCountryOption(
  countries: CatalogOptionDto[],
  locale?: string,
): CatalogOptionDto[] {
  if (countries.some((row) => row.value === 'OTHER')) return countries
  return [
    ...countries,
    {
      value: 'OTHER',
      label: locale?.startsWith('ru') ? 'Другая страна' : 'Other country',
      meta: {
        label_ru: 'Другая страна',
        label_en: 'Other country',
      },
    },
  ]
}
