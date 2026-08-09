/**
 * Field-level validation UX (buyer forms, public questionnaires).
 *
 * Prefer highlighting the control + inline message next to it.
 * Do NOT route client-side field validation through ErrorRecoveryBanner /
 * friendlyFormHintError (generic “retry or refresh” + wrong secondary CTAs).
 */

export const INVALID_FIELD_CONTROL_CLASS =
  'border-rose-400 bg-rose-50/40 ring-2 ring-rose-200 focus:border-rose-500 focus:ring-rose-200'

export const INVALID_FIELDSET_CLASS = 'rounded-lg border border-rose-400 bg-rose-50/50 p-3'

/** Merge base control classes with invalid outline when needed. */
export function fieldControlClass(base: string, invalid: boolean): string {
  return invalid ? `${base} ${INVALID_FIELD_CONTROL_CLASS}` : base
}

/** Focus and scroll the first invalid control into view. */
export function focusFirstInvalid(
  refs: Array<HTMLElement | null | undefined>,
  options?: ScrollIntoViewOptions,
): void {
  const el = refs.find((node) => node != null) ?? null
  if (!el) return
  el.focus({ preventScroll: true })
  el.scrollIntoView({ behavior: 'smooth', block: 'center', ...options })
}

/** Query the first `[aria-invalid="true"]` (or data-invalid) in a form and reveal it. */
export function focusFirstInvalidIn(container: ParentNode | null): void {
  if (!container) return
  const el =
    (container.querySelector('[aria-invalid="true"]') as HTMLElement | null) ||
    (container.querySelector('[data-invalid="true"]') as HTMLElement | null)
  if (!el) return
  el.focus({ preventScroll: true })
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
