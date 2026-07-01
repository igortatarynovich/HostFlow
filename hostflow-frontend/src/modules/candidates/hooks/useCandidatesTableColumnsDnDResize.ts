import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_COLUMN_ORDER } from '../constants'

type UseCandidatesTableColumnsDnDResizeArgs = {
  visibleCols: Record<string, boolean>
  columnWidthsStorageKey: string
  columnOrderStorageKey: string
}

const DEFAULT_COLUMN_WIDTHS: Record<string, number> = {
  /** Room for inline Call / Email / Open / Tasks under the name link (§2.14). */
  name: 300,
  email: 180,
  phone: 150,
  citizenship: 140,
  vacancy: 180,
  short: 120,
  manager: 160,
  stage: 160,
  risk: 120,
  created: 140,
  firstContact: 140,
  preferredChannel: 150,
  inPoland: 120,
  polandBasis: 220,
  trailerTypes: 160,
  reasons: 200,
  intakeKind: 130,
  is_favorite: 80,
  docsStatus: 140,
  docsOrdered: 140,
  docsValid: 140,
  docsFiles: 120,
}

export function useCandidatesTableColumnsDnDResize({
  visibleCols,
  columnWidthsStorageKey,
  columnOrderStorageKey,
}: UseCandidatesTableColumnsDnDResizeArgs) {
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    try {
      const raw = localStorage.getItem(columnWidthsStorageKey)
      const parsed = raw ? JSON.parse(raw) : {}
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return { ...DEFAULT_COLUMN_WIDTHS, ...parsed }
      }
    } catch {
      /* ignore malformed storage */
    }
    return { ...DEFAULT_COLUMN_WIDTHS }
  })

  useEffect(() => {
    try {
      localStorage.setItem(columnWidthsStorageKey, JSON.stringify(columnWidths))
    } catch {
      /* ignore storage errors */
    }
  }, [columnWidths, columnWidthsStorageKey])

  const [columnOrder, setColumnOrder] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(columnOrderStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed
        }
      }
    } catch {
      /* ignore malformed storage */
    }
    return [...DEFAULT_COLUMN_ORDER]
  })

  useEffect(() => {
    try {
      localStorage.setItem(columnOrderStorageKey, JSON.stringify(columnOrder))
    } catch {
      /* ignore storage errors */
    }
  }, [columnOrder, columnOrderStorageKey])

  const orderedVisibleColumns = useMemo(() => {
    const visible = columnOrder.filter((key) => visibleCols[key])
    const missing = Object.keys(visibleCols).filter((key) => visibleCols[key] && !columnOrder.includes(key))
    return [...visible, ...missing]
  }, [columnOrder, visibleCols])

  const reorderColumns = useCallback((fromKey: string, toKey: string) => {
    if (!fromKey || !toKey || fromKey === toKey) return
    setColumnOrder((prev) => {
      // Совпадает с orderedVisibleColumns: видимые ключи, которых ещё нет в сохранённом порядке
      const missing = Object.keys(visibleCols).filter(
        (key) => visibleCols[key] && !prev.includes(key),
      )
      const order = missing.length ? [...prev, ...missing] : [...prev]
      const fromIdx = order.indexOf(fromKey)
      const toIdx = order.indexOf(toKey)
      if (fromIdx < 0 || toIdx < 0) return prev
      const next = [...order]
      const [moved] = next.splice(fromIdx, 1)
      next.splice(toIdx, 0, moved)
      return next
    })
  }, [visibleCols])

  const [draggingColumn, setDraggingColumn] = useState<string | null>(null)
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null)

  // Состояние для ресайза колонок
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const [resizeStartX, setResizeStartX] = useState<number>(0)
  const [resizeStartWidth, setResizeStartWidth] = useState<number>(0)

  const handleResizeStartState = useCallback((columnKey: string, startX: number) => {
    // only sets local state; actual resize effect handled in hook
    setResizingColumn(columnKey)
    setResizeStartX(startX)
    setResizeStartWidth(columnWidths[columnKey] || DEFAULT_COLUMN_WIDTHS[columnKey] || 150)
  }, [columnWidths])

  useEffect(() => {
    if (!resizingColumn) return

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX
      const newWidth = Math.max(80, resizeStartWidth + diff)
      setColumnWidths((prev) => ({
        ...prev,
        [resizingColumn]: newWidth,
      }))
    }

    const handleMouseUp = () => {
      setResizingColumn(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [resizingColumn, resizeStartX, resizeStartWidth])

  const getColumnWidth = useCallback(
    (columnKey: string): number => columnWidths[columnKey] || DEFAULT_COLUMN_WIDTHS[columnKey] || 150,
    [columnWidths],
  )

  const applyPersistedLayout = useCallback(
    (payload: { order?: string[] | null; widths?: Record<string, number> | null }) => {
      if (payload.order && Array.isArray(payload.order) && payload.order.length > 0) {
        setColumnOrder([...payload.order])
      }
      if (payload.widths && typeof payload.widths === 'object' && !Array.isArray(payload.widths)) {
        setColumnWidths({ ...DEFAULT_COLUMN_WIDTHS, ...payload.widths })
      }
    },
    [],
  )

  const resetColumnLayout = useCallback(() => {
    setColumnOrder([...DEFAULT_COLUMN_ORDER])
    setColumnWidths({ ...DEFAULT_COLUMN_WIDTHS })
    try {
      localStorage.removeItem(columnOrderStorageKey)
      localStorage.removeItem(columnWidthsStorageKey)
    } catch {
      /* ignore */
    }
  }, [columnOrderStorageKey, columnWidthsStorageKey])

  const moveColumnRelative = useCallback(
    (key: string, delta: number) => {
      if (delta !== 1 && delta !== -1) return
      setColumnOrder((prev) => {
        const missing = Object.keys(visibleCols).filter(
          (k) => visibleCols[k] && !prev.includes(k),
        )
        const order = missing.length ? [...prev, ...missing] : [...prev]
        const idx = order.indexOf(key)
        if (idx < 0) return prev
        const ni = idx + delta
        if (ni < 0 || ni >= order.length) return prev
        const next = [...order]
        const [m] = next.splice(idx, 1)
        next.splice(ni, 0, m)
        return next
      })
    },
    [visibleCols],
  )

  return {
    columnOrder,
    columnWidths,
    orderedVisibleColumns,
    getColumnWidth,
    draggingColumn,
    setDraggingColumn,
    dragOverColumn,
    setDragOverColumn,
    reorderColumns,
    handleResizeStart: handleResizeStartState,
    applyPersistedLayout,
    resetColumnLayout,
    moveColumnRelative,
  }
}

