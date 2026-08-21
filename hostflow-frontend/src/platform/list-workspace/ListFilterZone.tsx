import { useEffect, useState, type ChangeEvent } from 'react'

import { Chip } from '../../components/ui/Chip'
import { Input } from '../../components/ui/Input'
import { filterUrlKey } from './queryState'
import type { ListDefinition, ListQueryState } from './types'

type ListFilterZoneProps<T> = {
  definition: ListDefinition<T>
  query: ListQueryState
  onFilter: (urlKey: string, value: string) => void
}

export function ListFilterZone<T>({ definition, query, onFilter }: ListFilterZoneProps<T>) {
  const filters = definition.filters ?? []
  if (filters.length === 0) return null
  return (
    <>
      {filters.map((filter) => {
        const key = filterUrlKey(filter)
        const value = query.filters[key] ?? ''
        if (filter.widget === 'chips') {
          return (filter.options ?? []).map((option) => (
            <Chip
              key={`${key}:${option.value || 'all'}`}
              behavior="selectable"
              size="md"
              selected={value === option.value}
              selectedAppearance="soft"
              label={option.label}
              onClick={() => onFilter(key, option.value)}
            />
          ))
        }
        return (
          <DebouncedTextFilter
            key={key}
            value={value}
            placeholder={filter.placeholder ?? filter.label}
            onCommit={(next) => onFilter(key, next)}
          />
        )
      })}
    </>
  )
}

function DebouncedTextFilter({
  value,
  placeholder,
  onCommit,
}: {
  value: string
  placeholder: string
  onCommit: (value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  useEffect(() => {
    setDraft(value)
  }, [value])
  useEffect(() => {
    if (draft === value) return
    const timer = window.setTimeout(() => onCommit(draft), 300)
    return () => window.clearTimeout(timer)
  }, [draft, onCommit, value])

  return (
    <Input
      value={draft}
      placeholder={placeholder}
      className="min-h-[40px] w-48 py-2 text-sm"
      onChange={(event: ChangeEvent<HTMLInputElement>) => setDraft(event.currentTarget.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          event.preventDefault()
          onCommit(draft)
        }
      }}
    />
  )
}
