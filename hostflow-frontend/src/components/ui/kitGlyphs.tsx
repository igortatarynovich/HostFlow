import type { SVGProps } from 'react'

/** Kit-internal close glyph — avoid a Tabler import in the public Modal. */
export function CloseGlyph(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden {...props}>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** Column-reorder handle — Candidates / TABLE_V1 customize mode. */
export function ColumnDragGlyph(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width="14" height="18" viewBox="0 0 14 18" fill="currentColor" className="opacity-90" aria-hidden {...props}>
      <circle cx="4" cy="3.5" r="1.35" />
      <circle cx="10" cy="3.5" r="1.35" />
      <circle cx="4" cy="9" r="1.35" />
      <circle cx="10" cy="9" r="1.35" />
      <circle cx="4" cy="14.5" r="1.35" />
      <circle cx="10" cy="14.5" r="1.35" />
    </svg>
  )
}
