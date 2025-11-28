import type { PublicDocumentEntry, PublicDocumentType } from '../../../api/publicIntake'
import type { TranslateFn } from '../../../i18n'

export type RequirementSummary = {
  title: string
  details: string[]
}

export function describeRequiredFiles(
  config: Record<string, any> | null | undefined,
  t: TranslateFn,
): RequirementSummary | null {
  if (!config || typeof config !== 'object') return null
  const details: string[] = []
  if (Array.isArray(config.accept) && config.accept.length > 0) {
    details.push(t('scanner.accept_formats', { values: { formats: config.accept.join(', ') } }))
  }
  if (config.max_total_mb) {
    details.push(t('scanner.max_total', { values: { mb: config.max_total_mb } }))
  }
  if (config.max_page_size_mb) {
    details.push(t('scanner.max_per_page', { values: { mb: config.max_page_size_mb } }))
  }
  if (config.min_files) {
    details.push(t('scanner.min_files', { values: { count: config.min_files } }))
  }
  if (config.max_files) {
    details.push(t('scanner.max_files', { values: { count: config.max_files } }))
  }
  if (config.frame?.preset) {
    details.push(t('scanner.place_in_frame'))
    details.push(t('documents.labels.preset', { values: { preset: config.frame.preset } }))
  }

  let titleKey: string = 'scanner.upload_any'
  if (config.type === 'sides') {
    titleKey = 'scanner.upload_sides'
    if (Array.isArray(config.sides) && config.sides.length > 0) {
      details.unshift(t('scanner.sides_order', { values: { order: config.sides.join(' -> ') } }))
    }
    if (config.sequence_required) {
      details.push(t('scanner.sequence_required'))
    }
  } else if (config.type === 'paged') {
    titleKey = 'scanner.upload_paged'
    if (config.min_pages) {
      details.unshift(t('scanner.min_pages', { values: { count: config.min_pages } }))
    }
    if (config.sequence_required) {
      details.push(t('scanner.sequence_required'))
    }
  }

  return {
    title: t(titleKey),
    details: details.filter(Boolean),
  }
}

export function metadataFieldLabels(meta: PublicDocumentType | undefined, t: TranslateFn): string[] {
  const fields = Array.isArray(meta?.required_meta) ? meta?.required_meta : []
  if (fields.length === 0) return []
  return fields.map((field) => t(`documents.meta_fields.${field}`, { defaultValue: field }))
}

export function requestedFromText(
  meta: PublicDocumentType | undefined,
  entry: PublicDocumentEntry | undefined,
  t: TranslateFn,
): string | null {
  if (entry?.has_files) {
    return t('documents.labels.requested_from_driver')
  }
  const source = entry?.requested_from || meta?.requested_from || 'driver'
  if (!source || source === 'driver') return null
  return t(`documents.labels.requested_from_${source}`, {
    defaultValue: source,
  })
}

export function formatDocumentStatus(status: string | undefined, t: TranslateFn, required: boolean): string {
  if (!status) {
    return required ? t('documents.status.missing') : t('documents.status.default')
  }
  const normalized = status.toLowerCase()
  return t(`documents.status.${normalized}`, { defaultValue: status })
}

export function getDocumentTitle(
  meta: PublicDocumentType | undefined,
  code: string,
  locale: string | undefined,
): string {
  if (!meta?.title) return code
  const shortLocale = (locale ?? 'ru').split('-')[0]
  return (
    meta.title[shortLocale] ||
    (shortLocale !== 'en' ? meta.title.en : undefined) ||
    meta.title.ru ||
    meta.title.en ||
    code
  )
}
