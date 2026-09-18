import { memo } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  IconAlertTriangle,
  IconCheck,
  IconClock,
  IconHourglass,
  IconPhoneCall,
  IconQuestionMark,
  IconUserExclamation,
} from '@tabler/icons-react'

import type {
  NextActionDTO,
  NextActionKind,
} from '../../api/nextAction'
import { useI18n } from '../../i18n'
import NextActionExplainabilityPopover from '../explainability/NextActionExplainabilityPopover'
import {
  STATUS_BADGE_SEMANTIC_CLASSES,
  STATUS_BADGE_SEMANTIC_CLASSES_INVERSE,
  nextActionPriorityToSemantic,
} from '../ui/statusBadgeSemantics'

/**
 * Single primary "what to do next" badge for any entity header.
 *
 * Closes G-8 stage 1b (candidates). Stage 2 widens it to leads / vacancies /
 * documents / threads — the badge stays a thin renderer over the canonical
 * `NextActionDTO` so every surface that shows this pill agrees on what the
 * next action is.
 *
 * Design contract:
 * - Always renders SOMETHING. An empty CTA reads as "UI is broken" to
 *   operators. On `kind: idle` we render a calm "Nothing to do right now"
 *   pill so the user sees that the system actually checked.
 * - Clickable only when `dto.href` is present and `kind` is non-terminal.
 *   Terminal/idle states are intentionally non-clickable: there is nothing
 *   to navigate to.
 * - Translates `title_key` / `hint_key` first, falls back to the raw
 *   `title` / `hint` strings the backend ships as a safe default.
 */

interface NextActionBadgeProps {
  dto: NextActionDTO | null
  loading?: boolean
  error?: unknown
  /** When true, render the badge in the dark-on-light header style (white-text
   *  on coloured pill). Defaults to true for the candidate header context. */
  inverse?: boolean
  /** Optional onClick for telemetry / drawer-open hooks. Navigation still
   *  happens via <Link> when href is present. */
  onClick?: () => void
}

const BADGE_BASE =
  'inline-flex max-w-[280px] items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold shadow-sm'

function badgePalette(inverse: boolean, semantic: keyof typeof STATUS_BADGE_SEMANTIC_CLASSES) {
  return inverse ? STATUS_BADGE_SEMANTIC_CLASSES_INVERSE[semantic] : STATUS_BADGE_SEMANTIC_CLASSES[semantic]
}

function iconForKind(kind: NextActionKind, size = 14) {
  switch (kind) {
    case 'reminder':
      return <IconAlertTriangle size={size} />
    case 'contact':
      return <IconPhoneCall size={size} />
    case 'handoff_decision':
      return <IconUserExclamation size={size} />
    case 'handoff_await':
      return <IconHourglass size={size} />
    case 'done':
      return <IconCheck size={size} />
    case 'idle':
    default:
      return <IconClock size={size} />
  }
}

function NextActionBadgeInner({
  dto,
  loading = false,
  error,
  inverse = true,
  onClick,
}: NextActionBadgeProps) {
  const { t } = useI18n()

  // Loading: keep the badge slot reserved so the header doesn't reflow when
  // the DTO arrives. A skeleton pill is calmer than a sudden chip pop-in.
  if (loading && !dto) {
    return (
      <span
        className={clsx(BADGE_BASE, badgePalette(inverse, 'neutral'), inverse && 'text-white/70')}
        aria-busy="true"
        aria-live="polite"
      >
        <IconHourglass size={12} />
        {t('app.candidate_card.next_action.loading', { defaultValue: 'Checking…' })}
      </span>
    )
  }

  // Hard error: don't pretend everything is fine. Operators need to see that
  // the recommendation surface is degraded so they fall back to manual
  // judgement instead of trusting silence.
  if (error && !dto) {
    return (
      <span
        className={clsx(BADGE_BASE, badgePalette(inverse, 'danger'))}
        title={t('app.candidate_card.next_action.error_hint', {
          defaultValue: 'Could not load the recommended next action.',
        })}
      >
        <IconQuestionMark size={12} />
        {t('app.candidate_card.next_action.error', { defaultValue: 'Recommendation unavailable' })}
      </span>
    )
  }

  if (!dto) {
    return null
  }

  const semantic = nextActionPriorityToSemantic(dto.priority)
  const pillClasses = clsx(BADGE_BASE, badgePalette(inverse, semantic))

  const titleText = dto.title_key
    ? t(dto.title_key, { defaultValue: dto.title })
    : dto.title

  const hintText = dto.hint_key
    ? t(dto.hint_key, { defaultValue: dto.hint ?? '' })
    : dto.hint ?? undefined

  // Tooltip combines hint + machine-readable reason code so power users (and
  // future G-10 explainability popover) can see why the system suggested
  // this. Until G-10 ships, the tooltip is the cheapest "why?" surface.
  const tooltipParts = [
    titleText,
    hintText,
    `[${dto.reason_code}]`,
  ].filter(Boolean)
  const tooltip = tooltipParts.join(' — ')

  const content = (
    <>
      {iconForKind(dto.kind)}
      <span className="truncate">{titleText}</span>
    </>
  )

  // Idle / done / handoff_await states are intentionally NOT clickable — the
  // CTA is "wait", not "click". A clickable button on those states would
  // invite mistaken actions on closed candidates.
  const navigable =
    dto.href &&
    dto.kind !== 'idle' &&
    dto.kind !== 'done' &&
    dto.kind !== 'handoff_await'

  // G-10: explainability popover lives RIGHT next to the badge so the
  // operator sees "what + why" together. Rendering it as a sibling rather
  // than nesting inside the Link/span keeps the badge's click target clean.
  const explain = <NextActionExplainabilityPopover dto={dto} variant={inverse ? 'inverse' : 'default'} />

  if (navigable && dto.href) {
    return (
      <span className="inline-flex items-center gap-1">
        <Link
          to={dto.href}
          onClick={onClick}
          className={clsx(pillClasses, 'transition hover:opacity-90')}
          title={tooltip}
          aria-label={titleText}
        >
          {content}
        </Link>
        {explain}
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1">
      <span className={pillClasses} title={tooltip}>
        {content}
      </span>
      {explain}
    </span>
  )
}

export const NextActionBadge = memo(NextActionBadgeInner)
export default NextActionBadge
