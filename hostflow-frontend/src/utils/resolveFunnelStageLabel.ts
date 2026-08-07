/**
 * Resolve a funnel stage display title for the active UI locale.
 *
 * Priority: labels_i18n[locale] → primary label → system i18n by code.
 */

import { translateStageLabel, type TranslateFn } from './stageLabels'

export type FunnelStageLabelSource = {
  code: string
  label?: string | null
  labels_i18n?: Record<string, string> | null
}

export function normalizeUiLocale(locale: string | null | undefined): string {
  return String(locale || 'en').trim().toLowerCase().slice(0, 2) || 'en'
}

export function resolveFunnelStageLabel(
  stage: FunnelStageLabelSource,
  locale: string | null | undefined,
  t: TranslateFn,
): string {
  const loc = normalizeUiLocale(locale)
  const fromI18n = String(stage.labels_i18n?.[loc] || '').trim()
  if (fromI18n) return fromI18n
  const primary = String(stage.label || '').trim()
  if (primary) return primary
  const code = String(stage.code || '').trim()
  return translateStageLabel(t, code, code) || code || '—'
}
