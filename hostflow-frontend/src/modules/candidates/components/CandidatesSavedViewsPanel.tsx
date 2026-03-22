import type { UserSavedView } from '../../../api/types'

type CandidatesSavedViewsPanelProps = {
  t: (key: string, options?: any) => string
  savedViews: UserSavedView[]
  onApplyView: (view: UserSavedView) => void
  onDeleteView: (id: string) => void
}

export function CandidatesSavedViewsPanel({ t, savedViews, onApplyView, onDeleteView }: CandidatesSavedViewsPanelProps) {
  if (savedViews.length === 0) return null

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="relative">
        <div className="text-xs font-semibold text-slate-600 pb-2 border-b border-slate-200 uppercase tracking-wide" title={t('app.candidates.views.manage_title')}>
          {t('app.candidates.views.toggle', { defaultValue: 'Views' })}
        </div>
        <div className="mt-3 space-y-1.5 max-h-64 overflow-auto">
          {savedViews.map((v) => (
            <div key={v.id} className="flex items-center justify-between gap-1.5 p-1.5 rounded-md hover:bg-slate-50 transition-colors">
              <button
                className="btn-secondary text-left justify-start flex-1 truncate text-xs font-medium px-1.5 py-1"
                title={t('app.candidates.views.apply_title', { values: { name: v.name } })}
                onClick={() => onApplyView(v)}
              >
                {v.name}
              </button>
              <button
                className="btn-danger btn-xs"
                title={t('app.candidates.views.delete_title')}
                onClick={(e) => {
                  e.preventDefault()
                  onDeleteView(v.id)
                }}
              >
                ×
              </button>
            </div>
          ))}
          {savedViews.length === 0 && <div className="text-[10px] text-slate-400 text-center py-3">{t('app.candidates.views.empty')}</div>}
        </div>
      </div>
    </div>
  )
}
