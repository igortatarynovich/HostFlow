import { useNavigate } from 'react-router-dom'
import { IconChevronLeft } from '@tabler/icons-react'

import { useI18n } from '../../i18n'

/**
 * Slim history back control under the top bar.
 * Replaces the retired global WorkContextTabs strip — primary nav lives in the sidebar.
 */
export default function WorkspaceBackBar() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const label = t('common.actions.back', { defaultValue: 'Back' })

  return (
    <div className="sticky top-0 z-20 shrink-0 border-b border-slate-200 bg-slate-50/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-slate-50/80 sm:px-4 lg:px-8">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-white hover:text-slate-900"
        aria-label={label}
        data-testid="workspace-back"
      >
        <IconChevronLeft size={18} stroke={1.9} aria-hidden />
        {label}
      </button>
    </div>
  )
}
