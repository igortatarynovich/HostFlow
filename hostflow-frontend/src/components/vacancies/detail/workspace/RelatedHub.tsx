import React from 'react'
import { Link } from 'react-router-dom'
import { SectionCard } from '../../ui/SectionCard'

export type RelatedLink = {
  id: string
  label: string
  href?: string
  value?: string
  disabled?: boolean
}

type Props = {
  title: string
  links: RelatedLink[]
}

export function RelatedHub({ title, links }: Props) {
  return (
    <SectionCard title={title}>
      <ul className="divide-y divide-slate-100">
        {links.map((l) => (
          <li key={l.id} className="flex items-center justify-between gap-2 py-2 text-sm">
            <span className="text-slate-500">{l.label}</span>
            {l.disabled || !l.href ? (
              <span className="truncate text-slate-400" title={l.value}>
                {l.value || '—'}
              </span>
            ) : (
              <Link className="truncate font-medium text-teal-700 hover:underline" to={l.href}>
                {l.value || l.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </SectionCard>
  )
}
