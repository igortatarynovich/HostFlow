import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import {
  buildModuleAbsoluteUrl,
  moduleHomePath,
  resolveDeployHost,
  shellLoginUrl,
} from '../platform/deployHosts'

/** Unauthenticated visitor on a module host → shell login with next= back to module. */
export function ModuleHostAuthRedirect() {
  const { t } = useI18n()
  const deployHost = resolveDeployHost()
  const nextPath = moduleHomePath(deployHost)
  const nextAbs = buildModuleAbsoluteUrl(deployHost, nextPath)
  const nextForLogin = nextAbs.startsWith('http') ? nextAbs : `${window.location.origin}${nextAbs}`
  const loginHref = shellLoginUrl(nextForLogin)

  useEffect(() => {
    if (loginHref.startsWith('http') && !loginHref.startsWith(window.location.origin)) {
      window.location.replace(loginHref)
    }
  }, [loginHref])

  if (loginHref.startsWith('http') && !loginHref.startsWith(window.location.origin)) {
    return (
      <div className="grid h-screen place-items-center text-slate-500">{t('common.loading')}</div>
    )
  }

  return <Navigate to={loginHref} replace />
}
