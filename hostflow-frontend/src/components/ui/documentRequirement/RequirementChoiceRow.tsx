import type { ReactNode } from 'react'
import { PresenceToggle } from './PresenceToggle'

type Props = {
  question: string
  value: boolean | null
  yesLabel: string
  noLabel: string
  disabled?: boolean
  onChange: (next: boolean) => void
  choiceLabel?: string | null
  choice?: ReactNode
}

/** One compact line: is this requirement needed, and which basis or procedure applies. */
export function RequirementChoiceRow({
  question,
  value,
  yesLabel,
  noLabel,
  disabled,
  onChange,
  choiceLabel,
  choice,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2" data-testid="requirement-choice-row">
      <span className="text-sm text-slate-700">{question}</span>
      <PresenceToggle value={value} yesLabel={yesLabel} noLabel={noLabel} disabled={disabled} onChange={onChange} />
      {choice ? (
        <label className="flex min-w-[12rem] max-w-xs flex-1 items-center gap-2">
          {choiceLabel ? <span className="shrink-0 text-xs text-slate-500">{choiceLabel}</span> : null}
          <span className="min-w-0 flex-1">{choice}</span>
        </label>
      ) : null}
    </div>
  )
}
