import type { KeyboardEvent, MouseEvent } from 'react'

/** For elements with `onClick` that are not native buttons/links: Enter/Space triggers the same action. */
export function runActionOnSpaceEnter(e: KeyboardEvent, action: () => void): void {
  if (e.key !== 'Enter' && e.key !== ' ') return
  e.preventDefault()
  action()
}

/** When the click handler needs the synthetic mouse event (e.g. stopPropagation). */
export function activateClickOnSpaceEnter<E extends HTMLElement>(
  e: KeyboardEvent<E>,
  onClick: (e: MouseEvent<E>) => void,
): void {
  if (e.key !== 'Enter' && e.key !== ' ') return
  e.preventDefault()
  onClick(e as unknown as MouseEvent<E>)
}
