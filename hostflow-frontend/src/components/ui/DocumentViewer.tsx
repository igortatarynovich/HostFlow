import { Button } from './Button'

/** System preview for a file the caller already resolved (Hub download or equivalent). */
export function DocumentViewer({
  open,
  url,
  contentType,
  title,
  closeLabel,
  onClose,
}: {
  open: boolean
  url: string | null
  contentType: string | null
  title: string
  closeLabel: string
  onClose: () => void
}) {
  if (!open || !url) return null
  const pdf = Boolean(contentType?.includes('pdf') || url.toLowerCase().endsWith('.pdf'))
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-3 sm:p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="flex h-[min(90vh,920px)] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 px-3 py-1.5">
          <div className="truncate text-sm font-medium text-slate-800">{title}</div>
          <Button type="button" variant="secondary" size="compact" onClick={onClose}>
            {closeLabel}
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto bg-slate-50">
          {pdf ? (
            <iframe title={title} src={url} className="h-full min-h-[70vh] w-full" />
          ) : (
            <img src={url} alt="" className="mx-auto block h-auto max-h-full min-h-0 w-auto max-w-full object-contain" />
          )}
        </div>
      </div>
    </div>
  )
}
