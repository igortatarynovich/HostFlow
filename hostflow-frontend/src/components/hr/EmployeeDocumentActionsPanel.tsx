import { useEffect, useState } from 'react'
import { getSummary } from '../../api/documents/summary'
import type { ReminderWorkQueueItem } from '../../api/types'
import { DocumentActionsPanel } from './DocumentActionsPanel'

type Props = {
  candidateId: string
  ownerContext?: Record<string, unknown> | null
}

export function EmployeeDocumentActionsPanel({ candidateId, ownerContext }: Props) {
  const [items, setItems] = useState<ReminderWorkQueueItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await getSummary(candidateId, {
          context: ownerContext || undefined,
          fillMissing: false,
        })
        if (!cancelled) {
          setItems(response.summary.reminder_work_queue || [])
        }
      } catch {
        if (!cancelled) {
          setItems(null)
          setError('Could not load document actions')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [candidateId, ownerContext])

  return <DocumentActionsPanel items={items} loading={loading} error={error} />
}
