import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useI18n } from '../../i18n'
import {
  resolveRecruitmentWorkspaceEntryHref,
  resolveRecruitmentWorkspaceEntrySegment,
} from '../../utils/recruitmentWorkspaceEntry'
import { crmAppRouteSegment } from '../../app/crmAppPaths'
import { isShellDeployHost, moduleHomePath, resolveDeployHost } from '../../platform/deployHosts'

type DefaultAppEntryNavigateProps = {
  mode: 'href' | 'segment'
  canOpenTasks: boolean
}

export function DefaultAppEntryNavigate({ mode, canOpenTasks }: DefaultAppEntryNavigateProps) {
  const { t } = useI18n()
  const [target, setTarget] = useState<string | null>(null)
  const deployHost = resolveDeployHost()

  useEffect(() => {
    let cancelled = false

    if (!isShellDeployHost(deployHost)) {
      const home = moduleHomePath(deployHost)
      const next = mode === 'segment' ? crmAppRouteSegment(home) || home.replace(/^\/app\/?/, '') : home
      if (!cancelled) setTarget(next)
      return () => {
        cancelled = true
      }
    }

    const resolve = mode === 'href' ? resolveRecruitmentWorkspaceEntryHref : resolveRecruitmentWorkspaceEntrySegment
    void resolve(canOpenTasks).then((next) => {
      if (!cancelled) setTarget(next)
    })
    return () => {
      cancelled = true
    }
  }, [canOpenTasks, mode, deployHost])

  if (!target) {
    return (
      <div className="grid h-screen place-items-center text-sm text-slate-500">
        {t('common.loading', { defaultValue: 'Загрузка…' })}
      </div>
    )
  }

  return <Navigate to={target} replace />
}
