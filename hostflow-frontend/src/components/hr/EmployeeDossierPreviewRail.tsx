import { useEffect, useState } from 'react'
import type { HrReviewDocumentRow } from '../../api/workforce'
import { downloadDocumentFile } from '../../api/documents'
import {
  detectPreviewMime,
  guessPreviewable,
  isProbablyHtmlBlob,
  resolveDocumentUrl,
} from '../../modules/documents/documentUtils'
import { useI18n } from '../../i18n'

type Props = {
  doc: HrReviewDocumentRow | null
  onClose: () => void
  className?: string
}

/** Sticky preview rail — document stays visible while HR edits fields on the left. */
export function EmployeeDossierPreviewRail({ doc, onClose, className }: Props) {
  const { t } = useI18n()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewMime, setPreviewMime] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPreviewUrl(null)
    setPreviewMime(null)
    setError(null)
    setLoading(false)

    if (!doc) return

    let cancelled = false
    let localRevoke: (() => void) | null = null

    const load = async () => {
      setLoading(true)
      try {
        const direct = resolveDocumentUrl(doc.open_url || doc.file_url || '')
        if (direct && doc.document_id) {
          try {
            const { blob, filename, contentType } = await downloadDocumentFile(doc.document_id)
            if (cancelled) return
            if (blob && blob.size > 0 && guessPreviewable(contentType, filename)) {
              const looksLikeHtml = await isProbablyHtmlBlob(blob, contentType)
              if (!looksLikeHtml) {
                const objectUrl = URL.createObjectURL(blob)
                localRevoke = () => URL.revokeObjectURL(objectUrl)
                setPreviewUrl(objectUrl)
                setPreviewMime(detectPreviewMime(contentType, filename))
                return
              }
            }
          } catch {
            /* fall through to direct URL */
          }
        }

        if (direct) {
          setPreviewUrl(direct)
          setPreviewMime(direct.toLowerCase().includes('.pdf') ? 'application/pdf' : 'image/*')
          return
        }

        if (doc.document_id) {
          const { blob, filename, contentType } = await downloadDocumentFile(doc.document_id)
          if (cancelled) return
          if (!blob || blob.size === 0) {
            setError(
              t('app.hr.dossier.preview_unavailable', { defaultValue: 'Preview is not available for this file.' }),
            )
            return
          }
          const objectUrl = URL.createObjectURL(blob)
          localRevoke = () => URL.revokeObjectURL(objectUrl)
          setPreviewUrl(objectUrl)
          setPreviewMime(detectPreviewMime(contentType, filename))
          return
        }

        setError(t('app.hr.dossier.preview_no_file', { defaultValue: 'No file uploaded yet.' }))
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : t('common.errors.request_failed'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
      if (localRevoke) localRevoke()
    }
  }, [doc, t])

  return (
    <aside className={className ?? 'hidden min-h-[420px] xl:block'}>
      <div className="sticky top-4 flex max-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.hr.dossier.preview_rail', { defaultValue: 'Document preview' })}
            </p>
            <p className="truncate text-sm font-medium text-slate-900">
              {doc?.label ||
                doc?.document_key ||
                t('app.hr.dossier.preview_empty', { defaultValue: 'Select Preview on a block' })}
            </p>
          </div>
          {doc ? (
            <button type="button" className="btn-secondary btn-xs shrink-0" onClick={onClose}>
              {t('common.actions.close')}
            </button>
          ) : null}
        </div>

        <div className="min-h-[360px] flex-1 overflow-auto bg-slate-100">
          {!doc ? (
            <p className="p-4 text-sm text-slate-500">
              {t('app.hr.dossier.preview_hint', {
                defaultValue: 'Click Preview in a document block to compare the file with the data.',
              })}
            </p>
          ) : loading ? (
            <p className="p-4 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
          ) : error ? (
            <p className="p-4 text-sm text-amber-800">{error}</p>
          ) : previewUrl ? (
            previewMime?.includes('pdf') || previewUrl.toLowerCase().includes('.pdf') ? (
              <iframe
                title={doc.label || doc.document_key}
                src={previewUrl}
                className="h-full min-h-[360px] w-full bg-white"
              />
            ) : (
              <img src={previewUrl} alt="" className="mx-auto block h-auto max-h-full w-full object-contain" />
            )
          ) : null}
        </div>
      </div>
    </aside>
  )
}
