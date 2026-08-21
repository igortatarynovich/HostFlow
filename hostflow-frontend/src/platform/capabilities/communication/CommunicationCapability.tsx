import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCommunicationThreads, type CommunicationThread } from '../../../api/communications'
import { useI18n } from '../../../i18n'
import { buildInboxHubPath, buildInboxThreadPath } from '../../../utils/inboxDeepLinks'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

/**
 * Platform surface `communication`. Owner = Communication.
 * Host places this contribution under `platform_slot`. Transport is the
 * Communication public API — not a second Inbox and not a page-local slot.
 */
export function CommunicationCapability(ctx: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const entity = ctx.entity
  const resourceId = String(entity?.resourceId || '').trim()
  const resourceType = String(entity?.resourceType || '').trim()
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!resourceId || !resourceType) return
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const res = await listCommunicationThreads({
          entityType: resourceType,
          entityId: resourceId,
          limit: 20,
          includeArchived: false,
        })
        if (!mounted) return
        setThreads(Array.isArray(res.items) ? res.items : [])
      } catch {
        if (mounted) setThreads([])
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void run()
    return () => {
      mounted = false
    }
  }, [resourceId, resourceType])

  if (!resourceId || !resourceType) return null

  const newest = threads[0] ?? null
  const candidateId = resourceType === 'candidate' ? resourceId : undefined

  return (
    <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" data-capability-id="communication">
      <p className="text-sm font-semibold text-slate-900">
        {t('app.entity_workspace.slot.communication', { defaultValue: 'Коммуникация' })}
      </p>
      <p className="text-sm text-slate-600">
        {loading
          ? t('app.candidates.communication.loading', { defaultValue: 'Загрузка переписки…' })
          : newest
            ? t('app.candidates.communication.linked', {
                defaultValue: 'Переписка по кандидату',
              })
            : t('app.candidates.communication.empty', {
                defaultValue: 'Нет связанной переписки',
              })}
      </p>
      {newest ? (
        <Link
          to={buildInboxThreadPath(newest.id, { candidateId })}
          className="text-sm font-medium text-brand-700 hover:underline"
        >
          {t('app.candidates.communication.open_thread', { defaultValue: 'Открыть в Inbox' })}
        </Link>
      ) : (
        <Link to={buildInboxHubPath({ candidateId })} className="text-sm font-medium text-brand-700 hover:underline">
          {t('app.candidates.communication.open_inbox', { defaultValue: 'Открыть Inbox' })}
        </Link>
      )}
    </div>
  )
}
