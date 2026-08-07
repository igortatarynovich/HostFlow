import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'

export type QuickAction = {
  id: string
  label: string
  onClick?: () => void
  href?: string
  disabled?: boolean
  title?: string
}

type Props = {
  title: string
  actions: QuickAction[]
}

export function QuickActions({ title, actions }: Props) {
  return (
    <SectionCard title={title}>
      <ul className="space-y-1">
        {actions.map((a) => {
          const className =
            'flex w-full items-center rounded-lg px-2 py-2 text-left text-sm text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400'
          if (a.href && !a.disabled) {
            return (
              <li key={a.id}>
                <a className={className} href={a.href} title={a.title}>
                  {a.label}
                </a>
              </li>
            )
          }
          return (
            <li key={a.id}>
              <button
                type="button"
                className={className}
                disabled={a.disabled || !a.onClick}
                title={a.title}
                onClick={a.onClick}
              >
                {a.label}
              </button>
            </li>
          )
        })}
      </ul>
    </SectionCard>
  )
}
