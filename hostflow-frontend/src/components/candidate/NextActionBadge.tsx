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
  NextActionPriority,
} from '../../api/nextAction'
import { useI18n } from '../../i18n'
import NextActionExplainabilityPopover from '../explainability/NextActionExplainabilityPopover'

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

// Visual tokens mapped from (kind, priority). These are deliberately small —
// the badge is a single pill, not a card. Colour conveys urgency, icon
// conveys the type of action.
const PRIORITY_BG: Record<NextActionPriority, string> = {
  critical: 'bg-rose-500 text-white border-rose-300',
  high: 'bg-amber-400 text-amber-950 border-amber-200',
  normal: 'bg-sky-500 text-white border-sky-300',
  idle: 'bg-white/15 text-white border-white/30',
}

// Same keys, light-background variant for non-inverse contexts (e.g. when
// the badge is reused outside the dark candidate header). Kept here so all
// the colour decisions live in one place.
const PRIORITY_BG_LIGHT: Record<NextActionPriority, string> = {
  critical: 'bg-rose-100 text-rose-800 border-rose-200',
  high: 'bg-amber-100 text-amber-800 border-amber-200',
  normal: 'bg-sky-100 text-sky-800 border-sky-200',
  idle: 'bg-slate-100 text-slate-700 border-slate-200',
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
        className={clsx(
          'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium',
          inverse ? 'border-white/20 bg-white/10 text-white/70' : 'border-slate-200 bg-slate-50 text-slate-500',
        )}
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
        className={clsx(
          'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium',
          inverse ? 'border-rose-200 bg-rose-500/30 text-white' : 'border-rose-200 bg-rose-100 text-rose-800',
        )}
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

  const palette = inverse ? PRIORITY_BG : PRIORITY_BG_LIGHT
  const pillClasses = clsx(
    'inline-flex max-w-[280px] items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold shadow-sm',
    palette[dto.priority] ?? palette.idle,
  )

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
