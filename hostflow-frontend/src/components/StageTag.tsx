// src/components/StageTag.tsx
import { useI18n } from '../i18n'
import { canonicalStageKey, translateStageLabel } from '../utils/stageLabels'
import { StatusBadge } from './ui/StatusBadge'
import { stageSemanticForCode } from './ui/statusBadgeSemantics'

export default function StageTag({
  code,
  label: labelOverride,
  size = 'md',
}: {
  code?: string | null
  /** When set (e.g. vacancy funnel SoT), wins over global i18n. */
  label?: string | null
  /** `sm` — компактный бейдж рядом с select в таблице кандидатов */
  size?: 'sm' | 'md'
}) {
  const { t } = useI18n()
  const raw = code || 'new'
  const canonical = canonicalStageKey(raw, raw)
  const c = canonical || String(raw).toLowerCase().trim()
  const label =
    (labelOverride && String(labelOverride).trim()) ||
    translateStageLabel(t, raw, raw) ||
    String(raw) ||
    '—'
  return (
    <StatusBadge label={label} semantic={stageSemanticForCode(c)} size={size} title={label} />
  )
}
