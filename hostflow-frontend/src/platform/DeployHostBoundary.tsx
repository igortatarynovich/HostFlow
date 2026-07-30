import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { ensureSharedSessionCookies } from '../api/client'
import {
  AUTH_HANDOFF_HASH_PREFIX,
  buildModuleAbsoluteUrl,
  locationTargetWithoutAuthHash,
  moduleHomePath,
  resolveDeployHost,
  resolvePathDeployHost,
  type ModuleDeployHost,
} from './deployHosts'

/**
 * Enforce path ↔ host ownership.
 * - Module host + foreign business path → owning module host
 * - Shell + business path → owning module host (shell is not a 6th business module)
 * - Legacy `#hf_auth=` fragments are stripped if still present in the URL
 */
export function DeployHostBoundary({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [blocked, setBlocked] = useState(false)

  const currentHost = useMemo(() => resolveDeployHost(), [location.search])
  const pathOwner = useMemo(() => resolvePathDeployHost(location.pathname), [location.pathname])

  useEffect(() => {
    const businessOnShell = currentHost === 'shell' && Boolean(pathOwner) && pathOwner !== 'shell'
    const foreignOnModule =
      currentHost !== 'shell' &&
      Boolean(pathOwner) &&
      pathOwner !== 'shell' &&
      pathOwner !== currentHost

    if (!businessOnShell && !foreignOnModule) {
      if (typeof window !== 'undefined') {
        const raw = window.location.hash.startsWith('#')
          ? window.location.hash.slice(1)
          : window.location.hash
        if (raw.startsWith(AUTH_HANDOFF_HASH_PREFIX) && window.history.replaceState) {
          window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
        }
      }
      setBlocked(false)
      return
    }

    const targetHost = pathOwner as ModuleDeployHost
    const targetPath = locationTargetWithoutAuthHash(
      location.pathname,
      location.search,
      location.hash,
    )
    const target = buildModuleAbsoluteUrl(targetHost, targetPath)
    const here = `${window.location.pathname}${window.location.search}${window.location.hash}`

    if (target.startsWith('/')) {
      const url = new URL(target, window.location.origin)
      url.searchParams.set('hf_module', targetHost)
      if (url.hash.startsWith(`#${AUTH_HANDOFF_HASH_PREFIX}`)) url.hash = ''
      const next = `${url.pathname}${url.search}${url.hash}`
      if (next !== here) {
        setBlocked(true)
        window.location.replace(next)
      } else {
        setBlocked(false)
      }
      return
    }

    let cancelled = false
    setBlocked(true)
    void (async () => {
      // Cross-subdomain hard nav: mint Domain=.hostflow.cc cookies first.
      const synced = await ensureSharedSessionCookies()
      if (cancelled) return
      if (!synced) {
        // Do not send users to /login?next=module (login↔module loops). Keep work on shell
        // with hf_module so the SPA stays usable until cookies can be minted.
        const url = new URL(targetPath, window.location.origin)
        url.searchParams.set('hf_module', targetHost)
        if (url.hash.startsWith(`#${AUTH_HANDOFF_HASH_PREFIX}`)) url.hash = ''
        window.location.replace(`${url.pathname}${url.search}${url.hash}`)
        return
      }
      window.location.replace(target)
    })()
    return () => {
      cancelled = true
    }
  }, [currentHost, pathOwner, location.pathname, location.search, location.hash])

  if (blocked) {
    return (
      <div className="grid h-screen place-items-center text-sm text-slate-500">
        Redirecting to module…
      </div>
    )
  }

  return <>{children}</>
}

export function useDeployHost(): ModuleDeployHost {
  const location = useLocation()
  return useMemo(() => resolveDeployHost({ search: location.search }), [location.search])
}

export function defaultLandingPathForHost(host: ModuleDeployHost): string {
  return moduleHomePath(host)
}
