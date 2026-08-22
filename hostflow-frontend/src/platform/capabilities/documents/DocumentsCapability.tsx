import { useEffect, useState } from 'react'
import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'
import {
  DOCUMENTS_HUB_ADAPTER_ID,
  DOCUMENTS_PUBLIC_CONTRACT_ID,
  listLinkedDocuments,
  type DocumentHubView,
} from './documentsOwner'

/**
 * Platform surface `documents`. Owner = Documents.
 * Host places this contribution under `platform_slot`. Consume path is
 * `documents.public_contract.v1` / `documents.hub_adapter_v1` via Document Link.
 * Not the local HR documents matrix. Not Shell nav. Not Candidate `candidate_id`.
 */
export function DocumentsCapability(ctx: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const [items, setItems] = useState<DocumentHubView[]>([])
  const [loading, setLoading] = useState(false)
  const [available, setAvailable] = useState(false)

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const result = await listLinkedDocuments(ctx)
        if (!mounted) return
        setAvailable(result.available)
        setItems(result.items)
      } catch {
        if (mounted) {
          setAvailable(false)
          setItems([])
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void run()
    return () => {
      mounted = false
    }
  }, [ctx.entity?.resourceType, ctx.entity?.resourceId])

  return (
    <div
      className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      data-capability-id="documents"
      data-public-contract={DOCUMENTS_PUBLIC_CONTRACT_ID}
      data-adapter-id={DOCUMENTS_HUB_ADAPTER_ID}
    >
      <p className="text-sm font-semibold text-slate-900">
        {t('app.entity_workspace.slot.documents', { defaultValue: 'Документы' })}
      </p>
      <p className="text-sm text-slate-600">
        {loading
          ? t('app.hr.employee_detail.documents.loading', { defaultValue: 'Загрузка документов…' })
          : !available
            ? t('app.hr.employee_detail.documents.unbound', {
                defaultValue: 'Документы на этой поверхности идут через Document Link',
              })
            : items.length
              ? t('app.hr.employee_detail.documents.bound', {
                  defaultValue: '{count} документ(ов) по Document Link',
                  values: { count: items.length },
                })
              : t('app.hr.employee_detail.documents.empty', {
                  defaultValue: 'Нет связанных документов Document Hub',
                })}
      </p>
      {!loading && items.length > 0 ? (
        <ul className="space-y-1 text-sm text-slate-700">
          {items.slice(0, 8).map((row) => (
            <li key={row.id}>
              <span className="font-medium text-slate-900">{row.title || row.doc_type}</span>
              {row.status ? <span className="text-slate-500"> · {row.status}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
