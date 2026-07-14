import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ColumnVisibilityState, ResourceSchema } from './types'

const FALLBACK_WIDTH = 150

export type UseDataTableColumnLayoutArgs = {
  schema: ResourceSchema
  visibilityStorageKey: string
  orderStorageKey: string
  widthsStorageKey: string
}

function defaultVisibility(schema: ResourceSchema): ColumnVisibilityState {
  const vis: ColumnVisibilityState = {}
  for (const field of schema.fields) {
    vis[field.id] = schema.defaultVisibleFieldIds.includes(field.id)
  }
  return vis
}

function defaultWidths(schema: ResourceSchema): Record<string, number> {
  const widths: Record<string, number> = { ...(schema.defaultColumnWidths ?? {}) }
  for (const field of schema.fields) {
    if (field.defaultWidth != null) widths[field.id] = field.defaultWidth
  }
  return widths
}

export function useDataTableColumnLayout({
  schema,
  visibilityStorageKey,
  orderStorageKey,
  widthsStorageKey,
}: UseDataTableColumnLayoutArgs) {
  const defaultVis = useMemo(() => defaultVisibility(schema), [schema])
  const defaultOrder = useMemo(() => [...schema.defaultFieldOrder], [schema])
  const defaultWidthMap = useMemo(() => defaultWidths(schema), [schema])

  const [visibility, setVisibilityState] = useState<ColumnVisibilityState>(() => {
    try {
      const raw = localStorage.getItem(visibilityStorageKey)
      const parsed = raw ? JSON.parse(raw) : null
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return { ...defaultVis, ...parsed }
      }
    } catch {
      /* ignore */
    }
    return { ...defaultVis }
  })

  useEffect(() => {
    try {
      const raw = localStorage.getItem(visibilityStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          setVisibilityState({ ...defaultVis, ...parsed })
          return
        }
      }
    } catch {
      /* ignore */
    }
    setVisibilityState({ ...defaultVis })
  }, [defaultVis, visibilityStorageKey])

  const persistVisibility = useCallback(
    (next: ColumnVisibilityState) => {
      setVisibilityState(next)
      try {
        localStorage.setItem(visibilityStorageKey, JSON.stringify(next))
      } catch {
        /* ignore */
      }
    },
    [visibilityStorageKey],
  )

  const [widths, setWidths] = useState<Record<string, number>>(() => {
    try {
      const raw = localStorage.getItem(widthsStorageKey)
      const parsed = raw ? JSON.parse(raw) : null
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return { ...defaultWidthMap, ...parsed }
      }
    } catch {
      /* ignore */
    }
    return { ...defaultWidthMap }
  })

  useEffect(() => {
    try {
      localStorage.setItem(widthsStorageKey, JSON.stringify(widths))
    } catch {
      /* ignore */
    }
  }, [widths, widthsStorageKey])

  const [order, setOrder] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(orderStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed
      }
    } catch {
      /* ignore */
    }
    return [...defaultOrder]
  })

  useEffect(() => {
    try {
      localStorage.setItem(orderStorageKey, JSON.stringify(order))
    } catch {
      /* ignore */
    }
  }, [order, orderStorageKey])

  const orderedVisibleFieldIds = useMemo(() => {
    const visible = order.filter((id) => visibility[id])
    const missing = schema.fields.map((f) => f.id).filter((id) => visibility[id] && !order.includes(id))
    return [...visible, ...missing]
  }, [order, visibility, schema.fields])

  const reorderFields = useCallback(
    (fromId: string, toId: string) => {
      if (!fromId || !toId || fromId === toId) return
      setOrder((prev) => {
        const missing = schema.fields.map((f) => f.id).filter((id) => visibility[id] && !prev.includes(id))
        const nextOrder = missing.length ? [...prev, ...missing] : [...prev]
        const fromIdx = nextOrder.indexOf(fromId)
        const toIdx = nextOrder.indexOf(toId)
        if (fromIdx < 0 || toIdx < 0) return prev
        const next = [...nextOrder]
        const [moved] = next.splice(fromIdx, 1)
        next.splice(toIdx, 0, moved)
        return next
      })
    },
    [schema.fields, visibility],
  )

  const moveFieldRelative = useCallback(
    (fieldId: string, delta: -1 | 1) => {
      setOrder((prev) => {
        const missing = schema.fields.map((f) => f.id).filter((id) => visibility[id] && !prev.includes(id))
        const nextOrder = missing.length ? [...prev, ...missing] : [...prev]
        const idx = nextOrder.indexOf(fieldId)
        if (idx < 0) return prev
        const ni = idx + delta
        if (ni < 0 || ni >= nextOrder.length) return prev
        const next = [...nextOrder]
        const [m] = next.splice(idx, 1)
        next.splice(ni, 0, m)
        return next
      })
    },
    [schema.fields, visibility],
  )

  const [draggingFieldId, setDraggingFieldId] = useState<string | null>(null)
  const [dragOverFieldId, setDragOverFieldId] = useState<string | null>(null)
  const [resizingFieldId, setResizingFieldId] = useState<string | null>(null)
  const [resizeStartX, setResizeStartX] = useState(0)
  const [resizeStartWidth, setResizeStartWidth] = useState(0)

  const getFieldWidth = useCallback(
    (fieldId: string) => widths[fieldId] ?? defaultWidthMap[fieldId] ?? FALLBACK_WIDTH,
    [widths, defaultWidthMap],
  )

  const handleResizeStart = useCallback(
    (fieldId: string, clientX: number) => {
      setResizingFieldId(fieldId)
      setResizeStartX(clientX)
      setResizeStartWidth(getFieldWidth(fieldId))
    },
    [getFieldWidth],
  )

  useEffect(() => {
    if (!resizingFieldId) return
    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX
      const newWidth = Math.max(80, resizeStartWidth + diff)
      setWidths((prev) => ({ ...prev, [resizingFieldId]: newWidth }))
    }
    const handleMouseUp = () => setResizingFieldId(null)
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
  }, [resizingFieldId, resizeStartX, resizeStartWidth])

  const resetLayout = useCallback(() => {
    setOrder([...defaultOrder])
    setWidths({ ...defaultWidthMap })
    persistVisibility({ ...defaultVis })
    try {
      localStorage.removeItem(orderStorageKey)
      localStorage.removeItem(widthsStorageKey)
      localStorage.removeItem(visibilityStorageKey)
    } catch {
      /* ignore */
    }
  }, [defaultOrder, defaultWidthMap, defaultVis, orderStorageKey, widthsStorageKey, visibilityStorageKey, persistVisibility])

  const applyPersistedLayout = useCallback(
    (payload: { order?: string[] | null; widths?: Record<string, number> | null; visibility?: ColumnVisibilityState | null }) => {
      if (payload.order?.length) setOrder([...payload.order])
      if (payload.widths && typeof payload.widths === 'object') {
        setWidths({ ...defaultWidthMap, ...payload.widths })
      }
      if (payload.visibility && typeof payload.visibility === 'object') {
        persistVisibility({ ...defaultVis, ...payload.visibility })
      }
    },
    [defaultWidthMap, defaultVis, persistVisibility],
  )

  const toggleFieldVisible = useCallback(
    (fieldId: string, visible: boolean) => {
      persistVisibility({ ...visibility, [fieldId]: visible })
    },
    [persistVisibility, visibility],
  )

  return {
    visibility,
    order,
    widths,
    orderedVisibleFieldIds,
    getFieldWidth,
    setVisibility: persistVisibility,
    toggleFieldVisible,
    reorderFields,
    moveFieldRelative,
    handleResizeStart,
    resetLayout,
    applyPersistedLayout,
    draggingFieldId,
    setDraggingFieldId,
    dragOverFieldId,
    setDragOverFieldId,
  }
}
