import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import {
  buildModuleAbsoluteUrl,
  DEPLOYMENT_HOSTS,
  moduleHomePath,
  resolveDeployHost,
  shellLoginUrl,
} from '../platform/deployHosts'

const BOUNCE_NEXT_KEY = 'hf:module_auth_bounce_next'
const BOUNCE_TS_KEY = 'hf:module_auth_bounce_ts'
const BOUNCE_WINDOW_MS = 45_000

/** Unauthenticated visitor on a module host → shell login with next= back to module. */
export function ModuleHostAuthRedirect() {
  const { t } = useI18n()
  const deployHost = resolveDeployHost()
  const nextPath = moduleHomePath(deployHost)
  const nextAbs = buildModuleAbsoluteUrl(deployHost, nextPath)
  const nextForLogin = nextAbs.startsWith('http') ? nextAbs : `${window.location.origin}${nextAbs}`
  let loginHref = shellLoginUrl(nextForLogin)

  // Break login↔module reload loops when Domain cookies never stick on the module host.
  try {
    const prevNext = sessionStorage.getItem(BOUNCE_NEXT_KEY)
    const prevTs = Number(sessionStorage.getItem(BOUNCE_TS_KEY) || 0)
    if (prevNext === nextForLogin && Date.now() - prevTs < BOUNCE_WINDOW_MS) {
      sessionStorage.removeItem(BOUNCE_NEXT_KEY)
      sessionStorage.removeItem(BOUNCE_TS_KEY)
      const shellOrigin =
        typeof window !== 'undefined' &&
        (window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1' ||
          window.location.hostname.endsWith('.local'))
          ? window.location.origin
          : `${window.location.protocol}//${DEPLOYMENT_HOSTS.shell}`
      loginHref = `${shellOrigin}/login`
    } else {
      sessionStorage.setItem(BOUNCE_NEXT_KEY, nextForLogin)
      sessionStorage.setItem(BOUNCE_TS_KEY, String(Date.now()))
    }
  } catch {
    // sessionStorage may be unavailable
  }

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
