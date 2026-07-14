import { useCallback, useMemo, useState } from 'react'

export type UseEntityListSelectionOptions = {
  pageRowIds: string[]
}

export function useEntityListSelection({ pageRowIds }: UseEntityListSelectionOptions) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())

  const toggleRow = useCallback((id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }, [])

  const togglePage = useCallback(
    (checked: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        for (const id of pageRowIds) {
          if (checked) next.add(id)
          else next.delete(id)
        }
        return next
      })
    },
    [pageRowIds],
  )

  const clearSelection = useCallback(() => setSelectedIds(new Set()), [])

  const pageAllSelected = useMemo(
    () => pageRowIds.length > 0 && pageRowIds.every((id) => selectedIds.has(id)),
    [pageRowIds, selectedIds],
  )

  const pageSomeSelected = useMemo(
    () => pageRowIds.some((id) => selectedIds.has(id)) && !pageAllSelected,
    [pageRowIds, selectedIds, pageAllSelected],
  )

  const isRowSelected = useCallback((id: string) => selectedIds.has(id), [selectedIds])

  return {
    selectedIds,
    selectedCount: selectedIds.size,
    toggleRow,
    togglePage,
    clearSelection,
    pageAllSelected,
    pageSomeSelected,
    isRowSelected,
  }
}
