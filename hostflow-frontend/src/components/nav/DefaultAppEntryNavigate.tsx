import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useI18n } from '../../i18n'
import {
  resolveRecruitmentWorkspaceEntryHref,
  resolveRecruitmentWorkspaceEntrySegment,
} from '../../utils/recruitmentWorkspaceEntry'

type DefaultAppEntryNavigateProps = {
  mode: 'href' | 'segment'
  canOpenTasks: boolean
}

export function DefaultAppEntryNavigate({ mode, canOpenTasks }: DefaultAppEntryNavigateProps) {
  const { t } = useI18n()
  const [target, setTarget] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const resolve = mode === 'href' ? resolveRecruitmentWorkspaceEntryHref : resolveRecruitmentWorkspaceEntrySegment
    void resolve(canOpenTasks).then((next) => {
      if (!cancelled) setTarget(next)
    })
    return () => {
      cancelled = true
    }
  }, [canOpenTasks, mode])

  if (!target) {
    return (
      <div className="grid h-screen place-items-center text-sm text-slate-500">
        {t('common.loading', { defaultValue: 'Загрузка…' })}
      </div>
    )
  }

  return <Navigate to={target} replace />
}
